import os
import io
import re
import base64
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

print("=======================================================")
print("🧠 ENTERPRISE MULTI-STAGE RAG ENGINE INITIALIZING 🧠")
print("=======================================================")

# Initialize Sarvam AI Client
try:
    from sarvamai import SarvamAI
    api_key = os.getenv("SARVAM_API_KEY", "").strip()
    
    if not api_key:
        print("[SARVAM LOG] ❌ WARNING: SARVAM_API_KEY missing from environment variables!")
        
    client = SarvamAI(api_subscription_key=api_key) if api_key else None
    MODEL_NAME = "sarvam-105b"
    if client:
        print(f"[SARVAM LOG] ✅ Engine Online: Model '{MODEL_NAME}' connected.")
except Exception as e:
    print(f"[SARVAM LOG] ❌ FATAL INIT ERROR: {e}")
    client = None
    MODEL_NAME = None


# Canonical Scheme Mapping Dictionary for Dialect Resolution
OFFICIAL_SCHEME_LEXICON = {
    r"\b(kishan|kisan|samman|nidhi|2000|6000|hafta|kist|modi paisa)\b": "PM-KISAN Pradhan Mantri Kisan Samman Nidhi",
    r"\b(bima|fasal bima|crop insurance|sukha|baadh|nuksan|claim)\b": "PMFBY Pradhan Mantri Fasal Bima Yojana crop insurance",
    r"\b(credit card|kcc|loan|karj|kisaan card|pashupalan loan)\b": "KCC Kisan Credit Card agricultural credit loan",
    r"\b(soil card|mitti|urvarak|fertilizer|khad|dap|urea)\b": "Soil Health Card Scheme nutrient management",
    r"\b(sinchai|irrigation|paani|drip|sprinkler|borewell)\b": "PMKSY Pradhan Mantri Krishi Sinchayee Yojana irrigation",
    r"\b(mandi|enam|e-nam|bhav|bechna|msp|rate)\b": "e-NAM National Agriculture Market MSP procurement",
    r"\b(samiti|cooperative|society|pacs|dairy|sahakar|sangh)\b": "PACS Primary Agricultural Credit Societies Cooperative Governance"
}


def normalize_query_to_english(raw_query: str) -> str:
    """
    Stage 1: Transforms dialect speech, phonetic typos, and code-mixed inputs
    into dense, official search keywords optimized specifically for BM25.
    """
    if not raw_query or not raw_query.strip():
        return ""

    if client is None:
        print("[SARVAM LOG] ⚠️ Client offline. Running rule-based dialect fallback.")
        return _apply_lexicon_fallback(raw_query)

    print(f"\n[SARVAM LOG] 🔄 Disambiguating & Normalizing Query: '{raw_query}'")
    
    try:
        normalization_prompt = (
            "You are a specialized linguistic pre-processor for Indian Agricultural Information Retrieval.\n"
            "The user input comes from rural farmers speaking regional dialects (e.g., Bundelkhandi, Bhojpuri, Malwi), "
            "vernacular languages (Kannada, Marathi, Hindi, Telugu), or mixed colloquial English with heavy phonetic typos "
            "(e.g., 'kishan kist', 'bima ka paisa', 'modi loan', 'raitha sahayak').\n\n"
            "YOUR TASKS:\n"
            "1. Detect the core agricultural intent.\n"
            "2. Map every vague, slang, or misspelled scheme name to its exact official government title and acronym "
            "(e.g., map 'kishan' -> 'PM-KISAN', 'fasal bima' -> 'PMFBY', 'kisan karj' -> 'Kisan Credit Card KCC').\n"
            "3. Output a space-separated list of clean, English keywords and official terms designed for maximum lexical BM25 matching.\n"
            "4. If the query is completely unrelated to agriculture/rural welfare (e.g., sports, movies, celebrity trivia), output 'OUT_OF_DOMAIN'.\n"
            "5. OUTPUT ONLY THE SEARCH KEYWORDS. Absolutely no introductory words, punctuation, or explanations.\n\n"
            f"User Input: {raw_query}"
        )

        response = client.chat.completions(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": normalization_prompt}]
        )

        raw_content = response.choices[0].message.content if response.choices else None
        cleaned_search_terms = raw_content.strip() if raw_content else _apply_lexicon_fallback(raw_query)

        # Append hardcoded lexicon hits to safeguard against any LLM omissions
        lexicon_boost = _apply_lexicon_fallback(raw_query)
        final_search_query = f"{cleaned_search_terms} {lexicon_boost}".strip()

        print(f"[SARVAM LOG] ✅ Search Keywords Generated: '{final_search_query}'")
        return final_search_query

    except Exception as e:
        print(f"[SARVAM LOG] ❌ Normalization failed ({str(e)}). Using regex fallback.")
        return _apply_lexicon_fallback(raw_query)


