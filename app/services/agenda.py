"""Agenda de compromissos por empresa (Secretaria IA).

Servico compartilhado entre o router de API e (futuramente) as tools da IA:

- Configuracao: janelas por dia, duracao padrao, antecedencia minima e bloqueios.
- Disponibilidade: slots livres para uma data (janela + duracao + bloqueios +
  conflitos + antecedencia).
- CRUD de compromissos com historico em `appointment_events`.

Datas/horarios ficam em strings no fuso configurado da empresa ("YYYY-MM-DD" e
"HH:MM") para nao expor conversao de UTC ao usuario final.
"""
from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.models.agenda_config import AgendaConfig
from app.models.appointment import Appointment
from app.models.appointment_event import AppointmentEvent
from app.services.business_hours import DAY_KEYS, DEFAULT_TIMEZONE, _valid_time, parse_schedule

DEFAULT_SLOT_DURATION = 30
DEFAULT_MIN_ADVANCE = 60
DEFAULT_CONFIRMATION_MESSAGE = "Sua visita foi agendada. Em caso de imprevisto, avise-nos!"
DEFAULT_CONFIRMATION_EXPIRY_HOURS = 24
DEFAULT_CONFIRMATION_REQUEST_MESSAGE = (
    "Olá {nome}! Para confirmar seu agendamento de {servico} no dia "
    "{data} às {horario}, responda CONFIRMAR. Para desistir, responda CANCELAR."
)
DEFAULT_REMINDER_HOURS = "[24]"
DEFAULT_REMINDER_MESSAGE = "Lembrete: você tem {servico} marcado para {data} às {horario}."

AWAITING_CONFIRMATION = "awaiting_confirmation"
ACTIVE_STATUSES = ("scheduled", "confirmed", AWAITING_CONFIRMATION)
ALLOWED_STATUSES = ("scheduled", "confirmed", AWAITING_CONFIRMATION, "completed", "canceled")


class AgendaError(Exception):
    """Erro de regra de negocio da agenda.

    code: "invalid" | "window_closed" | "blocked" | "conflict" | "min_advance"
          | "not_found" | "no_config"
    """

    def __init__(self, message: str, code: str = "invalid"):
        super().__init__(message)
        self.message = message
        self.code = code


# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------


def default_schedule() -> dict[str, list[str]]:
    return {
        "mon": ["09:00", "18:00"],
        "tue": ["09:00", "18:00"],
        "wed": ["09:00", "18:00"],
        "thu": ["09:00", "18:00"],
        "fri": ["09:00", "18:00"],
        "sat": [],
        "sun": [],
    }


def default_payload() -> dict:
    return {
        "enabled": False,
        "timezone": DEFAULT_TIMEZONE,
        "schedule": default_schedule(),
        "slot_duration": DEFAULT_SLOT_DURATION,
        "min_advance": DEFAULT_MIN_ADVANCE,
        "blocked": [],
        "confirmation_message": DEFAULT_CONFIRMATION_MESSAGE,
        "confirmation_required": True,
        "confirmation_expiry_hours": DEFAULT_CONFIRMATION_EXPIRY_HOURS,
        "confirmation_request_message": DEFAULT_CONFIRMATION_REQUEST_MESSAGE,
        "reminders_enabled": False,
        "reminder_hours": [24],
        "reminder_message": DEFAULT_REMINDER_MESSAGE,
        "whatsapp_number": "",
    }


def get_for_company(db: Session, company_id: int) -> AgendaConfig | None:
    return (
        db.query(AgendaConfig)
        .filter(AgendaConfig.company_id == company_id)
        .first()
    )


def get_or_create(db: Session, company_id: int) -> AgendaConfig:
    cfg = get_for_company(db, company_id)
    if cfg:
        return cfg
    cfg = AgendaConfig(company_id=company_id)
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


