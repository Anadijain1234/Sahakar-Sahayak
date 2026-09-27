import os
import re
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

print("=======================================================")
print("🧠 SAHAKAAR KIOSK RAG ENGINE INITIALIZING 🧠")
print("=======================================================")

try:
    from sarvamai import SarvamAI
    api_key = os.getenv("SARVAM_API_KEY", "").strip()
    client = SarvamAI(api_subscription_key=api_key) if api_key else None

    MODEL_NAME = "sarvam-105b"
    if client:
        print(f"[SARVAM LOG] ✅ Engine Online: Model '{MODEL_NAME}' connected.")
except Exception as e:
    print(f"[SARVAM LOG] ❌ FATAL INIT ERROR: {e}")
    client = None
    MODEL_NAME = None

# Full public address of THIS backend. The frontend lives on a different
# Render address, so a short link like "/documents/x.pdf" would open on the
# frontend's site (where the PDFs don't exist). Set PUBLIC_BACKEND_URL in
# Render if this address ever changes.
PUBLIC_BACKEND_URL = os.getenv("PUBLIC_BACKEND_URL", "https://sahakar-sahayak-4.onrender.com").rstrip("/")

OFFICIAL_SCHEME_LEXICON = {
    r"\b(kishan|kisan|samman|nidhi|2000|6000|hafta|kist|modi paisa)\b": "PM-KISAN Pradhan Mantri Kisan Samman Nidhi",
    r"\b(bima|fasal bima|crop insurance|sukha|baadh|nuksan|claim)\b": "PMFBY Pradhan Mantri Fasal Bima Yojana crop insurance",
    r"\b(credit card|kcc|loan|karj|kisaan card|pashupalan loan)\b": "KCC Kisan Credit Card agricultural credit loan",
    r"\b(soil card|mitti|urvarak|fertilizer|khad|dap|urea)\b": "Soil Health Card Scheme nutrient management",
    r"\b(sinchai|irrigation|paani|drip|sprinkler|borewell)\b": "PMKSY Pradhan Mantri Krishi Sinchayee Yojana irrigation",
    r"\b(mandi|enam|e-nam|bhav|bechna|msp|rate)\b": "e-NAM National Agriculture Market MSP procurement",
    r"\b(samiti|cooperative|society|pacs|dairy|sahakar|sangh)\b": "PACS Primary Agricultural Credit Societies Cooperative Governance",
    r"\b(register|registration|bye-?law|byelaw|election|board member|audit|agm|annual general meeting)\b": "Cooperative Society Registration Bye-laws Board Election Audit",
}

# Extend this as your frontend's language dropdown grows. Keys must match
# whatever `language` code the frontend sends.
LANG_MAP = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
    "ne": "Nepali",
    "ta": "Tamil",
    "te": "Telugu",
    "ml": "Malayalam",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "or": "Odia",
}


def _clean_model_text(message_obj) -> str:
    """Return ONLY the final answer text from a Sarvam chat message
    (never the hidden reasoning)."""
    if not message_obj:
        return ""
    content = (getattr(message_obj, "content", "") or "").strip()
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL | re.IGNORECASE).strip()
    return content


def _apply_lexicon_fallback(text: str) -> str:
    """Return official scheme names found in `text`, or "" if none.
    (It no longer echoes the whole text back -- that was causing the
    repeated words you saw in the 'Search Keywords' log line.)"""
    boosters = []
    for pattern, official_term in OFFICIAL_SCHEME_LEXICON.items():
        if re.search(pattern, text.lower(), re.IGNORECASE):
            boosters.append(official_term)
    return " ".join(boosters)


def lexicon_terms(text: str) -> str:
    """Official scheme names for words found in `text` (e.g. 'kisan' -> 'PM-KISAN
    Pradhan Mantri Kisan Samman Nidhi'). Used ONLY to help the search find
    candidates -- never counted in the match score, never sent to the AI."""
    return _apply_lexicon_fallback(text or "")


def normalize_query_to_english(raw_query: str) -> str:
    """Turn a messy, mixed-language question (Kannada + English + Hindi,
    local dialect, spelling mistakes) into ONE clear English question,
    so the English PDFs can be searched properly."""
    if not raw_query or not raw_query.strip():
        return ""

    if client is None:
        return raw_query.strip()

    print(f"\n[SARVAM LOG] 🔄 Normalizing Query: '{raw_query}'")

    try:
        response = client.chat.completions(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "The user is an Indian farmer or cooperative society "
                        "member. Their message may mix Kannada, Hindi and "
                        "English, use local dialect, or have spelling "
                        "mistakes. Rewrite it as ONE clear, complete question "
                        "in simple English, keeping its full meaning. Keep "
                        "scheme names and numbers exactly (e.g. PM-KISAN, "
                        "PMFBY, KCC, PACS, 72 hours). If the message is about "
                        "sports, movies, politics, or anything unrelated to "
                        "farming, farmer schemes or cooperative societies, "
                        "reply with exactly: OUT_OF_DOMAIN. Reply with ONLY "
                        "the rewritten question (or OUT_OF_DOMAIN) -- no "
                        "preamble, no explanation."
                    ),
                },
                {"role": "user", "content": raw_query},
            ],
            temperature=0.1,
            max_tokens=120,
            reasoning_effort=None,
        )

        message_obj = response.choices[0].message if response.choices else None
        english_question = _clean_model_text(message_obj)

        # If Sarvam thinks it's off-topic (or returns nothing), pass the
        # original question on unchanged. The answer step has its own
        # off-topic rule, so this avoids wrongly refusing a real question.
        if not english_question or "OUT_OF_DOMAIN" in english_question.upper():
            print("[SARVAM LOG] ⚠️ Marked off-topic or empty -- passing original question through.")
            return raw_query

        print(f"[SARVAM LOG] ✅ English Question: '{english_question}'")
        return english_question

    except Exception as e:
        print(f"[SARVAM LOG] ❌ Normalization failed: {e}")
        return raw_query.strip()


