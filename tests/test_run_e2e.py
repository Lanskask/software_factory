"""The whole Run against a real git repo and a bare origin, with fake `claude`, `gh` and `tickets.py` executables.

The fakes behave like the real tools as the Factory sees them: claude writes commits, marks the ticket done, writes
the Handoff and prints stream-json; gh records its arguments. Env vars make a fake session fail or a review say FAIL.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest

from factory.config import Config
from factory.run import Factory

FAKE_TICKETS = r"""
import json, sys
from pathlib import Path
args = sys.argv[1:]
d = Path(args[args.index("--dir") + 1]); cmd = args[args.index("--dir") + 2:]
db = d / "tickets.json"; t = json.loads(db.read_text())
if cmd[0] == "status":
    for n, v in t.items():
        ready = v["state"] == "todo" and all(t[b]["state"] == "done" for b in v["blocked_by"])
        print(f"{n}\t{v['state']}\t{'READY' if ready else ''}\t{v['slug']}")
elif cmd[0] == "show":
    print(f"# {cmd[1]}: {t[cmd[1]]['slug']}\n{t[cmd[1]].get('text', '')}")
elif cmd[0] == "mark":
    t[cmd[1]]["state"] = cmd[2]; db.write_text(json.dumps(t, indent=1))
"""

FAKE_CLAUDE = r"""
import json, os, re, subprocess, sys
prompt = sys.argv[sys.argv.index("-p") + 1]
log = os.environ["FAKE_LOG"]
with open(log, "a") as f: f.write(json.dumps(sys.argv[1:]) + "\n")
def result(text, subtype="success"):
    print(json.dumps({"type": "result", "subtype": subtype, "result": text, "total_cost_usd": 0.5}))
    sys.exit(0)
num = re.search(r"Ticket (\S+) ", prompt).group(1)
if "VERDICT" in prompt:
    fails = os.environ.get("FAKE_REVIEW_FAIL", "")
    marker = f".review-{num}"
    if num in fails.split(",") and not os.path.exists(marker):
        open(marker, "w").close()
        result("1. missing test for the empty case\nVERDICT: FAIL")
    result("looks fine\nVERDICT: PASS")
if num in os.environ.get("FAKE_FAIL", "").split(","):
    open(f"half-{num}.txt", "w").write("half done")
    result("BLOCKED: needs the owner's API key")
if "Review findings" in prompt:
    open(f"fix-{num}.txt", "w").write("x\n")
else:
    handoff = re.search(r"Handoff to (\S+\.md)", prompt).group(1)
    loose = os.environ.get("FAKE_HIGH", "")
    os.makedirs(os.path.dirname(handoff), exist_ok=True)
    with open(handoff, "w") as f:
        f.write("## Out of scope\n" + ("- [high] auth bypass\n" if num in loose.split(",") else "- [low] typo\n"))
    open(f"feature-{num}.txt", "w").write("x\n")
    tk = re.search(r"`(\S+ -I \S+ --dir \S+)`", prompt).group(1).split()
    subprocess.run([*tk, "mark", num, "done", "--brief", "did it"], check=True)
subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "commit", "-qm", f"ticket {num}"], check=True)
result("DONE")
"""

FAKE_GH = r"""
import json, os, sys
with open(os.environ["FAKE_GH_LOG"], "a") as f: f.write(json.dumps(sys.argv[1:]) + "\n")
print("https://github.com/o/r/pull/1")
"""


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def executable(path: Path, body: str) -> Path:
    path.write_text(f"#!{sys.executable}\n" + textwrap.dedent(body))
    path.chmod(0o755)
    return path


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    p = tmp_path / "proj"
    p.mkdir()
    git(p, "init", "-q", "-b", "main")
    git(p, "config", "user.email", "t@t")
    git(p, "config", "user.name", "t")
    tickets = p / "t"
    tickets.mkdir()
    (tickets / "tickets.py").write_text(FAKE_TICKETS)
    (p / ".gitignore").write_text(".factory/*\n!.factory/config.toml\n.review-*\n")
    git(p, "remote", "add", "origin", str(origin))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    executable(bin_dir / "claude", FAKE_CLAUDE)
    executable(bin_dir / "gh", FAKE_GH)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_LOG", str(tmp_path / "claude.log"))
    monkeypatch.setenv("FAKE_GH_LOG", str(tmp_path / "gh.log"))
    return p


def with_tickets(p: Path, tickets: dict[str, dict[str, object]]) -> None:
    for v in tickets.values():
        v.setdefault("state", "todo")
        v.setdefault("blocked_by", [])
    (p / "t" / "tickets.json").write_text(json.dumps(tickets, indent=1))
    git(p, "add", "-A")
    git(p, "commit", "-qm", "tickets")
    git(p, "push", "-q", "-u", "origin", "main")


def factory(p: Path, **kw: Any) -> Factory:
    cfg = Config(tickets_dir="t", checks=("test -f t/tickets.json",), implement_skills=(), review_skills=(), **kw)
    return Factory(p, cfg, python=sys.executable)


def gh_calls(p: Path) -> list[list[str]]:
    log = p.parent / "gh.log"
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def claude_calls(p: Path) -> list[list[str]]:
    log = p.parent / "claude.log"
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def test_run_stacks_branches_pushes_and_opens_draft_prs(project: Path) -> None:
    with_tickets(project, {"01": {"slug": "a"}, "02": {"slug": "b", "blocked_by": ["01"]}})
    assert factory(project).run() == 0
    assert git(project, "ls-remote", "--heads", "origin").count("refs/heads/factory/") == 2
    assert git(project, "merge-base", "--is-ancestor", "factory/01-a", "factory/02-b") == ""
    prs = gh_calls(project)
    assert [c[:3] for c in prs] == [["pr", "create", "--draft"]] * 2
    assert prs[0][prs[0].index("--base") + 1] == "main"
    assert prs[1][prs[1].index("--base") + 1] == "factory/01-a"
    assert all("merge" not in " ".join(c) for c in prs)
    assert "[low] typo" in (project / ".factory" / "LOOSE-ENDS.md").read_text()
    sessions = claude_calls(project)
    assert len(sessions) == 4  # implement + review per ticket
    assert all("Bash(git push*)" in c for c in sessions)


def test_blocked_ticket_is_recorded_its_dependent_skipped_and_the_rest_run(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_FAIL", "01")
    with_tickets(project, {"01": {"slug": "a"}, "02": {"slug": "b", "blocked_by": ["01"]}, "03": {"slug": "c"}})
    assert factory(project).run() == 1
    assert "API key" in (project / ".factory" / "blocked" / "01.md").read_text()
    heads = git(project, "ls-remote", "--heads", "origin")
    assert "factory/03-c" in heads and "factory/01-a" not in heads and "factory/02-b" not in heads
    assert git(project, "log", "-1", "--format=%s", "factory/01-a").startswith("factory: unfinished work")
    pr = gh_calls(project)[0]
    assert pr[pr.index("--base") + 1] == "main"


def test_run_stops_after_max_blocked(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_FAIL", "01,02")
    with_tickets(project, {"01": {"slug": "a"}, "02": {"slug": "b"}, "03": {"slug": "c"}})
    assert factory(project, max_blocked=2).run() == 1
    assert gh_calls(project) == []
    assert not (project / ".factory" / "blocked" / "03.md").exists()


def test_review_fail_gets_one_fix_session_then_passes(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_REVIEW_FAIL", "01")
    with_tickets(project, {"01": {"slug": "a"}})
    assert factory(project).run() == 0
    prompts = [c[c.index("-p") + 1] for c in claude_calls(project)]
    assert sum("VERDICT" in p for p in prompts) == 2
    assert any("missing test for the empty case" in p for p in prompts)


def test_high_loose_end_stops_the_run_after_its_pr(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_HIGH", "01")
    with_tickets(project, {"01": {"slug": "a"}, "02": {"slug": "b"}})
    assert factory(project).run() == 1
    assert len(gh_calls(project)) == 1


def test_ticket_mentioning_cloud_tools_is_skipped(project: Path) -> None:
    with_tickets(project, {"01": {"slug": "infra", "text": "run terraform apply"}, "02": {"slug": "b"}})
    assert factory(project).run() == 0
    assert "factory/01-infra" not in git(project, "branch")
    assert len(gh_calls(project)) == 1


def test_dirty_tree_refuses_to_start(project: Path) -> None:
    with_tickets(project, {"01": {"slug": "a"}})
    (project / "stray.txt").write_text("x")
    assert factory(project).run() == 1
    assert claude_calls(project) == []


def test_dry_run_spends_nothing(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with_tickets(project, {"01": {"slug": "a"}})
    assert factory(project).run(dry_run=True) == 0
    assert claude_calls(project) == [] and "/goal" in capsys.readouterr().out
