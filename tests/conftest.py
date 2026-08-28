import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.database import Base
from app.models.company import Company
from app.models.company_config import CompanyConfig
from app.models.workflow import Workflow
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.message import Message
from app.models.pending_flow import PendingFlow
from app.models.execution import Execution
from app.models.user import User


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session():
    """Cria um banco SQLite em memoria para cada teste."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def company(db_session):
    c = Company(name="Empresa Teste")
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def config(db_session, company):
    from app.services.config_service import get_or_create_config
    cfg = get_or_create_config(db_session, company.id)
    cfg.ai_provider = "mock"
    cfg.ai_model = "mock-model"
    cfg.ai_api_key = "mock-key"
    cfg.ai_base_url = "http://mock"
    cfg.evolution_base_url = "http://evo"
    cfg.evolution_api_key = "evo-key"
    cfg.evolution_instance = "default"
    cfg.system_prompt = "Voce e um assistente."
    cfg.ai_on = True
    db_session.commit()
    db_session.refresh(cfg)
    return cfg


@pytest.fixture
def customer(db_session, company):
    cust = Customer(company_id=company.id, phone="5511999999999", name="Cliente")
    db_session.add(cust)
    db_session.commit()
    db_session.refresh(cust)
    return cust


@pytest.fixture
def conversation(db_session, company, customer):
    conv = Conversation(company_id=company.id, customer_id=customer.id, status="open")
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)
    return conv


@pytest.fixture
def mock_payload(conversation):
    return {
        "message": {"text": "ola", "from": "5511999999999", "wa_message_id": "wamid_123"},
        "phone": "5511999999999",
        "conversation_id": conversation.id,
        "conversation": {"id": conversation.id},
    }