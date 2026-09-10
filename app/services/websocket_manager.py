import json
import logging
from typing import Any

from fastapi import WebSocket

from app.database.session import SessionLocal
from app.services.security import decode_access_token
from app.services import access_rules

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Gerencia conexoes WebSocket ativas por empresa."""

    def __init__(self):
        self._connections: dict[int, list[tuple[WebSocket, int]]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        company_id: int,
        user_id: int,
        *,
        subprotocol: str | None = None,
    ):
        await websocket.accept(subprotocol=subprotocol)
        self._connections.setdefault(company_id, []).append((websocket, user_id))

    def disconnect(self, websocket: WebSocket, company_id: int):
        conns = self._connections.get(company_id, [])
        self._connections[company_id] = [entry for entry in conns if entry[0] is not websocket]

    @staticmethod
    def _can_receive(db, company_id: int, user_id: int, event: str, data: Any) -> bool:
        if not event.startswith("message."):
            return True

        from app.models.conversation import Conversation
        from app.models.customer import Customer
        from app.models.user import User

        user = db.query(User).filter(User.id == user_id, User.company_id == company_id).first()
        if not user:
            return False

        department_id = None
        resolved = False
        if isinstance(data, dict) and "department_id" in data:
            department_id = data.get("department_id")
            resolved = True
        elif isinstance(data, dict) and data.get("conversation_id"):
            conversation = db.query(Conversation).filter(
                Conversation.id == data["conversation_id"],
                Conversation.company_id == company_id,
            ).first()
            if conversation:
                department_id = conversation.department_id
                resolved = True
        elif isinstance(data, dict) and data.get("phone"):
            conversation = (
                db.query(Conversation)
                .join(Customer, Conversation.customer_id == Customer.id)
                .filter(
                    Conversation.company_id == company_id,
                    Customer.company_id == company_id,
                    Customer.phone == data["phone"],
                )
                .order_by(Conversation.id.desc())
                .first()
            )
            if conversation:
                department_id = conversation.department_id
                resolved = True

        # Eventos de mensagem sem conversa resolvida podem conter PII. Em caso
        # de incerteza, entrega apenas a gestores em vez de vazar entre setores.
        if not resolved:
            return access_rules.has_full_access(user)
        return access_rules.can_view_department(db, user, department_id)

    async def broadcast(self, company_id: int, event: str, data: Any):
        conns = self._connections.get(company_id, [])
        if not conns:
            return
        payload = json.dumps({"event": event, "data": data}, default=str, ensure_ascii=False)
        dead = []
        db = SessionLocal()
        try:
            recipients = [
                (ws, user_id)
                for ws, user_id in list(conns)
                if self._can_receive(db, company_id, user_id, event, data)
            ]
        finally:
            db.close()
        for ws, _user_id in recipients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, company_id)

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
