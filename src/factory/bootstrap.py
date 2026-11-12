"""`factory bootstrap`: set a Project up for the Factory and say which stage it is at and what to run next."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path

from factory.config import Config
from factory.tracker import Tracker

SPEC_GLOBS = ("docs/SPEC.md", "docs/spec.md", "SPEC.md", "spec.md", ".scratch/*/spec.md")
TEMPLATES = Path(__file__).parent / "templates"
# Project path -> template file. An existing file is never overwritten.
PROJECT_FILES = {
    "CLAUDE.md": "CLAUDE.md",
    ".claude/settings.json": "settings.json",
    "docs/OWNER-ANSWERS.md": "interview.md",
}


def copy_templates(project: Path) -> list[str]:
    """Copy each template the Project lacks; return the Project paths written."""
    written = []
    for target, name in PROJECT_FILES.items():
        dest = project / target
        if dest.exists():
            if target == "CLAUDE.md":
                print(f"factory: CLAUDE.md exists: the rules template was not applied (see {TEMPLATES / name})")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text((TEMPLATES / name).read_text())
        written.append(target)
    return written


def find_spec(project: Path) -> Path | None:
    for pattern in SPEC_GLOBS:
        if found := next(project.glob(pattern), None):
            return found.relative_to(project)
    return None


def answered(project: Path) -> bool:
    """Coarse exit check of `answers`: Q1, the only question with no default, has an Answer."""
    f = project / "docs" / "OWNER-ANSWERS.md"
    # The answer may follow `Answer:` on the same line or sit on the lines below, before the next `## ` heading.
    pattern = r"^## 1\.(?:(?!^## ).)*?^Answer:(?:[ \t]*\S|\s+(?!## )\S)"
    return f.exists() and re.search(pattern, f.read_text(), re.S | re.M) is not None


def next_step(project: Path, cfg: Config) -> tuple[str, str]:
    """The Project's stage (with the Ticket count once there are Tickets) and the command that moves it on."""
    tracker = Tracker(project, cfg.tickets_dir)
    tickets = tracker.status() if tracker.exists() else []
    if tickets:
        done = sum(t.state == "done" for t in tickets)
        count = f"({done}/{len(tickets)} tickets)"
        if done == len(tickets):
            return f"verify {count}", "review the draft PRs"  # shortcut: PR and CI state unknown; no deploy or retro
        if any(t.ready for t in tickets):
            return f"build {count}", f"factory run {project}"
        return f"build {count}, blocked", f"factory status {project}"
    if spec := find_spec(project):
        return f"tickets (spec {spec})", f"factory plan {project} --spec {spec}"
    if answered(project):
        return "spec", f"factory plan {project}"
    if (project / "docs" / "IDEA.md").exists():
        return "answers", f"answer docs/OWNER-ANSWERS.md, then factory plan {project}"
    return "idea", f"write docs/IDEA.md, then factory plan {project}"


def branch_warning(project: Path, cfg: Config) -> str | None:
    out = subprocess.run(["git", "symbolic-ref", "--short", "HEAD"], cwd=project, capture_output=True, text=True)
    if out.returncode != 0:
        return f"{project} is has no git branch: run `git init` and commit first"
    branch = out.stdout.strip()
    if branch != cfg.base_branch:
        return f"on branch {branch}, but base_branch is {cfg.base_branch}: switch, or set base_branch in config.toml"
    return None


def run_command(cmd: list[str]) -> str:
    """Output (stdout and stderr) of `cmd`; empty when it cannot run or hangs."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout + r.stderr


def doctor(run: Callable[[list[str]], str] = run_command) -> str:
    """One line: MCP servers connected, gh scopes (repo, project) and whether the token can merge."""
    mcp = [ln for ln in run(["claude", "mcp", "list"]).splitlines() if " - " in ln]
    up = sum("Connected" in ln and "Failed" not in ln for ln in mcp)
    scopes = re.search(r"Token scopes: (.*)", run(["gh", "auth", "status"]))
    have = set(re.findall(r"[\w:-]+", scopes[1])) if scopes else set()
    missing = [s for s in ("repo", "project") if s not in have]
    perm = run(["gh", "repo", "view", "--json", "viewerPermission", "-q", ".viewerPermission"]).strip()
    # shortcut: viewerPermission is the user's repo role; branch protection rules are not checked
    merge = "yes" if perm in ("ADMIN", "MAINTAIN", "WRITE") else "no"
    gh = "ok" if not missing else f"missing {', '.join(missing)}"
    return f"Doctor: MCP {up}/{len(mcp)} up, gh scopes {gh}, can merge: {merge}"
