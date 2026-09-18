import os
import json
import re
from pypdf import PdfReader
from rank_bm25 import BM25Okapi

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS_DIR = os.path.join(BASE_DIR, "backend", "data", "documents")
if not os.path.exists(DOCS_DIR):
    DOCS_DIR = "/workspaces/Sahakar-Sahayak/backend/data/documents"
METADATA_PATH = os.path.join(BASE_DIR, "backend", "data", "metadata.json")

bm25 = None
documents_metadata = []


def tokenize(text: str) -> list:
    """Cleans and splits text into searchable keyword tokens."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return [word for word in cleaned.split() if len(word) > 2]


def build_or_load_index():
    """Extracts text from PDFs, tokenizes chunks, and builds the BM25 index."""
    global bm25, documents_metadata

    if not os.path.exists(DOCS_DIR):
        print(f"❌ Documents directory not found: {DOCS_DIR}")
        return

    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".pdf")]
    chunks = []
    metadata_list = []

    for pdf_name in pdf_files:
        pdf_path = os.path.join(DOCS_DIR, pdf_name)
        try:
            reader = PdfReader(pdf_path)
            for page_idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                paragraphs = page_text.split("\n\n")
                for para in paragraphs:
                    clean_para = " ".join(para.split())
                    if len(clean_para) > 60:
                        chunks.append(clean_para)
                        metadata_list.append({
                            "document": pdf_name,
                            "page": page_idx + 1,
                            "text": clean_para
                        })
        except Exception as e:
            print(f"Error reading {pdf_name}: {e}")

    if not chunks:
        print("❌ No readable text chunks found in PDFs.")
        return

    tokenized_corpus = [tokenize(chunk) for chunk in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    documents_metadata = metadata_list

    os.makedirs(os.path.dirname(METADATA_PATH), exist_ok=True)
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(documents_metadata, f, ensure_ascii=False)

    print(f"✅ BM25 search index built successfully ({len(chunks)} chunks).")


def retrieve_documents(query: str, top_k: int = 3, threshold: float = 0.0) -> list:
    """Searches documents via BM25 matching without requiring any API keys."""
    global bm25, documents_metadata
    if bm25 is None or not documents_metadata:
        build_or_load_index()

    if bm25 is None or len(documents_metadata) == 0:
        return []

    tokenized_query = tokenize(query)
    scores = bm25.get_scores(tokenized_query)

    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    results = []
    for idx in top_indices:
        if scores[idx] > threshold:
            doc_data = documents_metadata[idx].copy()
            doc_data["similarity_score"] = float(scores[idx])
            results.append(doc_data)

    return results


try:
    build_or_load_index()
except Exception as e:
    print(f"Retriever initialization warning: {e}")