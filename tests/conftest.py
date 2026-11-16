"""Tests never run the real `claude` or `gh` for the Doctor line of `factory status`."""

import pytest


@pytest.fixture(autouse=True)
def no_real_doctor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("factory.cli.doctor", lambda project: "Doctor: stub")
