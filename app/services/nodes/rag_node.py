from app.services.nodes.context import NodeContext
from app.services.llm import generate_reply


async def run_rag_node(ctx: NodeContext, node: dict) -> dict:
    data = node.get("data", {})
    prompt = data.get("prompt", "Responda com base no contexto fornecido.")
    top_k = int(data.get("top_k", 5))
    system_prompt = data.get("system_prompt", "")

    query = ctx.interpolate(prompt)
    if not query:
        query = prompt

    provider = ctx.config.ai_provider if ctx.config else "openai"
    api_key = ctx.config.ai_api_key if ctx.config else ""

    if api_key:
        from app.services.field_crypto import decrypt_field
        api_key = decrypt_field(api_key)

    embedding_model = "text-embedding-3-small"

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

    context_parts = [r["content"] for r in results]
    context_text = "\n\n".join(context_parts) if context_parts else "(nenhum contexto encontrado)"

    ai_prompt = f"Contexto da base de conhecimento:\n{context_text}\n\nPergunta: {query}"

    history = [{"role": "user", "content": ai_prompt}]

    reply = await generate_reply(
        system_prompt=system_prompt or (ctx.config.system_prompt if ctx.config else ""),
        history=history,
        provider=ctx.config.ai_provider if ctx.config else "mock",
        api_key=api_key,
        model=ctx.config.ai_model if ctx.config else None,
        base_url=ctx.config.ai_base_url if ctx.config else None,
    )

    if ctx.conversation_id and ctx.db:
        try:
            from app.models.message import Message
            msg = Message(
                conversation_id=ctx.conversation_id,
                sender_type="bot",
                content=reply,
            )
            ctx.db.add(msg)
            ctx.db.commit()
        except Exception:
            pass

    sources = [{"knowledge_id": r["knowledge_id"], "similarity": r["similarity"]} for r in results]

    return {
        "outputs": {
            "ai_reply": reply,
            "context_used": context_text[:500],
            "sources": sources,
            "num_sources": len(results),
        }
    }
