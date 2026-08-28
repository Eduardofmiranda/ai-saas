from pydantic import BaseModel


class MessageCreate(BaseModel):
    conversation_id: int
    sender_type: str
    content: str


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_type: str
    content: str
    wa_message_id: str
    created_at: object | None = None

    class Config:
        from_attributes = True


class MessageUpdate(BaseModel):
    content: str