def config_payload(cfg: AgendaConfig | None, company_id: int) -> dict:
    if not cfg:
        payload = default_payload()
        payload["company_id"] = company_id
        return payload
    return {
        "company_id": company_id,
        "enabled": bool(cfg.enabled),
        "timezone": cfg.timezone or DEFAULT_TIMEZONE,
        "schedule": _schedule_json(cfg.schedule),
        "slot_duration": int(cfg.slot_duration or DEFAULT_SLOT_DURATION),
        "min_advance": int(cfg.min_advance or DEFAULT_MIN_ADVANCE),
        "blocked": parse_blocked(cfg.blocked),
        "confirmation_message": cfg.confirmation_message or DEFAULT_CONFIRMATION_MESSAGE,
        "confirmation_required": bool(cfg.confirmation_required),
        "confirmation_expiry_hours": int(cfg.confirmation_expiry_hours or DEFAULT_CONFIRMATION_EXPIRY_HOURS),
        "confirmation_request_message": cfg.confirmation_request_message or DEFAULT_CONFIRMATION_REQUEST_MESSAGE,
        "reminders_enabled": bool(cfg.reminders_enabled),
        "reminder_hours": parse_reminder_hours(cfg.reminder_hours),
        "reminder_message": cfg.reminder_message or DEFAULT_REMINDER_MESSAGE,
        "whatsapp_number": cfg.whatsapp_number or "",
    }


def parse_blocked(raw: str | list) -> list[dict]:
    """Normaliza os bloqueios em [{"date", "start", "end"}] validos."""
    if isinstance(raw, list):
        data = raw
    else:
        try:
            data = json.loads(raw or "[]")
        except ValueError:
            data = []
    if not isinstance(data, list):
        return []

    blocked: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        date = str(item.get("date") or "").strip()
        start = str(item.get("start") or "").strip()
        end = str(item.get("end") or "").strip()
        if _valid_date(date) and _valid_time(start) and _valid_time(end):
            blocked.append({"date": date, "start": start, "end": end})
    return blocked


def parse_reminder_hours(raw: str | list) -> list[int]:
    """Normaliza a lista de horas de antecedencia em ints positivos unicos."""
    if isinstance(raw, list):
        data = raw
    else:
        try:
            data = json.loads(raw or "[24]")
        except ValueError:
            data = []
    if not isinstance(data, list):
        return [24]
    hours = []
    for item in data:
        try:
            value = int(item)
        except (ValueError, TypeError):
            continue
        if value > 0 and value not in hours:
            hours.append(value)
    return sorted(hours) or [24]


def push_event(
    db: Session,
    appointment: Appointment,
    *,
    action: str,
    actor_type: str = "system",
    user_id: int | None = None,
    user_name: str = "",
    details: dict | None = None,
) -> None:
    """Registra um evento operacional (confirmacao, lembrete, pedido) e faz commit."""
    _add_event(
        db,
        appointment,
        action=action,
        actor_type=actor_type,
        user_id=user_id,
        user_name=user_name,
        details=details,
    )
    db.commit()


# ---------------------------------------------------------------------------
# Helpers de tempo
# ---------------------------------------------------------------------------


