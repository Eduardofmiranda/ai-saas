"""Tasks de fundo da Agenda (8.6b): expiracao de provisorios e lembretes."""
from app.database.database import SessionLocal
from app.services.agenda_confirmation import expire_stale, send_due_reminders
from app.tasks.celery_app import celery_app


@celery_app.task
def expire_unconfirmed_appointments():
    """Cancela agendamentos provisorios (awaiting_confirmation) sem resposta."""
    db = SessionLocal()
    try:
        expired = expire_stale(db)
    finally:
        db.close()
    return {"expired": expired}


@celery_app.task
def send_agenda_reminders():
    """Envia lembretes dos proximos compromissos confirmados/scheduled."""
    db = SessionLocal()
    try:
        sent = send_due_reminders(db)
    finally:
        db.close()
    return {"sent": sent}