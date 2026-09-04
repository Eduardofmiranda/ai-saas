from sqlalchemy.orm import Session

from app.config import get_secret
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.message import Message
from app.models.pending_flow import PendingFlow
from app.models.workflow import Workflow
from app.services import evolution, llm
from app.services.config_service import get_or_create_config
from app.services.field_crypto import decrypt_field


async def handle_incoming_message(
    db: Session,
    *,
    company_id: int,
    phone: str,
    text: str,
    wa_message_id: str = "",
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

    # 2) Encontra ou cria o cliente
    customer = (
        db.query(Customer)
        .filter(
            Customer.company_id == company_id,
            Customer.phone == phone,
        )
        .first()
    )
    if not customer:
        customer = Customer(company_id=company_id, phone=phone, name=phone)
        db.add(customer)
        db.flush()

    # 3) Encontra ou cria a conversa ativa (open ou aguardando humano)
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.company_id == company_id,
            Conversation.customer_id == customer.id,
            Conversation.status.in_(["open", "pending_agent"]),
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
    config = get_or_create_config(db, company_id)

    ai_provider = config.ai_provider or get_secret("DEFAULT_AI_PROVIDER") or "groq"
    ai_model = config.ai_model or get_secret("DEFAULT_AI_MODEL")
    ai_api_key = decrypt_field(config.ai_api_key) or get_secret("DEFAULT_AI_API_KEY")
    ai_base_url = decrypt_field(config.ai_base_url) or get_secret("DEFAULT_AI_BASE_URL")

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
            reply_text = await llm.generate_reply(
                system_prompt=config.system_prompt,
                history=history,
                provider=ai_provider,
                model=ai_model,
                api_key=ai_api_key,
                base_url=ai_base_url,
            )
        except llm.LLMError:
            # IA indisponivel: nao quebra o fluxo, apenas registra
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

    # 2) Cliente
    customer = (
        db.query(Customer)
        .filter(Customer.company_id == company_id, Customer.phone == phone)
        .first()
    )
    if not customer:
        customer = Customer(company_id=company_id, phone=phone, name=phone)
        db.add(customer)
        db.flush()

    # 3) Conversa ativa (open ou aguardando humano)
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.company_id == company_id,
            Conversation.customer_id == customer.id,
            Conversation.status.in_(["open", "pending_agent"]),
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

    config = get_or_create_config(db, company_id)

    payload = {
        "message": {
            "text": text,
            "from": phone,
            "wa_message_id": wa_message_id,
        },
        "customer": phone,
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
