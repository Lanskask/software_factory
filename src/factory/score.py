"""Score a finished eval Run: one JSON line with what the Factory got done, what it cost and whether it holds up.

Usage: python -m factory.score RUN_DIR --hidden evals/hidden/slugify-cli

RUN_DIR is the fixture copy the Factory ran on. The hidden acceptance tests are copied into it only now, run with
this interpreter's pytest, and removed again. The hidden dir's `expected.json` names the trap Tickets (the review
should FAIL or Block them; every other Ticket should PASS) and the number of hidden tests. Cost, minutes and Session
counts come from `.factory/logs/*.jsonl`; interventions are the `- ` lines the Owner wrote in
`.factory/interventions.md` each time they stepped in.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from factory.claude import last_result
from factory.config import load_config
from factory.prompts import parse_verdict
from factory.tracker import Tracker

HIDDEN_DIR = ".hidden-tests"


def hidden_passed(run: Path, hidden: Path) -> int:
    dest = run / HIDDEN_DIR
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir()
    try:
        for f in hidden.glob("test_*.py"):
            shutil.copy(f, dest)
        report = dest / "report.xml"
        cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={report}", HIDDEN_DIR]
        subprocess.run(cmd, cwd=run, capture_output=True, text=True)
        if not report.exists():
            return 0
        suites = ET.parse(report).getroot().iter("testsuite")
        return sum(
            int(s.get("tests", 0)) - sum(int(s.get(k, 0)) for k in ("failures", "errors", "skipped")) for s in suites
        )
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def review_outcome(state: Path, key: str) -> str | None:
    """`blocked`, the verdict of the Ticket's last review (`PASS` or `FAIL`), or None when it was never reviewed."""
    if (state / "blocked" / f"{key}.md").exists():
        return "blocked"
    reviews = sorted((state / "logs").glob(f"{key}-review-*.jsonl"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
    if not reviews:
        return None
    final = last_result(reviews[-1].read_text()) or {}
    return "PASS" if parse_verdict(str(final.get("result") or ""))[0] else "FAIL"


def score(run: Path, hidden: Path) -> dict[str, object]:
    cfg = load_config(run)
    state = run / ".factory"
    expected = json.loads((hidden / "expected.json").read_text())
    tickets = Tracker(run, cfg.tickets_dir, sys.executable).status()
    checks_green = all(
        subprocess.run(["/bin/sh", "-c", c], cwd=run, capture_output=True).returncode == 0 for c in cfg.checks
    )
    agreed = judged = 0
    for t in tickets:
        outcome = review_outcome(state, t.file_key)
        if outcome is None:
            continue
        judged += 1
        agreed += outcome != "PASS" if t.num in expected["trap"] else outcome == "PASS"
    logs = sorted((state / "logs").glob("*.jsonl"))
    results = [last_result(p.read_text()) or {} for p in logs]
    interventions = state / "interventions.md"
    return {
        "run": run.name,
        "tickets": len(tickets),
        "done": sum(t.state == "done" for t in tickets),
        "blocked": len(list((state / "blocked").glob("*.md"))),
        "checks_green": checks_green,
        "hidden_passed": hidden_passed(run, hidden),
        "hidden_total": expected["hidden_tests"],
        "review_agreed": agreed,
        "review_judged": judged,
        "cost_usd": round(sum(float(str(r.get("total_cost_usd") or 0)) for r in results), 4),
        # shortcut: a Session killed by the timeout has no result event, so its minutes and cost count as 0
        "minutes": round(sum(float(str(r.get("duration_ms") or 0)) for r in results) / 60_000, 1),
        "sessions": len(logs),
        "fix_sessions": sum(bool(re.fullmatch(r".+-fix-\d+", p.stem)) for p in logs),
        "interventions": len(re.findall(r"^- ", interventions.read_text(), re.M)) if interventions.exists() else 0,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run", type=Path, help="the fixture copy the Factory ran on")
    p.add_argument("--hidden", type=Path, required=True, help="the hidden tests and expected.json")
    args = p.parse_args(argv)
    print(json.dumps(score(args.run.resolve(), args.hidden.resolve())), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
