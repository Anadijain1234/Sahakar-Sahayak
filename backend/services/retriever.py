"""
Sahakar Sahayak -- document search (retriever).

How it works, in simple words:
1. On startup, every PDF in backend/data/documents is cut into small
   pieces of about one paragraph each (~800 letters), instead of one
   whole page per piece.
2. Two kinds of matching are done for every question:
   - WORD match  : exact words, good for "PMFBY", "72 hours", "Section 6".
   - PART match  : small 3-letter parts of words, so "kishan", "kisaan"
                   and "kisan" still match each other. No dictionary needed.
   - MEANING match (Cloudflare Workers AI, model bge-m3): finds pieces
                   that mean the same thing even with different words,
                   e.g. "crop spoiled in rain, whom to tell" -> crop-loss
                   reporting rules. Needs CLOUDFLARE_ACCOUNT_ID and
                   CLOUDFLARE_API_TOKEN in the environment. If they are
                   missing or Cloudflare is down, search quietly keeps
                   working with the two word-based matches only.
3. The scores are mixed, and the best 6 pieces are returned.
4. Each piece gets a real score from 0 to 1 = how many of the important
   words in the question were found in that piece (exactly or closely).
   If even the best piece scores too low, nothing is returned, and the
   answer step falls back to Sarvam's general knowledge.

No AI model runs on this server (Cloudflare does the meaning part), so it
stays small in memory (safe for Render's 512MB plan). The cut-up pieces
and their meaning-numbers are saved to files, so a restart doesn't
re-read the PDFs or call Cloudflare again.
"""

import os
import re
import json
import math
from array import array
from collections import Counter, defaultdict

import numpy as np
import requests
from pypdf import PdfReader

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS_DIR = os.path.join(BASE_DIR, "backend", "data", "documents")
if not os.path.exists(DOCS_DIR):
    DOCS_DIR = "/workspaces/Sahakar-Sahayak/backend/data/documents"
METADATA_PATH = os.path.join(BASE_DIR, "backend", "data", "metadata.json")
CACHE_PATH = os.path.join(BASE_DIR, "backend", "data", "chunks_cache.json")
EMB_PATH = os.path.join(BASE_DIR, "backend", "data", "embeddings.npy")
EMB_META_PATH = os.path.join(BASE_DIR, "backend", "data", "embeddings_meta.json")

CF_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
CF_MODEL = "@cf/baai/bge-m3"

# ---- Settings you can tune ----
CHUNK_SIZE = 800        # letters per piece (about one paragraph)
CHUNK_OVERLAP = 150     # letters shared between neighbouring pieces, so no answer is cut in half
MIN_RESULTS = 6         # always return at least this many pieces (if they pass the score check)
MIN_SCORE = 0.50        # below this, the best piece isn't good enough -> use general knowledge
WORD_WEIGHT = 0.6       # how much exact-word match counts (inside the word search)
PART_WEIGHT = 0.4       # how much part-of-word match counts (inside the word search)
MEANING_WEIGHT = 0.5    # how much meaning search counts vs word search when ranking
MEANING_LOW = 0.45      # Cloudflare similarity at/below this = "not related" (score 0)
MEANING_HIGH = 0.75     # Cloudflare similarity at/above this = "very related" (score 1)
EMBED_BATCH = 50        # pieces sent to Cloudflare per request when building
QUERY_TIMEOUT = 4       # seconds to wait for Cloudflare per question
CACHE_VERSION = 2

STOPWORDS = {
    "the", "and", "for", "are", "was", "were", "with", "that", "this", "from", "what",
    "which", "who", "whom", "how", "when", "where", "why", "can", "does", "did", "has",
    "have", "had", "will", "shall", "should", "would", "could", "may", "might", "must",
    "any", "all", "not", "but", "into", "onto", "under", "over", "about", "there",
    "their", "they", "them", "then", "than", "these", "those", "its", "his", "her",
    "our", "your", "you", "also", "such", "each", "other", "more", "most", "some",
    "being", "been", "per", "within", "many", "much", "tell", "please", "get", "give",
}

# ---- In-memory search index ----
chunks = []            # list of {"document", "page", "text"}
_word_index = None
_part_index = None
_vectors = None        # numpy matrix: one row of meaning-numbers per piece (or None)
documents_metadata = chunks   # kept for older code that imports this name


