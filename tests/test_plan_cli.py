from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from factory.cli import main
from factory.config import Config, load_config
from factory.plan import Planner, chain, planning_rules
from factory.run import Factory

CLAUDE_LOG = r"""
import json, os, sys
with open(os.environ["FAKE_LOG"], "a") as f: f.write(json.dumps(sys.argv[1:]) + "\n")
print(json.dumps({"type": "result", "subtype": "success", "result": "ok", "total_cost_usd": 0.1}))
"""


def fake_claude(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    exe = tmp_path / "claude"
    exe.write_text(f"#!{sys.executable}\n{CLAUDE_LOG}")
    exe.chmod(0o755)
    monkeypatch.setenv("FAKE_LOG", str(tmp_path / "claude.log"))
    return exe


def calls(tmp_path: Path) -> list[list[str]]:
    log = tmp_path / "claude.log"
    return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []


def test_chain_without_spec_grills_first_and_with_spec_reviews_it() -> None:
    assert chain(spec=False) == (
        "mattpocock-skills:grill-with-docs",
        "mattpocock-skills:to-spec",
        "egm:egm-review-loop",
        "mattpocock-skills:to-tickets",
    )
    assert chain(spec=True) == ("egm:egm-review-loop", "mattpocock-skills:to-tickets")


def test_planning_rules_name_the_steps_the_tickets_dir_and_the_spec() -> None:
    cfg = Config(tickets_dir=".scratch/app/issues", checks=("make test",))
    r = planning_rules(cfg, Path("docs/spec.md"), chain(spec=True))
    assert "1. factory:egm-review-loop" in r and "2. factory:to-tickets" in r
    assert ".scratch/app/issues" in r and "docs/spec.md" in r
    assert "go-ahead" in r


def test_plan_does_nothing_when_tickets_exist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    exe = fake_claude(tmp_path, monkeypatch)
    proj = tmp_path / "p"
    (proj / "t").mkdir(parents=True)
    (proj / "t" / "tickets.py").write_text("print('01\\ttodo\\tREADY\\ta')\n")
    cfg = Config(tickets_dir="t", checks=("true",))
    assert Planner(proj, cfg, claude=str(exe), python=sys.executable).plan(None, bootstrap=True) == 0
    assert calls(tmp_path) == []


def test_plan_bootstraps_unattended_then_opens_an_interactive_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = fake_claude(tmp_path, monkeypatch)
    proj = tmp_path / "p"
    proj.mkdir()
    cfg = Config(tickets_dir="t", checks=("true",), implement_skills=(), review_skills=())
    planner = Planner(proj, cfg, claude=str(exe), python=sys.executable, skills=())
    assert planner.plan(None, bootstrap=True) == 1  # no Tickets were written by the fake
    boot, interactive = calls(tmp_path)
    assert boot[:2] == ["-p", "/egm:egm-bootstrap"] and "--max-budget-usd" in boot
    assert "-p" not in interactive and "--append-system-prompt" in interactive
    assert "factory:grill-with-docs" in interactive[interactive.index("--append-system-prompt") + 1]


def test_plan_without_bootstrap_puts_it_back_into_the_chain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    exe = fake_claude(tmp_path, monkeypatch)
    proj = tmp_path / "p"
    proj.mkdir()
    cfg = Config(tickets_dir="t", checks=("true",))
    Planner(proj, cfg, claude=str(exe), python=sys.executable, skills=()).plan(None, bootstrap=False)
    (interactive,) = calls(tmp_path)
    assert "1. factory:egm-bootstrap" in interactive[interactive.index("--append-system-prompt") + 1]


def test_init_writes_config_and_gitignore_once(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "Makefile").write_text("test:\n\ttrue\n")
    assert main(["init", str(tmp_path)]) == 0
    assert main(["init", str(tmp_path)]) == 0
    assert load_config(tmp_path).checks == ("make test",)
    gi = (tmp_path / ".gitignore").read_text()
    assert gi.count(".factory/*") == 1 and "!.factory/config.toml" in gi
    assert "already exists" in capsys.readouterr().out


def test_run_without_config_says_how_to_create_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", str(tmp_path)]) == 2
    assert "factory init" in capsys.readouterr().err


def test_run_flags_override_the_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".factory").mkdir()
    (tmp_path / ".factory" / "config.toml").write_text('tickets_dir = "t"\nchecks = ["true"]\n')
    seen: dict[str, Config] = {}

    def fake_run(self: Factory, *, dry_run: bool) -> int:
        seen["cfg"] = self.cfg
        return 0

    monkeypatch.setattr("factory.run.Factory.run", fake_run)
    assert main(["run", str(tmp_path), "--max-tickets", "3", "--budget-usd", "1.5"]) == 0
    assert (seen["cfg"].max_tickets, seen["cfg"].budget_usd) == (3, 1.5)
