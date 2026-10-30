"""`factory init|plan|run|status PROJECT`."""

from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

from factory.config import ConfigError, config_path, load_config, template
from factory.plan import Planner
from factory.run import Factory
from factory.tracker import Tracker

IGNORE = (".factory/*", "!.factory/config.toml")


def cmd_init(project: Path) -> int:
    path = config_path(project)
    if path.exists():
        print(f"factory: {path} already exists")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template(project))
        print(f"factory: wrote {path}; check `checks` and `tickets_dir`, then commit it")
    gitignore = project / ".gitignore"
    lines = gitignore.read_text().splitlines() if gitignore.exists() else []
    missing = [line for line in IGNORE if line not in lines]
    if missing:
        with gitignore.open("a") as f:
            f.write(("\n" if lines and lines[-1] else "") + "\n".join(missing) + "\n")
        print(f"factory: added {', '.join(missing)} to {gitignore}")
    return 0


def cmd_status(project: Path) -> int:
    cfg = load_config(project)
    tracker = Tracker(project, cfg.tickets_dir)
    tickets = tracker.status() if tracker.exists() else []
    done = sum(t.state == "done" for t in tickets)
    print(f"Tickets: {done}/{len(tickets)} done")
    for t in tickets:
        print(f"  {t.num}\t{t.state}\t{'READY' if t.ready else ''}\t{t.slug}")
    blocked = sorted((project / ".factory" / "blocked").glob("*.md"))
    print(f"Blocked: {len(blocked)}")
    for b in blocked:
        print(f"  {b}")
    loose = project / ".factory" / "LOOSE-ENDS.md"
    if loose.exists():
        text = loose.read_text()
        print(f"Loose ends: {text.count('- [high]')} high, {text.count('- [low]')} low, in {loose}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="factory", description="Plan a Project, then implement its Tickets unattended.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="write .factory/config.toml and the .gitignore lines").add_argument(
        "project", type=Path
    )
    pl = sub.add_parser("plan", help="interactive Planning: Spec and Tickets")
    pl.add_argument("project", type=Path)
    pl.add_argument("--spec", type=Path, help="an existing Spec: skip the interview and the /to-spec step")
    pl.add_argument("--no-bootstrap", action="store_true", help="do not run /egm:egm-bootstrap unattended first")
    r = sub.add_parser("run", help="implement the Ready Tickets unattended, one draft PR each")
    r.add_argument("project", type=Path)
    r.add_argument("--dry-run", action="store_true", help="print the next Ticket and its claude command, spend nothing")
    r.add_argument("--max-tickets", type=int)
    r.add_argument("--max-blocked", type=int)
    r.add_argument("--budget-usd", type=float, help="per implementation Session")
    r.add_argument("--timeout-minutes", type=int, help="per Session")
    sub.add_parser("status", help="Tickets, Blocked Tickets and loose ends").add_argument("project", type=Path)
    args = p.parse_args(argv)
    project: Path = args.project.resolve()
    try:
        if args.cmd == "init":
            return cmd_init(project)
        if args.cmd == "status":
            return cmd_status(project)
        if args.cmd == "plan" and not config_path(project).exists():
            cmd_init(project)
        cfg = load_config(project)
        if args.cmd == "plan":
            return Planner(project, cfg).plan(args.spec, bootstrap=not args.no_bootstrap)
        overrides = {
            k: v
            for k in ("max_tickets", "max_blocked", "budget_usd", "timeout_minutes")
            if (v := getattr(args, k)) is not None
        }
        return Factory(project, dataclasses.replace(cfg, **overrides)).run(dry_run=args.dry_run)
    except ConfigError as e:
        print(f"factory: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