def _call_synthesis(system_prompt: str, user_prompt: str) -> str:
    """One attempt at asking Sarvam to write the final answer. Raises on failure."""
    response = client.chat.completions(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=1024,
        reasoning_effort=None,
    )
    message_obj = response.choices[0].message if response.choices else None
    return _clean_model_text(message_obj)


def get_answer(
    query: str,
    language: str = "en",
    intent: str = "general",
    retrieved_docs: list = None,
    search_stats: dict = None,
) -> dict:
    context_chunks = []
    seen_texts = set()
    retrieved_docs = retrieved_docs or []

    for doc in retrieved_docs:
        doc_name = doc.get("document", doc.get("source_doc", "Official_Document.pdf"))
        raw_page = doc.get("page", doc.get("source_page", None))
        text_chunk = doc.get("text", "").strip()
        if not text_chunk or text_chunk in seen_texts:
            continue
        seen_texts.add(text_chunk)
        try:
            page_val = int(raw_page)
        except (ValueError, TypeError):
            page_val = None
        context_chunks.append(
            f"[Document: {doc_name} | Page: {page_val if page_val is not None else 'General'}]\n{text_chunk}"
        )

    # Sources shown to the user: only pieces that matched almost as well as the best one
    sources = _relevant_sources(retrieved_docs)
    report = _build_search_report(retrieved_docs, search_stats)

    context_block = "\n\n---\n\n".join(context_chunks[:6])

    if client is None:
        return {
            "answer": "AI Error: SARVAM_API_KEY is missing.",
            "language": language,
            "intent": intent,
            "sources": sources,
            "confidence": 0.0,
            "answer_source": "error",
            "trust_level": "error",
            "search_report": report,
            "action_url": None,
            "qr_code_base64": None,
        }

    target_lang = LANG_MAP.get(language, "English")

    system_prompt = (
        f"You are Sahakar Sahayak, an assistant for Indian cooperative societies "
        f"(registration, bye-laws, board elections, audits) and farmer welfare "
        f"schemes (PM-KISAN, PMFBY, KCC, irrigation, e-NAM). Always reply "
        f"naturally in {target_lang}, in plain prose -- no headers, no markdown, "
        "no meta-commentary about what you are doing.\n"
        "Rules:\n"
        "1. Base your answer entirely on the Context below when it is relevant. "
        "If the Context is empty or not relevant, answer from general knowledge "
        "about cooperative societies or farmer schemes instead.\n"
        "2. If the question is about cricket, movies, politics, or anything "
        "unrelated to farming, farmer schemes or cooperative societies, reply "
        f"with ONLY this sentence, translated into {target_lang}: 'I can only "
        "assist with cooperative society and farmer scheme questions.'\n"
        "3. Never show your reasoning, thinking, or notes -- output only the "
        "final answer meant for the user to read.\n"
        "4. Keep the answer short and to the point -- a few sentences, not an essay."
    )

    user_prompt = f"Context:\n{context_block if context_block else 'None'}\n\nUser Query: {query}"

    print(f"\n[SARVAM LOG] 🧠 Executing Master Synthesis for '{language}'")

    answer_text = ""
    used_context = bool(context_block)

    try:
        answer_text = _call_synthesis(system_prompt, user_prompt)
    except Exception as e:
        # Print the context that was sent, so if this happens again you can
        # see which paragraph likely tripped Sarvam's safety filter.
        print(f"[SARVAM LOG] ⚠️ Synthesis with context failed: {e}")
        print(f"[SARVAM LOG] 📄 Context that was sent:\n{context_block}")
        print("[SARVAM LOG] 🔁 Retrying once WITHOUT context...")
        try:
            fallback_prompt = f"Context:\nNone\n\nUser Query: {query}"
            answer_text = _call_synthesis(system_prompt, fallback_prompt)
            used_context = False
            sources = []
        except Exception as e2:
            print(f"[SARVAM LOG] ❌ Master Synthesis Exception (both attempts failed): {e2}")
            answer_text = ""

    if not answer_text:
        # Friendly message only -- never show raw error text to the user.
        return {
            "answer": "I'm having trouble answering that right now. Please try rephrasing your question, or try again in a moment.",
            "language": language,
            "intent": intent,
            "sources": [],
            "confidence": 0.0,
            "answer_source": "error",
            "trust_level": "error",
            "search_report": report,
            "action_url": None,
            "qr_code_base64": None,
        }

    print(f"[SARVAM LOG] 🔍 Final extracted length: {len(answer_text)}")
    print("[SARVAM LOG] ✅ Answer Synthesis Completed.")

    is_refusal = "can only assist with" in answer_text.lower() or "out_of_domain" in answer_text.lower()
    has_documents = used_context and len(sources) > 0

    best = retrieved_docs[0] if (has_documents and retrieved_docs) else None

    if is_refusal:
        sources = []
        confidence = 0.0
        answer_source = "refused"
        trust_level = "refused"
    elif best is not None:
        confidence = float(best.get("final_score", best.get("similarity_score", 0.0)))
        answer_source = "documents"
        trust_level = _trust_level(best, report)
    else:
        sources = []
        confidence = 0.0
        answer_source = "general"
        trust_level = "general"

    report["used_documents"] = answer_source == "documents"

    return {
        "answer": answer_text,
        "language": language,
        "intent": intent,
        "sources": sources,
        "confidence": round(confidence, 4),
        "answer_source": answer_source,
        "trust_level": trust_level,
        "search_report": report,
        # WhatsApp sharing is now done by the website itself with the FULL
        # answer (no 600-letter QR limit), so these stay empty.
        "action_url": None,
        "qr_code_base64": None,
    }


