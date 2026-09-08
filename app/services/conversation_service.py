import logging

from sqlalchemy.orm import Session

from app.config import get_secret
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.message import Message
from app.models.pending_flow import PendingFlow
from app.models.workflow import Workflow
from app.services import evolution, llm
from app.services.config_service import get_or_create_config, resolve_ai_config
from app.services.field_crypto import decrypt_field

logger = logging.getLogger(__name__)


async def _send_closed_reply(db: Session, conversation, config, phone: str) -> str:
    """Resposta automatica fora do horario de atendimento.

    Envia apenas uma vez por conversa (enquanto o expediente estiver fechado),
    para nao spammar o cliente a cada mensagem. Retorna o que foi feito.
    """
    from app.models.business_hours import BusinessHours
    from app.services.business_hours import is_open

    bh = db.query(BusinessHours).filter(BusinessHours.company_id == config.company_id).first()
    if not bh or not bh.enabled or is_open(bh):
        return "no_gate"

    message = (bh.message or "").strip()
    if not message:
        return "no_message"

    last_bot = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id, Message.sender_type == "bot")
        .order_by(Message.id.desc())
        .first()
    )
    if last_bot and last_bot.content == message:
        return "already_sent"

    evolution_base = decrypt_field(config.evolution_base_url) or get_secret("EVOLUTION_BASE_URL")
    evolution_key = decrypt_field(config.evolution_api_key) or get_secret("EVOLUTION_API_KEY")
    evolution_inst = config.evolution_instance or get_secret("EVOLUTION_INSTANCE") or "default"

    if not evolution_base:
        return "no_evolution"

    try:
        await evolution.send_text(
            to_phone=phone,
            text=message,
            base_url=evolution_base,
            api_key=evolution_key,
            instance=evolution_inst,
        )
    except evolution.EvolutionError:
        logger.warning("Resposta fora do horario nao enviada.", extra={"company_id": config.company_id})
        return "send_failed"

    bot_msg = Message(conversation_id=conversation.id, sender_type="bot", content=message)
    db.add(bot_msg)
    db.commit()
    return "sent"


