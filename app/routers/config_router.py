import httpx
from fastapi import APIRouter, Depends, HTTPException
from app.config import get_secret
from pydantic import BaseModel
from sqlalchemy.orm import Session


from app.database.session import get_db
from app.models.user import User
from app.schemas.config_schema import ConfigResponse, ConfigUpdate
from app.services import llm
from app.services.config_service import get_or_create_config, resolve_ai_config
from app.services.deps import get_current_user, require_company_manager
from app.services.field_crypto import decrypt_field, encrypt_field
from app.services.platform_access import is_platform_admin

router = APIRouter(prefix="/config", tags=["Config"])

# Valor enviado pelo frontend para representar "nao alterar a chave"
_MASKED = "__MASKED__"

# campos sensiveis que devem ser criptografados em repouso

# Somente o superadmin pode alterar endpoints, provedores ou credenciais.
_PLATFORM_ONLY_FIELDS = {"ai_provider", "ai_model", "ai_api_key", "ai_base_url", "evolution_base_url", "evolution_api_key", "evolution_instance"}

_SENSITIVE_FIELDS = ("ai_api_key", "evolution_api_key")

class AITestRequest(BaseModel):
    ai_provider: str | None = None
    ai_model: str | None = None


def _to_response(config, db: Session, user_id: int | None = None) -> ConfigResponse:
    resolved_ai = resolve_ai_config(config, db, user_id=user_id)
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
        ai_daily_message_limit=config.ai_daily_message_limit,
        ai_daily_token_limit=config.ai_daily_token_limit,
        ai_timeout_seconds=config.ai_timeout_seconds,
        ai_max_retries=config.ai_max_retries,
        ai_fallback_message=config.ai_fallback_message or "",
        resolved_ai_provider=resolved_ai["provider"],
        resolved_ai_model=resolved_ai["model"],
        ai_credential_source=resolved_ai["credential_source"],
    )


@router.get("/", response_model=ConfigResponse)
def get_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = get_or_create_config(db, current_user.company_id)
    return _to_response(config, db, user_id=current_user.id)


@router.patch("/", response_model=ConfigResponse)
def update_config(
    data: ConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = get_or_create_config(db, current_user.company_id)

    updates = data.model_dump(exclude_unset=True)
    protected_updates = set(updates) & _PLATFORM_ONLY_FIELDS
    if protected_updates and not is_platform_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Provedores, credenciais e infraestrutura são gerenciados pelo superadmin",
        )
    requested_provider = (updates.get("ai_provider") or "").strip().lower()
    current_provider = (config.ai_provider or get_secret("DEFAULT_AI_PROVIDER") or "groq").strip().lower()
    # O campo legado ai_api_key não informa a qual provedor pertence. Ao trocar
    # de provedor sem enviar outra chave, descartamos a antiga para impedir que
    # uma chave DeepSeek, por exemplo, seja enviada à OpenAI por engano.
    if requested_provider and requested_provider != current_provider and "ai_api_key" not in updates:
        config.ai_api_key = ""
        config.ai_base_url = ""
    for field, value in updates.items():
        if field in _SENSITIVE_FIELDS:
            if value in (None, "", _MASKED):
                continue  # nao altera a chave existente
            setattr(config, field, encrypt_field(value))
        else:
            setattr(config, field, value)

    db.commit()
    db.refresh(config)
    return _to_response(config, db, user_id=current_user.id)