# ---------------------------------------------------------------------------
# Trust card helpers
# ---------------------------------------------------------------------------
def _pct(x):
    """0-1 -> percent with 2 decimals (None stays None)."""
    return None if x is None else round(float(x) * 100, 2)


def _doc_link(doc_name: str, page_val) -> str:
    link = f"{PUBLIC_BACKEND_URL}/documents/{urllib.parse.quote(doc_name)}"
    if page_val is not None:
        link += f"#page={page_val}"
    return link


def _relevant_sources(retrieved_docs: list, max_sources: int = 3, margin: float = 0.15) -> list:
    """Best source(s) only: pieces scoring within `margin` of the top piece,
    one entry per document+page, at most `max_sources`."""
    if not retrieved_docs:
        return []
    top = float(retrieved_docs[0].get("final_score", retrieved_docs[0].get("similarity_score", 0.0)))
    out, seen = [], set()
    for doc in retrieved_docs:
        score = float(doc.get("final_score", doc.get("similarity_score", 0.0)))
        if score < top - margin:
            continue
        name = doc.get("document", "Official_Document.pdf")
        try:
            page_val = int(doc.get("page"))
        except (ValueError, TypeError):
            page_val = None
        key = (name, page_val)
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "document": name,
            "page": page_val,
            "link": _doc_link(name, page_val),
            "score": _pct(score),
        })
        if len(out) >= max_sources:
            break
    return out


def _build_search_report(retrieved_docs: list, stats: dict) -> dict:
    """Numbers for the 'Search report' panel. Every value comes from the real search."""
    stats = stats or {}
    best = retrieved_docs[0] if retrieved_docs else None
    report = {
        "final_confidence": _pct(best.get("final_score")) if best else 0.0,
        "keyword_score": _pct(best.get("keyword_score")) if best else 0.0,
        "spelling_score": _pct(best.get("spelling_score")) if best else 0.0,
        "meaning_score": _pct(best.get("meaning_score")) if best else None,
        "meaning_available": bool(stats.get("meaning_available", False)),
        "pieces_searched": stats.get("pieces_searched", 0),
        "pdfs_searched": stats.get("pdfs_searched", 0),
        "candidates_compared": stats.get("candidates_compared", 0),
        "pieces_used": len(retrieved_docs),
        "search_time_ms": stats.get("search_time_ms", 0.0),
        "used_documents": bool(retrieved_docs),
        "top_sources": [],
    }
    seen = set()
    for doc in retrieved_docs:
        key = (doc.get("document"), doc.get("page"))
        if key in seen:
            continue
        seen.add(key)
        report["top_sources"].append({
            "document": doc.get("document"),
            "page": doc.get("page"),
            "link": _doc_link(doc.get("document", ""), doc.get("page")),
            "final": _pct(doc.get("final_score")),
            "keyword": _pct(doc.get("keyword_score")),
            "spelling": _pct(doc.get("spelling_score")),
            "meaning": _pct(doc.get("meaning_score")),
        })
        if len(report["top_sources"]) >= 5:
            break
    return report


def _trust_level(best: dict, report: dict) -> str:
    """verified = words AND meaning agree strongly; partial = a document matched,
    but not strongly on both."""
    kw = float(best.get("keyword_score", 0.0))
    if report.get("meaning_available"):
        ms = float(best.get("meaning_scaled", 0.0))
        final = float(best.get("final_score", 0.0))
        return "verified" if (kw >= 0.5 and ms >= 0.35 and final >= 0.6) else "partial"
    return "verified" if kw >= 0.75 else "partial"
