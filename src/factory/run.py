"""The Run: every Ready Ticket in turn, one fresh Session each, checked by the Factory and an independent reviewer
before the Factory pushes it and opens a draft pull request. Nothing is ever merged."""

from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from factory.claude import SessionResult, run_session, session_command
from factory.config import Config
from factory.prompts import (
    blocked_reason,
    fix_goal,
    goal,
    has_high_loose_end,
    parse_verdict,
    review_prompt,
    session_rules,
)
from factory.skills import INSTALLED, build_plugin
from factory.tracker import Ticket, Tracker

GIT_READ = ("Bash(git status*)", "Bash(git diff*)", "Bash(git log*)", "Bash(git show*)")
NEVER = (
    "Bash(git push*)",
    "Bash(git merge*)",
    "Bash(git rebase*)",
    "Bash(git switch*)",
    "Bash(git checkout*)",
    "Bash(git reset*)",
    "Bash(gh *)",
)


class PushError(Exception):
    pass


@dataclass(frozen=True)
class Outcome:
    blocked: str | None = None  # why the Ticket is Blocked; None when it reached a pull request
    branch: str = ""
    handoff: Path | None = None
    high: bool = False  # the Handoff holds a [high] loose end


class Factory:
    def __init__(
        self,
        project: Path,
        cfg: Config,
        *,
        python: str = "python3",
        claude: str = "claude",
        gh: str = "gh",
        installed: Path = INSTALLED,
    ) -> None:
        self.project = project.resolve()
        self.cfg = cfg
        self.tracker = Tracker(self.project, cfg.tickets_dir, python)
        self.state = self.project / ".factory"
        self.claude = claude
        self.gh = gh
        self.installed = installed
        self.plugin_dir: str | None = None
        self.cost = 0.0

    # --- small helpers -------------------------------------------------------------------------------------------

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.project, check=True, capture_output=True, text=True
        ).stdout.strip()

    def say(self, msg: str) -> None:
        print(f"factory: {msg}", flush=True)

    def blocked_keys(self) -> set[str]:
        return {p.stem for p in (self.state / "blocked").glob("*.md")}

    def implement_tools(self) -> tuple[str, ...]:
        tk = self.tracker.command
        own = ("Skill", "Agent", "Read", "Glob", "Grep", "Edit", "Write", "TodoWrite")
        git = (*GIT_READ, "Bash(git add*)", "Bash(git commit*)", "Bash(git rm*)", "Bash(git mv*)")
        checks = tuple(f"Bash({c}*)" for c in self.cfg.checks)
        return (*own, *git, f"Bash({tk}*)", *checks, *self.cfg.allowed_tools)

    def review_tools(self) -> tuple[str, ...]:
        tk = self.tracker.command
        return ("Skill", "Agent", "Read", "Glob", "Grep", *GIT_READ, f"Bash({tk} show*)", f"Bash({tk} status*)")

    def command(self, prompt: str, *, review: bool) -> list[str]:
        return session_command(
            prompt,
            system=session_rules(self.cfg, self.tracker.command),
            allowed=self.review_tools() if review else self.implement_tools(),
            disallowed=(*NEVER, "Edit", "Write", "NotebookEdit", "Bash(git commit*)") if review else NEVER,
            budget_usd=self.cfg.review_budget_usd if review else self.cfg.budget_usd,
            model=self.cfg.model,
            plugin_dir=self.plugin_dir,
            permission_mode="default" if review else "acceptEdits",
            claude=self.claude,
        )

    def session(self, ticket: Ticket, kind: str, prompt: str, *, review: bool = False) -> SessionResult:
        n = len(list((self.state / "logs").glob(f"{ticket.file_key}-{kind}-*.jsonl"))) + 1
        log = self.state / "logs" / f"{ticket.file_key}-{kind}-{n}.jsonl"
        self.say(f"{ticket.num}: {kind} session {n}, log {log.relative_to(self.project)}")
        res = run_session(self.command(prompt, review=review), self.project, log, self.cfg.timeout_minutes * 60)
        self.cost += res.cost_usd
        self.say(f"{ticket.num}: {kind} session {n} ended, ${res.cost_usd:.2f}, ok={res.ok}")
        return res

    # --- the Run -------------------------------------------------------------------------------------------------

    def preflight(self) -> str | None:
        if self.git("status", "--porcelain"):
            return "the working tree is not clean: commit or stash first"
        ignored = subprocess.run(["git", "check-ignore", "-q", ".factory/handoffs/x.md"], cwd=self.project)
        if ignored.returncode != 0:
            return "`.factory/` is not git-ignored: run `factory init` or add `.factory/*` and `!.factory/config.toml`"
        if not self.tracker.exists():
            return f"no Tickets in {self.cfg.tickets_dir}: run `factory plan` first"
        return None

    def next_ticket(self, skipped: set[str]) -> Ticket | None:
        blocked = self.blocked_keys()
        for t in self.tracker.status():
            if not t.ready or t.file_key in blocked or t.num in skipped:
                continue
            if re.search(self.cfg.skip_pattern, self.tracker.show(t.num), re.IGNORECASE):
                self.say(f"{t.num}: skipped, it needs the Owner (go-ahead or cloud tooling)")
                skipped.add(t.num)
                continue
            return t
        return None

    def run(self, *, dry_run: bool = False) -> int:
        problem = self.preflight()
        if problem:
            self.say(problem)
            return 1
        base = self.git("rev-parse", "--abbrev-ref", "HEAD")
        skipped: set[str] = set()
        previous: Path | None = None
        done, blocked = 0, 0
        for _ in range(self.cfg.max_tickets):
            ticket = self.next_ticket(skipped)
            if ticket is None:
                self.say("no Ready Ticket left that can run unattended")
                break
            handoff = self.state / "handoffs" / f"{ticket.file_key}.md"
            if dry_run:
                self.plugin_dir = str(self.state / "plugin") if self.skills() else None
                print(f"next: {ticket.num} on {ticket.branch(self.cfg.branch_prefix)} from {base}")
                print(shlex.join(self.command(goal(ticket, self.tracker.command, handoff, previous), review=False)))
                return 0
            self.ensure_plugin()
            try:
                out = self.ticket(ticket, base, handoff, previous)
            except PushError as e:
                self.say(f"{ticket.num}: {e}. Stopping: fix the remote or gh, then run again.")
                return 1
            if out.blocked:
                blocked += 1
                self.say(f"{ticket.num}: Blocked: {out.blocked.splitlines()[0]}")
                if blocked >= self.cfg.max_blocked:
                    self.say(f"stopping: {blocked} Blocked Tickets (max_blocked = {self.cfg.max_blocked})")
                    break
                continue
            done += 1
            base, previous = out.branch, out.handoff
            if out.high:
                self.say(f"{ticket.num}: the Handoff has a [high] loose end. Stopping: read .factory/LOOSE-ENDS.md")
                return 1
        self.say(f"Run finished: {done} pull requests, {blocked} Blocked, ${self.cost:.2f} spent")
        return 1 if blocked else 0

    def skills(self) -> tuple[str, ...]:
        return (*self.cfg.implement_skills, *self.cfg.review_skills)

    def ensure_plugin(self) -> None:
        if self.plugin_dir is None and self.skills():
            self.plugin_dir = str(build_plugin(self.skills(), self.state / "plugin", self.installed))

    # --- one Ticket ----------------------------------------------------------------------------------------------

    def ticket(self, t: Ticket, base: str, handoff: Path, previous: Path | None) -> Outcome:
        branch = t.branch(self.cfg.branch_prefix)
        if self.git("branch", "--list", branch):
            return self.block(t, base, f"branch {branch} already exists from an earlier Run: delete or rename it")
        self.git("switch", "-q", "-c", branch, base)
        tk = self.tracker.command
        res = self.session(t, "implement", goal(t, tk, handoff, previous))
        problem = self.verify(t, base, res, handoff)
        if problem:
            return self.block(t, base, problem)
        review_log = ""
        for round_ in range(1, self.cfg.review_rounds + 1):
            rv = self.session(t, "review", review_prompt(t, base, tk, handoff, self.cfg), review=True)
            if not rv.ok:
                return self.block(t, base, f"review session failed: {rv.text}")
            passed, findings = parse_verdict(rv.text)
            review_log = f"Review {round_}: {'PASS' if passed else 'FAIL'}\n\n{findings}"
            if passed:
                break
            if round_ == self.cfg.review_rounds:
                return self.block(t, base, f"review still FAIL after {round_} rounds:\n{findings}")
            fx = self.session(t, "fix", fix_goal(t, tk, handoff, findings))
            problem = self.verify(t, base, fx, handoff)
            if problem:
                return self.block(t, base, f"fix after review {round_}: {problem}")
        self.publish(t, base, branch, handoff, review_log)
        loose = handoff.read_text()
        with (self.state / "LOOSE-ENDS.md").open("a") as f:
            f.write(f"\n<!-- {t.num} {t.slug}, branch {branch} -->\n{loose.rstrip()}\n")
        return Outcome(branch=branch, handoff=handoff, high=has_high_loose_end(loose))

    def verify(self, t: Ticket, base: str, res: SessionResult, handoff: Path) -> str | None:
        """Why the Ticket is not done, checked by the Factory itself; None when it is."""
        reason = blocked_reason(res.text)
        if reason:
            return reason
        if not res.ok:
            return f"session failed: {res.text}"
        if not self.tracker.is_done(t.num):
            return "the Ticket is not marked done"
        if self.git("status", "--porcelain"):
            return "the session left uncommitted changes"
        if self.git("rev-list", "--count", f"{base}..HEAD") == "0":
            return "the session made no commits"
        if not handoff.exists():
            return f"no Handoff at {handoff}"
        for check in self.cfg.checks:
            r = subprocess.run(["/bin/sh", "-c", check], cwd=self.project, capture_output=True, text=True)
            if r.returncode != 0:
                tail = "\n".join((r.stdout + r.stderr).splitlines()[-20:])
                return f"check `{check}` failed (exit {r.returncode}):\n{tail}"
        return None

    def block(self, t: Ticket, base: str, reason: str) -> Outcome:
        branch = t.branch(self.cfg.branch_prefix)
        on_branch = self.git("rev-parse", "--abbrev-ref", "HEAD") == branch
        if on_branch and self.git("status", "--porcelain"):
            # Keep the half-done work on its branch instead of losing it when switching back.
            self.git("add", "-A")
            self.git("commit", "-q", "--no-verify", "-m", f"factory: unfinished work of Blocked Ticket {t.num}")
        if on_branch:
            self.git("switch", "-q", base)
        d = self.state / "blocked"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{t.file_key}.md").write_text(
            f"# Blocked: {t.num} {t.slug}\n\nBranch: {branch} (not pushed)\n\n{reason}\n\n"
            f"Delete this file to let a later Run try the Ticket again.\n"
        )
        return Outcome(blocked=reason)

    def publish(self, t: Ticket, base: str, branch: str, handoff: Path, review_log: str) -> None:
        push = subprocess.run(
            ["git", "push", "-q", "-u", "origin", branch], cwd=self.project, capture_output=True, text=True
        )
        if push.returncode != 0:
            raise PushError(f"git push failed: {push.stderr.strip()}")
        body = (
            f"Ticket {t.num} ({t.slug}), implemented by the Software Factory. Draft: review before merging.\n\n"
            f"## Ticket\n\n{self.tracker.show(t.num)}\n\n## Handoff\n\n{handoff.read_text()}\n\n## {review_log}\n"
        )
        pr = subprocess.run(
            [self.gh, "pr", "create", "--draft", "--base", base, "--head", branch, "--title", f"{t.num} {t.slug}",
             "--body", body],
            cwd=self.project, capture_output=True, text=True,
        )  # fmt: skip
        if pr.returncode != 0:
            raise PushError(f"gh pr create failed: {pr.stderr.strip()}")
        self.say(f"{t.num}: draft pull request {pr.stdout.strip()}")
