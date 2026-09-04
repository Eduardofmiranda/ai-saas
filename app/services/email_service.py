"""Servico de email via SMTP (usado na recuperacao de senha).

Configuracao via variaveis de ambiente:
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_USE_TLS

Sem SMTP_HOST/SMTP_FROM configurados, os endpoints de email retornam 503
(EmailNotConfigured) em vez de simular envio.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_secret


class EmailNotConfigured(Exception):
    """SMTP nao configurado no ambiente."""


def email_is_configured() -> bool:
    return bool(get_secret("SMTP_HOST") and get_secret("SMTP_FROM"))


def _send(from_addr: str, to_addr: str, subject: str, html: str) -> None:
    host = get_secret("SMTP_HOST")
    port = int(get_secret("SMTP_PORT", "587"))
    user = get_secret("SMTP_USER")
    password = get_secret("SMTP_PASSWORD")
    use_tls = str(get_secret("SMTP_USE_TLS", "true")).lower() in ("1", "true", "yes", "on")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(host, port, timeout=20) as server:
        if use_tls:
            server.starttls()
        if user:
            server.login(user, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())


def send_reset_email(to_email: str, reset_url: str) -> None:
    """Envia o email de recuperacao de senha. Levanta EmailNotConfigured se sem SMTP."""
    if not email_is_configured():
        raise EmailNotConfigured("SMTP not configured")

    subject = "Recuperacao de senha - FlowAI"
    html = (
        "<p>Voce solicitou a recuperacao da sua senha do FlowAI.</p>"
        f'<p><a href="{reset_url}">Clique aqui para criar uma nova senha</a></p>'
        "<p>Se nao foi voce, ignore este email. O link expira em alguns minutos.</p>"
    )
    _send(get_secret("SMTP_FROM"), to_email, subject, html)