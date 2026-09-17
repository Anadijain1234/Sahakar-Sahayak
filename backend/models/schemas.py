from pydantic import BaseModel
from typing import Optional, List

class QueryRequest(BaseModel):
    query: str
    language: str

class Source(BaseModel):
    document: str
    page: Optional[int] = None

class QueryResponse(BaseModel):
    answer: str
    language: str
    intent: str
    sources: List[Source] = []
    confidence: float = 0.0
    action_url: Optional[str] = None
    qr_code_base64: Optional[str] = None