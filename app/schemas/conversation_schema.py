from typing import Optional

from pydantic import BaseModel

from app.schemas.customer_schema import CustomerResponse


class ConversationCreate(BaseModel):
    customer_id: int


class ConversationUpdate(BaseModel):
    status: str


class ConversationResponse(BaseModel):
    id: int
    company_id: int
    customer_id: int
    status: str
    created_at: object | None = None
    updated_at: object | None = None
    customer: Optional[CustomerResponse] = None
    last_message: Optional[str] = None
    last_message_at: object | None = None
    message_count: int = 0

    class Config:
        from_attributes = True
