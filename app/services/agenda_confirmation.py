"""Confirmacao em 2 passos e lembretes da agenda (8.6b).

Fluxo:
1. Com `confirmation_required` ligado, a IA cria um agendamento **provisorio**
   (status `awaiting_confirmation`) em vez de confirmar direto.
2. O pipeline (`conversation_service`) envia o pedido de confirmacao ao cliente
   via WhatsApp (uma unica vez por compromisso, deduplicado por evento).
3. Quando o cliente responde CONFIRMAR/CANCELAR, o pipeline intercepta ANTES da
   IA e processa de forma deterministica (sem custo de LLM):
   - confirmar -> status `confirmed` + envia `confirmation_message`;
   - cancelar -> status `canceled`.
4. Tasks de fundo (Celery): expiram provisorios sem confirmacao dentro de
   `confirmation_expiry_hours` e enviam lembretes em `reminder_hours`.

Auditabilidade: cada acao gera um `AppointmentEvent` (confirmation_requested,
confirmed, canceled_by_client, confirmation_expired, reminder_sent).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.config import get_secret
from app.models.agenda_config import AgendaConfig
from app.models.appointment import Appointment
from app.models.appointment_event import AppointmentEvent
from app.models.pending_appointment_action import PendingAppointmentAction
from app.services import agenda as ag
from app.services import evolution
from app.services.config_service import get_or_create_config
from app.services.field_crypto import decrypt_field

logger = logging.getLogger(__name__)

EVENT_REQUESTED = "confirmation_requested"
EVENT_CONFIRMED = "confirmed"
EVENT_CANCELED_BY_CLIENT = "canceled_by_client"
EVENT_EXPIRED = "confirmation_expired"
EVENT_REMINDER = "reminder_sent"

# Acoes pendentes de remarcar/cancelar (consentimento server-side)
EVENT_RESCHEDULE_REQUESTED = "reschedule_requested"
EVENT_RESCHEDULE_CONFIRMED = "reschedule_confirmed"
EVENT_RESCHEDULE_REJECTED = "reschedule_rejected"
EVENT_RESCHEDULE_FAILED = "reschedule_failed"
EVENT_CANCEL_REQUESTED = "cancel_requested"
EVENT_CANCEL_CONFIRMED = "cancel_confirmed_by_client"
EVENT_CANCEL_REJECTED = "cancel_rejected"
EVENT_PENDING_EXPIRED = "pending_action_expired"

CONFIRM_MARKERS = ("confirm", "agend")
CANCEL_MARKERS = (
    "cancel",
    "desmarc",
    "nao quero",
    "nao vou",
    "nao, ",
)
VERBAL_YES = {"sim", "ok", "pode", "pode sim", "quero sim", "beleza"}


# ---------------------------------------------------------------------------
# Parsing da resposta do cliente
# ---------------------------------------------------------------------------


def _strip_accents(value: str) -> str:
    replacements = {
        "á": "a", "à": "a", "â": "a", "ã": "a",
        "é": "e", "ê": "e",
        "í": "i",
        "ó": "o", "ô": "o", "õ": "o",
        "ú": "u", "ü": "u",
        "ç": "c",
        "não": "nao",
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    return value


def parse_confirmation_reply(text: str) -> str | None:
    """Interpreta a resposta do cliente a um pedido de confirmacao.

    Retorna "confirm" ou "cancel"; None quando a mensagem nao parece uma
    confirmacao (passa a ser tratada normalmente pela IA/workflow).
    """
    if not text or not text.strip():
        return None
    s = _strip_accents(text.strip().lower())
    if any(marker in s for marker in CANCEL_MARKERS):
        return "cancel"
    if any(marker in s for marker in CONFIRM_MARKERS):
        return "confirm"
    if s in VERBAL_YES:
        return "confirm"
    return None


# ---------------------------------------------------------------------------
# Templates de mensagem
# ---------------------------------------------------------------------------


def _fill(template: str | None, *, nome: str = "", servico: str = "", data: str = "", horario: str = "") -> str:
    return (template or "").format(
        nome=nome.strip() or "cliente",
        servico=servico.strip() or "agendamento",
        data=data or "",
        horario=horario or "",
    )


def build_request_text(cfg: AgendaConfig, appt: Appointment) -> str:
    return _fill(
        cfg.confirmation_request_message or ag.DEFAULT_CONFIRMATION_REQUEST_MESSAGE,
        nome=appt.customer_name or "",
        servico=appt.service or "",
        data=appt.date,
        horario=appt.start_time,
    )


def build_confirmation_text(cfg: AgendaConfig, appt: Appointment) -> str:
    return _fill(
        cfg.confirmation_message or ag.DEFAULT_CONFIRMATION_MESSAGE,
        nome=appt.customer_name or "",
        servico=appt.service or "",
        data=appt.date,
        horario=appt.start_time,
    )


def build_reminder_text(cfg: AgendaConfig, appt: Appointment) -> str:
    return _fill(
        cfg.reminder_message or ag.DEFAULT_REMINDER_MESSAGE,
        nome=appt.customer_name or "",
        servico=appt.service or "",
        data=appt.date,
        horario=appt.start_time,
    )


def build_reschedule_request_text(cfg: AgendaConfig, appt: Appointment, fields: dict) -> str:
    """Pedido de confirmacao de remarcacao (antigo -> novo)."""
    new_date = str(fields.get("date") or appt.date)
    new_start = str(fields.get("start_time") or appt.start_time)
    return (
        f"Voce pediu para remarcar seu compromisso de {appt.date} as {appt.start_time}"
        f" para {new_date} as {new_start}. Responda CONFIRMAR para aceitar ou "
        "CANCELAR para manter o horario atual."
    )


def build_cancel_request_text(cfg: AgendaConfig, appt: Appointment) -> str:
    """Pedido de confirmacao de cancelamento."""
    return (
        f"Deseja cancelar seu compromisso de {appt.date} as {appt.start_time}? "
        "Responda CONFIRMAR para cancelar ou CANCELAR para manter."
    )


def build_rejected_reschedule_text(cfg: AgendaConfig, appt: Appointment) -> str:
    return (
        f"Sem problemas! Mantivemos seu compromisso de {appt.date} as {appt.start_time}."
    )


def build_rejected_cancel_text(cfg: AgendaConfig, appt: Appointment) -> str:
    return (
        f"Ok! Seu compromisso de {appt.date} as {appt.start_time} permanece agendado."
    )


def build_canceled_text(cfg: AgendaConfig, appt: Appointment) -> str:
    return (
        f"Seu compromisso de {appt.date} as {appt.start_time} foi cancelado. "
        "Se quiser remarcar, e so chamar aqui!"
    )


# ---------------------------------------------------------------------------
# Evolution (config da empresa com fallback global)
# ---------------------------------------------------------------------------


def _evolution_settings(db: Session, company_id: int) -> dict:
    config = get_or_create_config(db, company_id)
    return {
        "base_url": decrypt_field(config.evolution_base_url) or get_secret("EVOLUTION_BASE_URL"),
        "api_key": decrypt_field(config.evolution_api_key) or get_secret("EVOLUTION_API_KEY"),
        "instance": config.evolution_instance or get_secret("EVOLUTION_INSTANCE") or "default",
    }


async def _send(db: Session, company_id: int, *, to_phone: str, text: str) -> bool:
    settings = _evolution_settings(db, company_id)
    if not settings["base_url"]:
        return False
    try:
        await evolution.send_text(
            to_phone=to_phone,
            text=text,
            base_url=settings["base_url"],
            api_key=settings["api_key"],
            instance=settings["instance"],
        )
        return True
    except evolution.EvolutionError:
        logger.warning(
            "Envio automatico da agenda falhou.",
            extra={"company_id": company_id, "phone": to_phone},
        )
        return False


def _has_event(db: Session, appointment_id: int, action: str) -> bool:
    from sqlalchemy import func

    count = (
        db.query(func.count(AppointmentEvent.id))
        .filter(
            AppointmentEvent.appointment_id == appointment_id,
            AppointmentEvent.action == action,
        )
        .scalar()
    )
    return bool(count)


def find_pending(db: Session, company_id: int, phone: str) -> Appointment | None:
    """Proximo compromisso aguardando confirmacao deste cliente."""
    return (
        db.query(Appointment)
        .filter(
            Appointment.company_id == company_id,
            Appointment.phone == phone,
            Appointment.status == ag.AWAITING_CONFIRMATION,
        )
        .order_by(Appointment.id.desc())
        .first()
    )


def find_pending_action(db: Session, company_id: int, phone: str) -> PendingAppointmentAction | None:
    """Proxima acao pendente (remarcar/cancelar) deste cliente."""
    return (
        db.query(PendingAppointmentAction)
        .filter(
            PendingAppointmentAction.company_id == company_id,
            PendingAppointmentAction.phone == phone,
        )
        .order_by(PendingAppointmentAction.id.desc())
        .first()
    )


# ---------------------------------------------------------------------------
# Pedido de confirmacao (apos criacao provisoria)
# ---------------------------------------------------------------------------


async def send_confirmation_request(db: Session, company_id: int, appointment_id: int) -> str:
    """Envia (uma unica vez) o pedido de confirmacao de um compromisso provisorio.

    Retorna: "sent" | "skipped" | "no_evolution" | "send_failed".
    """
    cfg = ag.get_for_company(db, company_id)
    appt = ag.get_appointment(db, company_id, appointment_id)
    if not cfg or appt.status != ag.AWAITING_CONFIRMATION:
        return "skipped"
    if _has_event(db, appt.id, EVENT_REQUESTED):
        return "skipped"

    settings = _evolution_settings(db, company_id)
    if not settings["base_url"]:
        return "no_evolution"

    if not await _send(db, company_id, to_phone=appt.phone, text=build_request_text(cfg, appt)):
        return "send_failed"

    ag.push_event(
        db,
        appt,
        action=EVENT_REQUESTED,
        actor_type="system",
        user_name="Secretaria IA",
        details={"message": build_request_text(cfg, appt)[:500]},
    )
    return "sent"


async def send_confirmation_requests_for_phone(db: Session, company_id: int, phone: str) -> int:
    """Envia os pedidos pendentes de um telefone (apos a IA criar provisorios)."""
    appts = (
        db.query(Appointment)
        .filter(
            Appointment.company_id == company_id,
            Appointment.phone == phone,
            Appointment.status == ag.AWAITING_CONFIRMATION,
        )
        .all()
    )
    sent = 0
    for appt in appts:
        try:
            if await send_confirmation_request(db, company_id, appt.id) == "sent":
                sent += 1
        except ag.AgendaError:
            continue
    return sent


# ---------------------------------------------------------------------------
# Acoes pendentes de remarcar/cancelar (consentimento server-side)
# ---------------------------------------------------------------------------


def _pending_payload(pending: PendingAppointmentAction) -> dict:
    try:
        data = json.loads(pending.payload or "{}")
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}


def _pending_appointment(db: Session, pending: PendingAppointmentAction) -> Appointment | None:
    try:
        return ag.get_appointment(db, pending.company_id, pending.appointment_id)
    except ag.AgendaError:
        return None


def _drop_pending(db: Session, pending: PendingAppointmentAction) -> None:
    db.delete(pending)
    db.commit()


async def send_pending_action_requests_for_phone(db: Session, company_id: int, phone: str) -> int:
    """Envia (uma unica vez cada) os pedidos de remarcacao/cancelamento pendentes.

    Idempotente pelo flag `notified`: pode ser chamado apos cada mensagem sem
    duplicar pedidos ao cliente.
    """
    pendings = (
        db.query(PendingAppointmentAction)
        .filter(
            PendingAppointmentAction.company_id == company_id,
            PendingAppointmentAction.phone == phone,
            PendingAppointmentAction.notified == 0,
        )
        .order_by(PendingAppointmentAction.id.desc())
        .all()
    )
    cfg = ag.get_for_company(db, company_id)
    sent = 0
    for pending in pendings:
        appt = _pending_appointment(db, pending)
        if appt is None or appt.status not in ag.ACTIVE_STATUSES:
            # Compromisso deixou de existir/esta cancelado: pendencia nao faz sentido.
            _drop_pending(db, pending)
            continue
        if pending.action == "reschedule":
            text = build_reschedule_request_text(cfg, appt, _pending_payload(pending))
            event = EVENT_RESCHEDULE_REQUESTED
        elif pending.action == "cancel":
            text = build_cancel_request_text(cfg, appt)
            event = EVENT_CANCEL_REQUESTED
        else:
            _drop_pending(db, pending)
            continue

        if not await _send(db, company_id, to_phone=appt.phone, text=text):
            continue
        pending.notified = 1
        db.commit()
        ag.push_event(
            db,
            appt,
            action=event,
            actor_type="system",
            user_name="Secretaria IA",
            details={"message": text[:500]},
        )
        sent += 1
    return sent


async def _resolve_reschedule_reply(
    db: Session,
    *,
    cfg: AgendaConfig,
    pending: PendingAppointmentAction,
    appt: Appointment,
    decision: str,
    text: str,
) -> dict:
    fields = _pending_payload(pending)
    if decision == "confirm":
        try:
            ag.update_appointment(
                db,
                appt.company_id,
                appt.id,
                fields=fields,
                actor_type="system",
                user_name="Secretaria IA",
            )
        except ag.AgendaError as exc:
            # Slot tomado por outro agendamento entre o pedido e a confirmacao.
            _drop_pending(db, pending)
            ag.push_event(
                db,
                appt,
                action=EVENT_RESCHEDULE_FAILED,
                actor_type="system",
                user_name="Secretaria IA",
                details={"code": exc.code},
            )
            reply = (
                f"O horario {fields.get('start_time', appt.start_time)} de "
                f"{fields.get('date', appt.date)} nao esta mais disponivel. "
                "Quer escolher outro horario?"
            )
            sent = await _send(db, appt.company_id, to_phone=appt.phone, text=reply)
            return {
                "status": "rejected",
                "appointment_id": appt.id,
                "reply_text": reply if sent else None,
            }

        _drop_pending(db, pending)
        ag.push_event(
            db,
            appt,
            action=EVENT_RESCHEDULE_CONFIRMED,
            actor_type="system",
            user_name="Secretaria IA",
            details={"via": "whatsapp", "message": text[:200]},
        )
        confirmation_text = build_confirmation_text(cfg, appt)
        sent = await _send(db, appt.company_id, to_phone=appt.phone, text=confirmation_text)
        return {
            "status": "confirmed",
            "appointment_id": appt.id,
            "reply_text": confirmation_text if sent else None,
        }

    # Cliente rejeitou: mantem o compromisso original.
    _drop_pending(db, pending)
    ag.push_event(
        db,
        appt,
        action=EVENT_RESCHEDULE_REJECTED,
        actor_type="system",
        user_name="Secretaria IA",
        details={"message": text[:200]},
    )
    reply = build_rejected_reschedule_text(cfg, appt)
    sent = await _send(db, appt.company_id, to_phone=appt.phone, text=reply)
    return {
        "status": "rejected",
        "appointment_id": appt.id,
        "reply_text": reply if sent else None,
    }


async def _resolve_cancel_reply(
    db: Session,
    *,
    cfg: AgendaConfig,
    pending: PendingAppointmentAction,
    appt: Appointment,
    decision: str,
    text: str,
) -> dict:
    if decision == "confirm":
        reason = str(_pending_payload(pending).get("reason") or "").strip()[:500]
        ag.cancel_appointment(
            db,
            appt.company_id,
            appt.id,
            actor_type="system",
            user_name="Secretaria IA",
            reason=reason or "Cliente confirmou cancelamento via WhatsApp",
        )
        _drop_pending(db, pending)
        ag.push_event(
            db,
            appt,
            action=EVENT_CANCEL_CONFIRMED,
            actor_type="system",
            user_name="Secretaria IA",
            details={"message": text[:200]},
        )
        reply = build_canceled_text(cfg, appt)
        sent = await _send(db, appt.company_id, to_phone=appt.phone, text=reply)
        return {
            "status": "canceled",
            "appointment_id": appt.id,
            "reply_text": reply if sent else None,
        }

    # Cliente rejeitou: compromisso permanece agendado.
    _drop_pending(db, pending)
    ag.push_event(
        db,
        appt,
        action=EVENT_CANCEL_REJECTED,
        actor_type="system",
        user_name="Secretaria IA",
        details={"message": text[:200]},
    )
    reply = build_rejected_cancel_text(cfg, appt)
    sent = await _send(db, appt.company_id, to_phone=appt.phone, text=reply)
    return {
        "status": "rejected",
        "appointment_id": appt.id,
        "reply_text": reply if sent else None,
    }


async def _process_pending_action_reply(
    db: Session,
    *,
    company_id: int,
    phone: str,
    text: str,
    decision: str,
) -> dict:
    """Resolve a acao pendente (remarcar/cancelar) mais recente do cliente."""
    cfg = ag.get_for_company(db, company_id)
    pending = find_pending_action(db, company_id, phone)
    if not cfg or not pending:
        return {"status": "ignored", "appointment_id": None, "reply_text": None}

    appt = _pending_appointment(db, pending)
    if appt is None or appt.status not in ag.ACTIVE_STATUSES:
        _drop_pending(db, pending)
        return {"status": "ignored", "appointment_id": None, "reply_text": None}

    if pending.action == "reschedule":
        return await _resolve_reschedule_reply(
            db, cfg=cfg, pending=pending, appt=appt, decision=decision, text=text
        )
    if pending.action == "cancel":
        return await _resolve_cancel_reply(
            db, cfg=cfg, pending=pending, appt=appt, decision=decision, text=text
        )
    _drop_pending(db, pending)
    return {"status": "ignored", "appointment_id": None, "reply_text": None}


# ---------------------------------------------------------------------------
# Processamento da resposta do cliente (interceptado antes da IA)
# ---------------------------------------------------------------------------


async def process_confirmation_reply(
    db: Session,
    *,
    company_id: int,
    phone: str,
    text: str,
) -> dict:
    """Processa a resposta do cliente a um pedido da Secretaria IA.

    Ordem: (1) acao pendente de remarcar/cancelar (consentimento server-side);
    (2) confirmacao de criacao provisoria. Retorna {"status":
    "confirmed"|"canceled"|"rejected"|"ignored", "appointment_id"|None,
    "reply_text"|None}. O pipeline persiste `reply_text` como mensagem do bot.
    """
    decision = parse_confirmation_reply(text)
    if not decision:
        return {"status": "ignored", "appointment_id": None, "reply_text": None}

    pending_result = await _process_pending_action_reply(
        db, company_id=company_id, phone=phone, text=text, decision=decision
    )
    if pending_result["status"] != "ignored":
        return pending_result

    cfg = ag.get_for_company(db, company_id)
    appt = find_pending(db, company_id, phone)
    if not cfg or not appt or appt.status != ag.AWAITING_CONFIRMATION:
        return {"status": "ignored", "appointment_id": None, "reply_text": None}

    if decision == "confirm":
        ag.update_appointment(
            db,
            company_id,
            appt.id,
            fields={"status": "confirmed"},
            actor_type="system",
            user_name="Secretaria IA",
        )
        ag.push_event(
            db,
            appt,
            action=EVENT_CONFIRMED,
            actor_type="system",
            user_name="Secretaria IA",
            details={"via": "whatsapp", "message": text[:200]},
        )
        confirmation_text = build_confirmation_text(cfg, appt)
        sent = await _send(db, company_id, to_phone=appt.phone, text=confirmation_text)
        return {
            "status": "confirmed",
            "appointment_id": appt.id,
            "reply_text": confirmation_text if sent else None,
        }

    # cancelar
    ag.cancel_appointment(
        db,
        company_id,
        appt.id,
        actor_type="system",
        user_name="Secretaria IA",
        reason="Cliente cancelou respondendo ao pedido de confirmacao no WhatsApp",
    )
    ag.push_event(
        db,
        appt,
        action=EVENT_CANCELED_BY_CLIENT,
        actor_type="system",
        user_name="Secretaria IA",
        details={"message": text[:200]},
    )
    return {"status": "canceled", "appointment_id": appt.id, "reply_text": None}


# ---------------------------------------------------------------------------
# Tasks de fundo: expiracao e lembretes
# ---------------------------------------------------------------------------


def _utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def expire_stale(db: Session, now: datetime | None = None) -> int:
    """Cancela provisorios sem confirmacao apos `confirmation_expiry_hours`.

    Retorna a quantidade de compromissos expirados.
    """
    now_utc = _utc_naive(now or datetime.now(timezone.utc)) or datetime.utcnow()
    expired = 0
    configs = db.query(AgendaConfig).all()
    for cfg in configs:
        expiry_hours = int(cfg.confirmation_expiry_hours or ag.DEFAULT_CONFIRMATION_EXPIRY_HOURS)
        if expiry_hours <= 0:
            continue
        cutoff = now_utc - timedelta(hours=expiry_hours)
        candidates = (
            db.query(Appointment)
            .filter(
                Appointment.company_id == cfg.company_id,
                Appointment.status == ag.AWAITING_CONFIRMATION,
            )
            .all()
        )
        for appt in candidates:
            created = _utc_naive(appt.created_at)
            if created is None or created >= cutoff:
                continue
            ag.cancel_appointment(
                db,
                cfg.company_id,
                appt.id,
                actor_type="system",
                user_name="Secretaria IA",
                reason=f"Agendamento provisorio expirado apos {expiry_hours}h sem confirmacao",
            )
            ag.push_event(
                db,
                appt,
                action=EVENT_EXPIRED,
                actor_type="system",
                user_name="Secretaria IA",
                details={"expiry_hours": expiry_hours},
            )
            expired += 1

        # Acoes pendentes de remarcar/cancelar: expira as antigas e descarta as
        # de compromissos que nao estao mais ativos. O compromisso original
        # permanece inalterado.
        pendings = (
            db.query(PendingAppointmentAction)
            .filter(PendingAppointmentAction.company_id == cfg.company_id)
            .all()
        )
        for pending in pendings:
            appt = _pending_appointment(db, pending)
            active = appt is not None and appt.status in ag.ACTIVE_STATUSES
            created = _utc_naive(pending.created_at)
            if active and created is not None and created >= cutoff:
                continue
            if active:
                ag.push_event(
                    db,
                    appt,
                    action=EVENT_PENDING_EXPIRED,
                    actor_type="system",
                    user_name="Secretaria IA",
                    details={"action": pending.action},
                )
            _drop_pending(db, pending)
    return expired


def send_due_reminders(db: Session, now: datetime | None = None) -> int:
    """Envia lembretes dos proximos compromissos confirmados/scheduled.

    Retorna a quantidade de lembretes enviados. Deduplicado por evento
    `reminder_sent` (um lembrete por compromisso).

    Sincrono: usa um loop assincrono proprio para enviar via Evolution, para
    ser chamado diretamente por tasks do Celery (padrao `asyncio.run`).
    """
    import asyncio

    return asyncio.run(_send_due_reminders_async(db, now=now))


async def _send_due_reminders_async(db: Session, now: datetime | None = None) -> int:
    now_utc = now or datetime.now(timezone.utc)
    sent = 0
    configs = (
        db.query(AgendaConfig)
        .filter(AgendaConfig.reminders_enabled == 1, AgendaConfig.enabled == 1)
        .all()
    )
    for cfg in configs:
        try:
            tz = ZoneInfo(cfg.timezone or ag.DEFAULT_TIMEZONE)
        except (ZoneInfoNotFoundError, ValueError):
            tz = ZoneInfo("UTC")
        local_now = now_utc.astimezone(tz).replace(second=0, microsecond=0)
        hours = ag.parse_reminder_hours(cfg.reminder_hours)
        windows = [
            {"hours": h, "min_from": (h - 1) * 60, "min_to": h * 60}
            for h in hours
        ]
        date_low = (local_now - timedelta(days=1)).strftime("%Y-%m-%d")
        date_high = (local_now + timedelta(days=(max(hours) // 24) + 2)).strftime("%Y-%m-%d")

        appts = (
            db.query(Appointment)
            .filter(
                Appointment.company_id == cfg.company_id,
                Appointment.status.in_(("scheduled", "confirmed")),
                Appointment.date.between(date_low, date_high),
            )
            .all()
        )
        for appt in appts:
            start_dt = ag._slot_datetime(appt.date, appt.start_time, tz)
            if not start_dt:
                continue
            minutes_until = (start_dt - local_now).total_seconds() / 60
            if minutes_until <= 0:
                continue
            due = next(
                (w["hours"] for w in windows if w["min_from"] < minutes_until <= w["min_to"]),
                None,
            )
            if due is None or _has_event(db, appt.id, EVENT_REMINDER):
                continue
            if not await _send(db, cfg.company_id, to_phone=appt.phone, text=build_reminder_text(cfg, appt)):
                continue
            ag.push_event(
                db,
                appt,
                action=EVENT_REMINDER,
                actor_type="system",
                user_name="Secretaria IA",
                details={"hours": due},
            )
            sent += 1
    return sent