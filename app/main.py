from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # registra todos os models no Base.metadata
from app.config import get_secret
from app.database.database import Base, engine, SessionLocal

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Garante que todas as tabelas existam no boot.
    # Evita depender de rodar `create_all` manualmente apos o deploy.
    Base.metadata.create_all(bind=engine)

    # Seed de usuario de teste (apenas dev, controlado por SEED_DEFAULT_USER)
    db = SessionLocal()
    try:
        from app.seed import seed_default_user
        seed_default_user(db)
    finally:
        db.close()

    yield


app = FastAPI(title="AI SaaS - Atendimento WhatsApp", lifespan=lifespan)

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

# Rate limiting via slowapi (se instalado)
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"detail": "Muitas requisicoes. Tente novamente em alguns segundos."},
        )
except ImportError:
    pass

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


@app.get("/")
def home():
    return {"status": "online"}


@app.get("/health")
def health():
    return {"status": "healthy"}
