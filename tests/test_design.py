from __future__ import annotations

from pathlib import Path

import pytest

from factory.bootstrap import missing_design, next_step
from factory.config import Config, ConfigError, load_config
from factory.tracker import Ticket, Tracker


def tickets(tmp_path: Path, files: dict[str, str]) -> Config:
    d = tmp_path / "t"
    d.mkdir()
    for name, text in files.items():
        (d / name).write_text(text)
    return Config(tickets_dir="t", checks=("true",), design=True)


def test_missing_design_lists_ui_tickets_without_a_design_line(tmp_path: Path) -> None:
    cfg = tickets(
        tmp_path,
        {
            "01-api.md": "# 01: Add the store\n\nOnly data and storage.\n",
            "02-board.md": "# 02: Board page\n\nA page with a button.\n",
            "03-form.md": "# 03: Login form\n\nDesign: penpot board Login v2\n\nA form.\n",
        },
    )
    assert missing_design(tmp_path, cfg) == ["02-board.md"]


def test_next_step_is_design_while_ui_tickets_lack_a_design_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tickets(tmp_path, {"01-page.md": "# 01: Home page\n"})
    ready = [Ticket(num="01", state="todo", ready=True, slug="page")]
    monkeypatch.setattr(Tracker, "exists", lambda self: True)
    monkeypatch.setattr(Tracker, "status", lambda self: ready)
    stage, cmd = next_step(tmp_path, cfg)
    assert stage == "design (0 of 1 tickets, 1 UI without a Design: line)"
    assert "design-checklist.md" in cmd
    (tmp_path / "t" / "01-page.md").write_text("# 01: Home page\n\nDesign: board Home\n")
    assert next_step(tmp_path, cfg)[0] == "build (0/1 tickets)"


def test_design_is_off_by_default_and_must_be_a_bool(tmp_path: Path) -> None:
    (tmp_path / ".factory").mkdir()
    cfg_file = tmp_path / ".factory" / "config.toml"
    cfg_file.write_text('tickets_dir = "t"\nchecks = ["make test"]\n')
    assert load_config(tmp_path).design is False
    cfg_file.write_text('tickets_dir = "t"\nchecks = ["make test"]\ndesign = true\n')
    assert load_config(tmp_path).design is True
    cfg_file.write_text('tickets_dir = "t"\nchecks = ["make test"]\ndesign = "yes"\n')
    with pytest.raises(ConfigError, match="design"):
        load_config(tmp_path)


def test_done_tickets_and_non_ticket_files_are_not_asked_for_a_design_line(tmp_path: Path) -> None:
    cfg = tickets(tmp_path, {"01-page.md": "# 01: Home page\n", "README.md": "Every page needs a button.\n"})
    assert missing_design(tmp_path, cfg) == ["01-page.md"]
    assert missing_design(tmp_path, cfg, frozenset({"page"})) == []