def tokenize(text: str) -> list:
    """Split text into lowercase words (letters/numbers), dropping tiny and common words."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return [w for w in cleaned.split() if len(w) > 2 and w not in STOPWORDS]


def word_parts(word: str) -> list:
    """Cut a word into overlapping 3-letter parts: 'kisan' -> '#ki','kis','isa','san','an#'."""
    w = f"#{word}#"
    return [w[i:i + 3] for i in range(len(w) - 2)]


def part_tokens(text: str) -> list:
    parts = []
    for w in tokenize(text):
        parts.extend(word_parts(w))
    return parts


class _BM25:
    """Small, memory-friendly BM25 search (the standard keyword-ranking formula).
    It only stores, for each term, which pieces contain it and how often."""

    def __init__(self, tokenized_docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.n = len(tokenized_docs)
        self.doc_len = [len(d) for d in tokenized_docs]
        self.avg_len = (sum(self.doc_len) / self.n) if self.n else 1.0
        # term -> (array of piece ids, array of counts). Compact number arrays
        # instead of Python tuples keep memory low on Render's 512MB plan.
        ids, counts = defaultdict(lambda: array("I")), defaultdict(lambda: array("H"))
        for doc_id, toks in enumerate(tokenized_docs):
            for term, count in Counter(toks).items():
                ids[term].append(doc_id)
                counts[term].append(min(count, 65535))
        self.postings = {t: (ids[t], counts[t]) for t in ids}
        self.idf = {
            t: math.log(1 + (self.n - len(p[0]) + 0.5) / (len(p[0]) + 0.5))
            for t, p in self.postings.items()
        }

    def scores(self, query_tokens) -> dict:
        out = defaultdict(float)
        for term in set(query_tokens):
            plist = self.postings.get(term)
            if not plist:
                continue
            idf = self.idf[term]
            for doc_id, tf in zip(*plist):
                denom = tf + self.k1 * (1 - self.b + self.b * self.doc_len[doc_id] / self.avg_len)
                out[doc_id] += idf * tf * (self.k1 + 1) / denom
        return out


def _split_into_pieces(text: str) -> list:
    """Cut one page of text into ~CHUNK_SIZE-letter pieces, ending at a sentence
    break where possible, with a small overlap between pieces."""
    text = " ".join(text.split())
    if len(text) <= CHUNK_SIZE:
        return [text] if len(text) > 60 else []

    pieces, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            # Try to stop at the end of a sentence in the last part of the window
            cut = max(text.rfind(". ", start + CHUNK_SIZE // 2, end),
                      text.rfind("; ", start + CHUNK_SIZE // 2, end))
            if cut != -1:
                end = cut + 1
        piece = text[start:end].strip()
        if len(piece) > 60:
            pieces.append(piece)
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return pieces


def _docs_signature() -> list:
    """A fingerprint of the PDF folder (names + sizes), used to know if the cache is still valid."""
    files = sorted(f for f in os.listdir(DOCS_DIR) if f.lower().endswith(".pdf"))
    return [CACHE_VERSION, CHUNK_SIZE, CHUNK_OVERLAP] + [
        [f, os.path.getsize(os.path.join(DOCS_DIR, f))] for f in files
    ]


def _read_all_pdfs() -> list:
    result = []
    pdf_files = sorted(f for f in os.listdir(DOCS_DIR) if f.lower().endswith(".pdf"))
    for pdf_name in pdf_files:
        try:
            reader = PdfReader(os.path.join(DOCS_DIR, pdf_name))
            for page_idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                for piece in _split_into_pieces(page_text):
                    result.append({"document": pdf_name, "page": page_idx + 1, "text": piece})
        except Exception as e:
            print(f"Error reading {pdf_name}: {e}")
    return result


def build_or_load_index():
    """Load pieces from the cache if the PDFs haven't changed, otherwise re-read the
    PDFs, then build the two search indexes in memory."""
    global chunks, documents_metadata, _word_index, _part_index

    if not os.path.exists(DOCS_DIR):
        print(f"❌ Documents directory not found: {DOCS_DIR}")
        return

    signature = _docs_signature()
    loaded = None
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("signature") == signature:
            loaded = cache["chunks"]
            print(f"📦 Loaded {len(loaded)} pieces from cache.")
    except Exception:
        pass

    if loaded is None:
        loaded = _read_all_pdfs()
        try:
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump({"signature": signature, "chunks": loaded}, f, ensure_ascii=False)
            with open(METADATA_PATH, "w", encoding="utf-8") as f:
                json.dump(loaded, f, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Could not save search cache: {e}")

    if not loaded:
        print("❌ No readable text pieces found in PDFs.")
        return

    chunks = loaded
    documents_metadata = chunks
    _word_index = _BM25([tokenize(c["text"]) for c in chunks])
    _part_index = _BM25([part_tokens(c["text"]) for c in chunks])
    import gc; gc.collect()
    _load_or_build_vectors(signature)
    print(f"✅ Search index ready ({len(chunks)} pieces from {len(set(c['document'] for c in chunks))} PDFs).")

# ---------------------------------------------------------------------------
# Meaning search (Cloudflare Workers AI embeddings)
# ---------------------------------------------------------------------------
def _cf_enabled() -> bool:
    return bool(CF_ACCOUNT_ID and CF_API_TOKEN)


def _embed(texts: list, timeout: float) -> np.ndarray:
    """Send texts to Cloudflare and get back one row of meaning-numbers per text.
    Raises on any failure."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{CF_MODEL}"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
        json={"text": texts},
        timeout=timeout,
    )
    body = resp.json()
    if resp.status_code != 200 or not body.get("success", False):
        raise RuntimeError(f"Cloudflare HTTP {resp.status_code}: {str(body.get('errors'))[:300]}")
    result = body.get("result") or {}
    data = result.get("data") if isinstance(result, dict) else None
    if data is None and isinstance(result, dict):
        data = result.get("response")
    if data and isinstance(data[0], dict):
        data = [d.get("embedding") or d.get("values") for d in data]
    if not data or len(data) != len(texts):
        raise RuntimeError(f"Unexpected Cloudflare response shape: {str(result)[:300]}")
    vecs = np.asarray(data, dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.maximum(norms, 1e-8)


def _load_or_build_vectors(signature) -> None:
    """Load saved meaning-numbers if they match the current PDFs, otherwise
    ask Cloudflare for them (once) and save them."""
    global _vectors
    _vectors = None
    if not _cf_enabled():
        print("ℹ️ Meaning search OFF (no CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN). Word search only.")
        return

    wanted = {"signature": signature, "model": CF_MODEL, "count": len(chunks)}
    try:
        with open(EMB_META_PATH, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if meta == wanted and os.path.exists(EMB_PATH):
            mat = np.load(EMB_PATH).astype(np.float32)
            if mat.shape[0] == len(chunks):
                _vectors = mat
                print(f"📦 Loaded meaning search data for {len(chunks)} pieces.")
                return
    except Exception:
        pass

    print(f"🧠 Building meaning search data with Cloudflare for {len(chunks)} pieces (one time)...")
    try:
        rows = []
        for i in range(0, len(chunks), EMBED_BATCH):
            batch = [c["text"] for c in chunks[i:i + EMBED_BATCH]]
            for attempt in range(3):
                try:
                    rows.append(_embed(batch, timeout=60))
                    break
                except Exception:
                    if attempt == 2:
                        raise
        mat = np.vstack(rows)
        np.save(EMB_PATH, mat.astype(np.float16))
        with open(EMB_META_PATH, "w", encoding="utf-8") as f:
            json.dump(wanted, f)
        _vectors = mat
        print(f"✅ Meaning search ready ({mat.shape[0]} pieces, {mat.shape[1]} numbers each).")
    except Exception as e:
        print(f"⚠️ Meaning search OFF -- could not build it: {e}")
        _vectors = None


def _meaning_scores(query: str) -> dict:
    """piece id -> 0..1 meaning score for this question. Empty if meaning search is off or fails."""
    if _vectors is None:
        return {}
    try:
        q = _embed([query], timeout=QUERY_TIMEOUT)[0]
    except Exception as e:
        print(f"[RETRIEVER] ⚠️ Meaning search skipped for this question: {e}")
        return {}
    sims = _vectors @ q
    top = np.argsort(-sims)[:40]
    span = MEANING_HIGH - MEANING_LOW
    return {int(i): float(min(1.0, max(0.0, (sims[i] - MEANING_LOW) / span))) for i in top}


def _similar(a: str, b: str) -> bool:
    """True if two words are close spellings of each other (share most of their 3-letter parts)."""
    if a == b:
        return True
    if len(a) < 5 or len(b) < 5:
        return False          # short words must match exactly (avoids "cup" ~ "cap")
    if abs(len(a) - len(b)) > 3:
        return False
    pa, pb = set(word_parts(a)), set(word_parts(b))
    return len(pa & pb) / len(pa | pb) >= 0.5


def _match_score(query_words: list, text: str) -> float:
    """0 to 1: how many of the question's important words appear in this piece.
    An exact match counts fully, a close spelling counts 0.8."""
    if not query_words:
        return 0.0
    piece_words = set(tokenize(text))
    total = 0.0
    for qw in query_words:
        if qw in piece_words:
            total += 1.0
        elif any(_similar(qw, pw) for pw in piece_words):
            total += 0.8
    return total / len(query_words)


def _normalise(score_map: dict) -> dict:
    if not score_map:
        return {}
    top = max(score_map.values()) or 1.0
    return {k: v / top for k, v in score_map.items()}


def retrieve_documents(query: str, top_k: int = 3, threshold: float = MIN_SCORE) -> list:
    """Find the best-matching PDF pieces for a question.
    Returns a list of {"document", "page", "text", "similarity_score"} (score 0-1),
    or an empty list if nothing matches well enough."""
    if _word_index is None:
        build_or_load_index()
    if _word_index is None or not chunks:
        return []

    top_k = max(top_k, MIN_RESULTS)
    query_words = list(dict.fromkeys(tokenize(query)))   # unique, in order
    if not query_words:
        return []

    word_scores = _normalise(_word_index.scores(query_words))
    part_scores = _normalise(_part_index.scores(part_tokens(query)))
    meaning = _meaning_scores(query)          # {} if Cloudflare is off/unavailable

    word_rank = {}
    for doc_id in set(word_scores) | set(part_scores):
        word_rank[doc_id] = WORD_WEIGHT * word_scores.get(doc_id, 0.0) + PART_WEIGHT * part_scores.get(doc_id, 0.0)

    # Shortlist = best by word search + best by meaning search
    shortlist = set(sorted(word_rank, key=word_rank.get, reverse=True)[: top_k * 3])
    shortlist |= set(sorted(meaning, key=meaning.get, reverse=True)[: top_k * 3])

    scored = []
    for doc_id in shortlist:
        match = _match_score(query_words, chunks[doc_id]["text"])   # 0-1: question words found
        sem = meaning.get(doc_id, 0.0)                              # 0-1: same meaning
        if meaning:
            # Score shown to users: counts either kind of match, rewards both
            final = max(match, sem, MEANING_WEIGHT * sem + (1 - MEANING_WEIGHT) * match + 0.1 * min(match, sem))
            final = min(final, 1.0)
        else:
            final = match
        scored.append((final, word_rank.get(doc_id, 0.0) + sem, doc_id, match, sem))
    scored.sort(reverse=True)

    results = []
    for final, _rank, doc_id, match, sem in scored[:top_k]:
        if final < threshold:
            continue
        doc_data = dict(chunks[doc_id])
        doc_data["similarity_score"] = round(final, 3)
        doc_data["word_match"] = round(match, 3)
        doc_data["meaning_match"] = round(sem, 3)
        results.append(doc_data)

    if results:
        print(f"[RETRIEVER] 🔎 Best match {results[0]['similarity_score']:.0%} "
              f"(words {results[0]['word_match']:.0%}, meaning {results[0]['meaning_match']:.0%}) in "
              f"{results[0]['document']} (page {results[0]['page']}); {len(results)} pieces returned.")
    else:
        print("[RETRIEVER] 🔎 No piece matched well enough -- using general knowledge.")
    return results


try:
    build_or_load_index()
except Exception as e:
    print(f"Retriever initialization warning: {e}")