from contextlib import asynccontextmanager
import logging

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

import app.models  # registra todos os models no Base.metadata
from app.config import get_secret
from app.database.database import Base, engine, SessionLocal
from app.services import llm
from app.services.rate_limit import limiter
from app.services.platform_bootstrap import bootstrap_platform_admin

from app.routers.auth_router import router as auth_router
from app.routers.company_router import router as company_router
from app.routers.config_router import router as config_router
from app.routers.customer_router import router as customer_router
from app.routers.conversation_router import router as conversation_router
from app.routers.message_router import router as message_router
from app.routers.dashboard_router import router as dashboard_router
from app.routers.webhook_router import router as webhook_router
from app.routers.workflow_router import router as workflow_router
from app.routers.knowledge_router import router as knowledge_router
from app.routers.template_router import router as template_router
from app.routers.users_router import router as users_router
from app.routers.platform_admin_router import router as platform_admin_router
from app.routers.department_router import router as department_router
from app.routers.outbound_webhook_router import router as outbound_webhook_router
from app.routers.api_key_router import router as api_key_router
from app.routers.agenda_router import router as agenda_router
from app.routers.audit_router import router as audit_router


logger = logging.getLogger("ai_saas")


def _should_auto_create_schema(dialect_name: str, requested: bool) -> bool:
    "create_all e permitido somente no bootstrap SQLite local."
    return dialect_name == "sqlite" and requested


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Em producao o schema e controlado exclusivamente pelo Alembic. SQLite
    # local continua pratico para desenvolvimento/testes sem setup adicional.
    requested_auto_create = get_secret(
        "AUTO_CREATE_SCHEMA",
        "true" if engine.dialect.name == "sqlite" else "false",
    ).lower() in {"1", "true", "yes"}
    if requested_auto_create and engine.dialect.name != "sqlite":
        logger.warning(
            "AUTO_CREATE_SCHEMA ignorado para %s; use migrations Alembic.",
            engine.dialect.name,
        )
    if _should_auto_create_schema(engine.dialect.name, requested_auto_create):
        Base.metadata.create_all(bind=engine)
        logger.info("Schema criado/verificado automaticamente para ambiente local")

    # Seed de usuario de teste (apenas dev, controlado por SEED_DEFAULT_USER)
    db = SessionLocal()
    try:
        from app.seed import seed_default_user
        seed_default_user(db)
        bootstrap_platform_admin(db)
    finally:
        db.close()

    yield


app = FastAPI(title="AI SaaS - Atendimento WhatsApp", lifespan=lifespan)

# OpenAPI security scheme para API key
app.openapi_schema = None

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )
    schema["components"] = schema.get("components", {})
    schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key para acesso externo. Obtenha em /admin.",
        }
    }
    schema["security"] = [{"ApiKeyAuth": []}]
    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi

# CORS configurado via variavel de ambiente
_origins = get_secret("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
allow_origins = [o.strip() for o in _origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting: a mesma instancia e usada pelos decorators das rotas auth.
from slowapi.errors import RateLimitExceeded

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Muitas requisicoes. Tente novamente em alguns segundos."},
    )

app.include_router(auth_router)
app.include_router(company_router)
app.include_router(customer_router)
app.include_router(conversation_router)
app.include_router(message_router)
app.include_router(config_router)
app.include_router(dashboard_router)
app.include_router(webhook_router)
app.include_router(workflow_router)
app.include_router(knowledge_router)
app.include_router(template_router)
app.include_router(users_router)
app.include_router(platform_admin_router)
app.include_router(department_router)
app.include_router(agenda_router)
app.include_router(audit_router)
app.include_router(outbound_webhook_router)
app.include_router(api_key_router)


@app.get("/")
def home():
    return {"status": "online"}


def _health_payload(name: str, check) -> JSONResponse:
    try:
        detail = check()
        return JSONResponse(status_code=200, content={"status": "healthy", "service": name, "detail": detail})
    except Exception:
        logger.warning("Health check indisponivel", extra={"service": name})
        return JSONResponse(status_code=503, content={"status": "unhealthy", "service": name})


@app.get("/health")
def health():
    """Liveness: confirma apenas que o processo HTTP esta em execucao."""
    return {"status": "healthy"}


@app.get("/health/db")
def health_database():
    def check():
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "connected"
    return _health_payload("database", check)


@app.get("/health/redis")
def health_redis():
    def check():
        from redis import Redis

        client = Redis.from_url(get_secret("REDIS_URL", "redis://localhost:6379/0"), socket_connect_timeout=2)
        try:
            return "pong" if client.ping() else "unavailable"
        finally:
            client.close()
    return _health_payload("redis", check)


@app.get("/health/evolution")
def health_evolution():
    def check():
        base_url = get_secret("EVOLUTION_BASE_URL")
        api_key = get_secret("EVOLUTION_API_KEY")
        if not base_url or not api_key:
            raise RuntimeError("Evolution nao configurada")
        response = httpx.get(
            f"{base_url.rstrip('/')}/instance/fetchInstances",
            headers={"apikey": api_key},
            timeout=5,
        )
        response.raise_for_status()
        return "reachable"
    return _health_payload("evolution", check)


@app.get("/health/llm")
def health_llm():
    def check():
        provider = get_secret("DEFAULT_AI_PROVIDER") or "groq"
        resolved = llm._resolve(
            provider,
            get_secret("DEFAULT_AI_MODEL"),
            get_secret("DEFAULT_AI_API_KEY"),
            get_secret("DEFAULT_AI_BASE_URL"),
        )
        if not resolved["base_url"]:
            raise RuntimeError("LLM sem URL")
        if resolved["provider"] not in {"mock", "ollama"} and not resolved["api_key"]:
            raise RuntimeError("LLM sem chave")
        return {"provider": resolved["provider"], "model": resolved["model"], "configured": True}
    return _health_payload("llm", check)
