"""`doctor` reads `claude mcp list`, `gh auth status` and `gh repo view` through an injectable runner."""

from collections.abc import Callable
from pathlib import Path

import pytest

from factory.bootstrap import doctor
from factory.cli import cmd_status
from factory.config import template

MCP = "Checking MCP server health...\n\na: npx a - ✓ Connected\nb: npx b - ✗ Failed to connect\n"
AUTH = "github.com\n  - Token scopes: 'gist', 'project', 'repo'\n"


def fake(mcp: str = MCP, auth: str = AUTH, perm: str = "WRITE\n") -> Callable[[list[str]], str]:
    out = {"mcp": mcp, "auth": auth, "repo": perm}
    return lambda cmd: out[cmd[1] if cmd[0] == "gh" else "mcp"]


def test_all_good() -> None:
    assert doctor(fake()) == "Doctor: MCP 1/2 up, gh scopes ok, can merge: yes"


def test_missing_scope_and_read_only() -> None:
    line = doctor(fake(auth="  - Token scopes: 'repo'\n", perm="READ\n"))
    assert line == "Doctor: MCP 1/2 up, gh scopes missing project, can merge: no"


def test_status_prints_doctor_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("factory.cli.doctor", lambda: "Doctor: stub line")
    (tmp_path / ".factory").mkdir()
    (tmp_path / ".factory" / "config.toml").write_text(template(tmp_path))
    cmd_status(tmp_path)
    assert "Doctor: stub line" in capsys.readouterr().out.splitlines()


def test_tools_absent() -> None:
    assert doctor(lambda cmd: "") == "Doctor: MCP 0/0 up, gh scopes missing repo, project, can merge: no"
