from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User
from app.services import evolution, llm
from app.services.config_service import get_config
from app.models.company_config import CompanyConfig
from app.models.message import Message
from app.config import get_secret
from app.services.field_crypto import decrypt_field


def _get(data, path: str):
    """Acessa data["a"]["b"] via notacao a.b.c. Retorna None se inexistente."""
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


class NodeError(Exception):
    """Erro de execucao de um no que deve parar (ou desviar) o fluxo."""

    def __init__(self, message: str, node_id: str = ""):
        super().__init__(message)
        self.message = message
        self.node_id = node_id


class NodeContext:
    """Contexto compartilhado de uma execucao passado para cada no."""

    def __init__(
        self,
        *,
        db: Session,
        company_id: int,
        execution_id: int,
        workflow_id: int,
        data: dict,
        config: CompanyConfig,
    ):
        self.db = db
        self.company_id = company_id
        self.execution_id = execution_id
        self.workflow_id = workflow_id
        # dados mutaveis compartilhados entre os nos
        self.data = data
        self.config = config
        # log da execucao
        self.logs: list[str] = []

    def log(self, message: str) -> None:
        self.logs.append(message)

    # --- helpers de servico ---

    async def load_history(self, *, force: bool = False) -> list[dict]:
        """Carrega o historico de mensagens da conversa atual (se houver) para usar como contexto.

        Prioriza uma `conversation_id` persistida no contexto; caso contrario tenta
        montar o historico a partir de `data.conversation.messages` fornecido no payload.
        """
        conv_id = self.data.get("conversation_id") or (self.data.get("conversation") or {}).get("id")
        if conv_id:
            msgs = (
                self.db.query(Message)
                .filter(Message.conversation_id == conv_id)
                .order_by(Message.id.asc())
                .all()
            )
            if msgs:
                return evolution.build_history(msgs)

        conv = _get(self.data, "conversation.messages")
        if isinstance(conv, list):
            history = []
            for m in conv:
                sender = m.get("sender_type") if isinstance(m, dict) else getattr(m, "sender_type", None)
                content = m.get("content") if isinstance(m, dict) else getattr(m, "content", None)
                if sender is None:
                    continue
                role = "assistant" if sender == "bot" else "user"
                history.append({"role": role, "content": content or ""})
            return history
        return []

    async def save_bot_message(self, content: str) -> None:
        """Persiste a resposta do bot na conversa atual (se houver uma aberta)."""
        conv_id = self.data.get("conversation_id") or (self.data.get("conversation") or {}).get("id")
        if not conv_id:
            return
        self.db.add(Message(conversation_id=conv_id, sender_type="bot", content=content))
        self.db.commit()

    async def ask_ai(
        self,
        prompt: str,
        *,
        history: list[dict] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Chama o LLM usando a config da empresa (provedor/modelo/chave)."""
        provider = self.config.ai_provider or get_secret("DEFAULT_AI_PROVIDER") or "groq"
        model = self.config.ai_model or get_secret("DEFAULT_AI_MODEL")
        api_key = decrypt_field(self.config.ai_api_key) or get_secret("DEFAULT_AI_API_KEY")
        base_url = decrypt_field(self.config.ai_base_url) or get_secret("DEFAULT_AI_BASE_URL")
        sys_prompt = system_prompt or self.config.system_prompt or "Voce e um assistente."

        if provider == "mock":
            return f"[mock] {prompt[:120]}"

        return await llm.generate_reply(
            system_prompt=sys_prompt,
            history=(history or []) + [{"role": "user", "content": prompt}],
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )

    async def send_whatsapp(self, phone: str, text: str) -> dict:
        """Envia mensagem WhatsApp via Evolution API."""
        base = decrypt_field(self.config.evolution_base_url) or get_secret("EVOLUTION_BASE_URL")
        key = decrypt_field(self.config.evolution_api_key) or get_secret("EVOLUTION_API_KEY")
        instance = (
            self.config.evolution_instance
            or get_secret("EVOLUTION_INSTANCE")
            or "default"
        )
        if not base:
            self.log("Evolution nao configurada; mensagem nao enviada.")
            return {"sent": False, "reason": "no_evolution"}
        await evolution.send_text(
            to_phone=phone,
            text=text,
            base_url=base,
            api_key=key,
            instance=instance,
        )
        return {"sent": True}


# alias pra facilitar import
WorkflowNodeContext = NodeContext
