"""Ferramentas de IA (function calling) da Agenda da Secretaria IA.

Expoe as definicoes OpenAPI-compativeis (`AGENDA_TOOLS`) e o executor
(`execute_agenda_tool`) usados pelo pipeline de atendimento
(`conversation_service`) quando a agenda da empresa esta habilitada.

Regras de seguranca:
- Nunca confirma um horario sem validar antes a disponibilidade: o executor de
  `criar_agendamento` exige que o slot esteja em `build_slots` no momento da
  criacao e que a agenda esteja ativa.
- Argumentos vêm do modelo (nao confiaveis): todos sao validados/tipados e
  traduzidos em mensagens de erro claras para o LLM se recuperar.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.models.agenda_config import AgendaConfig
from app.services import agenda as agenda_service
from app.services.business_hours import DEFAULT_TIMEZONE

ACTOR_TYPE = "system"
ACTOR_NAME = "Secretaria IA"

AGENDA_TOOLS_INSTRUCTION = (
    "\n\nVoce tambem pode gerenciar a agenda de compromissos da empresa. "
    "Quando o cliente pedir para agendar, remarcar ou cancelar: "
    "(1) pergunte a data desejada e do que se trata, se nao souber; "
    "(2) valide a disponibilidade com verificar_disponibilidade; "
    '(3) ofereça opções de horários livres e confirme com o cliente antes de criar; '
    "(4) use criar_agendamento SOMENTE apos validar a disponibilidade; "
    "(5) preencha o campo phone com o telefone do cliente; "
    "(6) datas relativas (hoje, amanha, segunda-feira) devem ser convertidas para "
    "o formato YYYY-MM-DD usando a data atual; "
    "(7) se o horario desejado estiver ocupado, verifique os proximos dias e "
    'ofereça alternativas; se a agenda não tiver horarios, informe educadamente.'
)


def _slots_payload(db: Session, company_id: int, date: str, cfg: AgendaConfig | None) -> dict:
    slots = agenda_service.build_slots(db, company_id, date)
    if not slots:
        return {"ok": True, "date": date, "slots": [], "message": "Nenhum horario livre neste dia."}
    window = agenda_service.window_for_date(cfg, date) if cfg else None
    message = (
        "Horarios livres: "
        + ", ".join(slots[:12])
        + (" (para mais horarios, informe outra data)." if len(slots) > 12 else ".")
    )
    return {"ok": True, "date": date, "slots": slots, "window": window, "message": message}


def _today(cfg: AgendaConfig | None) -> str:
    try:
        tz = ZoneInfo(cfg.timezone or DEFAULT_TIMEZONE) if cfg else ZoneInfo(DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo(DEFAULT_TIMEZONE)
    return datetime.now(tz).strftime("%Y-%m-%d")


def _criar(
    db: Session,
    company_id: int,
    args: dict,
    *,
    customer_name: str | None = None,
    phone: str | None = None,
) -> dict:
    phone = str(phone or args.get("phone") or "").strip()
    if not phone:
        return {"ok": False, "error": "Informe o telefone do cliente para criar o agendamento."}

    cfg = agenda_service.get_for_company(db, company_id)
    if not cfg or not cfg.enabled:
        return {
            "ok": False,
            "error": "A agenda da empresa nao esta ativa. Informe o cliente que ainda nao aceitamos agendamentos.",
        }

    date = str(args.get("date") or "").strip()
    start_time = str(args.get("start_time") or "").strip()
    end_time = str(args.get("end_time") or "").strip()
    if not date or not start_time:
        return {"ok": False, "error": "Informe data (YYYY-MM-DD) e horario inicial (HH:MM) para agendar."}

    if not agenda_service._valid_date(date) or not agenda_service._valid_time(start_time):
        return {"ok": False, "error": "Data ou horario invalidos. Use YYYY-MM-DD e HH:MM."}

    if not end_time:
        start_min = agenda_service._to_minutes(start_time)
        duration = int(cfg.slot_duration or agenda_service.default_duration())
        end_time = agenda_service._fmt(start_min + duration) if start_min is not None else ""

    service = str(args.get("service") or "").strip() or None
    notes = str(args.get("notes") or "").strip() or None
    customer_name = (str(customer_name or args.get("customer_name") or "").strip()) or None

    # Disponibilidade real no momento da criacao: o slot precisa estar livre.
    slots = agenda_service.build_slots(db, company_id, date)
    if start_time not in slots:
        return {
            "ok": False,
            "error": (
                f"O horario {start_time} nao esta disponivel em {date}. "
                "Chame verificar_disponibilidade para saber os horarios livres "
                "deste ou dos proximos dias e ofereça uma alternativa ao cliente."
            ),
        }

    try:
        appt = agenda_service.add_appointment(
            db,
            company_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            phone=phone,
            customer_name=customer_name,
            service=service,
            notes=notes,
            origin="whatsapp",
            actor_type=ACTOR_TYPE,
            user_name=ACTOR_NAME,
            skip_min_advance=False,
        )
    except agenda_service.AgendaError as exc:
        return {"ok": False, "error": exc.message}

    return {
        "ok": True,
        "appointment_id": appt.id,
        "date": appt.date,
        "start_time": appt.start_time,
        "end_time": appt.end_time,
        "message": f"Agendamento criado para {appt.date} das {appt.start_time} as {appt.end_time}.",
    }


def _alterar(db: Session, company_id: int, args: dict) -> dict:
    appt_id = args.get("appointment_id")
    try:
        appt_id = int(appt_id) if appt_id is not None else None
    except (TypeError, ValueError):
        return {"ok": False, "error": "Informe o appointment_id valido do compromisso a alterar."}
    if appt_id is None:
        return {"ok": False, "error": "Informe o appointment_id do compromisso a alterar."}

    fields: dict = {}
    for key in ("date", "start_time", "end_time", "service", "notes", "status"):
        value = args.get(key)
        if value is not None:
            fields[key] = str(value).strip()

    new_date = fields.get("date")
    if new_date is not None and not agenda_service._valid_date(new_date):
        return {"ok": False, "error": "Data invalida. Use YYYY-MM-DD."}
    if "start_time" in fields and not agenda_service._valid_time(fields["start_time"]):
        return {"ok": False, "error": "Horario inicial invalido. Use HH:MM."}
    if "start_time" in fields and "end_time" not in fields:
        cfg = agenda_service.get_for_company(db, company_id)
        start_min = agenda_service._to_minutes(fields["start_time"])
        duration = int(cfg.slot_duration or agenda_service.default_duration()) if cfg else agenda_service.default_duration()
        if start_min is not None:
            fields["end_time"] = agenda_service._fmt(start_min + duration)
    if "end_time" in fields and not agenda_service._valid_time(fields["end_time"]):
        return {"ok": False, "error": "Horario final invalido. Use HH:MM."}

    # Se remarcar data/horario, exigir que o novo slot esteja livre agora.
    if "date" in fields or "start_time" in fields:
        cfg = agenda_service.get_for_company(db, company_id)
        if not cfg or not cfg.enabled:
            return {"ok": False, "error": "A agenda da empresa nao esta ativa."}
        target_date = fields.get("date")
        target_start = fields.get("start_time")
        if target_date and target_start:
            slots = agenda_service.build_slots(db, company_id, target_date)
            if target_start not in slots:
                return {
                    "ok": False,
                    "error": (
                        f"O horario {target_start} em {target_date} nao esta disponivel. "
                        "Chame verificar_disponibilidade e ofereça uma alternativa."
                    ),
                }

    try:
        appt = agenda_service.update_appointment(
            db,
            company_id,
            appt_id,
            fields=fields,
            actor_type=ACTOR_TYPE,
            user_name=ACTOR_NAME,
            skip_min_advance=False,
        )
    except agenda_service.AgendaError as exc:
        return {"ok": False, "error": exc.message}

    return {
        "ok": True,
        "appointment_id": appt.id,
        "date": appt.date,
        "start_time": appt.start_time,
        "end_time": appt.end_time,
        "status": appt.status,
        "message": f"Compromisso atualizado para {appt.date} das {appt.start_time} as {appt.end_time}.",
    }


def _cancelar(db: Session, company_id: int, args: dict) -> dict:
    appt_id = args.get("appointment_id")
    try:
        appt_id = int(appt_id) if appt_id is not None else None
    except (TypeError, ValueError):
        return {"ok": False, "error": "Informe o appointment_id valido do compromisso a cancelar."}
    if appt_id is None:
        return {"ok": False, "error": "Informe o appointment_id do compromisso a cancelar."}

    reason = str(args.get("reason") or "").strip()[:500]
    try:
        appt = agenda_service.cancel_appointment(
            db,
            company_id,
            appt_id,
            actor_type=ACTOR_TYPE,
            user_name=ACTOR_NAME,
            reason=reason or "Cancelado pela Secretaria IA",
        )
    except agenda_service.AgendaError as exc:
        return {"ok": False, "error": exc.message}

    return {
        "ok": True,
        "appointment_id": appt.id,
        "status": appt.status,
        "message": f"Compromisso {appt.id} de {appt.date} cancelado.",
    }


def _consultar(db: Session, company_id: int, args: dict) -> dict:
    cfg = agenda_service.get_for_company(db, company_id)
    date_from = str(args.get("date_from") or "").strip() or _today(cfg)
    date_to = str(args.get("date_to") or "").strip()
    status = str(args.get("status") or "").strip() or None

    if not agenda_service._valid_date(date_from):
        return {"ok": False, "error": "date_from invalido. Use YYYY-MM-DD."}
    if date_to and not agenda_service._valid_date(date_to):
        return {"ok": False, "error": "date_to invalido. Use YYYY-MM-DD."}

    try:
        result = agenda_service.list_appointments(
            db,
            company_id,
            date_from=date_from or None,
            date_to=date_to or None,
            status=status,
            offset=0,
            limit=20,
        )
    except agenda_service.AgendaError as exc:
        return {"ok": False, "error": exc.message}

    return {
        "ok": True,
        "total": result["total"],
        "items": result["items"],
        "message": (
            f"{result['total']} compromisso(s) no período."
            if result["items"]
            else "Nenhum compromisso no período informado."
        ),
    }


def execute_agenda_tool(db: Session, company_id: int, name: str, args: dict) -> dict:
    """Executa uma ferramenta de agenda. Retorna sempre dict serializavel."""
    args = args or {}
    if name == "verificar_disponibilidade":
        date = str(args.get("date") or "").strip()
        if not date:
            return {"ok": False, "error": "Informe a data no formato YYYY-MM-DD."}
        if not agenda_service._valid_date(date):
            return {"ok": False, "error": "Data invalida. Use YYYY-MM-DD."}
        return _slots_payload(db, company_id, date, agenda_service.get_for_company(db, company_id))
    if name == "consultar_agenda":
        return _consultar(db, company_id, args)
    if name == "criar_agendamento":
        return _criar(db, company_id, args)
    if name == "alterar_agendamento":
        return _alterar(db, company_id, args)
    if name == "cancelar_agendamento":
        return _cancelar(db, company_id, args)
    return {"ok": False, "error": f"Ferramenta de agenda desconhecida: {name}"}


def _tool_schema(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


AGENDA_TOOLS: list[dict] = [
    _tool_schema(
        "verificar_disponibilidade",
        "Lista os horarios livres (HH:MM) de uma data para agendamento. "
        "Use SEMPRE antes de criar/alterar um agendamento e quando o horario "
        "solicitado pelo cliente estiver ocupado, para oferecer alternativas.",
        {
            "date": {
                "type": "string",
                "description": 'Data desejada no formato YYYY-MM-DD (use a data atual para "hoje", somando 1 dia para "amanha").',
            }
        },
        ["date"],
    ),
    _tool_schema(
        "consultar_agenda",
        "Lista os compromissos agendados da empresa, com filtro opcional por "
        "periodo e status. Use para saber o que ja esta marcado.",
        {
            "date_from": {"type": "string", "description": "Inicio do periodo (YYYY-MM-DD). Default: hoje."},
            "date_to": {"type": "string", "description": "Fim do periodo (YYYY-MM-DD)."},
            "status": {
                "type": "string",
                "description": 'Status: scheduled, confirmed, completed ou canceled.',
            },
        },
        [],
    ),
    _tool_schema(
        "criar_agendamento",
        "Cria um agendamento para o cliente. SO deve ser chamada depois de "
        "verificar disponibilidade (verificar_disponibilidade) e com o horario "
        "confirmado pelo cliente.",
        {
            "date": {"type": "string", "description": "Data do agendamento (YYYY-MM-DD)."},
            "start_time": {"type": "string", "description": "Horario de inicio (HH:MM)."},
            "end_time": {"type": "string", "description": "Horario de termino (HH:MM). Obrigatorio so se diferir da duracao padrao."},
            "service": {"type": "string", "description": "Tipo/assunto do compromisso."},
            "notes": {"type": "string", "description": "Observacoes do agendamento."},
            "customer_name": {"type": "string", "description": "Nome do cliente."},
            "phone": {"type": "string", "description": "Telefone do cliente (obrigatorio)."},
        },
        ["date", "start_time", "phone"],
    ),
    _tool_schema(
        "alterar_agendamento",
        "Altera um agendamento existente (remarcar data/horario, mudar servico, "
        "observacoes ou status). Informe appointment_id obtido em consultar_agenda.",
        {
            "appointment_id": {"type": "integer", "description": "ID do compromisso."},
            "date": {"type": "string", "description": "Nova data (YYYY-MM-DD)."},
            "start_time": {"type": "string", "description": "Novo horario de inicio (HH:MM)."},
            "end_time": {"type": "string", "description": "Novo horario de termino (HH:MM)."},
            "service": {"type": "string", "description": "Novo tipo/assunto do compromisso."},
            "notes": {"type": "string", "description": "Novas observacoes."},
            "status": {"type": "string", "description": "Novo status (scheduled/confirmed/completed/canceled)."},
        },
        ["appointment_id"],
    ),
    _tool_schema(
        "cancelar_agendamento",
        "Cancela um agendamento existente. Informe appointment_id obtido em "
        "consultar_agenda. Use somente apos confirmar o cancelamento com o cliente.",
        {
            "appointment_id": {"type": "integer", "description": "ID do compromisso."},
            "reason": {"type": "string", "description": "Motivo do cancelamento (opcional)."},
        },
        ["appointment_id"],
    ),
]