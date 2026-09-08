"""Horario de atendimento: consulta, calculo e mensagem fora do expediente.

Regras de decisao:
- Sem registro ou com `enabled` desligado -> aberto 24/7 (atendimento nunca trava).
- Sem nenhum dia com janela valida configurada -> aberto (config incompleta nao
  derruba o atendimento).
- Com dias configurados: dia sem janela = fechado; dentro da janela = aberto.
- Janela que cruza a meia-noite (ex.: 18:00 -> 02:00) e suportada.
"""
from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.models.business_hours import BusinessHours

DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

DEFAULT_SCHEDULE = {
    "mon": ["09:00", "18:00"],
    "tue": ["09:00", "18:00"],
    "wed": ["09:00", "18:00"],
    "thu": ["09:00", "18:00"],
    "fri": ["09:00", "18:00"],
    "sat": [],
    "sun": [],
}

DEFAULT_MESSAGE = "Estamos fora do horário de atendimento. Retornaremos em breve!"

DEFAULT_TIMEZONE = "America/Sao_Paulo"


def get_for_company(db: Session, company_id: int) -> BusinessHours | None:
    return (
        db.query(BusinessHours)
        .filter(BusinessHours.company_id == company_id)
        .first()
    )


def _valid_time(value: str) -> bool:
    try:
        hour, minute = value.split(":")
        return 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59
    except (ValueError, AttributeError):
        return False


def parse_schedule(raw: str | dict) -> dict:
    """Normaliza o JSON em {dia: ("HH:MM", "HH:MM") | None}."""
    if isinstance(raw, dict):
        data = raw
    else:
        try:
            data = json.loads(raw or "{}")
        except ValueError:
            data = {}
    if not isinstance(data, dict):
        return {}

    schedule: dict[str, tuple[str, str] | None] = {}
    for key in DAY_KEYS:
        value = data.get(key)
        if isinstance(value, (list, tuple)) and len(value) == 2:
            start, end = str(value[0]), str(value[1])
            if _valid_time(start) and _valid_time(end):
                schedule[key] = (start, end)
                continue
        schedule[key] = None
    return schedule


def _local_now(bh: BusinessHours) -> datetime:
    try:
        tz = ZoneInfo(bh.timezone or DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo("UTC")
    return datetime.now(tz)


def _open_at(schedule: dict, now_local: datetime) -> bool:
    day_key = DAY_KEYS[now_local.weekday()]
    window = schedule.get(day_key)
    if not window:
        return False
    start_h, start_m = map(int, window[0].split(":"))
    end_h, end_m = map(int, window[1].split(":"))
    start_min = start_h * 60 + start_m
    end_min = end_h * 60 + end_m
    now_min = now_local.hour * 60 + now_local.minute

    if start_min < end_min:
        return start_min <= now_min < end_min
    # turno que cruza a meia-noite (ex.: 18:00 -> 02:00)
    return now_min >= start_min or now_min < end_min


def is_open(bh: BusinessHours | None, now_local: datetime | None = None) -> bool:
    """Aberto agora? Sem config ou desabilitado, retorna True (24/7)."""
    if not bh or not bh.enabled:
        return True

    schedule = parse_schedule(bh.schedule)
    # Config incompleta (nenhum dia com janela valida) nunca bloqueia o fluxo.
    if not any(schedule.values()):
        return True

    now = now_local or _local_now(bh)
    return _open_at(schedule, now)


def is_company_open(
    db: Session,
    company_id: int,
    now_local: datetime | None = None,
) -> bool:
    bh = get_for_company(db, company_id)
    return is_open(bh, now_local=now_local)


def default_payload() -> dict:
    return {
        "enabled": False,
        "timezone": DEFAULT_TIMEZONE,
        "schedule": DEFAULT_SCHEDULE,
        "message": DEFAULT_MESSAGE,
    }