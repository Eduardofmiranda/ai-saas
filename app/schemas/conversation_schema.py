from pydantic import BaseModel


class ConversationCreate(BaseModel):
    company_id: int
    customer_id: int


class ConversationUpdate(BaseModel):
    status: str


class ConversationResponse(BaseModel):
    id: int
    company_id: int
    customer_id: int
    status: str

    class Config:
        from_attributes = True