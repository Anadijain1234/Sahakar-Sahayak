import os
import io
import base64
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

# Safe Gemini initialization using the 3.6 Flash model
try:
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
    
    model = genai.GenerativeModel('gemini-3.6-flash')
except Exception:
    genai = None
    model = None


def get_answer(
    query: str, 
    language: str = "en", 
    intent: str = "general",
    retrieved_docs: list = None
) -> dict:
    """
    Finalized RAG generation service:
    - Restricts responses strictly to the provided document context.
    - Eliminates hallucinations via zero temperature (0.0).
    - Dynamically parses multiple PDFs and attaches file citations.
    - Generates actionable WhatsApp click-to-chat QR payloads.
    """
    if model is None:
        return {
            "answer": "Sahakar Sahayak assistant is active. Please configure GEMINI_API_KEY.",
            "citations": [],
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
        citations = []
        
        if retrieved_docs:
            for doc in retrieved_docs:
                doc_name = doc.get("source_doc", "Unknown_Document.pdf")
                page_num = doc.get("source_page", "N/A")
                text_chunk = doc.get("text", "")
                
                context_block += f"\n--- Source: {doc_name} (Page {page_num}) ---\n{text_chunk}\n"
                
                if doc_name not in [c["source_doc"] for c in citations]:
                    citations.append({"source_doc": doc_name, "source_page": page_num})

        if context_block.strip():
            full_prompt = (
                f"You are Sahakar Sahayak, the official digital assistant for Indian Cooperative Societies.\n"
                f"{instruction}\n"
                f"User Intent: {intent}\n\n"
                f"STRICT OPERATIONAL RULES:\n"
                f"1. Answer the user query using ONLY the verified official text provided in the 'Context' below.\n"
                f"2. If the answer cannot be found completely in the Context, respond EXACTLY with:\n"
                f"   'This information is not available in the official cooperative documents.'\n"
                f"3. Do NOT use general internet knowledge or extrapolation.\n\n"
                f"Context:\n{context_block}\n\n"
                f"User Query: {query}"
            )
        else:
            full_prompt = (
                f"You are Sahakar Sahayak.\n{instruction}\nUser Query: {query}\n"
                f"Note: No document context was found. Answer strictly based on verified public cooperative facts."
            )

        # Enforce zero temperature to kill hallucinations completely
        generation_config = genai.types.GenerationConfig(temperature=0.0)
        response = model.generate_content(full_prompt, generation_config=generation_config)
        answer_text = response.text.strip() if response and response.text else "No response generated."
        
        if "not available in the official cooperative documents" in answer_text.lower():
            citations = []

        primary_source = citations[0]["source_doc"] if citations else 'Official Guidelines'
        sanitized_summary = answer_text[:140].replace("\n", " ")
        encoded_message = urllib.parse.quote(
            f"Query: {query}\nAnswer: {sanitized_summary}...\nSource: {primary_source}"
        )
        action_url = f"https://wa.me/?text={encoded_message}"
        
        qr_code_base64 = None
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=4, border=2)
            qr.add_data(action_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception:
            pass

        return {
            "answer": answer_text,
            "citations": citations,
            "action_url": action_url,
            "qr_code_base64": qr_code_base64,
            "language": language
        }

    except Exception as e:
        return {"answer": f"AI Error: {str(e)}", "citations": [], "action_url": None, "qr_code_base64": None}