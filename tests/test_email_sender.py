from email.message import EmailMessage
from unittest.mock import MagicMock

from app.services.email_sender import SmtpEmailSender


async def test_smtp_email_sender_uses_tls_and_authentication(monkeypatch) -> None:
    smtp = MagicMock()
    smtp_context = MagicMock()
    smtp_context.__enter__.return_value = smtp
    smtp_factory = MagicMock(return_value=smtp_context)
    monkeypatch.setattr("app.services.email_sender.smtplib.SMTP", smtp_factory)

    sender = SmtpEmailSender(
        host="smtp.example",
        port=587,
        username="smtp-user",
        password="smtp-password",
        use_tls=True,
        use_auth=True,
    )
    message = EmailMessage()

    await sender.send(message)

    smtp_factory.assert_called_once_with("smtp.example", 587)
    smtp.starttls.assert_called_once_with()
    smtp.login.assert_called_once_with("smtp-user", "smtp-password")
    smtp.send_message.assert_called_once_with(message)


async def test_smtp_email_sender_can_skip_tls_and_authentication(monkeypatch) -> None:
    smtp = MagicMock()
    smtp_context = MagicMock()
    smtp_context.__enter__.return_value = smtp
    smtp_factory = MagicMock(return_value=smtp_context)
    monkeypatch.setattr("app.services.email_sender.smtplib.SMTP", smtp_factory)

    sender = SmtpEmailSender(
        host="localhost",
        port=1025,
        username="local",
        password="local",
        use_tls=False,
        use_auth=False,
    )
    message = EmailMessage()

    await sender.send(message)

    smtp.starttls.assert_not_called()
    smtp.login.assert_not_called()
    smtp.send_message.assert_called_once_with(message)
