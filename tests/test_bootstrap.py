from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from factory.bootstrap import next_step
from factory.cli import main
from factory.config import Config
from factory.tracker import Ticket, Tracker


def repo(tmp_path: Path, branch: str = "main") -> Path:
    subprocess.run(["git", "init", "-q", "-b", branch, str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "config", k, v], cwd=tmp_path, check=True)
    return tmp_path


def git(p: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=p, check=True, capture_output=True, text=True).stdout.strip()


def test_bootstrap_commits_the_config_and_gitignore_it_wrote(tmp_path: Path) -> None:
    p = repo(tmp_path)
    (p / "notes.txt").write_text("the owner's own work\n")
    assert main(["bootstrap", str(p)]) == 0
    assert git(p, "log", "-1", "--format=%s") == "factory: config and .gitignore lines"
    assert git(p, "show", "--name-only", "--format=", "HEAD").splitlines() == [
        ".factory/config.toml",
        ".gitignore",
    ]
    assert git(p, "status", "--porcelain") == "?? notes.txt"  # the Owner's files stay uncommitted


def test_bootstrap_leaves_a_gitignore_with_the_owners_edits_uncommitted(tmp_path: Path) -> None:
    p = repo(tmp_path)
    (p / ".gitignore").write_text("a\n")
    git(p, "add", ".gitignore")
    git(p, "commit", "-qm", "init")
    (p / ".gitignore").write_text("a\nb\n")  # the Owner's uncommitted edit
    main(["bootstrap", str(p)])
    assert git(p, "show", "--name-only", "--format=", "HEAD").splitlines() == [".factory/config.toml"]
    assert git(p, "status", "--porcelain") == "M .gitignore"


def test_spec_without_tickets_points_at_plan_with_that_spec(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = repo(tmp_path)
    (p / "docs").mkdir()
    (p / "docs" / "SPEC.md").write_text("# Spec\n")
    assert main(["bootstrap", str(p)]) == 0
    out = capsys.readouterr().out
    assert f"factory plan {p.resolve()} --spec docs/SPEC.md" in out
    assert (p / ".factory" / "config.toml").exists() and (p / ".gitignore").exists()
    assert (p / ".scratch" / p.name / "tickets").is_dir()


def test_empty_project_on_wrong_branch_warns_and_points_at_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = repo(tmp_path, "master")
    main(["bootstrap", str(p)])
    out = capsys.readouterr().out
    assert "on branch master" in out and f"factory plan {p.resolve()}" in out and "--spec" not in out


def test_install_skill_copies_the_skill_into_the_given_directory(tmp_path: Path) -> None:
    assert main(["install-skill", "--dir", str(tmp_path)]) == 0
    assert (tmp_path / "factory" / "SKILL.md").read_text().startswith("---\nname: factory")


TEMPLATES = [".claude/settings.json", "CLAUDE.md", "docs/OWNER-ANSWERS.md"]


def test_bootstrap_copies_the_project_templates_and_commits_only_them(tmp_path: Path) -> None:
    p = repo(tmp_path)
    (p / "notes.txt").write_text("the owner's own work\n")
    main(["bootstrap", str(p)])
    assert git(p, "show", "--name-only", "--format=%s", "HEAD~1").splitlines() == [
        "factory: project rules, settings and owner-answers templates",
        "",
        *TEMPLATES,
    ]
    assert ".factory/handoffs/latest.md" in (p / "CLAUDE.md").read_text()
    assert "Default:" in (p / "docs" / "OWNER-ANSWERS.md").read_text()
    assert git(p, "status", "--porcelain") == "?? notes.txt"


def test_bootstrap_never_overwrites_an_existing_claude_md(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = repo(tmp_path)
    (p / "CLAUDE.md").write_text("the owner's rules\n")
    main(["bootstrap", str(p)])
    assert (p / "CLAUDE.md").read_text() == "the owner's rules\n"
    assert "CLAUDE.md exists: the rules template was not applied" in capsys.readouterr().out
    assert (p / ".claude" / "settings.json").exists() and (p / "docs" / "OWNER-ANSWERS.md").exists()


def tk(num: str, state: str, ready: bool = False) -> Ticket:
    return Ticket(num=num, state=state, ready=ready, slug="x")


CFG = Config(tickets_dir="t", checks=())


@pytest.mark.parametrize(
    "tickets, expected",
    [
        ([tk("01", "done"), tk("02", "todo", True)], ("build (1/2 tickets)", "factory run P")),
        ([tk("01", "done"), tk("02", "todo")], ("build (1/2 tickets), blocked", "factory status P")),
        ([tk("01", "done")], ("verify (1/1 tickets)", "review the draft PRs")),
    ],
)
def test_next_step_with_tickets(
    monkeypatch: pytest.MonkeyPatch, tickets: list[Ticket], expected: tuple[str, str]
) -> None:
    monkeypatch.setattr(Tracker, "exists", lambda self: True)
    monkeypatch.setattr(Tracker, "status", lambda self: tickets)
    assert next_step(Path("P"), CFG) == expected


def test_next_step_before_tickets_goes_idea_answers_spec_tickets(tmp_path: Path) -> None:
    assert next_step(tmp_path, CFG) == ("idea", f"write docs/IDEA.md, then factory plan {tmp_path}")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "IDEA.md").write_text("an idea\n")
    assert next_step(tmp_path, CFG)[0] == "answers"
    answers = tmp_path / "docs" / "OWNER-ANSWERS.md"
    answers.write_text("## 1. Idea\n\nDefault: none.\n\nAnswer:\n\n## 2. License\n\nAnswer: private\n")
    assert next_step(tmp_path, CFG)[0] == "answers"  # only Q2 is answered
    answers.write_text("## 1. Idea\n\nAnswer: a todo app\n")
    assert next_step(tmp_path, CFG) == ("spec", f"factory plan {tmp_path}")
    (tmp_path / "docs" / "SPEC.md").write_text("spec")
    assert next_step(tmp_path, CFG)[0] == "tickets (spec docs/SPEC.md)"


def test_status_prints_the_stage_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    p = repo(tmp_path)
    main(["bootstrap", str(p)])
    capsys.readouterr()
    monkeypatch.chdir(p)
    main(["status", str(p)])
    assert capsys.readouterr().out.startswith("Stage: idea, Next: write docs/IDEA.md, then factory plan .\n")


def test_session_start_hook_prints_the_latest_handoff_and_exits_0_without_one(tmp_path: Path) -> None:
    p = repo(tmp_path)
    main(["bootstrap", str(p)])
    hook = json.loads((p / ".claude" / "settings.json").read_text())["hooks"]["SessionStart"][0]["hooks"][0]

    def run() -> subprocess.CompletedProcess[str]:
        env = {"CLAUDE_PROJECT_DIR": str(p)}
        return subprocess.run(["/bin/sh", "-c", hook["command"]], cwd="/", env=env, capture_output=True, text=True)

    assert (run().returncode, run().stdout) == (0, "")
    (p / ".factory" / "handoffs").mkdir(parents=True)
    (p / ".factory" / "handoffs" / "latest.md").write_text("# Handoff\nnext: ticket 03\n")
    assert "next: ticket 03" in run().stdout
