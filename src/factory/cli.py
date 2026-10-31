"""`factory init|plan|run|status PROJECT`."""

from __future__ import annotations

import argparse
import dataclasses
import shutil
import subprocess
import sys
from pathlib import Path

from factory.bootstrap import branch_warning, next_step
from factory.config import ConfigError, config_path, load_config, template
from factory.plan import Planner
from factory.run import Factory
from factory.tracker import Tracker

IGNORE = (".factory/*", "!.factory/config.toml")


def rel(path: Path) -> Path:
    """Path relative to the current directory when inside it (no `../..` climbing), for readable output."""
    return path.relative_to(Path.cwd().resolve()) if path.is_relative_to(Path.cwd().resolve()) else path


def cmd_init(project: Path) -> int:
    path = config_path(project)
    written: list[Path] = []
    if path.exists():
        print(f"✔ {rel(path)} already exists")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(template(project))
        written.append(path)
        print(f"✔ wrote {rel(path)}  (check `checks` and `tickets_dir`, commit any edit)")
    gitignore = project / ".gitignore"
    lines = gitignore.read_text().splitlines() if gitignore.exists() else []
    missing = [line for line in IGNORE if line not in lines]
    if missing:
        owners_edits = subprocess.run(
            ["git", "status", "--porcelain", "--", ".gitignore"], cwd=project, capture_output=True, text=True
        ).stdout
        with gitignore.open("a") as f:
            f.write(("\n" if lines and lines[-1] else "") + "\n".join(missing) + "\n")
        if not owners_edits:  # never commit the Owner's uncommitted lines along with ours
            written.append(gitignore)
        print(f"✔ added {', '.join(missing)} to {rel(gitignore)}")
    if written:
        commit(project, [str(p.relative_to(project)) for p in written])
    return 0


def commit(project: Path, paths: list[str]) -> None:
    """Commit the files the Factory wrote, and only those, so that a Run starts from a clean tree."""
    msg = "factory: config and .gitignore lines"
    ok = subprocess.run(["git", "add", "--", *paths], cwd=project, capture_output=True).returncode == 0
    ok = ok and subprocess.run(["git", "commit", "-q", "-m", msg, "--", *paths], cwd=project).returncode == 0
    print(f"✔ committed {', '.join(paths)}" if ok else f"factory: could not commit {', '.join(paths)}: do it yourself")


def cmd_bootstrap(project: Path) -> int:
    cmd_init(project)
    cfg = load_config(project)
    (project / cfg.tickets_dir).mkdir(parents=True, exist_ok=True)
    if warning := branch_warning(project, cfg):
        print(f"factory: {warning}")
    stage, command = next_step(rel(project), cfg)
    print(f"Stage: {stage}\nNext:  {command}")
    return 0


SKILL = Path(__file__).parents[2] / "skills" / "factory"  # shortcut: found via the editable install, not packaged


def cmd_install_skill(dest: Path) -> int:
    shutil.copytree(SKILL, dest / "factory", dirs_exist_ok=True)
    print(f"factory: installed the factory skill into {dest / 'factory'}")
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
    sub.add_parser(
        "bootstrap", help="init, create the tickets folder, report the stage and the next command"
    ).add_argument("project", type=Path)
    sk = sub.add_parser("install-skill", help="copy the factory skill into ~/.claude/skills")
    sk.add_argument("--dir", type=Path, default=Path.home() / ".claude" / "skills")
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
    if args.cmd == "install-skill":
        return cmd_install_skill(args.dir)
    project: Path = args.project.resolve()
    try:
        if args.cmd == "init":
            return cmd_init(project)
        if args.cmd == "bootstrap":
            return cmd_bootstrap(project)
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
