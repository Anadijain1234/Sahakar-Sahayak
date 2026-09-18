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


router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):

    try:

        # 1. Validate target output language selected from UI
        language = validate_language(request.language)

        # 2. Clean query
        cleaned_query = preprocess_query(request.query)

        # 3. Normalize mixed speech (Kannada/Marathi/Hindi/English) to pure English
        english_query = normalize_query_to_english(cleaned_query)

        # 4. Detect intent using the normalized English query
        intent = detect_intent(
            english_query,
            language
        )

        print("Original Query :", request.query)
        print("Cleaned Query  :", cleaned_query)
        print("English Query  :", english_query)
        print("Language (UI)  :", language)
        print("Intent         :", intent)

        # 5. Process query through RAG
        # english_query ensures prompt comprehension, language dictates output script
        result = get_answer(
            query=english_query,
            language=language,
            intent=intent
        )

        # 6. Add NLP metadata
        result["language"] = language
        result["intent"] = intent

        # Force UTF-8 JSON response output
        return JSONResponse(
            content=jsonable_encoder(result),
            media_type="application/json; charset=utf-8"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )