"""Per-Project settings from `<project>/.factory/config.toml`."""

from __future__ import annotations

import dataclasses
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Tickets that need the Owner: a go-ahead, or tooling that creates cloud resources or costs money.
DEFAULT_SKIP = r"go-ahead|terraform|gcloud|fly deploy|modal run"


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    tickets_dir: str  # holds tickets.py and the NN-*.md Tickets, relative to the Project
    checks: tuple[str, ...]  # shell commands that must exit 0 before a Ticket is pushed
    base_branch: str = "main"
    branch_prefix: str = "factory/"
    allowed_tools: tuple[str, ...] = ()  # extra --allowedTools entries for implementation Sessions
    skip_pattern: str = DEFAULT_SKIP
    model: str | None = None
    resolve_model: str = "opus"  # decides what to do about a [high] loose end, so the Run does not stop
    budget_usd: float = 5.0
    review_budget_usd: float = 2.0
    timeout_minutes: int = 90
    max_tickets: int = 10
    max_blocked: int = 2
    review_rounds: int = 2
    implement_skills: tuple[str, ...] = (
        "mattpocock-skills:implement",
        "mattpocock-skills:tdd",
        "mattpocock-skills:diagnosing-bugs",
    )
    review_skills: tuple[str, ...] = ("mattpocock-skills:code-review", "agent-skills:security-and-hardening")


def config_path(project: Path) -> Path:
    return project / ".factory" / "config.toml"


def load_config(project: Path) -> Config:
    path = config_path(project)
    if not path.exists():
        raise ConfigError(f"{path} not found: run `factory init {project}` and edit it")
    try:
        raw = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: {e}") from e
    fields = {f.name: f for f in dataclasses.fields(Config)}
    unknown = sorted(set(raw) - set(fields))
    if unknown:
        raise ConfigError(f"{path}: unknown keys {', '.join(unknown)}")
    values: dict[str, Any] = {}
    for name, value in raw.items():
        values[name] = _check_type(path, name, value, dataclasses.asdict(Config("", ()))[name])
    for required in ("tickets_dir", "checks"):
        if required not in values:
            raise ConfigError(f"{path}: `{required}` is required")
    if not values["checks"]:
        raise ConfigError(f"{path}: `checks` needs at least one command")
    try:
        re.compile(str(values.get("skip_pattern", DEFAULT_SKIP)))
    except re.error as e:
        raise ConfigError(f"{path}: skip_pattern: {e}") from e
    return Config(**values)


def _check_type(path: Path, name: str, value: object, default: object) -> object:
    if isinstance(default, tuple):
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ConfigError(f"{path}: `{name}` must be a list of strings")
        return tuple(value)
    if name == "model":
        if not isinstance(value, str):
            raise ConfigError(f"{path}: `model` must be a string")
        return value
    if isinstance(default, float) and isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    if type(value) is not type(default):
        raise ConfigError(f"{path}: `{name}` must be {type(default).__name__}")
    return value


def template(project: Path) -> str:
    """A starting config.toml: checks from the Makefile targets that exist, tickets where /to-tickets puts them."""
    makefile = project / "Makefile"
    targets = re.findall(r"^([A-Za-z][\w-]*):", makefile.read_text(), re.M) if makefile.exists() else []
    checks = [f"make {t}" for t in ("test", "lint", "e2e") if t in targets] or ["make test"]
    quoted = ", ".join(f'"{c}"' for c in checks)
    return f'''# Software Factory settings for this Project. Every key but the first two is optional.
tickets_dir = ".scratch/{project.name}/tickets"  # where /to-tickets writes tickets.py and NN-*.md
checks = [{quoted}]  # must all exit 0 before a Ticket is pushed

# base_branch = "main"
# branch_prefix = "factory/"
# allowed_tools = ["Bash(bun run test*)"]  # extra tools a Session may use without asking
# skip_pattern = "{DEFAULT_SKIP}"
# model = "opus"
# resolve_model = "opus"     # the read-only Session that decides on a [high] loose end
# budget_usd = 5.0           # per implementation Session
# review_budget_usd = 2.0    # per review Session
# timeout_minutes = 90       # per Session
# max_tickets = 10           # per Run
# max_blocked = 2            # Blocked Tickets that stop a Run
# review_rounds = 2          # reviews per Ticket; each FAIL but the last gets a fix Session
# implement_skills = ["mattpocock-skills:implement", "mattpocock-skills:tdd", "mattpocock-skills:diagnosing-bugs"]
# review_skills = ["mattpocock-skills:code-review", "agent-skills:security-and-hardening"]
'''
