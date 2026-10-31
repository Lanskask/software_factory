"""What the Factory tells its Sessions, and how it reads their answers."""

from __future__ import annotations

import re
from pathlib import Path

from factory.config import Config
from factory.skills import local_name
from factory.tracker import Ticket

HANDOFF_FORMAT = """# Handoff <ticket number>

## Out of scope

- [high|low] <problem found outside this Ticket's scope, with file and line>

## Owner decisions

- [high|low] <assumption the Owner should confirm or revisit>

Write "None." under a heading that has nothing."""


def _skill_lines(cfg: Config) -> str:
    names = [local_name(s) for s in cfg.implement_skills]
    if not names:
        return "- Work test-first: a failing test, then the code that makes it pass."
    lines = [f"- Implement with the skill {names[0]}: invoke it with the Skill tool and follow it."]
    lines += [f"- Also available: {', '.join(names[1:])}. Use them where they fit." for _ in names[1:2]]
    return "\n".join(lines)


def session_rules(cfg: Config, tk: str) -> str:
    """The system prompt of an implementation or fix Session."""
    checks = "\n".join(f"  - `{c}`" for c in cfg.checks)
    return f"""You are one Session of the Software Factory: an unattended run. No human will answer questions. You work
on exactly one Ticket, on the branch that is already checked out. Follow this Project's CLAUDE.md where it does not
conflict with these rules.

How to work
- Read the Ticket with `{tk} show <number>`. It also prints the Briefs of the Tickets that blocked it.
{_skill_lines(cfg)}
- The checks. Each must exit 0, and you show its output. They are the definition of done; other checks that your
  instructions or rules mention are optional extras:
{checks}
- Commit in small commits with descriptive messages as you go (`git add`, `git commit`). End with a clean
  `git status`. No AI attribution lines in commit messages.
- Tick each task with `{tk} tick <number> "<task text>"`. When the Ticket is done, run
  `{tk} mark <number> done --brief "<what was produced, the commits, the numbers>"` (at most 8 short lines).
- Write the Handoff file named in your goal, in this format:

{HANDOFF_FORMAT}

Scope
- Finish everything in scope of this Ticket: its tasks, its acceptance criteria, and anything you broke or left half
  done. Nothing in scope may be left for a later Session.
- The Handoff may only hold problems outside this Ticket's scope and decisions the Owner should revisit. Tag an item
  [high] if it could later cause data loss, a security hole, wrong results or a broken build; otherwise [low].
- If the Ticket cannot be done correctly without a decision from the Owner, do not guess. Stop and end your last
  message with a line `BLOCKED: <reason>`. A decision means what to build or a missing credential. A tool or command
  the permissions refused is not a reason for BLOCKED: do without it and list it in the Handoff as [low].

Never
- `git push`, `git merge`, `git rebase`, `git switch`, `git checkout`, `git reset`, `gh`: the Factory pushes and opens
  the pull request after its own checks.
- Change the state of any other Ticket.
- Cloud or paid tooling (terraform, gcloud, fly, modal, deploy targets).
"""


def _checks(checks: tuple[str, ...]) -> str:
    return ", ".join(f"`{c}`" for c in checks)


# /goal has no turn limit of its own; a clause in the condition is the documented way to bound it.
_TURN_BOUND = "Or stop after 60 turns."


# The /goal judge reads the condition literally: name exact commands, never "the checks in your instructions".
def goal(
    ticket: Ticket,
    tk: str,
    handoff: Path,
    previous: Path | None,
    checks: tuple[str, ...],
    resolution: Path | None = None,
    lessons: Path | None = None,
) -> str:
    before = f" Read {previous} first: the previous Ticket's Handoff, for context only." if previous else ""
    if lessons:
        before += f" Read {lessons} first: what went wrong in earlier Tickets of this Project. Do not repeat it."
    if resolution:
        before += (
            f" Then read {resolution}: the decision on that Handoff's [high] loose ends. Do the steps it marks NOW"
            f" first, each in its own commit with a test; they are in scope of this Ticket."
        )
    return (
        f"/goal Ticket {ticket.num} ({ticket.slug}) is done: `{tk} status` shows it done, {_checks(checks)} each "
        f"exit 0 with output shown, `git status` is clean, and you wrote the Handoff to {handoff} . Or your last "
        f"message ends with a line BLOCKED: <reason>, because it needs the Owner. {_TURN_BOUND}{before}"
    )


