from app.services.nodes.context import NodeContext, _get
from app.services.llm import generate_reply
from app.services.config_service import resolve_ai_config, resolve_embedding_config


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
    resolved_ai = resolve_ai_config(ctx.config, ctx.db, user_id=ctx.user_id)
    provider = resolved_ai["provider"]
    api_key = resolved_ai["api_key"]

    embedding_config = resolve_embedding_config()

    # ---------------------------------------------------------
    # Busca semântica na base de conhecimento
    # ---------------------------------------------------------
    from app.services.vector_store import search_similar

    results = await search_similar(
        ctx.db,
        ctx.company_id,
        query,
        provider=embedding_config["provider"],
        api_key=embedding_config["api_key"],
        embedding_model=embedding_config["model"],
        base_url=embedding_config["base_url"],
        top_k=top_k,
        # Um workflow global usa apenas conhecimento global. Um workflow de
        # setor combina conhecimento global com o do proprio setor.
        department_ids=({ctx.department_id} if ctx.department_id is not None else set()),
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
        provider=provider,
        api_key=api_key,
        model=resolved_ai["model"],
        base_url=resolved_ai["base_url"],
    )

    # ---------------------------------------------------------
    # Salvar resposta na conversa
    # ---------------------------------------------------------
    conversation_id = (
        ctx.data.get("conversation_id")
        or (ctx.data.get("conversation") or {}).get("id")
    )

    if conversation_id and ctx.db:
        if ctx.dry_run:
            ctx.log("Teste: resposta da IA RAG nao foi salva na conversa.")
        else:
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