async def handle_incoming_message(
    db: Session,
    *,
    company_id: int,
    phone: str,
    text: str,
    wa_message_id: str = "",
    push_name: str = "",
) -> dict:
    """Pipeline de atendimento: mensagem recebida -> IA -> resposta no WhatsApp."""

    # 1) Deduplicacao: ja processamos este id do WhatsApp?
    existing = None
    if wa_message_id:
        existing = (
            db.query(Message)
            .filter(Message.wa_message_id == wa_message_id)
            .first()
        )
        if existing:
            return {"status": "duplicated"}

    # 2) Encontra ou cria o cliente (com lock para evitar race condition)
    from sqlalchemy import select

    customer = (
        db.execute(
            select(Customer)
            .where(Customer.company_id == company_id, Customer.phone == phone)
            .with_for_update()
        )
        .scalars()
        .first()
    )
    if not customer:
        customer = Customer(company_id=company_id, phone=phone, name=push_name or phone)
        db.add(customer)
        db.flush()
    elif push_name and customer.name == phone:
        customer.name = push_name
        db.flush()

    # 3) Encontra ou cria a conversa ativa (open, agent ou aguardando humano)
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.company_id == company_id,
            Conversation.customer_id == customer.id,
            Conversation.status.in_(["open", "pending_agent", "agent"]),
        )
        .order_by(Conversation.id.desc())
        .first()
    )
    if not conversation:
        conversation = Conversation(
            company_id=company_id,
            customer_id=customer.id,
            status="open",
        )
        db.add(conversation)
        db.flush()

    # 4) Persiste a mensagem do cliente
    incoming = Message(
        conversation_id=conversation.id,
        sender_type="customer",
        content=text,
        wa_message_id=wa_message_id,
    )
    db.add(incoming)
    db.commit()

    # 5) Resolve configuracao da empresa (IA + Evolution) com fallback global
    # Handoff humano (pending_agent ou agent): persiste a mensagem, cancela
    # qualquer espera automatica e nao gera nem retoma respostas da IA.
    if conversation.status in ("pending_agent", "agent"):
        db.query(PendingFlow).filter(
            PendingFlow.company_id == company_id,
            PendingFlow.phone == phone,
        ).delete(synchronize_session=False)
        db.commit()
        return {"status": "pending_agent", "conversation_id": conversation.id}

    config = get_or_create_config(db, company_id)

    # Fora do horario de atendimento: responde com a mensagem configurada
    # (uma unica vez) e nao gera nem retoma respostas da IA.
    if conversation.status not in ("pending_agent", "agent"):
        closed_status = await _send_closed_reply(db, conversation, config, phone)
        if closed_status in ("sent", "already_sent", "send_failed", "no_evolution"):
            return {"status": "closed", "conversation_id": conversation.id}

    resolved_ai = resolve_ai_config(config, db)
    ai_provider = resolved_ai["provider"]
    ai_model = resolved_ai["model"]
    ai_api_key = resolved_ai["api_key"]
    ai_base_url = resolved_ai["base_url"]

    evolution_base = decrypt_field(config.evolution_base_url) or get_secret("EVOLUTION_BASE_URL")
    evolution_key = decrypt_field(config.evolution_api_key) or get_secret("EVOLUTION_API_KEY")
    evolution_inst = config.evolution_instance or get_secret("EVOLUTION_INSTANCE") or "default"

    # 6) Gera resposta com IA (se habilitada e configuravel)
    reply_text: str | None = None
    if config.ai_on:
        history_messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.id.asc())
            .all()
        )
        history = evolution.build_history(history_messages)
        try:
            # Agenda habilitada: ativa as tools da Secretaria IA (function calling).
            # Sem agenda ou desativada: atende normalmente, sem tools (sem mudanca
            # no comportamento, mesmo para provedores sem suporte a tool_calls).
            from app.services.agenda import get_for_company as get_agenda_for_company
            from app.services.agenda_tools import (
                AGENDA_TOOLS,
                AGENDA_TOOLS_INSTRUCTION,
                execute_agenda_tool,
            )

            agenda_cfg = get_agenda_for_company(db, company_id)
            if agenda_cfg and agenda_cfg.enabled:
                reply_text = await llm.generate_reply_with_tools(
                    system_prompt=(config.system_prompt or "") + AGENDA_TOOLS_INSTRUCTION,
                    history=history,
                    provider=ai_provider,
                    model=ai_model,
                    api_key=ai_api_key,
                    base_url=ai_base_url,
                    tools=AGENDA_TOOLS,
                    execute_tool=lambda name, args, /: execute_agenda_tool(db, company_id, name, args),
                )
            else:
                reply_text = await llm.generate_reply(
                    system_prompt=config.system_prompt,
                    history=history,
                    provider=ai_provider,
                    model=ai_model,
                    api_key=ai_api_key,
                    base_url=ai_base_url,
                )
        except llm.LLMError:
            # IA indisponivel: nao quebra o fluxo. O diagnostico preserva
            # apenas metadados operacionais, nunca prompt, chave ou resposta.
            logger.warning(
                "Resposta da IA indisponivel",
                extra={"company_id": company_id, "provider": ai_provider, "model": ai_model},
            )
            reply_text = None

    # 7) Envia resposta pelo WhatsApp e registra
    if reply_text and evolution_base:
        try:
            await evolution.send_text(
                to_phone=phone,
                text=reply_text,
                base_url=evolution_base,
                api_key=evolution_key,
                instance=evolution_inst,
            )
            bot_msg = Message(
                conversation_id=conversation.id,
                sender_type="bot",
                content=reply_text,
            )
            db.add(bot_msg)
            db.commit()
            db.refresh(conversation)
            return {"status": "replied", "conversation_id": conversation.id}
        except evolution.EvolutionError:
            return {"status": "ai_ready_but_send_failed", "conversation_id": conversation.id}
    elif reply_text:
        # Rascunho gerado mas sem Evolution configurada
        bot_msg = Message(
            conversation_id=conversation.id,
            sender_type="bot",
            content=reply_text,
        )
        db.add(bot_msg)
        db.commit()
        return {"status": "ai_reply_drafted", "conversation_id": conversation.id}

    return {"status": "no_reply", "conversation_id": conversation.id}


