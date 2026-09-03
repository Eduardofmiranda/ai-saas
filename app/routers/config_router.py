import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.config_schema import ConfigResponse, ConfigUpdate
from app.services.config_service import get_or_create_config
from app.services.deps import get_current_user
from app.services.field_crypto import decrypt_field, encrypt_field

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
        has_evolution_key=bool(config.evolution_api_key),
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


# ---------------------------------------------------------------------------
# WhatsApp / Evolution API - conexao
# ---------------------------------------------------------------------------

class WhatsAppTestRequest(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    instance: str | None = None


def _evo_config(config) -> tuple[str | None, str | None, str | None]:
    base_url = decrypt_field(config.evolution_base_url) or config.evolution_base_url
    api_key = decrypt_field(config.evolution_api_key) or config.evolution_api_key
    instance = config.evolution_instance
    return (base_url or None, api_key or None, instance or None)


@router.get("/whatsapp")
def whatsapp_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna o estado atual da conexao WhatsApp (Evolution) da empresa."""
    config = get_or_create_config(db, current_user.company_id)
    base_url, api_key, instance = _evo_config(config)

    if not base_url:
        return {"configured": False, "state": "not_configured", "instance": None, "detail": "Evolution nao configurada"}

    state = "unknown"
    detail = ""
    if not api_key or not instance:
        return {
            "configured": True,
            "state": "needs_config",
            "instance": instance,
            "base_url": base_url,
            "detail": "Falta a API key e/ou o nome da instância na configuração",
        }
    if api_key and instance:
        try:
            from urllib.parse import urljoin
            resp = httpx.get(
                urljoin(base_url.rstrip("/") + "/", f"instance/connectionState/{instance}"),
                headers={"apikey": api_key},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                state = data.get("state", "open" if data.get("instance") else "unknown")
                detail = data.get("status", "")
            elif resp.status_code == 404:
                state = "instance_not_found"
                detail = "Instancia nao encontrada na Evolution"
            else:
                state = "error"
                detail = f"HTTP {resp.status_code}"
        except httpx.HTTPError as exc:
            state = "unreachable"
            detail = str(exc)

    return {
        "configured": True,
        "state": state,
        "instance": instance,
        "base_url": base_url,
        "detail": detail,
    }


@router.post("/whatsapp/test")
async def whatsapp_test(
    data: WhatsAppTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Testa a conexao com a Evolution API (alcance + credenciais)."""
    config = get_or_create_config(db, current_user.company_id)
    base_url = data.base_url or (decrypt_field(config.evolution_base_url) or config.evolution_base_url)
    api_key = data.api_key or (decrypt_field(config.evolution_api_key) or config.evolution_api_key)
    instance = data.instance or config.evolution_instance

    if not base_url:
        raise HTTPException(status_code=400, detail="Informe a URL da Evolution API")

    base = base_url.rstrip("/")
    try:
        resp = httpx.get(
            f"{base}/instance/fetchInstances",
            headers={"apikey": api_key or ""},
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return {
                "ok": True,
                "reachable": True,
                "authenticated": True,
                "detail": "Evolution acessivel e autenticacao valida",
            }
        if resp.status_code == 401:
            return {"ok": False, "reachable": True, "authenticated": False, "detail": "API key invalida (401)"}
        return {"ok": False, "reachable": True, "authenticated": False, "detail": f"HTTP {resp.status_code}"}
    except httpx.HTTPError as exc:
        return {"ok": False, "reachable": False, "authenticated": False, "detail": f"Sem conexao: {exc}"}


def _evolve_pair(base_url: str | None, api_key: str | None, instance: str | None) -> tuple[str, str, str]:
    """Valida e devolve (base, key, instance) para chamadas a Evolution, ou levanta HTTPException."""
    if not base_url:
        raise HTTPException(status_code=400, detail="Evolution nao configurada. Informe a URL da Evolution API.")
    if not api_key:
        raise HTTPException(status_code=400, detail="Falta a API key da Evolution na configuração.")
    if not instance:
        raise HTTPException(status_code=400, detail="Falta o nome da instancia na configuração.")
    return base_url.rstrip("/"), api_key, instance


@router.post("/whatsapp/connect")
def whatsapp_connect(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Gera o QR Code para conectar o WhatsApp (Ex: botao "Conectar" na UI).

    Chamada a Evolution `GET /instance/connect/{instance}` e devolve o QR em
    base64. A API key nao e exposta ao navegador (fica no backend).
    """
    config = get_or_create_config(db, current_user.company_id)
    base_url, api_key, instance = _evo_config(config)
    base, key, inst = _evolve_pair(base_url, api_key, instance)

    try:
        resp = httpx.get(f"{base}/instance/connect/{inst}", headers={"apikey": key}, timeout=30)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Sem conexao com a Evolution: {exc}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=f"Evolution retornou HTTP {resp.status_code}")

    data = resp.json()
    qr = (data.get("qrcode") or {}).get("base64")
    if not qr:
        # pode estar conectado ou ainda gerando o QR
        state = (data.get("instance") or {}).get("state")
        detail = "QR indisponível"
        if state == "open":
            detail = "WhatsApp já conectado."
        raise HTTPException(status_code=409, detail=detail)

    # base64 costuma vir como "data:image/png;base64,...." - devolve ja limpo
    if "," in qr:
        qr = qr.split(",", 1)[1]
    return {"qr_base64": qr}


@router.post("/whatsapp/disconnect")
def whatsapp_disconnect(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Desconecta o WhatsApp (Ex: botao "Desconectar" na UI)."""
    config = get_or_create_config(db, current_user.company_id)
    base_url, api_key, instance = _evo_config(config)
    base, key, inst = _evolve_pair(base_url, api_key, instance)

    try:
        resp = httpx.post(f"{base}/instance/logout/{inst}", headers={"apikey": key}, timeout=30)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Sem conexao com a Evolution: {exc}")

    if resp.status_code not in (200, 201, 204):
        raise HTTPException(status_code=resp.status_code, detail=f"Evolution retornou HTTP {resp.status_code}")

    return {"ok": True, "detail": "WhatsApp desconectado."}
