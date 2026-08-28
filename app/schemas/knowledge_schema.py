from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class KnowledgeCreate(BaseModel):
    name: str
    description: str = ""
    content: str


class KnowledgeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None


class KnowledgeResponse(BaseModel):
    id: int
    company_id: int
    name: str
    description: str
    source_type: str
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeDetail(BaseModel):
    id: int
    company_id: int
    name: str
    description: str
    source_type: str
    chunks: list[dict] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeSearch(BaseModel):
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    chunk_id: int
    knowledge_id: int
    content: str
    tokens: int
    similarity: float
