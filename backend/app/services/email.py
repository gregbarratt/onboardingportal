from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import settings


def smtp_is_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_from_email)


def send_password_reset_email(*, to_email: str, reset_url: str) -> bool:
    if not smtp_is_configured():
        return False

    message = EmailMessage()
    message["Subject"] = "Reset your One Travel Club portal password"
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message.set_content(
        "A password reset was requested for your One Travel Club portal account.\n\n"
        "Use this secure link to choose a new password:\n"
        f"{reset_url}\n\n"
        "This link expires soon and can only be used once. If you did not ask for this, "
        "please contact One Travel Club."
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)

    return True
