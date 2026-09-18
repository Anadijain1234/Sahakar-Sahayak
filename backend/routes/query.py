from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from backend.models.schemas import QueryRequest, QueryResponse

from backend.services.nlp_service import (
    preprocess_query,
    detect_intent,
    validate_language
)
from backend.services.rag_service import get_answer, normalize_query_to_english
from backend.services.retriever import retrieve_documents


router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    try:
        # 1. Validate target UI output language
        language = validate_language(request.language)

        # 2. Clean query
        cleaned_query = preprocess_query(request.query)

        # 3. Translate code-mixed input into clean English
        english_query = normalize_query_to_english(cleaned_query)

        # 4. Detect intent
        intent = detect_intent(english_query, language)

        # 5. Retrieve top matching PDF paragraphs via FAISS
        retrieved_docs = retrieve_documents(english_query, top_k=3)

        # 6. Generate answer in user's UI language with English citations preserved
        result = get_answer(
            query=english_query,
            language=language,
            intent=intent,
            retrieved_docs=retrieved_docs
        )

        result["language"] = language
        result["intent"] = intent

        return JSONResponse(
            content=jsonable_encoder(result),
            media_type="application/json; charset=utf-8"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )