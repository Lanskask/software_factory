"""Unattended `claude -p` sessions: the command line, running it with a wall-clock limit, and reading its result."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SessionResult:
    ok: bool
    text: str  # the final message, or why there is none
    cost_usd: float = 0.0
    rate_limited: bool = False  # HTTP 429, e.g. the subscription's 5-hour limit: running again later works


def session_command(
    prompt: str,
    *,
    system: str,
    allowed: tuple[str, ...],
    disallowed: tuple[str, ...],
    budget_usd: float,
    model: str | None,
    plugin_dir: str | None,
    permission_mode: str,
    name: str,
    claude: str = "claude",
) -> list[str]:
    cmd = [claude, "-p", prompt, "--permission-mode", permission_mode, "--name", name]
    if system:
        cmd += ["--append-system-prompt", system]
    if allowed:
        cmd += ["--allowedTools", *allowed]
    if disallowed:
        cmd += ["--disallowedTools", *disallowed]
    if plugin_dir:
        cmd += ["--plugin-dir", plugin_dir]
    if model:
        cmd += ["--model", model]
    cmd += ["--max-budget-usd", str(budget_usd), "--output-format", "stream-json", "--verbose"]
    # No MCP servers in unattended sessions: they write into the Project (.serena/) or reach outside (mail, chat).
    return [*cmd, "--strict-mcp-config", "--no-session-persistence"]


def parse_stream(text: str) -> SessionResult:
    """The last `result` event of a stream-json log."""
    final: dict[str, object] | None = None
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") == "result":
            final = event
    if final is None:
        return SessionResult(ok=False, text="")
    cost = float(str(final.get("total_cost_usd") or 0.0))
    if final.get("subtype") != "success" or final.get("is_error"):
        # an API error (e.g. "Credit balance is too low") comes as subtype success with is_error and the message
        why = final.get("result") if final.get("is_error") and final.get("result") else final.get("subtype")
        limited = final.get("is_error") is True and final.get("api_error_status") == 429
        return SessionResult(ok=False, text=f"session ended with {why}", cost_usd=cost, rate_limited=limited)
    return SessionResult(ok=True, text=str(final.get("result") or ""), cost_usd=cost)


def run_session(cmd: list[str], cwd: Path, log: Path, timeout_s: float) -> SessionResult:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as out:
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True)
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            return SessionResult(ok=False, text=f"timed out after {timeout_s / 60:.0f} min")
    return parse_stream(log.read_text())
