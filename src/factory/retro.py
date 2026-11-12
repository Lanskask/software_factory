"""`factory retro PROJECT`: count the Owner's typed interventions in the Project's Claude Code transcripts and
append a dated table to `.factory/LESSONS.md`.

A "message" is a top-level user turn that is typed text: no tool results, no meta, no slash-command echoes, no `!`
shell echoes. One message may carry several labels. Labels are regex heuristics: counts are approximate (about
+/-10 % per bucket). See docs/factory-analysis.md section 3, P10.
"""

from __future__ import annotations

import collections
import json
import re
from collections.abc import Iterator
from datetime import date
from pathlib import Path

ECHO = re.compile(
    r"^(<task-notification|<local-command|<command-name>|<command-message>|Caveat:|\[Request interrupted"
    r"|<system-reminder|This session is being continued|<bash-input>|<bash-stdout>|/compact)"
)

PATTERNS = {
    # session plumbing: the owner carries state between sessions by hand
    "handoff_relay": r"handoff (doc|is|document)|handoff-[\w-]+\.md|scratchpad/handoff",
    # owner pastes the agent's own skipped/not-done/unchecked list back and says "do it"
    "echo_skipped": r"(I (haven't|have not|did not|didn't)|Not done|Skipped|not checked|still unfixed|is not pushed"
    r"|Nothing pushed|Left alone)",
    # git / PR / CI choreography
    "git_pr": r"\b(push|PRs?\b|pull request|merge|stacked|branch|worktree|gh pr)",
    # external tracker mirroring (Linear, GitHub issues/projects)
    "tracker_sync": r"(linear|JOH-\d+|issues in GH|GH issues|github issues|Update Issues|tickets_to_issues"
    r"|Move new tickets to GH|Sync local closed tickets)",
    # owner pastes an error or failing output for the agent to solve
    "pasted_error": r"(error:|Error:|ERROR|--- FAIL|failed with|fatal:|HTTPError|Error \d)",
    # owner asks where we are / what is next / is it done
    "what_next": r"(what (to do|is|are) (next|left)|What is next|what next|What to do next|Next ticket|is .* finished"
    r"|Can we move to the next|what is left|what should be done)",
    # visual review against screenshots / Penpot boards
    "visual_review": r"\[Image #\d+\]|penpot|\bboards?\b",
    # owner answers a grill / option question or approves a proposal
    "decision": r"(\bq\d+\b|❓|I (agree|aggree|choose|prefer|approve)|option \(?[a-e]\)?|Agree with"
    r"|I like (the|this|variant)|looks good|Ok, np|yes,? (do|skip)|Consider .* approved)",
    # owner repeats a standing rule ("don't forget", "always", "remember")
    "repeat_rule": r"(don'?t forget|Remember that|Always |Don't be blind|You can run all commands|create a new branch"
    r"|Each ticket should have)",
    # owner widens scope mid-session (new epic/ticket/feature)
    "scope_add": r"(create (a new |an )?(epic|ticket)|Add (epic|a ticket)|create tickets|new epic|Create a ticket)",
    # owner unblocks autonomy ("do it yourself", "continue until the end", "fix all")
    "autonomy_grant": r"(do (all )?(changes|it|that) (youself|yourself)|make all changes yourself|continue all|Fix all!"
    r"|Do all designes|You can work on several|you can do anything|forget this limit)",
    # tool / plugin / harness setup (MCP, plugins, hooks, context size)
    "tooling_meta": r"\b(plugins?|MCP|hooks?|context window|ctx|tokens|reload-skills)\b",
}
LABELS = {k: re.compile(v, re.I) for k, v in PATTERNS.items()}


def transcript_dir(project: Path) -> Path:
    """Claude Code keeps a Project's transcripts in ~/.claude/projects/<absolute path, non-alphanumerics as `-`>."""
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(project.resolve()))


def messages(directory: Path) -> Iterator[str]:
    for f in sorted(directory.glob("*.jsonl"), key=lambda p: p.stat().st_mtime):
        for line in f.read_text().splitlines():
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("type") != "user" or d.get("isMeta") or d.get("isSidechain"):
                continue
            c = d.get("message", {}).get("content")
            parts = (
                [c]
                if isinstance(c, str)
                else [x.get("text", "") for x in c or [] if isinstance(x, dict) and x.get("type") == "text"]
            )
            for t in parts:
                t = t.strip()
                if t and not ECHO.match(t):
                    yield t


def count(directory: Path) -> tuple[int, collections.Counter[str]]:
    counts: collections.Counter[str] = collections.Counter()
    total = 0
    for t in messages(directory):
        total += 1
        counts.update(k for k, rx in LABELS.items() if rx.search(t))
    return total, counts


ROW = re.compile(r"^- retro (\w+) \[open\] (\d+) of ")


def retro(project: Path, directory: Path | None = None, today: date | None = None) -> Path:
    """Append one `- retro BUCKET [open] ...` line per bucket to LESSONS.md (a Run keeps these lines).

    An older [open] line of a bucket becomes [resolved] when the new count is lower: the bucket shrank.
    """
    total, counts = count(directory or transcript_dir(project))
    path = project / ".factory" / "LESSONS.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    kept = []
    for ln in path.read_text().splitlines(keepends=True) if path.exists() else []:
        m = ROW.match(ln)
        kept.append(ln.replace("[open]", "[resolved]", 1) if m and counts.get(m[1], 0) < int(m[2]) else ln)
    when = today or date.today()
    new = [f"- retro {k} [open] {n} of {total} typed messages on {when}\n" for k, n in counts.most_common()]
    path.write_text("".join(kept + new))
    return path
