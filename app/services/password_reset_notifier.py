from typing import Protocol
from urllib.parse import urlencode


class PasswordResetNotifier(Protocol):
    async def send_password_reset_link(
        self,
        *,
        email: str,
        token: str,
    ) -> None: ...


class ConsolePasswordResetNotifier:
    def __init__(self, frontend_url: str) -> None:
        self._frontend_url = frontend_url.rstrip("/")

    async def send_password_reset_link(
        self,
        *,
        email: str,
        token: str,
    ) -> None:
        fragment = urlencode({"token": token})
        print(
            f"Password reset link for {email}: "
            f"{self._frontend_url}/reset-password/confirm#{fragment}",
            flush=True,
        )
