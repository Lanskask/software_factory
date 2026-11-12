"""`factory retro` counts typed Owner messages in a canned transcript and appends a dated table to LESSONS.md."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from factory.cli import main
from factory.retro import transcript_dir


def line(content: object, **kw: object) -> str:
    return json.dumps({"type": "user", "timestamp": "2026-11-12T00:00:00Z", "message": {"content": content}, **kw})


def test_retro_appends_dated_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    tdir = transcript_dir(project)
    tdir.mkdir(parents=True)
    (tdir / "abcdefgh.jsonl").write_text(
        "\n".join(
            [
                line("please push the branch and open a PR"),
                line("error: boom, solve this"),
                line([{"type": "tool_result", "content": "push"}]),
                line("push", isMeta=True),
                line("<system-reminder>push</system-reminder>"),
                "not json",
            ]
        )
    )
    assert main(["retro", str(project)]) == 0
    assert main(["retro", str(project)]) == 0
    text = (project / ".factory" / "LESSONS.md").read_text()
    assert f"<!-- retro {date.today()}: 2 typed messages -->" in text
    assert "| git_pr | 1 | [open] |" in text
    assert "| pasted_error | 1 | [open] |" in text
    assert text.count("<!-- retro") == 2  # appends, never overwrites
