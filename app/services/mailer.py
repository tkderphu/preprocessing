"""
mailer.py
---------
Send the formatted Markdown document via SMTP email.
Uses aiosmtplib for async sending (called from sync Celery task via asyncio.run).
"""

import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

import aiosmtplib

from app.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()


def _build_html_body(job_id: str, file_name: str, markdown_preview: str) -> str:
    """Build a minimal HTML email body with a preview of the Markdown output."""
    preview = markdown_preview[:1500].replace("\n", "<br>")
    return f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 800px; margin: auto;">
      <h2 style="color: #2c3e50;">📄 Document Processing Complete</h2>
      <p><b>Job ID:</b> {job_id}</p>
      <p><b>File:</b> {file_name}</p>
      <hr>
      <h3>Preview</h3>
      <div style="background:#f8f9fa; padding:16px; border-radius:8px; font-family: monospace; white-space: pre-wrap;">
        {preview}
      </div>
      <br>
      <p style="color: #7f8c8d; font-size: 12px;">
        Full document attached as Markdown file.<br>
        <em>Document Intelligence Pipeline</em>
      </p>
    </body></html>
    """


async def _send_async(
    to:        str,
    subject:   str,
    html_body: str,
    attachment_path: Path | None = None,
) -> None:
    msg = MIMEMultipart("mixed")
    msg["From"]    = settings.mail_from or settings.smtp_user
    msg["To"]      = to
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if attachment_path and attachment_path.exists():
        with attachment_path.open("rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename=attachment_path.name,
        )
        msg.attach(part)

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )
    logger.info("Email sent to %s (subject: %s)", to, subject)


class MailService:
    """Send processing result emails with the Markdown file attached."""

    def send(
        self,
        to:              str,
        job_id:          str,
        file_name:       str,
        markdown:        str,
        markdown_file:   Path | None = None,
    ) -> None:
        """
        Synchronous wrapper around the async send — safe to call from Celery tasks.
        """
        if not settings.smtp_user or not settings.smtp_password:
            logger.warning("SMTP credentials not configured — skipping email.")
            return

        recipient = to or settings.mail_to
        if not recipient:
            logger.warning("No recipient email configured — skipping email.")
            return

        subject   = f"[Doc Intelligence] Processing complete — {file_name}"
        html_body = _build_html_body(job_id, file_name, markdown)

        try:
            asyncio.run(_send_async(recipient, subject, html_body, markdown_file))
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", recipient, exc)
            raise
