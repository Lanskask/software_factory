"""The Run: every Ready Ticket in turn, one fresh Session each, checked by the Factory and an independent reviewer
before the Factory pushes it and opens a draft pull request. Nothing is ever merged."""

from __future__ import annotations

import json
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from factory.claude import SessionResult, run_session, session_command
from factory.config import Config
from factory.pr_text import code_quote, pr_title
from factory.prompts import (
    blocked_reason,
    fix_goal,
    goal,
    has_high_loose_end,
    parse_verdict,
    resolve_prompt,
    review_prompt,
    session_rules,
)
from factory.skills import INSTALLED, build_plugin
from factory.tracker import Ticket, Tracker

# Read-only shell commands, so compound commands like `ls; cat x` are not refused (measured in the bootstrap log).
SHELL_READ = tuple(f"Bash({c}*)" for c in ("ls", "cat", "head", "tail", "wc", "pwd", "echo", "grep", "diff"))
GIT_READ = (*SHELL_READ, "Bash(git status*)", "Bash(git diff*)", "Bash(git log*)", "Bash(git show*)")
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
        checks = tuple(f"Bash({c}*)" for c in self.cfg.checks)  # reviewer verifies by running them, not by reading
        own = ("Skill", "Agent", "Read", "Glob", "Grep", *GIT_READ)
        return (*own, f"Bash({tk} show*)", f"Bash({tk} status*)", *checks)

    def command(self, prompt: str, *, review: bool, name: str, resolve: bool = False) -> list[str]:
        review = review or resolve  # the resolver is a read-only Session too, with web research added
        return session_command(
            prompt,
            system=session_rules(self.cfg, self.tracker.command),
            allowed=(*self.review_tools(), *(("WebSearch", "WebFetch") if resolve else ()))
            if review
            else self.implement_tools(),
            disallowed=(*NEVER, "Edit", "Write", "NotebookEdit", "Bash(git commit*)") if review else NEVER,
            budget_usd=self.cfg.review_budget_usd if review else self.cfg.budget_usd,
            model=self.cfg.resolve_model if resolve else self.cfg.model,
            plugin_dir=self.plugin_dir,
            permission_mode="default" if review else "acceptEdits",
            name=name,
            claude=self.claude,
        )

    def session(
        self, ticket: Ticket, kind: str, prompt: str, *, review: bool = False, resolve: bool = False
    ) -> SessionResult:
        n = len(list((self.state / "logs").glob(f"{ticket.file_key}-{kind}-*.jsonl"))) + 1
        log = self.state / "logs" / f"{ticket.file_key}-{kind}-{n}.jsonl"
        self.say(f"{ticket.num}: {kind} session {n}, log {log.relative_to(self.project)}")
        name = f"factory {self.project.name} {ticket.num} {kind} {n}"
        cmd = self.command(prompt, review=review, name=name, resolve=resolve)
        res = run_session(cmd, self.project, log, self.cfg.timeout_minutes * 60)
        self.cost += res.cost_usd
        self.say(f"{ticket.num}: {kind} session {n} ended, ${res.cost_usd:.2f}, ok={res.ok}")
        return res

    # --- the Run -------------------------------------------------------------------------------------------------

    def preflight(self) -> str | None:
        if dirty := self.git("status", "--porcelain"):
            return (
                "the working tree is not clean. Commit what belongs to the Project (docs, config), git-ignore local "
                "tool state (caches, live sessions), then run again:\n" + dirty
            )
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

    def tip_ticket(self) -> Ticket | None:
        """The newest unblocked Ticket that has a Factory branch: the tip of the stack.

        shortcut: any existing branch of an unblocked Ticket counts as done work; upgrade when Tickets can be
        abandoned half-way without a Blocked marker.
        """
        blocked = self.blocked_keys()
        for t in reversed(self.tracker.status()):
            if t.file_key not in blocked and self.git("branch", "--list", t.branch(self.cfg.branch_prefix)):
                return t
        return None

    def stack_tip(self) -> str:
        """The branch the next Ticket stacks on, else `base_branch`. Never the checked-out branch, which may be
        hand-made."""
        tip = self.tip_ticket()
        return tip.branch(self.cfg.branch_prefix) if tip else self.cfg.base_branch

    def carried_over(self, dry_run: bool) -> tuple[Path | None, Path | None] | None:
        """The Handoff and resolution of the Ticket the stack ends on, from an earlier Run; None if its resolver fails.

        A [high] item without a resolution is resolved first, which is what the end of the previous Run would have
        done had it not stopped. `--dry-run` spends nothing, so it only passes on a resolution that already exists.
        """
        tip = self.tip_ticket()
        handoff = self.state / "handoffs" / f"{tip.file_key}.md" if tip else None
        if tip is None or handoff is None or not handoff.exists():
            return None, None
        resolution = self.state / "resolutions" / f"{tip.file_key}.md"
        if resolution.exists():
            return handoff, resolution
        if dry_run or not has_high_loose_end(handoff.read_text()):
            return handoff, None
        self.say(f"{tip.num}: [high] loose end left by an earlier Run, resolving it first")
        self.ensure_plugin()  # the resolver gets the same skills as it would at the end of a Run
        return (handoff, resolved) if (resolved := self.resolve(tip, handoff)) else None

    def run(self, *, dry_run: bool = False) -> int:
        problem = self.preflight()
        if problem:
            self.say(problem)
            return 1
        try:
            self.retry_unpublished()
        except PushError as e:
            self.say(f"{e}. Stopping: fix the remote or gh, then run again.")
            return 1
        base = self.stack_tip()
        if base != self.git("rev-parse", "--abbrev-ref", "HEAD"):
            self.say(f"switching to {base}, the tip of the stack")
            self.git("switch", "-q", base)
        skipped: set[str] = set()
        carried = self.carried_over(dry_run)
        if carried is None:
            self.say("[high] loose end, the resolver failed. Stopping: read .factory/LOOSE-ENDS.md")
            return 1
        previous, resolution = carried
        done, blocked = 0, 0
        for _ in range(self.cfg.max_tickets):
            ticket = self.next_ticket(skipped)
            if ticket is None:
                self.say("no Ready Ticket left that can run unattended")
                break
            handoff = self.state / "handoffs" / f"{ticket.file_key}.md"
            if dry_run:
                self.plugin_dir = str(self.state / "plugin") if self.skills() else None
                self.preview(ticket, base, handoff, previous, resolution)
                return 0
            self.ensure_plugin()
            if done == 0 and blocked == 0:  # only the `next:` line; --dry-run adds the claude command
                self.preview(ticket, base, handoff, previous, resolution, command=False)
            try:
                out = self.ticket(ticket, base, handoff, previous, resolution)
            except PushError as e:
                self.say(f"{e}. Stopping: fix the remote or gh, then run again.")
                return 1
            if out.blocked:
                blocked += 1
                self.say(f"{ticket.num}: Blocked: {out.blocked.splitlines()[0]}")
                if blocked >= self.cfg.max_blocked:
                    self.say(f"stopping: {blocked} Blocked Tickets (max_blocked = {self.cfg.max_blocked})")
                    break
                continue
            done += 1
            base, previous, resolution = out.branch, out.handoff, None
            if out.high and out.handoff:
                resolution = self.resolve(ticket, out.handoff)
                if resolution is None:
                    self.say(
                        f"{ticket.num}: [high] loose end, the resolver failed. Stopping: read .factory/LOOSE-ENDS.md"
                    )
                    return 1
        self.say(f"Run finished: {done} pull requests, {blocked} Blocked, ${self.cost:.2f} spent")
        return 1 if blocked else 0

    def preview(
        self,
        t: Ticket,
        base: str,
        handoff: Path,
        previous: Path | None,
        resolution: Path | None,
        *,
        command: bool = True,
    ) -> None:
        print(f"next: {t.num} on {t.branch(self.cfg.branch_prefix)} from {base}", flush=True)
        if not command:
            return
        goal_text = goal(t, self.tracker.command, handoff, previous, self.cfg.checks, resolution)
        name = f"factory {self.project.name} {t.num} implement 1"
        print(shlex.join(self.command(goal_text, review=False, name=name)), flush=True)

    def resolve(self, t: Ticket, handoff: Path) -> Path | None:
        """A read-only Session on `resolve_model` decides what to do about the [high] items; None if it fails."""
        res = self.session(t, "resolve", resolve_prompt(t, self.tracker.command, handoff), resolve=True)
        if not res.ok or not res.text.strip():
            return None
        path = self.state / "resolutions" / f"{t.file_key}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(res.text.rstrip() + "\n")
        with (self.state / "LOOSE-ENDS.md").open("a") as f:
            f.write(
                f"\n<!-- {t.num} {t.slug}: decision of the {self.cfg.resolve_model} resolver -->\n{res.text.rstrip()}\n"
            )
        return path

    def log_loose_ends(self, t: Ticket, branch: str, handoff: Path) -> None:
        if handoff.exists():
            with (self.state / "LOOSE-ENDS.md").open("a") as f:
                f.write(f"\n<!-- {t.num} {t.slug}, branch {branch} -->\n{handoff.read_text().rstrip()}\n")

    def skills(self) -> tuple[str, ...]:
        return (*self.cfg.implement_skills, *self.cfg.review_skills)

    def ensure_plugin(self) -> None:
        if self.plugin_dir is None and self.skills():
            self.plugin_dir = str(build_plugin(self.skills(), self.state / "plugin", self.installed))

    # --- one Ticket ----------------------------------------------------------------------------------------------

    def ticket(
        self, t: Ticket, base: str, handoff: Path, previous: Path | None, resolution: Path | None = None
    ) -> Outcome:
        branch = t.branch(self.cfg.branch_prefix)
        if self.git("branch", "--list", branch):
            return self.block(t, base, f"branch {branch} already exists from an earlier Run: delete or rename it")
        self.git("switch", "-q", "-c", branch, base)
        tk = self.tracker.command
        res = self.session(t, "implement", goal(t, tk, handoff, previous, self.cfg.checks, resolution))
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
            fx = self.session(t, "fix", fix_goal(t, tk, handoff, findings, self.cfg.checks))
            problem = self.verify(t, base, fx, handoff)
            if problem:
                return self.block(t, base, f"fix after review {round_}: {problem}")
        self.log_loose_ends(t, branch, handoff)  # before publishing: a failed push must not lose them
        self.say(f"{t.num}: publishing, pushing {branch} and opening a draft pull request")
        self.publish(t.num, t.slug, base, branch, handoff, review_log)
        return Outcome(branch=branch, handoff=handoff, high=has_high_loose_end(handoff.read_text()))

    def verify(self, t: Ticket, base: str, res: SessionResult, handoff: Path) -> str | None:
        """Why the Ticket is not done; None when it is. The Factory's own checks outrank what the Session says."""
        reason = blocked_reason(res.text)
        self.say(f"{t.num}: checking the Ticket is done, tree clean, commits, Handoff, {', '.join(self.cfg.checks)}")
        problem = self.objective_problem(t, base, handoff)
        if problem:
            return reason or (f"session failed: {res.text}" if not res.ok else problem)
        if reason:
            # Done and verified, yet the Session asked for the Owner: the Owner reads it before more is stacked.
            with handoff.open("a") as f:
                f.write(f"\n- [high] The Session ended with BLOCKED although the Ticket checks pass: {reason}\n")
        return None

    def objective_problem(self, t: Ticket, base: str, handoff: Path) -> str | None:
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
        self.log_loose_ends(t, branch, self.state / "handoffs" / f"{t.file_key}.md")
        d = self.state / "blocked"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{t.file_key}.md").write_text(
            f"# Blocked: {t.num} {t.slug}\n\nBranch: {branch} (not pushed)\n\n{reason}\n\n"
            f"Delete this file to let a later Run try the Ticket again.\n"
        )
        return Outcome(blocked=reason)

    def retry_unpublished(self) -> None:
        """A Ticket whose push or pull request failed is done in the tracker, so only this retry ever publishes it."""
        for f in sorted((self.state / "unpublished").glob("*.json")):
            a = json.loads(f.read_text())
            self.publish(a["num"], a["slug"], a["base"], a["branch"], Path(a["handoff"]), a["review_log"])

    def publish(self, num: str, slug: str, base: str, branch: str, handoff: Path, review_log: str) -> None:
        pending = self.state / "unpublished" / f"{num}-{slug}.json"
        pending.parent.mkdir(parents=True, exist_ok=True)
        record = {"num": num, "slug": slug, "base": base, "branch": branch, "handoff": str(handoff)}
        pending.write_text(json.dumps({**record, "review_log": review_log}))
        # `gh pr create` answers "Base ref must be a branch" for a base that origin does not have.
        on_origin = self.git("ls-remote", "--heads", "origin", base)
        for b in (branch,) if on_origin else (base, branch):
            push = subprocess.run(
                ["git", "push", "-q", "-u", "origin", b], cwd=self.project, capture_output=True, text=True
            )
            if push.returncode != 0:
                raise PushError(f"{num}: git push of {b} failed: {push.stderr.strip()}")
        ticket = self.tracker.show(num)
        body = code_quote(
            f"Ticket {num} ({slug}), implemented by the Software Factory. Draft: review before merging.\n\n"
            f"## Ticket\n\n{ticket}\n\n## Handoff\n\n{handoff.read_text()}\n\n## {review_log}\n"
        )
        pr = subprocess.run(
            [self.gh, "pr", "create", "--draft", "--base", base, "--head", branch,
             "--title", pr_title(ticket, num, slug), "--body", body],
            cwd=self.project, capture_output=True, text=True,
        )  # fmt: skip
        if pr.returncode != 0:
            raise PushError(f"{num}: gh pr create failed: {pr.stderr.strip()}")
        pending.unlink()
        self.say(f"{num}: draft pull request {pr.stdout.strip()}")
