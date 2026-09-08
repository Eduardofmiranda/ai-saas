from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.services import agenda as agenda_service
from app.services.agenda import AgendaError, DAY_KEYS
from app.services.business_hours import _valid_time
from app.services.deps import get_current_user, require_company_manager

router = APIRouter(prefix="/agenda", tags=["Agenda"])


def _http_error(exc: AgendaError) -> HTTPException:
    codes = {
        "not_found": 404,
        "conflict": 409,
        "blocked": 409,
        "min_advance": 409,
    }
    return HTTPException(status_code=codes.get(exc.code, 400), detail=exc.message)


# ---------------------------------------------------------------------------
# Configuracao da agenda da empresa
# ---------------------------------------------------------------------------


class AgendaConfigUpdate(BaseModel):
    enabled: bool | None = None
    timezone: str | None = None
    schedule: dict[str, list[str]] | None = None
    slot_duration: int | None = None
    min_advance: int | None = None
    blocked: list[dict] | None = None
    confirmation_message: str | None = None


def _validate_config(data: AgendaConfigUpdate) -> None:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    if data.timezone is not None:
        try:
            ZoneInfo(data.timezone.strip())
        except (ZoneInfoNotFoundError, ValueError):
            raise HTTPException(status_code=400, detail=f"Fuso horario invalido: {data.timezone}")

    if data.schedule is not None:
        for key, value in data.schedule.items():
            if key not in DAY_KEYS:
                raise HTTPException(status_code=400, detail=f"Dia invalido na agenda: {key}")
            if value in (None, [], ""):
                continue
            if not (isinstance(value, list) and len(value) == 2
                    and _valid_time(str(value[0])) and _valid_time(str(value[1]))
                    and agenda_service._to_minutes(str(value[1])) > agenda_service._to_minutes(str(value[0]))):
                raise HTTPException(
                    status_code=400,
                    detail=f"Janela invalida para {key}: use [\"HH:MM\", \"HH:MM\"] com fim depois do inicio",
                )

    if data.slot_duration is not None and not (5 <= int(data.slot_duration) <= 240):
        raise HTTPException(status_code=400, detail="Duracao do compromisso deve estar entre 5 e 240 minutos")

    if data.min_advance is not None and int(data.min_advance) < 0:
        raise HTTPException(status_code=400, detail="Antecedencia minima nao pode ser negativa")

    if data.blocked is not None:
        parsed = agenda_service.parse_blocked(data.blocked)
        if len(parsed) != len(data.blocked):
            raise HTTPException(
                status_code=400,
                detail="Bloqueio invalido: use [{\"date\": \"YYYY-MM-DD\", \"start\": \"HH:MM\", \"end\": \"HH:MM\"}]",
            )

    if data.confirmation_message is not None and len(data.confirmation_message.strip()) > 500:
        raise HTTPException(status_code=400, detail="Mensagem de confirmacao muito longa (max 500)")


@router.get("/config")
def get_agenda_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna a configuracao de agenda da empresa (default se ainda nao criada)."""
    cfg = agenda_service.get_for_company(db, current_user.company_id)
    return agenda_service.config_payload(cfg, current_user.company_id)


@router.put("/config")
def update_agenda_config(
    data: AgendaConfigUpdate,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    """Cria ou atualiza a configuracao de agenda da empresa (gestor)."""
    _validate_config(data)

    cfg = agenda_service.get_for_company(db, current_user.company_id)
    if not cfg:
        cfg = agenda_service.AgendaConfig(company_id=current_user.company_id)
        db.add(cfg)
        db.flush()

    updates = data.model_dump(exclude_unset=True)
    if "enabled" in updates:
        cfg.enabled = 1 if updates["enabled"] else 0
    if "timezone" in updates and updates["timezone"]:
        cfg.timezone = updates["timezone"].strip()
    if "schedule" in updates:
        cfg.schedule = agenda_service.json_schedule(updates["schedule"])
    if "slot_duration" in updates:
        cfg.slot_duration = int(updates["slot_duration"])
    if "min_advance" in updates:
        cfg.min_advance = int(updates["min_advance"])
    if "blocked" in updates:
        cfg.blocked = agenda_service.json.dumps(agenda_service.parse_blocked(updates["blocked"]), ensure_ascii=False)
    if "confirmation_message" in updates:
        cfg.confirmation_message = (updates["confirmation_message"] or "").strip()

    db.commit()
    db.refresh(cfg)
    return agenda_service.config_payload(cfg, current_user.company_id)


# ---------------------------------------------------------------------------
# Disponibilidade
# ---------------------------------------------------------------------------


@router.get("/availability")
def availability(
    date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Slots livres para uma data (respeita janela, bloqueios, conflitos e antecedencia)."""
    return {"date": date, "slots": agenda_service.build_slots(db, current_user.company_id, date)}


# ---------------------------------------------------------------------------
# Compromissos
# ---------------------------------------------------------------------------


class AppointmentCreate(BaseModel):
    date: str
    start_time: str
    end_time: str
    phone: str
    customer_name: str | None = None
    customer_id: int | None = None
    service: str | None = None
    notes: str | None = None
    origin: str = "manual"


class AppointmentUpdate(BaseModel):
    date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    customer_name: str | None = None
    service: str | None = None
    notes: str | None = None
    status: str | None = None


@router.get("/appointments")
def list_appointments(
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return agenda_service.list_appointments(
            db,
            current_user.company_id,
            date_from=date_from,
            date_to=date_to,
            status=status,
            offset=skip,
            limit=limit,
        )
    except AgendaError as exc:
        raise _http_error(exc)


@router.post("/appointments")
def create_appointment(
    data: AppointmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cria um compromisso (operador; cria manual mesmo sem agenda ativa)."""
    if not data.phone.strip():
        raise HTTPException(status_code=400, detail="Telefone e obrigatorio")
    try:
        appt = agenda_service.add_appointment(
            db,
            current_user.company_id,
            date=data.date,
            start_time=data.start_time,
            end_time=data.end_time,
            phone=data.phone,
            customer_name=data.customer_name,
            customer_id=data.customer_id,
            service=data.service,
            notes=data.notes,
            origin=data.origin,
            user_id=current_user.id,
            user_name=current_user.name or current_user.email or "Operador",
            actor_type="user",
            skip_min_advance=True,
        )
    except AgendaError as exc:
        raise _http_error(exc)
    return agenda_service.to_dict(appt)


@router.get("/appointments/{appointment_id}")
def get_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        appt = agenda_service.get_appointment(db, current_user.company_id, appointment_id)
    except AgendaError as exc:
        raise _http_error(exc)
    return agenda_service.to_dict(appt)


@router.patch("/appointments/{appointment_id}")
def update_appointment(
    appointment_id: int,
    data: AppointmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        appt = agenda_service.update_appointment(
            db,
            current_user.company_id,
            appointment_id,
            fields=data.model_dump(exclude_unset=True),
            user_id=current_user.id,
            user_name=current_user.name or current_user.email or "Operador",
            actor_type="user",
            skip_min_advance=True,
        )
    except AgendaError as exc:
        raise _http_error(exc)
    return agenda_service.to_dict(appt)


@router.delete("/appointments/{appointment_id}")
def cancel_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancela (soft delete) o compromisso e registra o historico."""
    try:
        appt = agenda_service.cancel_appointment(
            db,
            current_user.company_id,
            appointment_id,
            user_id=current_user.id,
            user_name=current_user.name or current_user.email or "Operador",
            actor_type="user",
        )
    except AgendaError as exc:
        raise _http_error(exc)
    return agenda_service.to_dict(appt)