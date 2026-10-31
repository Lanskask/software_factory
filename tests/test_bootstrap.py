from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from factory.cli import main


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
