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
from factory.tracker import Ticket

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
if "RESOLVE" in prompt:
    if os.environ.get("FAKE_RESOLVE_FAIL"):
        result("", subtype="error_max_turns")
    result("Decision: drop the auth bypass.\nNOW: delete the bypass branch, with a test.")
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
    tk = re.search(r"`(\S+ -I \S+ --dir \S+) status`", prompt).group(1).split()
    subprocess.run([*tk, "mark", num, "done", "--brief", "did it"], check=True)
subprocess.run(["git", "add", "-A"], check=True)
if num in os.environ.get("FAKE_BLOCKED_DONE", "").split(","):
    subprocess.run(["git", "commit", "-qm", f"ticket {num}"], check=True)
    result("all done, but\nBLOCKED: wants the owner to allow uvx ty")
subprocess.run(["git", "commit", "-qm", f"ticket {num}"], check=True)
result("DONE")
"""

FAKE_GH = r"""
import json, os, sys
with open(os.environ["FAKE_GH_LOG"], "a") as f: f.write(json.dumps(sys.argv[1:]) + "\n")
if os.environ.get("FAKE_GH_FAIL"):
    print("GraphQL: Base ref must be a branch", file=sys.stderr)
    sys.exit(1)
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
    names = [c[c.index("--name") + 1] for c in sessions]
    assert names == [
        "factory proj 01 implement 1",
        "factory proj 01 review 1",
        "factory proj 02 implement 1",
        "factory proj 02 review 1",
    ]


