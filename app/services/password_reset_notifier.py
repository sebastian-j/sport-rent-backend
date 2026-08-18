from email.message import EmailMessage
from typing import Protocol
from urllib.parse import urlencode

from app.services.email_sender import EmailSender


class PasswordResetNotifier(Protocol):
    async def send_password_reset_link(
        self,
        *,
        email: str,
        token: str,
    ) -> None: ...


class EmailPasswordResetNotifier:
    def __init__(
        self,
        *,
        frontend_url: str,
        from_email: str,
        email_sender: EmailSender,
    ) -> None:
        self._frontend_url = frontend_url.rstrip("/")
        self._from_email = from_email
        self._email_sender = email_sender

    async def send_password_reset_link(
        self,
        *,
        email: str,
        token: str,
    ) -> None:
        fragment = urlencode({"token": token})
        reset_url = f"{self._frontend_url}/reset-password/confirm#{fragment}"

        message = EmailMessage()
        message["Subject"] = "Resetowanie hasła"
        message["From"] = self._from_email
        message["To"] = email
        message.set_content(
            "Otrzymaliśmy prośbę o zresetowanie hasła.\n\n"
            f"Ustaw nowe hasło: {reset_url}\n\n"
            "Jeśli nie wysyłałeś tej prośby, zignoruj tę wiadomość."
        )

        await self._email_sender.send(message)
