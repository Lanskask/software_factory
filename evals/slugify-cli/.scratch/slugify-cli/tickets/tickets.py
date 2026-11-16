#!/usr/bin/env python3
"""A set of local tickets as files: init from a spec, status, show, tick, mark. State lives in `<dir>/NN-slug.md`.

`init --spec spec.json` writes one file per ticket (numbered in the order of the spec, blockers first), a copy of
this script and a `Makefile` (`make status`, `make tickets`, `make show NUM=02`) next to them. A spec is a JSON list:

  [{"slug": "parser", "title": "Parse the input", "build": "what works end to end when this is done",
    "blocked_by": [],                         # slugs or numbers of EARLIER tickets
    "tasks": [{"text": "Write the parser", "how": ["file or command", "reference"]}, "a task with no how-steps"],
    "acceptance": ["what proves it"]}, ...]

A ticket is: What to build, Blocked by (number and title), Status, `## Tasks` (checkboxes, each with how-steps),
`## Acceptance`, and after the `-----------` line the brief written by `mark NN done`.
`status` prints every ticket's state and whether it is READY (todo, all blockers done); `status --tasks` also lists
each checkbox. `tick NN TEXT` ticks the one open task of NN whose text contains TEXT. `mark NN
<todo|in_progress|done>` changes the **Status:** line and refuses `done`/`in_progress` while a blocker is not done, and
`done` while a task is `[ ]` (`--tick-all` ticks them after you have checked each). `done` needs `--brief TEXT` (at
most 8 lines of 120 columns: what was produced, commit, numbers from runs). `show NN` prints the ticket and the briefs
of its blockers; `mark NN in_progress` prints the same briefs. Exit code 0 on success, 1 on failure.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

STATES = ("todo", "in_progress", "done")
OPEN_TASK = re.compile(r"^- \[ \] (.*)$", re.M)
BRIEF_RULE = "-----------"
BRIEF_LINE = re.compile(rf"^{BRIEF_RULE}$", re.M)
BRIEF_MAX_LINES = 8
BRIEF_MAX_WIDTH = 120
MAKEFILE = """\
# Written by `tickets.py init`. Run: make status | make tickets | make show NUM=02
TICKETS := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
TOOL    := python3 -I $(TICKETS)/tickets.py --dir $(TICKETS)

.PHONY: status tickets show

status:   ## one line per ticket: state, READY when unblocked
\t@$(TOOL) status

tickets:  ## every ticket with its tasks: [x] done, [ ] open
\t@$(TOOL) status --tasks