def _tz(cfg: AgendaConfig) -> ZoneInfo:
    try:
        return ZoneInfo(cfg.timezone or DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _local_now(cfg: AgendaConfig, now: datetime | None = None) -> datetime:
    if now is not None:
        return now
    return datetime.now(_tz(cfg))


def _to_minutes(hhmm: str) -> int | None:
    try:
        hour, minute = hhmm.split(":")
        minutes = int(hour) * 60 + int(minute)
        if 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59:
            return minutes
    except (ValueError, AttributeError):
        return None
    return None


def _fmt(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def _slot_datetime(date: str, hhmm: str, tz: ZoneInfo) -> datetime | None:
    if not _valid_date(date) or not _valid_time(hhmm):
        return None
    y, m, d = (int(part) for part in date.split("-"))
    h, minute = (int(part) for part in hhmm.split(":"))
    return datetime(y, m, d, h, minute, tzinfo=tz)


def window_for_date(cfg: AgendaConfig, date: str) -> tuple[str, str] | None:
    """Janela disponivel (start, end) para a data, ou None (dia fechado/invalido)."""
    if not _valid_date(date):
        return None
    schedule = parse_schedule(cfg.schedule)
    weekday_key = DAY_KEYS[datetime.strptime(date, "%Y-%m-%d").weekday()]
    return schedule.get(weekday_key) or None


# ---------------------------------------------------------------------------
# Disponibilidade
# ---------------------------------------------------------------------------


def has_conflict(
    db: Session,
    company_id: int,
    date: str,
    start_time: str,
    end_time: str,
    exclude_id: int | None = None,
) -> bool:
    """True se o intervalo (date, start, end) sobrepoe um compromisso ativo."""
    start_min = _to_minutes(start_time)
    end_min = _to_minutes(end_time)
    if start_min is None or end_min is None or start_min >= end_min:
        return True

    q = db.query(Appointment).filter(
        Appointment.company_id == company_id,
        Appointment.date == date,
        Appointment.status.in_(ACTIVE_STATUSES),
    )
    if exclude_id is not None:
        q = q.filter(Appointment.id != exclude_id)

    for appt in q.all():
        other_start = _to_minutes(appt.start_time)
        other_end = _to_minutes(appt.end_time)
        if other_start is None or other_end is None:
            continue
        if start_min < other_end and other_start < end_min:
            return True
    return False


def is_blocked(cfg: AgendaConfig, date: str, start_time: str, end_time: str) -> bool:
    """True se o intervalo sobrepoe um bloqueio configurado."""
    start_min = _to_minutes(start_time)
    end_min = _to_minutes(end_time)
    if start_min is None or end_min is None:
        return True
    for item in parse_blocked(cfg.blocked):
        if item["date"] != date:
            continue
        b_start = _to_minutes(item["start"])
        b_end = _to_minutes(item["end"])
        if b_start is None or b_end is None:
            continue
        if start_min < b_end and b_start < end_min:
            return True
    return False


def within_min_advance(cfg: AgendaConfig, date: str, start_time: str, now: datetime | None = None) -> bool:
    """True se o inicio do compromisso respeita a antecedencia minima."""
    now = _local_now(cfg, now)
    start_dt = _slot_datetime(date, start_time, now.tzinfo)
    if start_dt is None:
        return False
    advance_minutes = (start_dt - now).total_seconds() / 60.0
    return advance_minutes >= int(cfg.min_advance or 0)


def build_slots(
    db: Session,
    company_id: int,
    date: str,
    *,
    now: datetime | None = None,
) -> list[str]:
    """Slots livres (HH:MM de inicio) para uma data.

    Respeita: agenda habilitada, janela do dia, duracao padrao, bloqueios,
    conflitos reais e antecedencia minima. Agenda desabilitada -> [].
    """
    cfg = get_for_company(db, company_id)
    if not cfg or not cfg.enabled:
        return []

    window = window_for_date(cfg, date)
    if not window:
        return []

    start_min = _to_minutes(window[0]) or 0
    end_min = _to_minutes(window[1])
    if end_min is None or start_min >= end_min:
        return []

    duration = max(1, int(cfg.slot_duration or DEFAULT_SLOT_DURATION))
    now_local = _local_now(cfg, now)

    slots: list[str] = []
    t = start_min
    while t + duration <= end_min:
        start_hhmm = _fmt(t)
        end_hhmm = _fmt(t + duration)
        if (
            not has_conflict(db, company_id, date, start_hhmm, end_hhmm)
            and not is_blocked(cfg, date, start_hhmm, end_hhmm)
            and within_min_advance(cfg, date, start_hhmm, now_local)
        ):
            slots.append(start_hhmm)
        t += duration
    return slots


# ---------------------------------------------------------------------------
# CRUD + historico
# ---------------------------------------------------------------------------


def to_dict(appt: Appointment) -> dict:
    return {
        "id": appt.id,
        "company_id": appt.company_id,
        "customer_id": appt.customer_id,
        "customer_name": appt.customer_name,
        "phone": appt.phone,
        "status": appt.status,
        "date": appt.date,
        "start_time": appt.start_time,
        "end_time": appt.end_time,
        "service": appt.service,
        "notes": appt.notes,
        "origin": appt.origin,
        "created_by_user_id": appt.created_by_user_id,
        "created_at": appt.created_at,
        "updated_at": appt.updated_at,
    }


def _add_event(
    db: Session,
    appointment: Appointment,
    *,
    action: str,
    actor_type: str = "user",
    user_id: int | None = None,
    user_name: str = "",
    details: dict | None = None,
) -> None:
    db.add(
        AppointmentEvent(
            appointment_id=appointment.id,
            company_id=appointment.company_id,
            action=action,
            actor_type=actor_type,
            user_id=user_id,
            user_name=user_name or "",
            details=json.dumps(details, ensure_ascii=False) if details else None,
        )
    )


def _validate_interval(
    db: Session,
    cfg: AgendaConfig | None,
    *,
    date: str,
    start_time: str,
    end_time: str,
    skip_min_advance: bool = False,
    exclude_id: int | None = None,
    company_id: int | None = None,
) -> None:
    """Valida um intervalo de agendamento (regras gerais).

    Levanta AgendaError com o codigo descritivo apos a primeira violacao.
    """
    if not _valid_date(date):
        raise AgendaError("Data invalida. Use o formato YYYY-MM-DD.", "invalid")
    if not _valid_time(start_time) or not _valid_time(end_time):
        raise AgendaError("Horario invalido. Use o formato HH:MM.", "invalid")
    if _to_minutes(end_time) <= _to_minutes(start_time):
        raise AgendaError("O horario final deve ser depois do inicial.", "invalid")

    if cfg and cfg.enabled:
        window = window_for_date(cfg, date)
        if not window:
            raise AgendaError("Nao ha horarios disponiveis para esta data.", "window_closed")
        if start_time < window[0] or end_time > window[1]:
            raise AgendaError(
                f"O horario deve estar entre {window[0]} e {window[1]}.",
                "window_closed",
            )
        if is_blocked(cfg, date, start_time, end_time):
            raise AgendaError("Este horario esta bloqueado.", "blocked")
        if not skip_min_advance and not within_min_advance(cfg, date, start_time):
            raise AgendaError(
                f"Respeite a antecedencia minima de {int(cfg.min_advance or 0)} minutos.",
                "min_advance",
            )
    elif cfg and not cfg.enabled:
        if is_blocked(cfg, date, start_time, end_time):
            raise AgendaError("Este horario esta bloqueado.", "blocked")

    if company_id is not None and has_conflict(
        db, company_id, date, start_time, end_time, exclude_id=exclude_id
    ):
        raise AgendaError("Este horario ja esta ocupado.", "conflict")


def add_appointment(
    db: Session,
    company_id: int,
    *,
    date: str,
    start_time: str,
    end_time: str,
    phone: str,
    customer_name: str | None = None,
    customer_id: int | None = None,
    service: str | None = None,
    notes: str | None = None,
    origin: str = "manual",
    user_id: int | None = None,
    user_name: str = "",
    actor_type: str = "user",
    skip_min_advance: bool = False,
    status: str = "scheduled",
) -> Appointment:
    """Cria um compromisso. Agenda desabilitada continua permitindo criacao
    manual (operador), mas os tools da IA nunca confirmam sem agenda ativa.

    `status` inicial: "scheduled" por padrao; a IA usa AWAITING_CONFIRMATION
    quando `confirmation_required` esta ativo.
    """
    cfg = get_for_company(db, company_id)
    if not origin:
        origin = "manual"
    if customer_id is not None:
        from app.models.customer import Customer
        customer = db.query(Customer).filter(
            Customer.id == customer_id, Customer.company_id == company_id,
        ).first()
        if customer is None:
            raise AgendaError("Cliente nao encontrado.", "not_found")
    _validate_interval(
        db,
        cfg,
        date=date,
        start_time=start_time,
        end_time=end_time,
        skip_min_advance=skip_min_advance or origin in ("manual", "workflow"),
        exclude_id=None,
        company_id=company_id,
    )

    initial_status = status if status in ALLOWED_STATUSES else "scheduled"
    appt = Appointment(
        company_id=company_id,
        customer_id=customer_id,
        customer_name=(customer_name or "").strip() or None,
        phone=phone.strip(),
        status=initial_status,
        date=date,
        start_time=start_time,
        end_time=end_time,
        service=(service or "").strip() or None,
        notes=(notes or "").strip() or None,
        origin=origin,
        created_by_user_id=user_id,
    )
    db.add(appt)
    db.flush()
    _add_event(
        db,
        appt,
        action="created",
        actor_type=actor_type,
        user_id=user_id,
        user_name=user_name,
        details={
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "service": appt.service,
            "status": appt.status,
        },
    )
    db.commit()
    db.refresh(appt)
    return appt


def get_appointment(db: Session, company_id: int, appointment_id: int) -> Appointment:
    appt = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id,
            Appointment.company_id == company_id,
        )
        .first()
    )
    if not appt:
        raise AgendaError("Compromisso nao encontrado.", "not_found")
    return appt


