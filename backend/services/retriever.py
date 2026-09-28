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
3. Every candidate piece gets three real scores (keyword, spelling,
   meaning) and a weighted final score; the best 6 pieces are returned.
4. A piece is only used if its keyword match or its meaning match is
   strong enough. If no piece qualifies, nothing is returned, and the
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
import time
from array import array
from collections import Counter, defaultdict

import numpy as np
import requests
from pypdf import PdfReader

from backend.services.reqlog import log

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
WORD_WEIGHT = 0.6       # how much exact-word match counts (inside the word search)
PART_WEIGHT = 0.4       # how much part-of-word match counts (inside the word search)
BOOST_WEIGHT = 0.2      # how much official scheme names (keyword booster) help pick candidates
SHORTLIST = 5           # candidates checked = SHORTLIST x 6 from words + the same from meaning
# Final confidence = weighted mix of the three signals (weights add up to 1)
FINAL_W_KEYWORD = 0.35  # exact important words found
FINAL_W_SPELLING = 0.15 # 3-letter word parts found (spelling-tolerant)
FINAL_W_MEANING = 0.50  # same meaning (Cloudflare)
INCLUDE_KEYWORD = 0.50  # a piece is used if keyword match >= this ...
INCLUDE_MEANING = 0.50  # ... or scaled meaning match >= this
MEANING_LOW = 0.45      # Cloudflare similarity at/below this = "not related" (score 0)
MEANING_HIGH = 0.75     # Cloudflare similarity at/above this = "very related" (score 1)
EMBED_BATCH = 50        # pieces sent to Cloudflare per request when building
QUERY_TIMEOUT = 4       # seconds to wait for Cloudflare per question
CACHE_VERSION = 2

# Scheme routing: when a question clearly names a scheme or law, pieces from THAT
# scheme's own PDF get a small ranking bonus, so its official document is shown
# first. Right side = part of the PDF file name in backend/data/documents
# (update it here if you rename a PDF).
SCHEME_ROUTES = [
    (r"\b(pm[-\s]?kisan|kisan samman|samman nidhi)\b", "PM-KISAN"),
    (r"\b(pmfby|fasal bima|pradhan mantri fasal)\b", "doc1"),
    (r"\b(rwbcis|weather[-\s]based)\b", "RWBCIS"),
    (r"\b(upis|unified package)\b", "UPIS"),
    (r"\b(kcc|kisan credit card)\b", "405MDD58"),
    (r"\b(pmksy|krishi sinchayee|per drop more crop|micro[-\s]?irrigation)\b", "PMKSY"),
    (r"\b(karnataka)\b", "11of1959"),
    (r"\b(multi[-\s]?state|2023 amendment|amendment act,? 2023)\b", "247816"),
    (r"\b(model bye[-\s]?laws?|byelaws?)\b", "Model Byelaws"),
    (r"\b(jan aushadhi|common service cent(re|er)s?|computeri[sz]ation of pacs|pacs computeri[sz]ation)\b", "Initiatives"),
]
ROUTE_BONUS = 0.12      # ranking bonus for the named scheme's own PDF (does not change the shown score)
ROUTE_MIN_MATCH = 0.30  # a named scheme's passage this relevant can always be given to the AI
ROUTE_MIN_PIECES = 2    # ... at least this many passages from the named scheme's own PDF

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


def _meaning_similarities(query: str):
    """Cloudflare similarity (-1..1, usually 0.2-0.8) of the question to EVERY piece,
    as a numpy array. None if meaning search is off or Cloudflare fails."""
    if _vectors is None:
        return None
    try:
        q = _embed([query], timeout=QUERY_TIMEOUT)[0]
    except Exception as e:
        log("SEARCH", f"⚠️ meaning search (Cloudflare) failed for this question, using word search only: {e}")
        return None
    return _vectors @ q


def _scale_meaning(sim: float) -> float:
    """Turn a raw Cloudflare similarity into 0..1 (MEANING_LOW -> 0, MEANING_HIGH -> 1)."""
    return min(1.0, max(0.0, (sim - MEANING_LOW) / (MEANING_HIGH - MEANING_LOW)))


