from pydantic import BaseModel


class DashboardResponse(BaseModel):
    companies: int
    customers: int
    conversations: int
    open_conversations: int
    closed_conversations: int
    messages: int
    workflows_total: int
    workflows_active: int
    executions_total: int
    executions_success: int
    executions_error: int