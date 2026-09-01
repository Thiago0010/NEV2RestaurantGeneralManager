import logging
from email.message import EmailMessage
import aiosmtplib
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

async def send_email(to: str, subject: str, body: str, html_body: Optional[str] = None) -> None:
    """
    Sends an email using SMTP settings defined in the application config.
    Supports both plain text and HTML bodies.
    """
    # Create the email message
    message = EmailMessage()
    message["From"] = settings.FROM_EMAIL
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        logger.info(f"Attempting to send email to {to} via {settings.SMTP_HOST}:{settings.SMTP_PORT}")

        use_tls = (settings.SMTP_PORT == 465)

        async with aiosmtplib.SMTP(
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            use_tls=use_tls
        ) as smtp:
            if not use_tls and settings.SMTP_TLS:
                try:
                    logger.info("Starting TLS (STARTTLS)...")
                    await smtp.starttls()
                except aiosmtplib.SMTPException as e:
                    if "already using TLS" in str(e):
                        logger.info("Connection already using TLS, skipping starttls()")
                    else:
                        raise e

            if settings.SMTP_USER and settings.SMTP_PASS:
                logger.info(f"Authenticating as {settings.SMTP_USER}...")
                await smtp.login(settings.SMTP_USER, settings.SMTP_PASS)

            await smtp.send_message(message)
            logger.info(f"Email successfully sent to {to}")

    except Exception as e:
        logger.error(f"SMTP Error sending email to {to}: {str(e)}", exc_info=True)
        raise RuntimeError(f"Failed to send email to {to}: {str(e)}") from e