def fix_goal(ticket: Ticket, tk: str, handoff: Path, findings: str, checks: tuple[str, ...]) -> str:
    return (
        f"/goal Ticket {ticket.num} ({ticket.slug}): every review finding below is fixed, with a test where one "
        f"applies; {_checks(checks)} each exit 0 with output shown; `git status` is clean; the Handoff {handoff} is "
        f"up to date (Tickets: `{tk} status`). Or your last message ends with a line BLOCKED: <reason>. "
        f"{_TURN_BOUND}\n\n"
        f"Review findings:\n{findings}"
    )


def resolve_prompt(ticket: Ticket, tk: str, handoff: Path) -> str:
    return f"""RESOLVE. Ticket {ticket.num} ({ticket.slug}) is done and its pull request is open, but its
Handoff {handoff} holds [high] loose ends. The unattended Run does not stop for them: you decide, and the next
Ticket's Session acts on your answer. You cannot edit files.

Read the Handoff and the Ticket (`{tk} show {ticket.num}`), then the code each [high] item names. Check facts in the
code and, where a library or service decides it, in its official documentation (WebSearch, WebFetch) before you decide.

For each [high] item answer in this form:
- Item: <the item, one line>
- Decision: <valid or not, and what to do, one line>
- Steps: <the smallest correct change: files, what changes, the test that proves it>
- When: NOW if the next Ticket's Session must do it first (data loss, security, wrong results, broken build);
  LATER if it can wait; OWNER if only a human can do it (credentials, money, a product choice).
Mark each NOW step with a line starting `NOW:`. End with what you did not verify."""


def review_prompt(ticket: Ticket, base: str, tk: str, handoff: Path, cfg: Config) -> str:
    names = [local_name(s) for s in cfg.review_skills]
    how = f"Use the skill {names[0]} with the fixed point `{base}`" if names else "Review it yourself"
    extra = (
        f" If the diff touches authentication, input handling, secrets or crypto, also apply {', '.join(names[1:])}."
        if len(names) > 1
        else ""
    )
    return f"""Ticket {ticket.num} ({ticket.slug}): review the commits on this branch since `{base}`
(`git diff {base}...HEAD`). You are an independent reviewer with a fresh context and you cannot edit files.

Read the Ticket with `{tk} show {ticket.num}`. {how}: Standards are this repo's documented standards, the Spec is the
Ticket.{extra} Read the Handoff {handoff}: an item there that is actually inside this Ticket's scope is a finding.

Report only must-fix findings: bugs, acceptance criteria without a test, security holes, mismatches with the Ticket.
Not style. Number them, each with file and line. Your last line is exactly `VERDICT: PASS` or `VERDICT: FAIL`."""


_VERDICT = re.compile(r"^\W*VERDICT:\s*(PASS|FAIL)\W*$", re.M)
_BLOCKED = re.compile(r"^\W*BLOCKED:\s*(.+)$", re.M)


def parse_verdict(text: str) -> tuple[bool, str]:
    """(passed, findings). A review without a verdict line counts as FAIL."""
    matches = list(_VERDICT.finditer(text))
    if not matches:
        return False, text.strip() or "the reviewer gave no verdict"
    last = matches[-1]
    return last.group(1) == "PASS", text[: last.start()].strip()


def blocked_reason(text: str) -> str | None:
    matches = _BLOCKED.findall(text)
    return matches[-1].strip() if matches else None


def has_high_loose_end(handoff: str) -> bool:
    return "[high]" in handoff
