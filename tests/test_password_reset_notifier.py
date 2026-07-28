import pytest

from app.services.password_reset_notifier import ConsolePasswordResetNotifier


async def test_console_password_reset_notifier_prints_frontend_link(
    capsys: pytest.CaptureFixture[str],
) -> None:
    notifier = ConsolePasswordResetNotifier("https://frontend.example/")

    await notifier.send_password_reset_link(
        email="user@example.com",
        token="reset token",
    )

    assert capsys.readouterr().out == (
        "Password reset link for user@example.com: "
        "https://frontend.example/reset-password/confirm#token=reset+token\n"
    )
