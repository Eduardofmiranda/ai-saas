from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class TestRunRequest(BaseModel):
    # dados de entrada para disparar o workflow (ex: mensagem simulada)
    payload: dict[str, Any] = {}
    # se true, executa de forma síncrona e retorna o resultado (para testes no editor)
    await_result: bool = True


class ExecutionResponse(BaseModel):
    id: int
    workflow_id: int
    company_id: int
    status: str
    context: dict[str, Any]
    node_results: dict[str, Any]
    error: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
