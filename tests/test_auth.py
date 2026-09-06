import pytest
from fastapi import HTTPException
from app.services.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_access_token,
)


class TestSecurity:
    def test_password_hash_and_verify(self):
        pwd = "minha_senha_forte_123"
        h = hash_password(pwd)
        assert h != pwd
        assert verify_password(pwd, h) is True
        assert verify_password("errada", h) is False

    def test_token_create_and_decode(self):
        token = create_access_token("user123", {"role": "admin"})
        assert isinstance(token, str)
        assert len(token) > 20

        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"

    def test_token_invalid_returns_none(self):
        assert decode_access_token("token.invalido.aqui") is None
        assert decode_access_token("") is None

    def test_refresh_token_is_tagged_refresh(self):
        token = create_refresh_token("user123")
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    def test_access_token_is_tagged_access(self):
        token = create_access_token("user123")
        payload = decode_access_token(token)
        assert payload["type"] == "access"

    def test_refresh_token_cannot_authenticate_api_request(self, db_session, company):
        from app.models.user import User
        from app.services.deps import get_current_user

        user = User(company_id=company.id, email="auth@test.com", name="Auth")
        user.set_password("senha123")
        db_session.add(user)
        db_session.commit()

        refresh_token = create_refresh_token(str(user.id))
        with pytest.raises(HTTPException) as exc:
            get_current_user(token=refresh_token, db=db_session)
        assert exc.value.status_code == 401

    def test_rate_limiter_is_shared_by_app_and_auth_routes(self):
        from app.main import app
        from app.routers.auth_router import limiter as auth_limiter
        from app.services.rate_limit import limiter as service_limiter

        assert auth_limiter is service_limiter
        assert app.state.limiter is service_limiter