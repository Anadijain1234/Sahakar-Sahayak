import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from backend.models.schemas import QueryRequest, QueryResponse

from backend.services.nlp_service import (
    preprocess_query,
    detect_intent,
    validate_language
)
from backend.services.rag_service import get_answer, normalize_query_to_english, lexicon_terms
from backend.services.retriever import search


router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    started = time.perf_counter()
    try:
        # 1. Validate target UI output language
        language = validate_language(request.language)

        # 2. Clean query
        cleaned_query = preprocess_query(request.query)

        # 3. Translate code-mixed input into clean English
        english_query = normalize_query_to_english(cleaned_query)

        # 4. Detect intent
        intent = detect_intent(english_query, language)

        # 5. Hybrid search of the PDFs: keyword (BM25) + spelling + meaning (Cloudflare).
        #    Official scheme names only help find candidates; they don't change the scores.
        boost = lexicon_terms(f"{cleaned_query} {english_query}")
        retrieved_docs, search_stats = search(english_query, boost_terms=boost)

        # 6. Generate answer in user's UI language with English citations preserved
        result = get_answer(
            query=english_query,
            language=language,
            intent=intent,
            retrieved_docs=retrieved_docs,
            search_stats=search_stats,
        )

        result["language"] = language
        result["intent"] = intent
        if isinstance(result.get("search_report"), dict):
            result["search_report"]["total_time_ms"] = round((time.perf_counter() - started) * 1000, 2)
            result["search_report"]["search_query"] = english_query

        return JSONResponse(
            content=jsonable_encoder(result),
            media_type="application/json; charset=utf-8"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )