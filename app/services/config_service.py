from sqlalchemy.orm import Session

from app.models.company_config import CompanyConfig


def get_or_create_config(db: Session, company_id: int) -> CompanyConfig:
    """Retorna a configuracao da empresa, criando com defaults se nao existir."""
    config = (
        db.query(CompanyConfig)
        .filter(CompanyConfig.company_id == company_id)
        .first()
    )
    if not config:
        config = CompanyConfig(company_id=company_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def get_config(db: Session, company_id: int) -> CompanyConfig | None:
    return (
        db.query(CompanyConfig)
        .filter(CompanyConfig.company_id == company_id)
        .first()
    )