@router.post("/ai/test")
async def ai_test(
    data: AITestRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Testa a configuracao de IA da empresa chamando o provedor com um prompt curto.

    Usa a mesma resolucao do fluxo real (config da empresa -> .env -> default):
    provider/modelo/chave/base_url. Nao persiste nada.
    """
    config = get_or_create_config(db, current_user.company_id)

    data = data or AITestRequest()

    selected = config
    if data.ai_provider is not None or data.ai_model is not None:
        # O teste usa o que está selecionado na tela, sem persistir o override.
        from types import SimpleNamespace
        selected_provider = data.ai_provider if data.ai_provider is not None else config.ai_provider
        current_provider = config.ai_provider or get_secret("DEFAULT_AI_PROVIDER") or "groq"
        keeps_company_credential = selected_provider.strip().lower() == current_provider.strip().lower()
        selected = SimpleNamespace(
            ai_provider=selected_provider,
            ai_model=data.ai_model if data.ai_model is not None else config.ai_model,
            ai_api_key=config.ai_api_key if keeps_company_credential else "",
            ai_base_url=config.ai_base_url if keeps_company_credential else "",
        )
    resolved_ai = resolve_ai_config(selected, db, user_id=current_user.id)
    provider = resolved_ai["provider"]
    model = resolved_ai["model"]
    api_key = resolved_ai["api_key"]
    base_url = resolved_ai["base_url"]

    resolved = llm._resolve(provider, model, api_key, base_url)

    try:
        reply = await llm.generate_reply(
            system_prompt="Voce e um teste de conectividade.",
            history=[{"role": "user", "content": "Responda apenas com: PONG"}],
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout=30,
        )
    except llm.LLMError as exc:
        return {"ok": False, "provider": resolved["provider"], "model": resolved["model"], "detail": str(exc)}

    return {
        "ok": True,
        "provider": resolved["provider"],
        "model": resolved["model"],
        "reply": reply[:200],
        "detail": f"IA respondeu via {resolved['provider']} com {resolved['model']}.",
    }


# ---------------------------------------------------------------------------
# AI — politica por usuario (allowed / effective)
# ---------------------------------------------------------------------------

import json

from app.services.config_service import get_user_ai_config, get_user_allowed_providers


@router.get("/ai/allowed")
def ai_allowed(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna os provedores/modelos liberados para o usuario logado.

    Se nao houver politica de usuario, retorna vazio (fallback para empresa/.env).
    """
    allowed = get_user_allowed_providers(db, current_user.id)
    uc = get_user_ai_config(db, current_user.id)
    return {
        "allowed_providers": allowed,
        "default_provider": uc.default_provider if uc else "",
        "default_model": uc.default_model if uc else "",
    }


@router.get("/ai/effective")
def ai_effective(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna a config efetiva de IA do usuario (somente leitura)."""
    config = get_or_create_config(db, current_user.company_id)
    resolved = resolve_ai_config(config, db, user_id=current_user.id)
    allowed = get_user_allowed_providers(db, current_user.id)
    return {
        "provider": resolved["provider"],
        "model": resolved["model"],
        "credential_source": resolved.get("credential_source", "unknown"),
        "allowed_providers": allowed,
    }


# ---------------------------------------------------------------------------
# Horario de atendimento da empresa
# ---------------------------------------------------------------------------

import json as _json

from app.services import business_hours as bh_service


class BusinessHoursUpdate(BaseModel):
    enabled: bool | None = None
    timezone: str | None = None
    schedule: dict[str, list[str]] | None = None
    message: str | None = None


def _validate_business_hours(data: BusinessHoursUpdate) -> None:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    if data.timezone is not None:
        try:
            ZoneInfo(data.timezone.strip())
        except (ZoneInfoNotFoundError, ValueError):
            raise HTTPException(status_code=400, detail=f"Fuso horario invalido: {data.timezone}")

    if data.schedule is not None:
        for key, value in data.schedule.items():
            if key not in bh_service.DAY_KEYS:
                raise HTTPException(status_code=400, detail=f"Dia invalido na agenda: {key}")
            if value in (None, [], ""):
                continue
            if not (isinstance(value, list) and len(value) == 2
                    and bh_service._valid_time(str(value[0])) and bh_service._valid_time(str(value[1]))):
                raise HTTPException(
                    status_code=400,
                    detail=f"Horario invalido para {key}: use [\"HH:MM\", \"HH:MM\"]",
                )

    if data.message is not None and len(data.message.strip()) > 500:
        raise HTTPException(status_code=400, detail="Mensagem fora do horario muito longa (max 500)")


def _business_hours_payload(db: Session, company_id: int) -> dict:
    bh = bh_service.get_for_company(db, company_id)
    if not bh:
        return {"company_id": company_id, **bh_service.default_payload()}
    return {
        "company_id": company_id,
        "enabled": bool(bh.enabled),
        "timezone": bh.timezone or bh_service.DEFAULT_TIMEZONE,
        "schedule": bh_service.parse_schedule(bh.schedule),
        "message": bh.message or "",
    }


@router.get("/business-hours")
def get_business_hours(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna a configuracao de horario de atendimento da empresa."""
    return _business_hours_payload(db, current_user.company_id)


@router.put("/business-hours")
def update_business_hours(
    data: BusinessHoursUpdate,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    """Cria ou atualiza o horario de atendimento da empresa (gestor.)."""
    _validate_business_hours(data)

    bh = bh_service.get_for_company(db, current_user.company_id)
    if not bh:
        bh = bh_service.BusinessHours(company_id=current_user.company_id)
        db.add(bh)

    updates = data.model_dump(exclude_unset=True)
    if "enabled" in updates:
        bh.enabled = 1 if updates["enabled"] else 0
    if "timezone" in updates and updates["timezone"]:
        bh.timezone = updates["timezone"].strip()
    if "schedule" in updates:
        normalized = {
            key: (list(value) if isinstance(value, list) and len(value) == 2 else [])
            for key, value in updates["schedule"].items()
        }
        bh.schedule = _json.dumps(normalized, ensure_ascii=False)
    if "message" in updates:
        bh.message = (updates["message"] or "").strip()

    db.commit()
    return _business_hours_payload(db, current_user.company_id)


# ---------------------------------------------------------------------------
# WhatsApp / Evolution API - conexao
# ---------------------------------------------------------------------------

class WhatsAppTestRequest(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    instance: str | None = None


def _evo_config(config) -> tuple[str | None, str | None, str | None]:
    """Resolve a config da Evolution para a empresa, com fallback de infraestrutura.

    A Evolution e um servico do proprio deploy (mesma VPS). Por isso, quando a
    empresa ainda nao preencheu os campos em `company_configs`, caímos para os
    valores de infraestrutura do ambiente (.env) — o usuario comum nao precisa
    configurar URL/chave manualmente.

    Multi-tenant: a INSTANCIA e sempre unica POR EMPRESA (`inst-<company_id>`),
    pois cada empresa tem seu proprio numero de WhatsApp na Evolution. NUNCA
    usar uma instancia global compartilhada.
    """
    # A Evolution é infraestrutura da plataforma. URL e chave nunca vêm de
    # uma configuração editável por uma empresa.
    base_url = get_secret("EVOLUTION_BASE_URL")
    api_key = get_secret("EVOLUTION_API_KEY")
    instance = config.evolution_instance or f"inst-{config.company_id}"
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
        base = base_url.rstrip("/")
        # 1) connectionState (tempo real)
        cs_ok = False
        try:
            resp = httpx.get(f"{base}/instance/connectionState/{instance}", headers={"apikey": api_key}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                inst_obj = data.get("instance") or {}
                state = data.get("state") or inst_obj.get("state") or data.get("connectionStatus") or "unknown"
                detail = f"cs:{str(data)[:200]}"
                cs_ok = True
            elif resp.status_code == 400 and "not connected" in resp.text.lower():
                state = "close"
                detail = "offline"
                cs_ok = True
        except Exception:
            pass

        # 2) fetchInstances (fallback / complemento)
        if not cs_ok or state == "unknown":
            try:
                resp2 = httpx.get(f"{base}/instance/fetchInstances", headers={"apikey": api_key}, timeout=10)
                if resp2.status_code == 200:
                    instances = resp2.json() or []
                    found = next((i for i in instances if i.get("name") == instance), None)
                    if found:
                        db_state = found.get("connectionStatus", "unknown")
                        if state == "unknown":
                            state = db_state
                        detail = f"cs:{detail} fi:{db_state}"
            except Exception:
                pass

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
    base_url, api_key, instance = _evo_config(config)

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
    """Desconecta o WhatsApp (Ex: botao 'Desconectar' na UI).

    A Evolution expoe o logout como DELETE /instance/logout/{instance}
    (doc oficial; POST nessa rota retorna 404).
    """
    config = get_or_create_config(db, current_user.company_id)
    base_url, api_key, instance = _evo_config(config)
    base, key, inst = _evolve_pair(base_url, api_key, instance)

    try:
        resp = httpx.delete(f"{base}/instance/logout/{inst}", headers={"apikey": key}, timeout=30)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Sem conexao com a Evolution: {exc}")

    if resp.status_code == 404:
        return {"ok": True, "detail": "Instancia nao encontrada na Evolution (ja desconectada ou removida)."}
    if resp.status_code == 400:
        body = resp.text.lower()
        if "not connected" in body or "not_found" in body:
            return {"ok": True, "detail": "WhatsApp ja desconectado na Evolution."}
    if resp.status_code not in (200, 201, 204):
        raise HTTPException(status_code=resp.status_code, detail=f"Evolution retornou HTTP {resp.status_code}")

    return {"ok": True, "detail": "WhatsApp desconectado."}


@router.post("/whatsapp/setup")
def whatsapp_setup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Configura o WhatsApp automaticamente e retorna o QR Code.

    Fluxo simplificado:
    1. Verifica se a instância já existe na Evolution
    2. Se não existe, cria automaticamente
    3. Retorna o QR Code para escanear

    O usuário não precisa configurar nada - só scannear o QR.
    """
    config = get_or_create_config(db, current_user.company_id)
    base_url, api_key, instance = _evo_config(config)
    base, key, inst = _evolve_pair(base_url, api_key, instance)

    # Garante que a instancia unica da empresa fique persistida no banco,
    # para que o status refletir o nome real da instancia.
    if not config.evolution_instance:
        config.evolution_instance = inst
        db.commit()

    # 1. Verificar se a instância já existe
    instance_exists = False
    instance_state = "unknown"
    try:
        resp = httpx.get(f"{base}/instance/fetchInstances", headers={"apikey": key}, timeout=15)
        if resp.status_code == 200:
            instances = resp.json()
            if isinstance(instances, list):
                for i in instances:
                    if i.get("name") == inst:
                        instance_exists = True
                        instance_state = i.get("connectionStatus") or i.get("state", "unknown")
                        break
    except httpx.HTTPError:
        pass

    # 2. Se não existe, criar automaticamente
    if not instance_exists:
        try:
            create_resp = httpx.post(
                f"{base}/instance/create",
                headers={"apikey": key, "Content-Type": "application/json"},
                json={
                    "instanceName": inst,
                    "integration": "WHATSAPP-BAILEYS",
                    "qrcode": True,
                    "reject_call": False,
                    "groups_ignore": True,
                    "always_online": True,
                },
                timeout=30,
            )
            if create_resp.status_code not in (200, 201):
                raise HTTPException(
                    status_code=create_resp.status_code,
                    detail=f"Erro ao criar instância na Evolution: {create_resp.text}"
                )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Sem conexao com a Evolution: {exc}")

    # Tambem repara instancias existentes criadas antes do webhook automatico.
    _configure_instance_webhook(
        base=base,
        api_key=key,
        instance=inst,
        company_id=current_user.company_id,
    )

    if instance_state == "open":
        return {
            "instance": inst,
            "connected": True,
            "webhook_configured": True,
        }

    # 3. Gerar o QR Code
    try:
        resp = httpx.get(f"{base}/instance/connect/{inst}", headers={"apikey": key}, timeout=30)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Sem conexao com a Evolution: {exc}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=f"Evolution retornou HTTP {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    qr = (data.get("qrcode") or {}).get("base64") or data.get("base64") or data.get("baseCode")
    if not qr:
        state = (data.get("instance") or {}).get("state") or data.get("state", "")
        detail = f"QR indisponivel (resp keys: {list(data.keys())})"
        if state == "open":
            detail = "WhatsApp ja conectado."
        raise HTTPException(status_code=409, detail=detail)

    if "," in qr:
        qr = qr.split(",", 1)[1]
    return {"qr_base64": qr, "instance": inst}

def _configure_instance_webhook(*, base: str, api_key: str, instance: str, company_id: int) -> None:
    """Registra o webhook autenticado da instancia na rede interna Docker."""
    custom_headers: dict[str, str] = {}
    webhook_auth_key = get_secret("EVOLUTION_AUTH_KEY")
    if webhook_auth_key:
        custom_headers["evolution-auth"] = webhook_auth_key

    try:
        response = httpx.post(
            f"{base}/webhook/set/{instance}",
            headers={"apikey": api_key, "Content-Type": "application/json"},
            # A Evolution v2.3.x exige que a configuracao fique no objeto webhook.
            json={
                "webhook": {
                    "enabled": True,
                    "url": f"http://backend:8000/webhook/whatsapp/{company_id}",
                    "headers": custom_headers,
                    "events": ["MESSAGES_UPSERT"],
                }
            },
            timeout=15,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Sem conexao ao configurar webhook da Evolution") from exc

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Evolution recusou a configuracao do webhook (HTTP {response.status_code})",
        )
