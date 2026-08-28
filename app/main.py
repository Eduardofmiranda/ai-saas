from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models

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

app = FastAPI(title="AI SaaS - Atendimento WhatsApp")

# Frontend (Vite) acessa o backend de outra porta
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/")
def home():
    return {"status": "online"}
