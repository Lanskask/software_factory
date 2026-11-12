"""`factory bootstrap`: set a Project up for the Factory and say which stage it is at and what to run next."""

from __future__ import annotations

import subprocess
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


def next_step(project: Path, cfg: Config) -> tuple[str, str]:
    """The Project's stage and the command that moves it on."""
    tracker = Tracker(project, cfg.tickets_dir)
    if tracker.exists():
        tickets = tracker.status()
        if any(t.ready for t in tickets):
            return "Tickets are ready", f"factory run {project} --dry-run   # then without --dry-run"
        done = all(t.state == "done" for t in tickets)
        return (
            ("All Tickets are done", "review the draft PRs")
            if done
            else ("Tickets are blocked", f"factory status {project}")
        )
    if spec := find_spec(project):
        return f"A Spec exists ({spec}), no Tickets", f"factory plan {project} --spec {spec}"
    return "No Spec and no Tickets", f"factory plan {project}"


def branch_warning(project: Path, cfg: Config) -> str | None:
    out = subprocess.run(["git", "symbolic-ref", "--short", "HEAD"], cwd=project, capture_output=True, text=True)
    if out.returncode != 0:
        return f"{project} is has no git branch: run `git init` and commit first"
    branch = out.stdout.strip()
    if branch != cfg.base_branch:
        return f"on branch {branch}, but base_branch is {cfg.base_branch}: switch, or set base_branch in config.toml"
    return None
