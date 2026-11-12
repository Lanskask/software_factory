"""The `protected` config key: --disallowedTools entries and the rules template's Protected section."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from factory.bootstrap import copy_templates
from factory.cli import cmd_bootstrap
from factory.config import Config, load_config
from factory.plan import Planner
from factory.run import Factory


def test_protected_paths_become_edit_and_write_disallowed_entries(tmp_path: Path) -> None:
    cfg = Config(tickets_dir="t", checks=("true",), protected=("data/shared.db",))
    cmd = Factory(tmp_path, cfg, python=sys.executable).command("p", review=False, name="n")
    disallowed = cmd[cmd.index("--disallowedTools") + 1 :]
    assert "Edit(data/shared.db)" in disallowed and "Write(data/shared.db)" in disallowed


def test_plan_bootstrap_session_denies_protected_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []

    def fake_run(cmd: list[str], *_: object) -> SimpleNamespace:
        seen.append(cmd)
        return SimpleNamespace(ok=True, text="", cost_usd=0.0)

    monkeypatch.setattr("factory.plan.run_session", fake_run)
    cfg = Config(tickets_dir="t", checks=("true",), protected=("data/shared.db",))
    Planner(tmp_path, cfg, python=sys.executable).bootstrap()
    disallowed = seen[0][seen[0].index("--disallowedTools") + 1 :]
    assert "Edit(data/shared.db)" in disallowed and "Write(data/shared.db)" in disallowed


def test_cmd_bootstrap_reads_protected_from_config(tmp_path: Path) -> None:
    (tmp_path / ".factory").mkdir()
    (tmp_path / ".factory" / "config.toml").write_text('tickets_dir = "t"\nchecks = ["x"]\nprotected = ["data/a.db"]\n')
    cmd_bootstrap(tmp_path)
    assert "- `data/a.db`" in (tmp_path / "CLAUDE.md").read_text()


def test_cmd_bootstrap_without_config_leaves_protected_empty(tmp_path: Path) -> None:
    cmd_bootstrap(tmp_path)
    assert "`protected` in `.factory/config.toml`" in (tmp_path / "CLAUDE.md").read_text()


def test_protected_defaults_to_nothing_and_loads_from_toml(tmp_path: Path) -> None:
    (tmp_path / ".factory").mkdir()
    (tmp_path / ".factory" / "config.toml").write_text('tickets_dir = "t"\nchecks = ["x"]\nprotected = ["a", "b/"]\n')
    assert load_config(tmp_path).protected == ("a", "b/")
    assert Config(tickets_dir="t", checks=()).protected == ()


def test_rules_template_lists_protected_paths(tmp_path: Path) -> None:
    copy_templates(tmp_path, ("data/shared.db",))
    text = (tmp_path / "CLAUDE.md").read_text()
    assert "- `data/shared.db`" in text and "{protected}" not in text


def test_rules_template_without_protected_says_how_to_fill_it(tmp_path: Path) -> None:
    copy_templates(tmp_path)
    assert "`protected` in `.factory/config.toml`" in (tmp_path / "CLAUDE.md").read_text()
