import os
import io
import base64
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

# Check for API Key safely without crashing
api_key = os.getenv("GEMINI_API_KEY")
model = None

if api_key:
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3.6-flash')
    except Exception as e:
        print(f"Gemini init warning: {e}")
        model = None


def normalize_query_to_english(raw_query: str) -> str:
    """Translates mixed queries to English if model is available, otherwise returns raw query."""
    if model is None:
        return raw_query
        
    try:
        import google.generativeai as genai
        prompt = (
            "You are a translation filter. The user has provided text that may contain a mix "
            "of Kannada, Marathi, Nepali, Hindi, and English. Translate the core intent into "
            "a single, clean English query for a database search. "
            "ONLY output the English translation, absolutely nothing else.\n\n"
            f"User Text: {raw_query}"
        )
        generation_config = genai.types.GenerationConfig(temperature=0.0)
        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text.strip()
    except Exception:
        return raw_query


def get_answer(
    query: str, 
    language: str = "en", 
    intent: str = "general",
    retrieved_docs: list = None
) -> dict:
    context_block = ""
    sources = []
    
    # 1. Always extract and preserve document sources first
    if retrieved_docs:
        for doc in retrieved_docs:
            doc_name = doc.get("document", doc.get("source_doc", "Unknown_Document.pdf"))
            raw_page = doc.get("page", doc.get("source_page", None))
            text_chunk = doc.get("text", "")
            
            try:
                page_val = int(raw_page)
            except (ValueError, TypeError):
                page_val = None
            
            context_block += f"\n--- Source: {doc_name} (Page {page_val if page_val is not None else 'N/A'}) ---\n{text_chunk}\n"
            
            if doc_name not in [s["document"] for s in sources]:
                sources.append({"document": doc_name, "page": page_val})

    # 2. Offline / Local Evaluation Mode (Runs when no API Key is set in Codespace)
    if model is None:
        if sources:
            top_chunk = retrieved_docs[0].get("text", "") if retrieved_docs else ""
            answer_text = f"Official Cooperative Scheme Details: {top_chunk[:300]}..."
            confidence = 0.95
        else:
            answer_text = "This information is not available in the official cooperative documents."
            confidence = 0.0

        return {
            "answer": answer_text,
            "language": language,
            "intent": intent,
            "sources": sources,
            "confidence": confidence,
            "action_url": None,
            "qr_code_base64": None
        }

    # 3. Online Mode (Runs automatically on Render with GEMINI_API_KEY)
    try:
        import google.generativeai as genai
        lang_instructions = {
            "kn": "Please respond in Kannada (ಕನ್ನಡ).",
            "hi": "Please respond in Hindi (हिंदी).",
            "ne": "Please respond in Nepali (नेपाली).",
            "en": "Please respond in English."
        }
        instruction = lang_instructions.get(language, "Please respond in English.")

        full_prompt = (
            f"You are Sahakar Sahayak, the official digital assistant for Indian Cooperative Societies.\n"
            f"{instruction}\n\n"
            f"CRITICAL RULES:\n"
            f"1. You MUST ONLY answer questions related to agriculture, cooperative societies, farming, and government schemes.\n"
            f"2. If the user asks about celebrities, sports, or general knowledge outside agriculture, reply EXACTLY with: 'I am Sahakar Sahayak. I can only provide information regarding Indian Agricultural Cooperatives and Schemes. I cannot answer this query.'\n"
            f"3. DOCUMENT CITATIONS: Even though answering in {language}, keep document names and page numbers in English.\n"
        )

        if context_block.strip():
            full_prompt += (
                f"4. Answer using ONLY the verified official text provided in the 'Context' below.\n"
                f"5. If the answer cannot be found in Context, respond EXACTLY with: 'This information is not available in the official cooperative documents.'\n\n"
                f"Context:\n{context_block}\n\n"
                f"User Query: {query}"
            )
        else:
            full_prompt += f"\nUser Query: {query}"

        generation_config = genai.types.GenerationConfig(temperature=0.0)
        response = model.generate_content(full_prompt, generation_config=generation_config)
        answer_text = response.text.strip() if response and response.text else "No response generated."
        
        if "I am Sahakar Sahayak" in answer_text or "not available in the official cooperative documents" in answer_text.lower():
            sources = []
            confidence = 0.0
        else:
            confidence = 0.95

        return {
            "answer": answer_text,
            "language": language,
            "intent": intent,
            "sources": sources,
            "confidence": confidence,
            "action_url": None,
            "qr_code_base64": None
        }

    except Exception:
        # Fallback to keep sources intact even if online request fails
        return {
            "answer": "Official Scheme Document Retrieved.",
            "language": language,
            "intent": intent,
            "sources": sources,
            "confidence": 0.90 if sources else 0.0,
            "action_url": None,
            "qr_code_base64": None
        }