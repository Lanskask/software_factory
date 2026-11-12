"""The eval scorer on a canned run directory: the slugify-cli fixture, the reference solution and fake Session logs."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from factory.config import load_config
from factory.run import Factory

EVALS = Path(__file__).resolve().parent.parent / "evals"
HIDDEN = EVALS / "hidden" / "slugify-cli"


def result(cost: float, text: str = "done") -> str:
    event = {"type": "result", "subtype": "success", "total_cost_usd": cost, "duration_ms": 60_000, "result": text}
    return json.dumps({"type": "system"}) + "\n" + json.dumps(event) + "\n"


def canned_run(tmp_path: Path, *, trap_passed: bool, checks: str) -> Path:
    run = tmp_path / "run"
    shutil.copytree(EVALS / "slugify-cli", run)
    shutil.copytree(HIDDEN / "reference" / "slugify_cli", run / "slugify_cli", dirs_exist_ok=True)
    state = run / ".factory"
    (state / "logs").mkdir(parents=True)
    (state / "config.toml").write_text(f'tickets_dir = ".scratch/slugify-cli/tickets"\nchecks = ["{checks}", "true"]\n')
    tickets = run / ".scratch" / "slugify-cli" / "tickets"
    done = ["01", "02", "03", "04", *(["05"] if trap_passed else [])]
    for f in tickets.glob("[0-9][0-9]-*.md"):
        if f.name[:2] in done:
            f.write_text(f.read_text().replace("**Status:** todo", "**Status:** done"))
    logs = {
        "01-implement-1": "done",
        "01-review-1": "a test is missing\n\nVERDICT: FAIL",
        "01-fix-1": "done",
        "01-review-2": "VERDICT: PASS",
        **{f"0{n}-implement-1": "done" for n in (2, 3, 4, 5)},
        **{f"0{n}-review-1": "VERDICT: PASS" for n in (2, 3, 4)},
    }
    if trap_passed:
        logs["05-review-1"] = "VERDICT: PASS"
    else:
        (state / "blocked").mkdir()
        (state / "blocked" / "05.md").write_text("# Blocked: 05 keep-case\n")
    for name, text in logs.items():
        (state / "logs" / f"{name}.jsonl").write_text(result(0.25, text))
    (state / "interventions.md").write_text("# Interventions\n\n- restarted the Run after a network error\n")
    return run


def score(run: Path) -> dict[str, object]:
    out = subprocess.run(
        [sys.executable, "-m", "factory.score", str(run), "--hidden", str(HIDDEN)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert len(out.splitlines()) == 1, out
    return json.loads(out)


def test_scores_a_run_whose_review_blocked_the_trap(tmp_path: Path) -> None:
    run = canned_run(tmp_path, trap_passed=False, checks="true")
    assert score(run) == {
        "run": "run",
        "tickets": 5,
        "done": 4,
        "blocked": 1,
        "checks_green": True,
        "hidden_passed": 15,
        "hidden_total": 15,
        "review_agreed": 5,
        "review_judged": 5,
        "cost_usd": 2.75,
        "minutes": 11.0,
        "sessions": 11,
        "fix_sessions": 1,
        "interventions": 1,
    }
    assert not (run / ".hidden-tests").exists()  # the hidden tests leave the run as they found it


def test_new_run_is_a_project_the_factory_can_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for k in ("GIT_AUTHOR", "GIT_COMMITTER"):
        monkeypatch.setenv(f"{k}_NAME", "t")
        monkeypatch.setenv(f"{k}_EMAIL", "t@t")
    run = tmp_path / "eval-1"
    subprocess.run(["sh", str(EVALS / "new_run.sh"), str(run), "sonnet"], check=True, capture_output=True)
    cfg = load_config(run)
    assert (cfg.model, cfg.checks) == ("sonnet", ("make test", "make lint"))
    assert Factory(run, cfg).run(dry_run=True) == 0
    assert "next: 01 on factory/01-core-slugify from main" in capsys.readouterr().out
    gh = subprocess.run([str(tmp_path / "eval-1.bin" / "gh"), "pr", "create"], capture_output=True, text=True)
    assert gh.returncode == 0 and gh.stdout.startswith("https://")


def test_a_passed_trap_disagrees_and_red_checks_count(tmp_path: Path) -> None:
    run = canned_run(tmp_path, trap_passed=True, checks="false")
    s = score(run)
    assert (s["done"], s["blocked"], s["checks_green"]) == (5, 0, False)
    assert (s["review_agreed"], s["review_judged"]) == (4, 5)
