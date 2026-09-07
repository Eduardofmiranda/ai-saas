from app.models.user import User
from app.services.platform_bootstrap import bootstrap_platform_admin


def test_bootstrap_creates_operator_once_and_does_not_reset_password(db_session, monkeypatch):
    values = {
        "PLATFORM_ADMIN_BOOTSTRAP_EMAIL": "gestor@exemplo.com",
        "PLATFORM_ADMIN_BOOTSTRAP_PASSWORD": "senha-temporaria-segura",
        "PLATFORM_ADMIN_NAME": "Gestor",
        "PLATFORM_ADMIN_COMPANY_NAME": "Plataforma",
    }
    monkeypatch.setattr("app.services.platform_bootstrap.get_secret", lambda name, default="": values.get(name, default))

    assert bootstrap_platform_admin(db_session) is True
    user = db_session.query(User).filter(User.email == "gestor@exemplo.com").first()
    assert user is not None
    assert user.is_platform_admin is True
    assert user.verify_password("senha-temporaria-segura")

    values["PLATFORM_ADMIN_BOOTSTRAP_PASSWORD"] = "outra-senha-segura"
    assert bootstrap_platform_admin(db_session) is False
    assert user.verify_password("senha-temporaria-segura")