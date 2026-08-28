from pydantic import BaseModel


class DashboardResponse(BaseModel):
    companies: int
    customers: int
    conversations: int
    open_conversations: int
    closed_conversations: int
    messages: int