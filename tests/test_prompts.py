from __future__ import annotations

from pathlib import Path

from factory.config import Config
from factory.prompts import (
    blocked_reason,
    fix_goal,
    goal,
    has_high_loose_end,
    parse_verdict,
    review_prompt,
    session_rules,
)
from factory.tracker import Ticket

CFG = Config(tickets_dir="t", checks=("make test", "make lint"))
T = Ticket("10/13", "todo", True, "web-build")


def test_goal_is_a_slash_goal_with_the_done_condition() -> None:
    g = goal(T, "python3 -I t/tickets.py --dir t", Path("/p/.factory/handoffs/10-13.md"), None, CFG.checks)
    assert g.startswith("/goal ")
    assert "/p/.factory/handoffs/10-13.md" in g and "BLOCKED:" in g


def test_goal_names_the_exact_status_command_and_checks() -> None:
    # Live run 2026-10-30: the /goal judge ran the bare tickets command (an error) and counted the owner's global
    # rules (`uvx ty`) as "checks in your instructions", so a finished Ticket never met its goal.
    g = goal(T, "python3 -I t/tickets.py --dir t", Path("/h/now.md"), None, CFG.checks)
    assert "`python3 -I t/tickets.py --dir t status`" in g
    assert "`make test`, `make lint`" in g and "instructions" not in g


def test_goals_bound_the_turns() -> None:
    # code.claude.com/docs/en/goal: a turn clause in the condition is the only turn limit /goal has; the Session
    # budget and timeout alone let a looping Session burn all of them.
    g = goal(T, "tk", Path("/h/now.md"), None, CFG.checks)
    f = fix_goal(T, "tk", Path("/h/now.md"), "- finding", CFG.checks)
    assert "stop after 60 turns" in g and "stop after 60 turns" in f


def test_goal_points_at_the_previous_handoff_when_there_is_one() -> None:
    g = goal(T, "tk", Path("/h/now.md"), Path("/h/prev.md"), CFG.checks)
    assert "/h/prev.md" in g


def test_session_rules_forbid_push_and_list_checks_and_skills() -> None:
    r = session_rules(CFG, "tk")
    assert "make test" in r and "make lint" in r
    assert "factory:implement" in r
    assert "git push" in r and "in scope" in r.lower()
    assert "[high]" in r


def test_session_rules_make_the_checks_the_definition_of_done_and_a_denied_tool_no_blocker() -> None:
    # Live run 2026-10-30: a global rule asked for `uvx ty`, the allowlist refused it, and the Session gave up.
    r = session_rules(CFG, "tk")
    assert "definition of done" in r
    assert "refused" in r and "not a reason for BLOCKED" in r


def test_review_prompt_asks_for_a_verdict_against_the_base() -> None:
    p = review_prompt(T, "factory/10-12-x", "tk", Path("/h/now.md"), CFG)
    assert "factory/10-12-x" in p and "VERDICT: PASS" in p and "VERDICT: FAIL" in p
    assert "factory:code-review" in p


def test_parse_verdict() -> None:
    assert parse_verdict("lots of text\nVERDICT: PASS\n") == (True, "lots of text")
    ok, findings = parse_verdict("1. SQL injection in x.go\nVERDICT: FAIL")
    assert not ok and "SQL injection" in findings
    assert parse_verdict("no verdict at all")[0] is False


def test_blocked_reason() -> None:
    assert blocked_reason("work...\nBLOCKED: needs the owner's API key") == "needs the owner's API key"
    assert blocked_reason("all good") is None


def test_has_high_loose_end() -> None:
    assert has_high_loose_end("## Out of scope\n- [high] auth bypass in admin.go\n")
    assert not has_high_loose_end("## Out of scope\n- [low] typo in README\n")
