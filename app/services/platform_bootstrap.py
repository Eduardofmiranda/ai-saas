"""Bootstrap único da conta de operador da plataforma via ambiente."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import get_secret
from app.models.company import Company
from app.models.user import User

logger = logging.getLogger(__name__)


def bootstrap_platform_admin(db: Session) -> bool:
    """Cria ou promove uma conta de plataforma uma única vez.

    A senha de bootstrap é usada somente ao criar/promover a conta. Depois que
    ``is_platform_admin`` estiver persistido, deixar as variáveis no `.env` não
    redefine a senha em novos reinícios.
    """
    email = get_secret("PLATFORM_ADMIN_BOOTSTRAP_EMAIL").casefold()
    password = get_secret("PLATFORM_ADMIN_BOOTSTRAP_PASSWORD")
    if not email and not password:
        return False
    if not email or not password:
        logger.warning("Bootstrap de plataforma ignorado: email ou senha ausente")
        return False
    if "@" not in email or len(password) < 12:
        logger.warning("Bootstrap de plataforma ignorado: dados de acesso invalidos")
        return False

    user = db.query(User).filter(User.email == email).first()
    if user and user.is_platform_admin:
        return False

    if not user:
        company_name = get_secret("PLATFORM_ADMIN_COMPANY_NAME", "Administração da Plataforma")
        user_name = get_secret("PLATFORM_ADMIN_NAME", "Administrador da Plataforma")
        company = Company(name=company_name)
        db.add(company)
        db.flush()
        user = User(
            company_id=company.id,
            name=user_name,
            email=email,
            role="owner",
            is_platform_admin=True,
        )
        user.set_password(password)
        db.add(user)
    else:
        # Promove uma conta existente e substitui a senha apenas nesta primeira
        # promoção explícita por ambiente.
        user.is_platform_admin = True
        user.set_password(password)

    db.commit()
    logger.info("Conta de operador da plataforma inicializada")
    return True