def update_appointment(
    db: Session,
    company_id: int,
    appointment_id: int,
    *,
    fields: dict,
    user_id: int | None = None,
    user_name: str = "",
    actor_type: str = "user",
    skip_min_advance: bool = True,
) -> Appointment:
    """Atualiza os campos informados e registra evento (rescheduled/updated)."""
    appt = get_appointment(db, company_id, appointment_id)

    rescheduled = False
    new_date = fields.get("date", appt.date)
    new_start = fields.get("start_time", appt.start_time)
    new_end = fields.get("end_time", appt.end_time)
    rescheduled = (new_date, new_start, new_end) != (appt.date, appt.start_time, appt.end_time)
    reactivating = appt.status not in ACTIVE_STATUSES and fields.get("status") in ACTIVE_STATUSES
    if rescheduled or reactivating:
        cfg = get_for_company(db, company_id)
        _validate_interval(
            db,
            cfg,
            date=new_date,
            start_time=new_start,
            end_time=new_end,
            skip_min_advance=skip_min_advance,
            exclude_id=appt.id,
            company_id=company_id,
        )

    allowed = {f for f in ("customer_name", "service", "notes", "status", "date", "start_time", "end_time") if f in fields}
    if "status" in fields:
        status = (fields["status"] or "").strip()
        if status not in ALLOWED_STATUSES:
            raise AgendaError(f"Status invalido: {status}", "invalid")
        appt.status = status
    for field in allowed - {"status"}:
        setattr(appt, field, fields[field])

    action = "rescheduled" if rescheduled else "updated"
    _add_event(
        db,
        appt,
        action=action,
        actor_type=actor_type,
        user_id=user_id,
        user_name=user_name,
        details={
            "date": appt.date,
            "start_time": appt.start_time,
            "end_time": appt.end_time,
            "status": appt.status,
            "service": appt.service,
        },
    )
    db.commit()
    db.refresh(appt)
    return appt