def _exact_keyword_score(query_words: list, text: str) -> float:
    """0 to 1: share of the question's important words found EXACTLY in this piece."""
    if not query_words:
        return 0.0
    piece_words = set(tokenize(text))
    return sum(1 for w in query_words if w in piece_words) / len(query_words)


def _spelling_score(query_parts: set, text: str) -> float:
    """0 to 1: share of the question's 3-letter word parts found in this piece.
    Rewards close spellings (kishan ~ kisan) with partial credit."""
    if not query_parts:
        return 0.0
    return len(query_parts & set(part_tokens(text))) / len(query_parts)


def _routed_documents(question: str) -> list:
    """File-name parts of the scheme PDFs the question clearly names (may be empty)."""
    q = (question or "").lower()
    out = []
    for pattern, doc_part in SCHEME_ROUTES:
        if re.search(pattern, q) and doc_part not in out:
            out.append(doc_part)
    return out


def _normalise(score_map: dict) -> dict:
    if not score_map:
        return {}
    top = max(score_map.values()) or 1.0
    return {k: v / top for k, v in score_map.items()}


def search(query: str, top_k: int = MIN_RESULTS, boost_terms: str = ""):
    """Full hybrid search. Returns (results, stats).

    query       : the clean English question (used for ALL scores)
    boost_terms : official scheme names from the keyword booster; they only help
                  pick candidate pieces and are NOT counted in any score.

    results: best PDF pieces, each with
        document, page, text,
        keyword_score  (0-1, exact important words found),
        spelling_score (0-1, 3-letter word parts found),
        meaning_score  (raw Cloudflare similarity, or None if unavailable),
        meaning_scaled (0-1 version of meaning_score),
        final_score    (0-1 weighted mix, used for ranking),
        similarity_score (same as final_score, kept for older code)
    stats: numbers for the on-screen "Search report".
    """
    started = time.perf_counter()
    stats = {
        "pieces_searched": len(chunks),
        "pdfs_searched": len(set(c["document"] for c in chunks)) if chunks else 0,
        "candidates_compared": 0,
        "meaning_available": False,
        "search_time_ms": 0.0,
    }

    if _word_index is None:
        build_or_load_index()
        stats["pieces_searched"] = len(chunks)
        stats["pdfs_searched"] = len(set(c["document"] for c in chunks)) if chunks else 0
    if _word_index is None or not chunks:
        return [], stats

    top_k = max(top_k, MIN_RESULTS)
    query_words = list(dict.fromkeys(tokenize(query)))   # unique, in order
    if not query_words:
        return [], stats
    query_parts = set(part_tokens(query))

    boost_words = [w for w in dict.fromkeys(tokenize(boost_terms or "")) if w not in query_words]

    # 1) Word search (BM25 on whole words + BM25 on 3-letter parts).
    #    Boost words get a small weight so they can't push out pieces that match the real question.
    word_scores = _normalise(_word_index.scores(query_words))
    part_scores = _normalise(_part_index.scores(list(query_parts)))
    boost_scores = _normalise(_word_index.scores(boost_words)) if boost_words else {}
    word_rank = {}
    for doc_id in set(word_scores) | set(part_scores) | set(boost_scores):
        word_rank[doc_id] = (WORD_WEIGHT * word_scores.get(doc_id, 0.0)
                             + PART_WEIGHT * part_scores.get(doc_id, 0.0)
                             + BOOST_WEIGHT * boost_scores.get(doc_id, 0.0))

    # 2) Meaning search (Cloudflare)
    sims = _meaning_similarities(query)
    meaning_on = sims is not None
    stats["meaning_available"] = meaning_on

    # 3) Shortlist = best by words + best by meaning (+ best pieces of a scheme PDF the question names)
    shortlist = set(sorted(word_rank, key=word_rank.get, reverse=True)[: top_k * SHORTLIST])
    if meaning_on:
        shortlist |= set(int(i) for i in np.argsort(-sims)[: top_k * SHORTLIST])
    routed = _routed_documents(query)
    stats["scheme_routing"] = routed
    if routed:
        in_routed = [i for i in range(len(chunks)) if any(d.lower() in chunks[i]["document"].lower() for d in routed)]
        by_words = sorted((i for i in in_routed if i in word_rank), key=word_rank.get, reverse=True)[:10]
        shortlist |= set(by_words)
        if meaning_on:
            shortlist |= set(sorted(in_routed, key=lambda i: -float(sims[i]))[:10])
    stats["candidates_compared"] = len(shortlist)

    # 4) Score every candidate on all three signals
    scored = []
    route_backup = []
    for doc_id in shortlist:
        text = chunks[doc_id]["text"]
        kw = _exact_keyword_score(query_words, text)
        sp = _spelling_score(query_parts, text)
        if meaning_on:
            raw = float(sims[doc_id])
            ms = _scale_meaning(raw)
            final = FINAL_W_KEYWORD * kw + FINAL_W_SPELLING * sp + FINAL_W_MEANING * ms
            keep = kw >= INCLUDE_KEYWORD or ms >= INCLUDE_MEANING
        else:
            raw, ms = None, 0.0
            final = 0.7 * kw + 0.3 * sp
            keep = kw >= INCLUDE_KEYWORD
        in_route = bool(routed) and any(d.lower() in chunks[doc_id]["document"].lower() for d in routed)
        if keep:
            bonus = ROUTE_BONUS if in_route else 0.0
            scored.append((final + bonus, word_rank.get(doc_id, 0.0), doc_id, kw, sp, raw, ms, final))
        elif in_route and (kw >= ROUTE_MIN_MATCH or ms >= ROUTE_MIN_MATCH):
            route_backup.append((final, word_rank.get(doc_id, 0.0), doc_id, kw, sp, raw, ms, final))
    scored.sort(reverse=True)
    picked = scored[:top_k]

    # The question names a scheme (e.g. "Per Drop More Crop"): make sure the AI sees at least
    # two passages from that scheme's own PDF, using the last slots if needed.
    if routed:
        def _is_routed(x):
            return any(d.lower() in chunks[x[2]]["document"].lower() for d in routed)
        have = [x for x in picked if _is_routed(x)]
        extra = sorted([x for x in scored[top_k:] if _is_routed(x)] + route_backup, reverse=True)
        need = max(0, ROUTE_MIN_PIECES - len(have))
        if need and extra:
            add = extra[:need]
            others = [x for x in picked if not _is_routed(x)]
            picked = sorted(have + others[:max(0, top_k - len(have) - len(add))] + add, reverse=True)
            log("SEARCH", f"📌 added {len(add)} passage(s) from the named scheme's PDF ({chunks[add[0][2]]['document']})")

    results = []
    for _key, _rank, doc_id, kw, sp, raw, ms, final in picked:
        doc_data = dict(chunks[doc_id])
        doc_data.update({
            "keyword_score": round(kw, 4),
            "spelling_score": round(sp, 4),
            "meaning_score": round(raw, 4) if raw is not None else None,
            "meaning_scaled": round(ms, 4),
            "final_score": round(final, 4),
            "similarity_score": round(final, 4),
        })
        results.append(doc_data)

    stats["search_time_ms"] = round((time.perf_counter() - started) * 1000, 2)

    if results:
        b = results[0]
        meaning_txt = f"{b['meaning_score'] * 100:.2f}%" if b["meaning_score"] is not None else "off"
        log("SEARCH", f"🔎 best {b['final_score'] * 100:.2f}% | keyword {b['keyword_score'] * 100:.2f}% | "
              f"spelling {b['spelling_score'] * 100:.2f}% | meaning {meaning_txt} | "
              f"{b['document']} p.{b['page']} | {len(results)} pieces | {stats['search_time_ms']} ms")
    else:
        log("SEARCH", f"🔎 no piece matched well enough -- answer will use general knowledge ({stats['search_time_ms']} ms)")
    return results, stats


def retrieve_documents(query: str, top_k: int = 3, threshold: float = None) -> list:
    """Older, simpler entry point (used by older code): just the pieces."""
    results, _stats = search(query, top_k=top_k)
    return results


try:
    build_or_load_index()
except Exception as e:
    print(f"Retriever initialization warning: {e}")