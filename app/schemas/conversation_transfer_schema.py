from pydantic import BaseModel


class ConversationTransferResponse(BaseModel):
    id: int
    action: str
    actor_type: str
    user_name: str
    created_at: object | None = None

    class Config:
        from_attributes = True