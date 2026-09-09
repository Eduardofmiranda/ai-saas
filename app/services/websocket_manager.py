import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.services.security import decode_access_token

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gerencia conexoes WebSocket ativas por empresa."""

    def __init__(self):
        self._connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, company_id: int):
        await websocket.accept()
        self._connections.setdefault(company_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, company_id: int):
        conns = self._connections.get(company_id, [])
        if websocket in conns:
            conns.remove(websocket)

    async def broadcast(self, company_id: int, event: str, data: Any):
        conns = self._connections.get(company_id, [])
        if not conns:
            return
        payload = json.dumps({"event": event, "data": data}, default=str, ensure_ascii=False)
        dead = []
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.remove(ws)

    def count(self, company_id: int) -> int:
        return len(self._connections.get(company_id, []))


manager = ConnectionManager()


def authenticate_ws_token(token: str) -> int | None:
    """Valida token JWT e retorna user_id. Retorna None se invalido."""
    payload = decode_access_token(token)
    if not payload or payload.get("type") != "access" or not payload.get("sub"):
        return None
    try:
        return int(payload["sub"])
    except (TypeError, ValueError):
        return None


def get_company_id_for_user(user_id: int) -> int | None:
    """Busca company_id do usuario. Retorna None se nao encontrado."""
    db = SessionLocal()
    try:
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        return user.company_id if user else None
    finally:
        db.close()
