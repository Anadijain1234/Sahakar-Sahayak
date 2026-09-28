import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from pydantic import BaseModel

from backend.models.schemas import QueryRequest, QueryResponse

from backend.services.nlp_service import (
    preprocess_query,
    detect_intent,
    validate_language
)
from backend.services.rag_service import get_answer, normalize_query, lexicon_terms
from backend.services.reqlog import new_request_id, log
from backend.services.retriever import search
from backend.services.help_contacts import helplines_for
from backend.services import analytics
from backend.services import live_judge

# Friendly names for the Insights page (keys = file-name parts used by scheme routing)
TOPIC_NAMES = {
    "PM-KISAN": "PM-KISAN", "doc1": "PMFBY crop insurance", "RWBCIS": "Weather crop insurance",
    "UPIS": "Package insurance (UPIS)", "405MDD58": "Kisan Credit Card", "PMKSY": "PMKSY irrigation",
    "11of1959": "Karnataka Co-op Act", "247816": "Multi-State Co-op Act", "Model Byelaws": "PACS bye-laws",
    "Initiatives": "PACS initiatives",
}


router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    started = time.perf_counter()
    rid = new_request_id()
    try:
        # 1. Validate target UI output language
        language = validate_language(request.language)

        # 2. Clean query
        cleaned_query = preprocess_query(request.query)
        log("QUERY", f"📩 new question | language={language} | {cleaned_query[:200]!r}")

        # 3. Translate code-mixed input into clean English (Sarvam -> Groq -> Cloudflare)
        english_query, translated_by = normalize_query(cleaned_query)

        # 4. Detect intent
        intent = detect_intent(english_query, language)

        # 5. Hybrid search of the PDFs: keyword (BM25) + spelling + meaning (Cloudflare).
        #    Official scheme names only help find candidates; they don't change the scores.
        boost = lexicon_terms(f"{cleaned_query} {english_query}")
        retrieved_docs, search_stats = search(english_query, boost_terms=boost)
        routed = search_stats.get("scheme_routing") or []
        log("QUERY", f"📚 intent={intent} | {len(retrieved_docs)} pieces found | routed to {routed or 'none'}")

        # 6. Generate answer in user's UI language (Sarvam -> Groq -> Cloudflare -> search-only)
        result = get_answer(
            query=english_query,
            language=language,
            intent=intent,
            retrieved_docs=retrieved_docs,
            search_stats=search_stats,
            original_query=cleaned_query,
        )

        result["language"] = language
        result["intent"] = intent

        # 7. "Talk to a person": official helplines under answers that aren't fully verified
        result["helplines"] = helplines_for(
            f"{cleaned_query} {english_query}", result.get("trust_level"), intent, routed)

        total_ms = round((time.perf_counter() - started) * 1000, 2)
        if isinstance(result.get("search_report"), dict):
            result["search_report"].update({
                "total_time_ms": total_ms,
                "search_query": english_query,
                "request_id": rid,
                "translated_by": translated_by,
                "answered_by": result.get("answered_by"),
            })

        # 8. Log for the admin Insights page (never breaks the answer)
        analytics.log_query(
            question=cleaned_query, english_question=english_query, language=language, intent=intent,
            trust_level=result.get("trust_level"), answer_source=result.get("answer_source"),
            top_document=(result.get("sources") or [{}])[0].get("document"),
            confidence=result.get("confidence"), response_ms=total_ms,
            topics=[TOPIC_NAMES.get(d, d) for d in routed],
            answered_by=result.get("answered_by"),
            report=result.get("search_report"),
            top_page=(result.get("sources") or [{}])[0].get("page"),
        )
        # 9. Keep what the AI judges need; the website asks for the check right after showing the answer
        live_judge.remember(rid, cleaned_query, english_query, result.get("answer"), language,
                            result.get("trust_level"), result.get("answered_by"),
                            [d.get("text", "") for d in retrieved_docs] if result.get("answer_source") == "documents" else [])
        log("QUERY", f"🏁 finished in {total_ms / 1000:.2f}s | translated by {translated_by or 'none'} | "
                     f"answered by {result.get('answered_by')} | trust={result.get('trust_level')} | "
                     f"helplines={len(result['helplines'])}")

        return JSONResponse(
            content=jsonable_encoder(result),
            media_type="application/json; charset=utf-8"
        )

    except Exception as e:
        log("QUERY", f"💥 crashed after {time.perf_counter() - started:.2f}s: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query (request {rid}): {str(e)}"
        )


class JudgeRequest(BaseModel):
    request_id: str


@router.post("/judge")
def judge_answer(request: JudgeRequest):
    """Live AI check of one answer: graded by the AIs that did NOT write it (see live_judge.py).
    Called by the website right after an answer is shown; never delays the answer."""
    return JSONResponse(content=jsonable_encoder(live_judge.judge(request.request_id.strip()[:32])))
