"""`factory retro` counts typed Owner messages in a canned transcript and appends a dated table to LESSONS.md."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from factory.cli import main
from factory.retro import retro, transcript_dir


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
    assert f"- retro git_pr [open] 1 of 2 typed messages on {date.today()}" in text
    assert "- retro pasted_error [open] 1 of 2" in text
    assert text.count("- retro git_pr") == 2  # appends, never overwrites
    assert all(ln.startswith("- retro ") for ln in text.splitlines())


def test_retro_resolves_shrunk_bucket(tmp_path: Path) -> None:
    (tmp_path / ".factory").mkdir()
    (tmp_path / ".factory" / "LESSONS.md").write_text("- retro git_pr [open] 5 of 9 typed messages on 2026-01-01\n")
    tdir = tmp_path / "t"
    tdir.mkdir()
    (tdir / "a.jsonl").write_text(line("hello"))
    retro(tmp_path, tdir)
    assert (tmp_path / ".factory" / "LESSONS.md").read_text().startswith("- retro git_pr [resolved] 5 of 9")


def test_run_keeps_retro_lines(tmp_path: Path) -> None:
    from factory.run import Factory

    r = object.__new__(Factory)
    r.state = tmp_path
    (tmp_path / "LESSONS.md").write_text("- retro git_pr [open] 1 of 2 x\n- 3 slug [open] review FAIL y\n")
    r.reset_lessons()
    assert (tmp_path / "LESSONS.md").read_text() == "- retro git_pr [open] 1 of 2 x\n"
