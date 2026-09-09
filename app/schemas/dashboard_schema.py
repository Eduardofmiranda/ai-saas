from typing import List

from pydantic import BaseModel


class DailyCount(BaseModel):
    date: str
    count: int


class DailyExecutions(BaseModel):
    date: str
    success: int
    error: int


class DailyAIUsage(BaseModel):
    date: str
    messages: int
    tokens: int


class TopWorkflow(BaseModel):
    workflow_id: int
    name: str
    executions: int
    errors: int


class NodeErrorCount(BaseModel):
    node_id: str
    count: int


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
    conversations_last_30_days: List[DailyCount]
    avg_response_time_minutes: float
    auto_resolved: int
    human_resolved: int
    ai_messages_total: int
    ai_tokens_total: int
    ai_estimated_cost: float
    ai_usage_last_30_days: List[DailyAIUsage]
    top_workflows: List[TopWorkflow]
    errors_by_node: List[NodeErrorCount]