def cancel_appointment(
    db: Session,
    company_id: int,
    appointment_id: int,
    *,
    user_id: int | None = None,
    user_name: str = "",
    actor_type: str = "user",
    reason: str = "",
) -> Appointment:
    """Cancela (soft delete) o compromisso e registra o evento."""
    appt = get_appointment(db, company_id, appointment_id)
    appt.status = "canceled"
    _add_event(
        db,
        appt,
        action="canceled",
        actor_type=actor_type,
        user_id=user_id,
        user_name=user_name,
        details={"reason": (reason or "").strip()[:500] or None},
    )
    db.commit()
    db.refresh(appt)
    return appt


# ---------------------------------------------------------------------------
# Consulta (listagem com filtros + paginacao)
# ---------------------------------------------------------------------------


def list_appointments(
    db: Session,
    company_id: int,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
    phone: str | None = None,
) -> dict:
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    q = db.query(Appointment).filter(Appointment.company_id == company_id)
    if phone is not None:
        q = q.filter(Appointment.phone == phone)
    if date_from:
        if not _valid_date(date_from):
            raise AgendaError("date_from invalido. Use YYYY-MM-DD.", "invalid")
        q = q.filter(Appointment.date >= date_from)
    if date_to:
        if not _valid_date(date_to):
            raise AgendaError("date_to invalido. Use YYYY-MM-DD.", "invalid")
        q = q.filter(Appointment.date <= date_to)
    if status:
        if status not in ALLOWED_STATUSES:
            raise AgendaError(f"Status invalido: {status}", "invalid")
        q = q.filter(Appointment.status == status)

    total = q.count()
    rows = (
        q.order_by(Appointment.date.asc(), Appointment.start_time.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {"total": total, "items": [to_dict(a) for a in rows]}


def _schedule_json(raw: str | dict) -> dict[str, list[str]]:
    if isinstance(raw, dict):
        data = raw
    else:
        try:
            data = json.loads(raw or "{}")
        except ValueError:
            data = {}
    if not isinstance(data, dict):
        return default_schedule()
    result: dict[str, list[str]] = {}
    for key in DAY_KEYS:
        value = data.get(key)
        if isinstance(value, (list, tuple)) and len(value) == 2:
            start, end = str(value[0]), str(value[1])
            if _valid_time(start) and _valid_time(end):
                result[key] = [start, end]
                continue
        result[key] = []
    return result


def normalize_schedule(schedule: dict) -> dict[str, list[str]]:
    """Normaliza o schedule recebido do operador em {dia: [start, end]|[]}."""
    normalized: dict[str, list[str]] = {}
    for key in DAY_KEYS:
        value = schedule.get(key)
        if isinstance(value, (list, tuple)) and len(value) == 2:
            start, end = str(value[0]), str(value[1])
            if _valid_time(start) and _valid_time(end) and _to_minutes(end) > _to_minutes(start):
                normalized[key] = [start, end]
                continue
        normalized[key] = []
    return normalized


def json_schedule(schedule: dict) -> str:
    return json.dumps(normalize_schedule(schedule), ensure_ascii=False)


def default_duration() -> int:
    return DEFAULT_SLOT_DURATION


def default_advance() -> int:
    return DEFAULT_MIN_ADVANCE
