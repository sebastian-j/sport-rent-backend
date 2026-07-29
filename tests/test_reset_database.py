import sys

import pytest

from scripts.reset_database import confirm_database_reset, run_seed


def test_database_reset_requires_matching_database_name() -> None:
    assert not confirm_database_reset(
        "sport_rent",
        assume_yes=False,
        input_function=lambda _: "wrong_database",
    )
    assert confirm_database_reset(
        "sport_rent",
        assume_yes=False,
        input_function=lambda _: "sport_rent",
    )


def test_database_reset_can_skip_confirmation() -> None:
    def unexpected_input(_: str) -> str:
        raise AssertionError("input should not be requested")

    assert confirm_database_reset(
        "sport_rent",
        assume_yes=True,
        input_function=unexpected_input,
    )


def test_database_reset_runs_only_main_seed_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], bool]] = []

    def fake_run(command: list[str], *, check: bool) -> None:
        calls.append((command, check))

    monkeypatch.setattr("scripts.reset_database.subprocess.run", fake_run)

    run_seed()

    assert calls == [([sys.executable, "-m", "scripts.seed"], True)]
