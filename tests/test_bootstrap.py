from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from factory.cli import main


def repo(tmp_path: Path, branch: str = "main") -> Path:
    subprocess.run(["git", "init", "-q", "-b", branch, str(tmp_path)], check=True)
    return tmp_path


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
