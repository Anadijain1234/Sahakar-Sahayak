from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class QueryRequest(BaseModel):
    query: str
    language: str

class Source(BaseModel):
    document: str
    page: Optional[int] = None
    link: Optional[str] = None
    score: Optional[float] = None          # final match score of this passage, in %

class QueryResponse(BaseModel):
    answer: str
    language: str
    intent: str
    sources: List[Source] = []
    confidence: float = 0.0                 # 0-1 final confidence of the best passage
    answer_source: Optional[str] = None      # documents | general | refused | error
    trust_level: Optional[str] = None        # verified | partial | general | refused | error
    search_report: Optional[Dict[str, Any]] = None  # numbers shown in the "Search report" panel
    helplines: List[Dict[str, Any]] = []             # official helplines shown under unverified answers
    answered_by: Optional[str] = None                # which AI wrote the answer
    prices: Optional[Dict[str, Any]] = None          # live mandi prices for price questions (mandi_prices.py)
    action_url: Optional[str] = None
    qr_code_base64: Optional[str] = None