async def handle_incoming_workflow(
    db: Session,
    *,
    company_id: int,
    phone: str,
    text: str,
    wa_message_id: str = "",
    push_name: str = "",
) -> dict:
    """Persiste a mensagem recebida e a roteia pelo MOTOR DE WORKFLOWS.

    1. Deduplica e grava o cliente/conversa/mensagem (para memoria).
    2. Se houver um fluxo pausado (PendingFlow) para essa conversa, retoma-o.
    3. Caso contrario, executa o workflow de mensagem ativo da empresa.
    """
    # 1) Deduplicacao
    if wa_message_id:
        existing = db.query(Message).filter(Message.wa_message_id == wa_message_id).first()
        if existing:
            return {"status": "duplicated"}

    # 2) Cliente (com lock para evitar race condition na criacao de conversas)
    from sqlalchemy import select

    customer = (
        db.execute(
            select(Customer)
            .where(Customer.company_id == company_id, Customer.phone == phone)
            .with_for_update()
        )
        .scalars()
        .first()
    )
    if not customer:
        customer = Customer(company_id=company_id, phone=phone, name=push_name or phone)
        db.add(customer)
        db.flush()
    elif push_name and customer.name == phone:
        customer.name = push_name
        db.flush()

    # 3) Conversa ativa (open, agent ou aguardando humano)
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.company_id == company_id,
            Conversation.customer_id == customer.id,
            Conversation.status.in_(["open", "pending_agent", "agent"]),
        )
        .order_by(Conversation.id.desc())
        .first()
    )
    if not conversation:
        conversation = Conversation(company_id=company_id, customer_id=customer.id, status="open")
        db.add(conversation)
        db.flush()

    # 4) Mensagem do cliente
    db.add(
        Message(conversation_id=conversation.id, sender_type="customer", content=text, wa_message_id=wa_message_id)
    )
    db.commit()

    # O handoff pertence ao atendente humano: persiste a mensagem, cancela
    # qualquer espera automatica e nao gera nem retoma respostas da IA.
    if conversation.status in ("pending_agent", "agent"):
        db.query(PendingFlow).filter(
            PendingFlow.company_id == company_id,
            PendingFlow.phone == phone,
        ).delete(synchronize_session=False)
        db.commit()
        return {"status": conversation.status, "conversation_id": conversation.id}

    config = get_or_create_config(db, company_id)

    # Fora do horario de atendimento: responde com a mensagem configurada
    # (uma unica vez) e nao executa nem retoma workflows automaticos. O
    # fluxo pausado permanece e volta a ser retomado dentro do expediente.
    if conversation.status not in ("pending_agent", "agent"):
        closed_status = await _send_closed_reply(db, conversation, config, phone)
        if closed_status in ("sent", "already_sent", "send_failed", "no_evolution"):
            return {"status": "closed", "conversation_id": conversation.id}

    customer_name = customer.name if customer and customer.name != phone else ""

    payload = {
        "message": {
            "text": text,
            "from": phone,
            "wa_message_id": wa_message_id,
        },
        "customer": phone,
        "customer_name": customer_name,
        "phone": phone,
        "conversation_id": conversation.id,
        "conversation": {"id": conversation.id},
    }

    # 5) Fluxo pausado? -> retoma
    pending = (
        db.query(PendingFlow)
        .filter(PendingFlow.company_id == company_id, PendingFlow.phone == phone)
        .order_by(PendingFlow.id.desc())
        .first()
    )
    if pending:
        from app.services.workflow_engine import resume_workflow

        execution = await resume_workflow(db, pending=pending, payload=payload, config=config)
        return {"status": "resumed", "execution_id": execution.id, "conversation_id": conversation.id}

    # 6) Workflow de mensagem ativo da empresa
    from app.services.workflow_engine import execute_workflow

    wf = (
        db.query(Workflow)
        .filter(
            Workflow.company_id == company_id,
            Workflow.active.is_(True),
            Workflow.trigger_type == "message",
        )
        .order_by(Workflow.id.asc())
        .first()
    )
    if not wf:
        return {"status": "no_workflow", "conversation_id": conversation.id}

    execution = await execute_workflow(db, workflow=wf, payload=payload, config=config)
    return {
        "status": execution.status,
        "execution_id": execution.id,
        "conversation_id": conversation.id,
    }
