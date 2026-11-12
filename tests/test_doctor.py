"""`doctor` reads `claude mcp list`, `gh auth status` and `gh repo view` through an injectable runner."""

from collections.abc import Callable
from pathlib import Path

import pytest

from factory.bootstrap import doctor
from factory.cli import cmd_status
from factory.config import template

MCP = "Checking MCP server health...\n\na: npx a - ✓ Connected\nb: npx b - ✗ Failed to connect\n"
AUTH = "github.com\n  - Token scopes: 'gist', 'project', 'repo'\n"


def fake(mcp: str = MCP, auth: str = AUTH, perm: str = "WRITE\n") -> Callable[[list[str], Path], str]:
    out = {"mcp": mcp, "auth": auth, "repo": perm}
    return lambda cmd, cwd: out[cmd[1] if cmd[0] == "gh" else "mcp"]


def test_all_good() -> None:
    assert doctor(Path("."), fake()) == "Doctor: MCP 1/2 up, gh scopes ok, can merge: yes"


def test_missing_scope_and_read_only() -> None:
    line = doctor(Path("."), fake(auth="  - Token scopes: 'repo'\n", perm="READ\n"))
    assert line == "Doctor: MCP 1/2 up, gh scopes missing project, can merge: no"


def test_status_prints_doctor_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("factory.cli.doctor", lambda project: "Doctor: stub line")
    (tmp_path / ".factory").mkdir()
    (tmp_path / ".factory" / "config.toml").write_text(template(tmp_path))
    cmd_status(tmp_path)
    assert "Doctor: stub line" in capsys.readouterr().out.splitlines()


def test_tools_absent() -> None:
    line = doctor(Path("."), lambda cmd, cwd: "")
    assert line == "Doctor: MCP 0/0 up, gh scopes missing repo, project, can merge: no"


def test_gh_repo_view_runs_in_the_project_directory(tmp_path: Path) -> None:
    seen: dict[str, Path] = {}

    def run(cmd: list[str], cwd: Path) -> str:
        seen[cmd[1]] = cwd
        return fake()(cmd, cwd)

    doctor(tmp_path, run)
    assert seen["repo"] == tmp_path


def test_token_login_without_a_scopes_line_is_unknown_not_missing() -> None:
    auth = "github.com\n  - Logged in to github.com account me (GH_TOKEN)\n"
    assert "gh scopes unknown" in doctor(Path("."), fake(auth=auth))
