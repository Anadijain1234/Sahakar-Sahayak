import os
import io
import base64
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
    
    # Note: Updated to the correct active model name to prevent 404 errors.
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception:
    genai = None
    model = None


def normalize_query_to_english(raw_query: str) -> str:
    """
    Translates mixed-language speech (Kannada, Marathi, Hindi, etc.) into clean English
    for accurate FAISS vector database searching.
    """
    if model is None:
        return raw_query
        
    try:
        prompt = (
            "You are a translation filter. The user has provided text that may contain a messy mix "
            "of Kannada, Marathi, Nepali, Hindi, and English. Translate the core intent into "
            "a single, clean English query for a database search. "
            "ONLY output the English translation, absolutely nothing else.\n\n"
            f"User Text: {raw_query}"
        )
        generation_config = genai.types.GenerationConfig(temperature=0.0)
        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text.strip()
    except Exception as e:
        print(f"Translation Error: {e}")
        return raw_query


def get_answer(
    query: str, 
    language: str = "en", 
    intent: str = "general",
    retrieved_docs: list = None
) -> dict:
    if model is None:
        return {
            "answer": "Sahakar Sahayak assistant is active. Please configure GEMINI_API_KEY.",
            "language": language,
            "intent": intent,
            "sources": [],
            "confidence": 0.0,
            "action_url": None,
            "qr_code_base64": None
        }

    try:
        lang_instructions = {
            "kn": "Please respond in Kannada (ಕನ್ನಡ).",
            "hi": "Please respond in Hindi (हिंदी).",
            "ne": "Please respond in Nepali (नेपाली).",
            "en": "Please respond in English."
        }
        instruction = lang_instructions.get(language, "Please respond in English.")
        
        context_block = ""
        sources = []
        
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

        # AGGRESSIVE ANTI-HALLUCINATION PROMPT + CITATION ENFORCEMENT
        full_prompt = (
            f"You are Sahakar Sahayak, the official digital assistant for Indian Cooperative Societies.\n"
            f"{instruction}\n\n"
            f"CRITICAL RULES:\n"
            f"1. You MUST ONLY answer questions related to agriculture, cooperative societies, farming, and government schemes.\n"
            f"2. If the user asks about celebrities (like Virat Kohli), sports, movies, or general knowledge outside agriculture, you MUST refuse to answer and reply EXACTLY with: 'I am Sahakar Sahayak. I can only provide information regarding Indian Agricultural Cooperatives and Schemes. I cannot answer this query.'\n"
            f"3. DOCUMENT CITATIONS: Even though you are answering in {language}, you MUST keep the names of the source documents and page numbers exactly as they appear in English.\n"
        )

        if context_block.strip():
            full_prompt += (
                f"4. Answer the user query using ONLY the verified official text provided in the 'Context' below.\n"
                f"5. If the answer cannot be found completely in the Context, respond EXACTLY with: 'This information is not available in the official cooperative documents.'\n\n"
                f"Context:\n{context_block}\n\n"
                f"User Query: {query}"
            )
        else:
            full_prompt += (
                f"4. No official documents were retrieved for this query. If the query is a standard greeting (hello, hi), reply politely. Otherwise, state clearly that no official cooperative documents mention this topic.\n\n"
                f"User Query: {query}"
            )

        generation_config = genai.types.GenerationConfig(temperature=0.0)
        response = model.generate_content(full_prompt, generation_config=generation_config)
        answer_text = response.text.strip() if response and response.text else "No response generated."
        
        # Determine confidence and strip citations if the AI refused to answer
        if "I am Sahakar Sahayak. I can only provide information" in answer_text or "not available in the official cooperative documents" in answer_text.lower():
            sources = []
            confidence = 0.0
        else:
            confidence = 0.95

        # Fix QR text chopping: Expanded from 140 to 800 characters
        primary_source = sources[0]["document"] if sources else 'Official_Guidelines.pdf'
        sanitized_summary = answer_text[:800].replace("\n", " ")
        if len(answer_text) > 800:
            sanitized_summary += "..."
            
        encoded_message = urllib.parse.quote(
            f"Query: {query}\nAnswer: {sanitized_summary}\nSource: {primary_source}"
        )
        action_url = f"https://wa.me/?text={encoded_message}"
        
        qr_code_base64 = None
        if confidence > 0.0:
            try:
                import qrcode
                qr = qrcode.QRCode(version=None, box_size=4, border=2)
                qr.add_data(action_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                qr_code_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            except Exception:
                pass
        else:
            action_url = None

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
        return {
            "answer": f"AI Error: {str(e)}", 
            "language": language,
            "intent": intent,
            "sources": [],
            "confidence": 0.0,
            "action_url": None, 
            "qr_code_base64": None
        }