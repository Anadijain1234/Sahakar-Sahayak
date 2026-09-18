import os
import json
import numpy as np
from pypdf import PdfReader
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini for vector embeddings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "documents")
INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "faiss_index.bin")
METADATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "metadata.json")

# In-memory storage for runtime speed
index = None
documents_metadata = []


def get_embedding(text: str, task_type: str = "retrieval_query") -> np.ndarray:
    """Generates normalized vector embeddings via Gemini."""
    try:
        res = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type=task_type
        )
        vec = np.array(res["embedding"], dtype=np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
    except Exception as e:
        print(f"Embedding error: {e}")
        return np.zeros(768, dtype=np.float32)


def build_or_load_index():
    """Builds the FAISS index on first run, or loads the saved cache if already present."""
    global index, documents_metadata
    import faiss

    if os.path.exists(INDEX_PATH) and os.path.exists(METADATA_PATH):
        try:
            index = faiss.read_index(INDEX_PATH)
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                documents_metadata = json.load(f)
            print(f"✅ Loaded existing FAISS index with {len(documents_metadata)} document chunks.")
            return
        except Exception as e:
            print(f"Could not load cached index ({e}), rebuilding from PDFs...")

    print("Building FAISS index from documents directory...")
    chunks = []
    metadata_list = []

    if not os.path.exists(DOCS_DIR):
        print(f"❌ Documents directory not found: {DOCS_DIR}")
        return

    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".pdf")]

    for pdf_name in pdf_files:
        pdf_path = os.path.join(DOCS_DIR, pdf_name)
        try:
            reader = PdfReader(pdf_path)
            for page_idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                # Chunk into sections of ~600 words to retain paragraph context
                paragraphs = page_text.split("\n\n")
                for para in paragraphs:
                    clean_para = " ".join(para.split())
                    if len(clean_para) > 60:  # Ignore tiny headers or empty lines
                        chunks.append(clean_para)
                        metadata_list.append({
                            "document": pdf_name,
                            "page": page_idx + 1,
                            "text": clean_para
                        })
        except Exception as e:
            print(f"Error reading {pdf_name}: {e}")

    if not chunks:
        print("No readable text chunks found in PDFs.")
        return

    print(f"Generating embeddings for {len(chunks)} text chunks...")
    vectors = []
    for chunk in chunks:
        vec = get_embedding(chunk, task_type="retrieval_document")
        vectors.append(vec)

    dim = len(vectors[0])
    index = faiss.IndexFlatIP(dim)  # Inner Product on normalized vectors = Cosine Similarity
    index.add(np.array(vectors, dtype=np.float32))

    documents_metadata = metadata_list

    # Save to disk to avoid re-embedding on restarts
    faiss.write_index(index, INDEX_PATH)
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(documents_metadata, f, ensure_ascii=False)

    print(f"✅ FAISS index built and cached successfully ({len(chunks)} chunks).")


def retrieve_documents(query: str, top_k: int = 3, threshold: float = 0.50) -> list:
    """Searches FAISS for the top_k most similar PDF paragraphs matching the query."""
    global index, documents_metadata
    if index is None or not documents_metadata:
        build_or_load_index()

    if index is None or index.ntotal == 0:
        return []

    query_vector = np.array([get_embedding(query, task_type="retrieval_query")], dtype=np.float32)
    scores, indices = index.search(query_vector, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx != -1 and score >= threshold:
            doc_data = documents_metadata[idx].copy()
            doc_data["similarity_score"] = float(score)
            results.append(doc_data)

    return results


# Initialize index on module load
try:
    build_or_load_index()
except Exception as e:
    print(f"Retriever initialization warning: {e}")