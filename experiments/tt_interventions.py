"""Count owner interventions in the terminal-task-tracker Claude Code transcripts.

Question: where did the owner have to step in while building terminal-task-tracker, and how often, so the
Factory knows what to automate? Input: every `*.jsonl` in the project's transcript folder (61 files, 2026-10-14 to
2026-11-12). A "message" is a top-level user turn that is typed text: no tool results, no meta, no slash-command
echoes, no `!` shell echoes. One message may carry several labels (owners send numbered lists).

Answer (run 2026-11-12, see docs/factory-analysis.md): 311 typed messages. Biggest buckets: git/PR plumbing (91),
decisions (72), visual review (65), echoing the agent's own "skipped / not done" list back as an order (48), pasted
errors (43), relaying handoff docs (41).

Labels are regex heuristics, so counts are approximate (about +/-10 % per bucket); read the examples it prints.

Usage: python3 -I experiments/tt_interventions.py [TRANSCRIPT_DIR]
"""

import collections
import glob
import json
import os
import re
import sys

DIR = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.path.expanduser("~/.claude/projects/-Users-a1-Programming-My-Projects-terminal-task-tracker/")
)

ECHO = re.compile(
    r"^(<task-notification|<local-command|<command-name>|<command-message>|Caveat:|\[Request interrupted"
    r"|<system-reminder|This session is being continued|<bash-input>|<bash-stdout>|/compact)"
)

LABELS = {
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
LABELS = {k: re.compile(v, re.I) for k, v in LABELS.items()}


def messages():
    for f in sorted(glob.glob(os.path.join(DIR, "*.jsonl")), key=os.path.getmtime):
        sid = os.path.basename(f)[:8]
        with open(f) as fh:
            lines = fh.readlines()
        for line in lines:
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
                    yield sid, d["timestamp"], t


def main():
    counts, examples, total = collections.Counter(), collections.defaultdict(list), 0
    for sid, ts, t in messages():
        total += 1
        for k, rx in LABELS.items():
            m = rx.search(t)
            if m:
                counts[k] += 1
                if len(examples[k]) < 3:
                    i = max(0, m.start() - 40)
                    examples[k].append(f"{sid} {ts[:10]}: …{t[i : i + 140]!r}")
    print(f"typed messages: {total}")
    for k, n in counts.most_common():
        print(f"{n:4d}  {k}")
        for e in examples[k]:
            print("        ", e)


if __name__ == "__main__":
    main()
