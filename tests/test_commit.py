"""`commit()` force-adds the Factory's own files, even under an ignore rule, and nothing else."""

from __future__ import annotations

import subprocess
from pathlib import Path

from factory.cli import commit


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def test_commit_adds_ignored_path_but_not_other_ignored_files(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        git(tmp_path, "config", k, v)
    (tmp_path / ".gitignore").write_text(".claude/\n")  # stands in for the Owner's global excludes
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text("{}")
    (tmp_path / ".claude" / "scratch.txt").write_text("x")

    commit(tmp_path, [".claude/settings.json"], "msg")

    assert git(tmp_path, "ls-files").split() == [".claude/settings.json"]
