"""`factory bootstrap` prints project-relative paths, one aligned line per fact."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from factory.cli import cmd_bootstrap


def test_bootstrap_output_uses_relative_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, capture_output=True, check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "config", k, v], cwd=tmp_path, check=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "SPEC.md").write_text("spec")
    monkeypatch.chdir(tmp_path)

    cmd_bootstrap(tmp_path)

    out = capsys.readouterr().out
    assert str(tmp_path) not in out
    assert out.splitlines() == [
        "✔ wrote .factory/config.toml  (check `checks` and `tickets_dir`, commit any edit)",
        "✔ added .factory/*, !.factory/config.toml to .gitignore",
        "✔ committed .factory/config.toml, .gitignore",
        "Stage: A Spec exists (docs/SPEC.md), no Tickets",
        "Next:  factory plan . --spec docs/SPEC.md",
    ]
