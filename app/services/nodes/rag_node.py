from app.services.nodes.context import NodeContext, _get
from app.services.llm import generate_reply


async def run_rag_node(ctx: NodeContext, node: dict) -> dict:
    data = node.get("data", {})

    prompt = data.get(
        "prompt",
        "Responda com base no contexto fornecido."
    )

    top_k = int(data.get("top_k", 5))
    system_prompt = data.get("system_prompt", "")

    # ---------------------------------------------------------
    # Interpolação das variáveis do workflow
    # Exemplo:
    # {{ data.message.text }}
    # {{ data.customer }}
    # ---------------------------------------------------------
    query = prompt

    if isinstance(prompt, str):
        import re

        def replace_variable(match):
            path = match.group(1).strip()

            # Aceita:
            # {{ data.message.text }}
            # {{data.message.text}}
            if path.startswith("data."):
                path = path[5:]

            value = _get(ctx.data, path)

            if value is None:
                return ""

            return str(value)

        query = re.sub(
            r"\{\{\s*([^{}]+?)\s*\}\}",
            replace_variable,
            prompt,
        )

    query = query.strip()

    if not query:
        query = prompt

    # ---------------------------------------------------------
    # Configuração da IA
    # ---------------------------------------------------------
    provider = (
        ctx.config.ai_provider
        if ctx.config
        else "openai"
    )

    api_key = (
        ctx.config.ai_api_key
        if ctx.config
        else ""
    )

    if api_key:
        from app.services.field_crypto import decrypt_field

        api_key = decrypt_field(api_key)

    embedding_model = "text-embedding-3-small"

    # ---------------------------------------------------------
    # Busca semântica na base de conhecimento
    # ---------------------------------------------------------
    from app.services.vector_store import search_similar

    results = await search_similar(
        ctx.db,
        ctx.company_id,
        query,
        provider=provider,
        api_key=api_key,
        embedding_model=embedding_model,
        top_k=top_k,
    )

    context_parts = [
        r["content"]
        for r in results
    ]

    context_text = "\n\n".join(context_parts)

    if not context_text:
        context_text = "(nenhum contexto encontrado)"

    # ---------------------------------------------------------
    # Prompt enviado para a IA
    # ---------------------------------------------------------
    ai_prompt = (
        "Contexto da base de conhecimento:\n"
        f"{context_text}\n\n"
        f"Pergunta: {query}"
    )

    history = [
        {
            "role": "user",
            "content": ai_prompt,
        }
    ]

    reply = await generate_reply(
        system_prompt=(
            system_prompt
            or (
                ctx.config.system_prompt
                if ctx.config
                else ""
            )
        ),
        history=history,
        provider=(
            ctx.config.ai_provider
            if ctx.config
            else "mock"
        ),
        api_key=api_key,
        model=(
            ctx.config.ai_model
            if ctx.config
            else None
        ),
        base_url=(
            ctx.config.ai_base_url
            if ctx.config
            else None
        ),
    )

    # ---------------------------------------------------------
    # Salvar resposta na conversa
    # ---------------------------------------------------------
    conversation_id = (
        ctx.data.get("conversation_id")
        or (ctx.data.get("conversation") or {}).get("id")
    )

    if conversation_id and ctx.db:
        try:
            from app.models.message import Message

            msg = Message(
                conversation_id=conversation_id,
                sender_type="bot",
                content=reply,
            )

            ctx.db.add(msg)
            ctx.db.commit()

        except Exception:
            ctx.db.rollback()

    # ---------------------------------------------------------
    # Fontes utilizadas
    # ---------------------------------------------------------
    sources = [
        {
            "knowledge_id": r["knowledge_id"],
            "similarity": r["similarity"],
        }
        for r in results
    ]

    return {
        "outputs": {
            "ai_reply": reply,
            "context_used": context_text[:500],
            "sources": sources,
            "num_sources": len(results),
        }
    }