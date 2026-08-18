from email.message import EmailMessage
from unittest.mock import AsyncMock

from app.services.password_reset_notifier import EmailPasswordResetNotifier


async def test_email_password_reset_notifier_builds_frontend_link() -> None:
    email_sender = AsyncMock()
    notifier = EmailPasswordResetNotifier(
        frontend_url="https://frontend.example/",
        from_email="no-reply@example.com",
        email_sender=email_sender,
    )

    await notifier.send_password_reset_link(
        email="user@example.com",
        token="reset token",
    )

    email_sender.send.assert_awaited_once()
    message = email_sender.send.await_args.args[0]
    assert isinstance(message, EmailMessage)
    assert message["Subject"] == "Resetowanie hasła"
    assert message["From"] == "no-reply@example.com"
    assert message["To"] == "user@example.com"
    assert (
        "https://frontend.example/reset-password/confirm#token=reset+token"
        in message.get_content()
    )
