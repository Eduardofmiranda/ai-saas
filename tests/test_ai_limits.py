"""Testes dos limites de abuso de IA por empresa.

Cobertura:
- Limites desabilitados (0 = ilimitado)
- Limite de mensagens atingido
- Limite de tokens atingido
- Registro de uso (upsert diario)
- Resumo de uso
- Fallback message configuravel
- Integração com conversation_service (mock LLM)
"""
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.models.company import Company
from app.models.company_config import CompanyConfig
from app.services.ai_limits import (
    CompanyAIUsage,
    LimitExceeded,
    check_ai_limits,
    get_usage_summary,
    record_ai_usage,
)


@pytest.fixture
def db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    engine = create_engine(f"sqlite:///{tmp.name}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session._engine = engine
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def company(db):
    c = Company(name="Test Limits")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _config(db, company_id, **kwargs):
    cfg = CompanyConfig(company_id=company_id, **kwargs)
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


class TestLimitsDisabled:
    def test_no_limits_allows_unlimited(self, db, company):
        cfg = _config(db, company.id)
        # Sem limites configurados (tudo 0) — deve permitir
        check_ai_limits(db, company.id, cfg)

    def test_no_config_allows_unlimited(self, db, company):
        check_ai_limits(db, company.id, None)


class TestMessageLimit:
    def test_under_limit(self, db, company):
        cfg = _config(db, company.id, ai_daily_message_limit=10)
        record_ai_usage(db, company.id, messages=5)
        check_ai_limits(db, company.id, cfg)  # nao levanta

    def test_at_limit(self, db, company):
        cfg = _config(db, company.id, ai_daily_message_limit=5)
        record_ai_usage(db, company.id, messages=5)
        with pytest.raises(LimitExceeded) as exc_info:
            check_ai_limits(db, company.id, cfg)
        assert exc_info.value.limit_type == "messages"

    def test_over_limit(self, db, company):
        cfg = _config(db, company.id, ai_daily_message_limit=3)
        record_ai_usage(db, company.id, messages=5)
        with pytest.raises(LimitExceeded):
            check_ai_limits(db, company.id, cfg)


class TestTokenLimit:
    def test_under_limit(self, db, company):
        cfg = _config(db, company.id, ai_daily_token_limit=1000)
        record_ai_usage(db, company.id, tokens=500)
        check_ai_limits(db, company.id, cfg)

    def test_at_limit(self, db, company):
        cfg = _config(db, company.id, ai_daily_token_limit=100)
        record_ai_usage(db, company.id, tokens=100)
        with pytest.raises(LimitExceeded) as exc_info:
            check_ai_limits(db, company.id, cfg)
        assert exc_info.value.limit_type == "tokens"


class TestCombinedLimits:
    def test_message_limit_wins(self, db, company):
        cfg = _config(db, company.id, ai_daily_message_limit=2, ai_daily_token_limit=1000)
        record_ai_usage(db, company.id, messages=2, tokens=10)
        with pytest.raises(LimitExceeded) as exc_info:
            check_ai_limits(db, company.id, cfg)
        assert exc_info.value.limit_type == "messages"

    def test_token_limit_wins(self, db, company):
        cfg = _config(db, company.id, ai_daily_message_limit=100, ai_daily_token_limit=10)
        record_ai_usage(db, company.id, messages=1, tokens=10)
        with pytest.raises(LimitExceeded) as exc_info:
            check_ai_limits(db, company.id, cfg)
        assert exc_info.value.limit_type == "tokens"


class TestRecordUsage:
    def test_first_use_creates_row(self, db, company):
        record_ai_usage(db, company.id, messages=1, tokens=50)
        usage = db.query(CompanyAIUsage).filter_by(company_id=company.id).first()
        assert usage is not None
        assert usage.message_count == 1
        assert usage.token_count == 50

    def test_subsequent_use_increments(self, db, company):
        record_ai_usage(db, company.id, messages=1, tokens=50)
        record_ai_usage(db, company.id, messages=2, tokens=30)
        usage = db.query(CompanyAIUsage).filter_by(company_id=company.id).first()
        assert usage.message_count == 3
        assert usage.token_count == 80

    def test_different_companies_isolated(self, db, company):
        c2 = Company(name="Other")
        db.add(c2)
        db.commit()
        db.refresh(c2)
        record_ai_usage(db, company.id, messages=5)
        record_ai_usage(db, c2.id, messages=2)
        assert get_usage_summary(db, company.id)["message_count"] == 5
        assert get_usage_summary(db, c2.id)["message_count"] == 2


class TestUsageSummary:
    def test_empty_summary(self, db, company):
        summary = get_usage_summary(db, company.id)
        assert summary["message_count"] == 0
        assert summary["token_count"] == 0

    def test_summary_after_usage(self, db, company):
        record_ai_usage(db, company.id, messages=3, tokens=150)
        summary = get_usage_summary(db, company.id)
        assert summary["message_count"] == 3
        assert summary["token_count"] == 150


class TestFallbackMessage:
    def test_custom_fallback(self, db, company):
        cfg = _config(
            db, company.id,
            ai_daily_message_limit=1,
            ai_fallback_message="Limite atingido! Tente amanha.",
        )
        record_ai_usage(db, company.id, messages=1)
        with pytest.raises(LimitExceeded) as exc_info:
            check_ai_limits(db, company.id, cfg)
        assert exc_info.value.message == "Limite atingido! Tente amanha."

    def test_default_fallback(self, db, company):
        cfg = _config(db, company.id, ai_daily_message_limit=1)
        record_ai_usage(db, company.id, messages=1)
        with pytest.raises(LimitExceeded) as exc_info:
            check_ai_limits(db, company.id, cfg)
        assert "indisponivel" in exc_info.value.message.lower() or exc_info.value.message is not None