show:     ## one ticket and the briefs of its blockers: make show NUM=02
\t@$(TOOL) show $(NUM)
"""


@dataclass(frozen=True)
class Task:
    text: str
    how: tuple[str, ...] = ()


@dataclass(frozen=True)
class Ticket:
    num: str
    slug: str
    title: str
    build: str
    blocked_by: tuple[str, ...]  # numbers
    tasks: tuple[Task, ...]
    acceptance: tuple[str, ...]


def parse_spec(raw: object) -> list[Ticket]:
    """Validate a spec and number it; blockers must name earlier tickets (by slug or number)."""
    if not isinstance(raw, list) or not raw:
        raise ValueError("spec must be a non-empty JSON list of tickets")
    out: list[Ticket] = []
    by_slug: dict[str, str] = {}
    for i, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise ValueError(f"ticket {i}: not an object")
        for key in ("slug", "title", "build"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f"ticket {i}: missing {key}")
        num = f"{i:02d}"
        slug = str(item["slug"])
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug) or slug in by_slug:
            raise ValueError(f"ticket {num}: slug {slug!r} must be unique lowercase letters, digits and dashes")
        blockers: list[str] = []
        for b in item.get("blocked_by", []):
            ref = by_slug.get(str(b), str(b))
            if not re.fullmatch(r"\d{2}", ref) or int(ref) >= i:
                raise ValueError(f"ticket {num}: blocked_by {b!r} is not an earlier ticket (list blockers first)")
            blockers.append(ref)
        tasks: list[Task] = []
        for t in item.get("tasks", []):
            if isinstance(t, str):
                tasks.append(Task(t))
            elif isinstance(t, dict) and isinstance(t.get("text"), str):
                tasks.append(Task(t["text"], tuple(str(h) for h in t.get("how", []))))
            else:
                raise ValueError(f"ticket {num}: a task is a string or {{text, how}}")
        if not item.get("acceptance"):
            raise ValueError(f"ticket {num}: acceptance criteria are required")
        by_slug[slug] = num
        out.append(
            Ticket(
                num,
                slug,
                str(item["title"]),
                str(item["build"]),
                tuple(dict.fromkeys(blockers)),
                tuple(tasks),
                tuple(str(a) for a in item["acceptance"]),
            )
        )
    return out


def render(t: Ticket, titles: dict[str, str]) -> str:
    blocked = ", ".join(f"{b} {titles[b]}" for b in t.blocked_by) or "None (can start immediately)"

    def how(h: str) -> str:
        return textwrap.fill(h, 120, initial_indent="  - ", subsequent_indent="    ", break_long_words=False)

    tasks = "\n".join(f"- [ ] {k.text}" + "".join(f"\n{how(h)}" for h in k.how) for k in t.tasks)
    checks = "\n".join(f"- [ ] {a}" for a in t.acceptance)
    build = textwrap.fill(f"**What to build:** {t.build}", 120, break_long_words=False)
    parts = [f"# {t.num}: {t.title}\n\n{build}\n\n**Blocked by:** {blocked}\n\n**Status:** todo\n"]
    if tasks:
        parts.append(f"## Tasks\n\n{tasks}\n")
    parts.append(f"## Acceptance\n\n{checks}\n")
    return "\n".join(parts)


def read_state(path: Path) -> str:
    m = re.search(r"^\*\*Status:\*\* (\w+)", path.read_text(), re.M)
    if not m or m.group(1) not in STATES:
        raise ValueError(f"{path.name}: no valid **Status:** line")
    return m.group(1)


def blockers(path: Path) -> list[str]:
    m = re.search(r"^\*\*Blocked by:\*\* (.*)$", path.read_text(), re.M)
    if not m:
        return []
    return [n.group(1) for item in m.group(1).split(",") if (n := re.match(r"\s*(\d{2})\b", item))]


def split_brief(text: str) -> tuple[str, str | None]:
    m = BRIEF_LINE.search(text)
    if not m:
        return text, None
    return text[: m.start()], text[m.end() :].strip() or None


def format_brief(raw: str) -> str:
    lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]
    if not lines:
        raise ValueError("--brief is empty: say what was produced, the commit and the numbers (max 8 short lines)")
    bullets = [ln if ln.startswith("- ") else f"- {ln}" for ln in lines]
    if len(bullets) > BRIEF_MAX_LINES or any(len(b) > BRIEF_MAX_WIDTH for b in bullets):
        raise ValueError(f"--brief is too long: at most {BRIEF_MAX_LINES} lines of {BRIEF_MAX_WIDTH} columns")
    return "## Done\n\n" + "\n".join(bullets)


def title_and_tasks(path: Path) -> tuple[str, list[str]]:
    text = split_brief(path.read_text())[0]
    m = re.search(r"^# \d{2}: (.*)$", text, re.M)
    tasks = [f"  - [{c.lower()}] {t}" for c, t in re.findall(r"^- \[([ xX])\] (.*)$", text, re.M)]
    return (m.group(1) if m else path.stem[3:]), tasks


def print_blocker_briefs(tickets: dict[str, Path], num: str) -> None:
    for b in blockers(tickets[num]):
        if b not in tickets:
            continue
        _, brief = split_brief(tickets[b].read_text())
        body = brief.removeprefix("## Done").strip() if brief else "(no brief yet)"
        print(f"== brief of {b} {title_and_tasks(tickets[b])[0]}\n{body}")


def load(d: Path) -> dict[str, Path]:
    files = sorted(d.glob("[0-9][0-9]-*.md"))
    if not files:
        raise ValueError(f"no tickets in {d} (run: tickets.py --dir {d} init --spec spec.json)")
    return {f.name[:2]: f for f in files}


def cmd_init(d: Path, spec_path: Path, force: bool) -> int:
    tickets = parse_spec(json.loads(spec_path.read_text()))
    if d.exists() and any(d.glob("[0-9][0-9]-*.md")) and not force:
        print(f"tickets: {d} already has tickets (use --force to overwrite)", file=sys.stderr)
        return 1
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("[0-9][0-9]-*.md"):
        old.unlink()
    titles = {t.num: t.title for t in tickets}
    for t in tickets:
        (d / f"{t.num}-{t.slug}.md").write_text(render(t, titles))
    shutil.copyfile(Path(__file__).resolve(), d / "tickets.py")
    (d / "Makefile").write_text(MAKEFILE)
    print(f"tickets: wrote {len(tickets)} tickets, tickets.py and Makefile to {d}", file=sys.stderr)
    return 0


def cmd_status(d: Path, with_tasks: bool) -> int:
    tickets = load(d)
    state = {n: read_state(p) for n, p in tickets.items()}
    for n, p in tickets.items():
        ready = state[n] == "todo" and all(state.get(b) == "done" for b in blockers(p))
        if with_tasks:
            title, tasks = title_and_tasks(p)
            print(f"Ticket_{n} {state[n]}{' READY' if ready else ''} {title}")
            print("\n".join(tasks))
        else:
            print(f"{n}\t{state[n]}\t{'READY' if ready else ''}\t{p.stem[3:]}")
    print(f"tickets: {sum(s == 'done' for s in state.values())}/{len(state)} done", file=sys.stderr)
    return 0


def cmd_show(d: Path, num: str) -> int:
    tickets = load(d)
    if num not in tickets:
        raise ValueError(f"no ticket {num}")
    print(tickets[num].read_text().rstrip())
    print_blocker_briefs(tickets, num)
    return 0


def cmd_tick(d: Path, num: str, text: str) -> int:
    tickets = load(d)
    if num not in tickets:
        raise ValueError(f"no ticket {num}")
    body = tickets[num].read_text()
    hits = [t for t in OPEN_TASK.findall(split_brief(body)[0]) if text.lower() in t.lower()]
    if len(hits) != 1:
        raise ValueError(
            f"ticket {num}: {len(hits)} open tasks match {text!r} (need exactly 1); open: "
            f"{OPEN_TASK.findall(body) or 'none'}"
        )
    tickets[num].write_text(body.replace(f"- [ ] {hits[0]}", f"- [x] {hits[0]}", 1))
    print(f"tickets: {num} ticked: {hits[0]}", file=sys.stderr)
    return 0


def cmd_mark(d: Path, num: str, new: str, tick_all: bool, brief: str | None) -> int:
    tickets = load(d)
    if num not in tickets:
        raise ValueError(f"no ticket {num}")
    path = tickets[num]
    text = path.read_text()
    formatted = ""
    if new == "done":
        open_tasks = OPEN_TASK.findall(split_brief(text)[0])
        if open_tasks and not tick_all:
            raise ValueError(
                f"ticket {num} has {len(open_tasks)} open task(s); tick each with `tick` once it holds "
                f"(a skipped one: edit it to `- [x] <task> (skipped: <reason>)`), or pass --tick-all after "
                "checking them:\n  " + "\n  ".join(open_tasks)
            )
        if brief is None:
            raise ValueError(
                f"ticket {num}: `done` needs --brief TEXT (what was produced, commit, numbers; max 8 lines)"
            )
        formatted = format_brief(brief)
    if new != "todo":
        open_blockers = [b for b in blockers(path) if b in tickets and read_state(tickets[b]) != "done"]
        if open_blockers:
            raise ValueError(f"ticket {num} is blocked by {', '.join(open_blockers)}")
    if new == "done":
        body = split_brief(text)[0]
        if tick_all:
            body = re.sub(r"^- \[ \] ", "- [x] ", body, flags=re.M)
        text = f"{body.rstrip()}\n\n{BRIEF_RULE}\n{formatted}\n"
    path.write_text(re.sub(r"^(\*\*Status:\*\* )\w+", rf"\g<1>{new}", text, count=1, flags=re.M))
    print(f"tickets: {num} -> {new}", file=sys.stderr)
    if new == "in_progress":
        print_blocker_briefs(tickets, num)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", required=True, type=Path, help="ticket directory, e.g. .scratch/<feature>/tickets")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init", help="write the tickets of a JSON spec, tickets.py and a Makefile")
    i.add_argument("--spec", required=True, type=Path)
    i.add_argument("--force", action="store_true", help="replace existing tickets (their state and briefs are lost)")
    st = sub.add_parser("status")
    st.add_argument("--tasks", action="store_true", help="also list each ticket's checkbox tasks")
    sh = sub.add_parser("show", help="print ticket NN and the briefs of its blockers")
    sh.add_argument("num")
    t = sub.add_parser("tick", help="tick the one open task of ticket NN whose text contains TEXT")
    t.add_argument("num")
    t.add_argument("text")
    m = sub.add_parser("mark")
    m.add_argument("num")
    m.add_argument("state", choices=STATES)
    m.add_argument("--tick-all", action="store_true", help="with `done`: tick every open task (after checking)")
    m.add_argument("--brief", help="with `done`: what was produced, commit, numbers; max 8 lines of 120 columns")
    args = p.parse_args(argv)
    try:
        if args.cmd == "init":
            return cmd_init(args.dir, args.spec, args.force)
        if args.cmd == "status":
            return cmd_status(args.dir, args.tasks)
        if args.cmd == "show":
            return cmd_show(args.dir, args.num)
        if args.cmd == "tick":
            return cmd_tick(args.dir, args.num, args.text)
        return cmd_mark(args.dir, args.num, args.state, args.tick_all, args.brief)
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(f"tickets: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
