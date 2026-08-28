import httpx

from app.config import get_secret

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap
    return chunks


async def generate_embeddings(
    texts: list[str],
    provider: str = "openai",
    api_key: str = "",
    model: str = "text-embedding-3-small",
    base_url: str = "",
) -> list[list[float]]:
    if not api_key:
        raise ValueError("API key is required for embeddings")

    if not base_url:
        base_url = _resolve_embedding_base_url(provider)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "input": texts,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{base_url}/embeddings",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    sorted_data = sorted(data["data"], key=lambda x: x["index"])
    return [item["embedding"] for item in sorted_data]


async def generate_single_embedding(
    text: str,
    provider: str = "openai",
    api_key: str = "",
    model: str = "text-embedding-3-small",
    base_url: str = "",
) -> list[float]:
    results = await generate_embeddings([text], provider, api_key, model, base_url)
    return results[0]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _resolve_embedding_base_url(provider: str) -> str:
    urls = {
        "openai": "https://api.openai.com/v1",
        "groq": "https://api.groq.com/openai/v1",
        "deepseek": "https://api.deepseek.com",
        "mistral": "https://api.mistral.ai/v1",
    }
    return urls.get(provider, urls["openai"])
