from typing import List

from pydantic import BaseModel


class DailyCount(BaseModel):
    date: str
    count: int


class DailyExecutions(BaseModel):
    date: str
    success: int
    error: int


class DashboardResponse(BaseModel):
    companies: int
    customers: int
    conversations: int
    open_conversations: int
    pending_conversations: int
    agent_conversations: int
    closed_conversations: int
    messages: int
    workflows_total: int
    workflows_active: int
    executions_total: int
    executions_success: int
    executions_error: int
    messages_last_7_days: List[DailyCount]
    executions_last_7_days: List[DailyExecutions]