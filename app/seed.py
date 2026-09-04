from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_config import CompanyConfig
from app.models.user import User
from app.config import get_secret


def seed_default_user(db: Session) -> None:
    """Cria um usuario de teste padrao se o banco estiver vazio e o seed estiver habilitado.

    Controlado por SEED_DEFAULT_USER (ex.: 'true'). Util para desenvolvimento local.
    Nao roda em producao (produção nao define essa var).
    """
    enabled = get_secret("SEED_DEFAULT_USER", "").lower() in ("1", "true", "yes")
    if not enabled:
        return

    existing = db.query(User).first()
    if existing:
        return

    email = get_secret("SEED_USER_EMAIL", "teste@flowai.com")
    password = get_secret("SEED_USER_PASSWORD", "teste123")
    name = get_secret("SEED_USER_NAME", "Usuario Teste")
    company_name = get_secret("SEED_COMPANY_NAME", "Empresa Teste")

    company = Company(name=company_name)
    db.add(company)
    db.flush()

    user = User(
        company_id=company.id,
        name=name,
        email=email,
        role="owner",
    )
    user.set_password(password)
    db.add(user)

    db.add(CompanyConfig(company_id=company.id))
    db.commit()

    print(f"[seed] Usuario de teste criado: {email} (empresa: {company_name})")