def _apply_lexicon_fallback(text: str) -> str:
    """Deterministic keyword booster for common colloquialisms."""
    boosters = []
    text_lower = text.lower()
    for pattern, official_term in OFFICIAL_SCHEME_LEXICON.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            boosters.append(official_term)
    return " ".join(boosters) if boosters else text


def get_answer(
    query: str, 
    language: str = "en", 
    intent: str = "general",
    retrieved_docs: list = None
) -> dict:
    """
    Stage 2 & 3: Context deduplication, domain boundary verification, 
    grounded generation in the user's native language, and QR packaging.
    """
    sources = []
    context_chunks = []
    seen_texts = set()

    # 1. Context Deduplication and Source Extraction
    if retrieved_docs:
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

            # Build frontend citation link
            if doc_name not in [s["document"] for s in sources]:
                link_url = f"/documents/{urllib.parse.quote(doc_name)}"
                if page_val is not None:
                    link_url += f"#page={page_val}"
                
                sources.append({
                    "document": doc_name,
                    "page": page_val,
                    "link": link_url
                })

    context_block = "\n\n---\n\n".join(context_chunks[:5])  # Cap at top 5 unique chunks to preserve context focus

    if client is None:
        return {
            "answer": "AI Error: SARVAM_API_KEY is missing from the server environment.",
            "language": language,
            "intent": intent,
            "sources": sources,
            "confidence": 0.0,
            "action_url": None,
            "qr_code_base64": None
        }

    # 2. Regional Instruction Scaffolding
    lang_instructions = {
        "kn": "Respond strictly in clear, respectful, natural Kannada (ಕನ್ನಡ). Use simple vocabulary suitable for a farmer.",
        "hi": "Respond strictly in clear, respectful, natural Hindi (हिंदी). Use simple, rural-friendly vocabulary.",
        "ne": "Respond strictly in clear, respectful, natural Nepali (नेपाली).",
        "mr": "Respond strictly in clear, respectful, natural Marathi (मराठी).",
        "ta": "Respond strictly in clear, respectful, natural Tamil (தமிழ்).",
        "te": "Respond strictly in clear, respectful, natural Telugu (తెలుగు).",
        "en": "Respond strictly in clear, structured, professional English."
    }
    target_lang_instruction = lang_instructions.get(language, "Respond in clear, accessible English.")

    # 3. Master RAG Prompt
    master_prompt = (
        "You are Sahakar Sahayak, an official, empathetic digital kiosk assistant dedicated to Indian farmers, "
        "agricultural laborers, and rural cooperative societies.\n"
        f"{target_lang_instruction}\n\n"
        "STRICT OPERATIONAL GUIDELINES:\n"
        "1. DOMAIN BOUNDARY LOCK: You are ONLY allowed to answer questions concerning agriculture, farming practices, "
        "crop diseases, seeds, fertilizers, weather protection, irrigation, rural credit, and government schemes "
        "(e.g., PM-KISAN, PMFBY, KCC, PACS). If the user asks about sports (e.g., Virat Kohli), politics, movies, "
        "coding, or celebrity gossip, you MUST REFUSE immediately and reply EXACTLY with:\n"
        "'I am Sahakar Sahayak. I can only provide assistance regarding Indian Agriculture, Cooperative Societies, and Farmer Welfare Schemes.'\n\n"
        "2. DOCUMENT FIDELITY (PRIMARY): Whenever Context is present, your answer must be grounded directly in those facts. "
        "Cite the document name and page number clearly when stating requirements, amounts, or rules. "
        "Keep official document names in English for administrative verification.\n\n"
        "3. GRACEFUL GENERAL FALLBACK (SECONDARY): If the Context block below is empty or lacks specific answers, DO NOT say "
        "'Information not available'. Instead, use your extensive knowledge of Indian agricultural governance to give the farmer "
        "a complete, accurate, and step-by-step helpful answer. Add a polite introductory phrase indicating this is general administrative advice.\n\n"
        "4. STRUCTURE & TONE: Present lists with bullet points, break steps into numbered sequences, and maintain a warm, supportive tone.\n\n"
        f"Context:\n{context_block if context_block else 'No direct document chunks matched for this query.'}\n\n"
        f"Farmer Query: {query}"
    )

    try:
        print(f"\n[SARVAM LOG] 🧠 Executing Master Synthesis for language: '{language}'")
        response = client.chat.completions(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": master_prompt}]
        )

        raw_content = response.choices[0].message.content if response.choices else None
        answer_text = raw_content.strip() if raw_content else "I apologize, but I could not synthesize an answer at this moment. Please try asking again."

        print("[SARVAM LOG] ✅ Answer Synthesis Completed.")

        # 4. Confidence & Citation Calibration
        is_refusal = "I am Sahakar Sahayak. I can only provide assistance" in answer_text
        has_documents = len(sources) > 0 and "No direct document chunks matched" not in master_prompt

        if is_refusal:
            sources = []
            confidence = 0.0
        elif has_documents:
            confidence = 0.98
        else:
            # Answer generated from verified general agricultural knowledge
            sources = []
            confidence = 0.85

        # 5. WhatsApp Receipt Link & QR Code Generation
        action_url, qr_code_base64 = _generate_share_qr(query, answer_text, sources, confidence)

        return {
            "answer": answer_text,
            "language": language,
            "intent": intent,
            "sources": sources,
            "confidence": confidence,
            "action_url": action_url,
            "qr_code_base64": qr_code_base64
        }

    except Exception as e:
        print(f"[SARVAM LOG] ❌ Master Synthesis Exception: {str(e)}")
        return {
            "answer": f"System Notice: We experienced an issue communicating with the reasoning engine ({str(e)}). Please try again.",
            "language": language,
            "intent": intent,
            "sources": sources,
            "confidence": 0.0,
            "action_url": None,
            "qr_code_base64": None
        }


def _generate_share_qr(query: str, answer: str, sources: list, confidence: float):
    """Produces a clean WhatsApp click-to-chat URL and accompanying QR code."""
    if confidence <= 0.0:
        return None, None

    try:
        primary_doc = sources[0]["document"] if sources else "Official Agricultural Guidelines"
        clean_excerpt = answer[:600].replace("\n", " ").strip()
        if len(answer) > 600:
            clean_excerpt += "..."

        share_text = f"🌾 *Sahakar Sahayak Assistance Receipt*\n\n*Query:* {query}\n\n*Guidance:* {clean_excerpt}\n\n*Source Reference:* {primary_doc}"
        encoded_message = urllib.parse.quote(share_text)
        action_url = f"https://wa.me/?text={encoded_message}"

        import qrcode
        qr = qrcode.QRCode(version=None, box_size=4, border=2)
        qr.add_data(action_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return action_url, qr_code_base64
    except Exception as e:
        print(f"[RAG QR LOG] ⚠️ QR generation bypassed: {e}")
        return None, None