def test_failed_publish_is_retried_by_the_next_run_before_new_tickets(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with_tickets(project, {"01": {"slug": "a"}, "02": {"slug": "b", "blocked_by": ["01"]}})
    monkeypatch.setenv("FAKE_GH_FAIL", "1")
    assert factory(project).run() == 1
    git(project, "push", "-q", "origin", "--delete", "factory/01-a")  # the remote lost it, as in a fresh remote
    monkeypatch.delenv("FAKE_GH_FAIL")
    assert factory(project).run() == 0
    assert git(project, "ls-remote", "--heads", "origin").count("refs/heads/factory/") == 2
    created = [c for c in gh_calls(project) if c[1] == "create"][1:]  # the first call is the failed attempt
    assert [c[c.index("--head") + 1] for c in created] == ["factory/01-a", "factory/02-b"]
    assert [c[c.index("--base") + 1] for c in created] == ["main", "factory/01-a"]


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


def test_review_fail_is_a_lesson_the_next_ticket_is_told_to_read(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_REVIEW_FAIL", "01")
    with_tickets(project, {"01": {"slug": "a"}, "02": {"slug": "b"}})
    assert factory(project).run() == 0
    lessons = project / ".factory" / "LESSONS.md"
    assert "01 a: review FAIL" in lessons.read_text() and "empty case" in lessons.read_text()
    prompts = [c[c.index("-p") + 1] for c in claude_calls(project)]
    implement_01 = next(p for p in prompts if "Ticket 01" in p and "VERDICT" not in p)
    implement_02 = next(p for p in prompts if "Ticket 02" in p and "VERDICT" not in p)
    assert str(lessons) not in implement_01 and str(lessons) in implement_02


def test_lesson_keeps_the_whole_reason_on_one_line_cut_at_300_characters(project: Path) -> None:
    f = factory(project)
    f.state.mkdir(parents=True, exist_ok=True)
    f.lesson(Ticket("01", "todo", True, "a"), "check `make test` failed (exit 1):\nE assert 1 == 2\n\n" + "x" * 400)
    (line,) = (project / ".factory" / "LESSONS.md").read_text().splitlines()
    assert line.startswith("- 01 a: check `make test` failed (exit 1): E assert 1 == 2 x") and len(line) < 320


def test_lessons_start_empty_each_run_and_a_final_review_fail_is_one_lesson(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lessons = project / ".factory" / "LESSONS.md"
    lessons.parent.mkdir(parents=True, exist_ok=True)
    lessons.write_text("- 99 old: from an earlier Run\n")
    monkeypatch.setenv("FAKE_REVIEW_FAIL", "01")
    with_tickets(project, {"01": {"slug": "a"}})
    assert factory(project, review_rounds=1).run() == 1
    assert [line.split(": ")[1] for line in lessons.read_text().splitlines()] == ["Blocked"]


def test_blocked_ticket_is_a_lesson(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_FAIL", "01")
    with_tickets(project, {"01": {"slug": "a"}, "02": {"slug": "b"}})
    assert factory(project).run() == 1
    assert "01 a: Blocked: " in (project / ".factory" / "LESSONS.md").read_text()


def test_high_loose_end_is_resolved_by_opus_and_the_run_continues(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_HIGH", "01")
    with_tickets(project, {"01": {"slug": "a"}, "02": {"slug": "b"}})
    assert factory(project).run() == 0
    assert len(gh_calls(project)) == 2  # ticket 02 ran after the [high] item of 01
    calls = claude_calls(project)
    (resolve,) = [c for c in calls if "RESOLVE" in c[c.index("-p") + 1]]
    assert resolve[resolve.index("--model") + 1] == "opus"
    assert resolve[resolve.index("--name") + 1] == "factory proj 01 resolve 1"
    allowed = resolve[resolve.index("--allowedTools") + 1 : resolve.index("--disallowedTools")]
    assert "WebSearch" in allowed and "Edit" not in allowed and "Write" not in allowed
    resolution = project / ".factory" / "resolutions" / "01.md"
    assert "delete the bypass branch" in resolution.read_text()
    implement_02 = next(c[c.index("-p") + 1] for c in calls if "Ticket 02" in c[c.index("-p") + 1])
    assert str(resolution) in implement_02
    loose = (project / ".factory" / "LOOSE-ENDS.md").read_text()
    assert "auth bypass" in loose and "delete the bypass branch" in loose


def test_run_stops_when_the_resolver_fails(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_HIGH", "01")
    monkeypatch.setenv("FAKE_RESOLVE_FAIL", "1")
    with_tickets(project, {"01": {"slug": "a"}, "02": {"slug": "b"}})
    assert factory(project).run() == 1
    assert len(gh_calls(project)) == 1
    assert "auth bypass" in (project / ".factory" / "LOOSE-ENDS.md").read_text()


def test_loose_ends_of_a_blocked_ticket_are_logged(project: Path) -> None:
    with_tickets(project, {"01": {"slug": "a"}})
    cfg = Config(tickets_dir="t", checks=("false",), implement_skills=(), review_skills=())
    assert Factory(project, cfg, python=sys.executable).run() == 1
    assert "[low] typo" in (project / ".factory" / "LOOSE-ENDS.md").read_text()


def test_blocked_claim_on_a_verified_ticket_becomes_a_high_loose_end(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_BLOCKED_DONE", "01")
    with_tickets(project, {"01": {"slug": "a"}, "02": {"slug": "b"}})
    assert factory(project).run() == 0  # the resolver decides, the Run goes on
    assert len(gh_calls(project)) == 2
    assert "[high]" in (project / ".factory" / "LOOSE-ENDS.md").read_text()
    assert "uvx ty" in (project / ".factory" / "LOOSE-ENDS.md").read_text()
    assert not (project / ".factory" / "blocked").exists()


def test_ticket_mentioning_cloud_tools_is_skipped(project: Path) -> None:
    with_tickets(project, {"01": {"slug": "infra", "text": "run terraform apply"}, "02": {"slug": "b"}})
    assert factory(project).run() == 0
    assert "factory/01-infra" not in git(project, "branch")
    assert len(gh_calls(project)) == 1


def test_dirty_tree_refuses_to_start_and_names_the_files(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with_tickets(project, {"01": {"slug": "a"}})
    (project / "stray.txt").write_text("x")
    assert factory(project).run() == 1
    assert claude_calls(project) == []
    assert "?? stray.txt" in capsys.readouterr().out


def test_dry_run_spends_nothing(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with_tickets(project, {"01": {"slug": "a"}})
    assert factory(project).run(dry_run=True) == 0
    assert claude_calls(project) == [] and "/goal" in capsys.readouterr().out


def test_real_run_prints_the_dry_run_preview_before_the_first_session(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with_tickets(project, {"01": {"slug": "a"}})
    assert factory(project).run() == 0
    out = capsys.readouterr().out
    assert out.index("next: 01 on factory/01-a from main") < out.index("01: implement session 1")


def test_review_session_may_run_the_configured_checks(project: Path) -> None:
    f = factory(project)
    assert "Bash(test -f t/tickets.json*)" in f.review_tools()
