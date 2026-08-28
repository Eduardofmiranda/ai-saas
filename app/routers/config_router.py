from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.config_schema import ConfigResponse, ConfigUpdate
from app.services.config_service import get_or_create_config
from app.services.deps import get_current_user
from app.services.field_crypto import encrypt_field

router = APIRouter(prefix="/config", tags=["Config"])

# Valor enviado pelo frontend para representar "nao alterar a chave"
_MASKED = "__MASKED__"

# campos sensiveis que devem ser criptografados em repouso
_SENSITIVE_FIELDS = ("ai_api_key", "evolution_api_key")


def _to_response(config) -> ConfigResponse:
    return ConfigResponse(
        company_id=config.company_id,
        ai_provider=config.ai_provider,
        ai_model=config.ai_model,
        ai_base_url=config.ai_base_url,
        system_prompt=config.system_prompt,
        evolution_base_url=config.evolution_base_url,
        evolution_instance=config.evolution_instance,
        ai_on=config.ai_on,
    )


@router.get("/", response_model=ConfigResponse)
def get_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = get_or_create_config(db, current_user.company_id)
    return _to_response(config)


@router.patch("/", response_model=ConfigResponse)
def update_config(
    data: ConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = get_or_create_config(db, current_user.company_id)

    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field in _SENSITIVE_FIELDS:
            if value in (None, "", _MASKED):
                continue  # nao altera a chave existente
            setattr(config, field, encrypt_field(value))
        else:
            setattr(config, field, value)

    db.commit()
    db.refresh(config)
    return _to_response(config)
