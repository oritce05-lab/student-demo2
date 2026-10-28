"""Email delivery and the error log.

If email is not configured or sending fails, the message is kept in $STOCK_AGENT_HOME/outbox
so nothing is lost, and the problem is written to errors.log.
"""

from __future__ import annotations

import re
import smtplib
import traceback
from datetime import datetime, timezone
from email.message import EmailMessage

from .config import email_settings
from .portfolio import _home


def log_error(context: str, exc: BaseException | None = None) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    detail = "".join(traceback.format_exception(exc)).strip() if exc else ""
    with open(_home() / "errors.log", "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {context}\n{detail}\n\n" if detail else f"[{stamp}] {context}\n")


def _save_to_outbox(subject: str, html: str) -> str:
    outbox = _home() / "outbox"
    outbox.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^\w-]+", "-", subject)[:40].strip("-")
    path = outbox / f"{stamp}-{slug}.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


def send_email(subject: str, html: str, text: str | None = None, dry_run: bool = False) -> dict:
    """Send an HTML email. Returns {"sent", "configured", "outbox"}; unsent mail is kept in the outbox."""
    settings = email_settings()
    configured = all(settings[k] for k in ("user", "password", "to"))
    if dry_run or not configured:
        if not dry_run:
            log_error(f"Email not configured (SMTP_USER / SMTP_PASSWORD / ALERT_EMAIL_TO); kept in outbox: {subject}")
        return {"sent": False, "configured": configured, "outbox": _save_to_outbox(subject, html)}

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings["sender"]
    message["To"] = settings["to"]
    message.set_content(text or re.sub(r"<[^>]+>", "", html))
    message.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(settings["host"], settings["port"], timeout=30) as smtp:
            smtp.starttls()
            smtp.login(settings["user"], settings["password"])
            smtp.send_message(message)
        return {"sent": True, "configured": True, "outbox": None}
    except (smtplib.SMTPException, OSError) as e:
        log_error(f"Email send failed: {subject}", e)
        return {"sent": False, "configured": True, "outbox": _save_to_outbox(subject, html)}
