"""Planning: the interactive phase where the Owner and a Claude session turn a Project (and maybe a Spec) into Tickets.

`/egm:egm-bootstrap` runs first, unattended. Then one interactive `claude` session walks the chain of skills, calling
model-invocable copies of them (see skills.py), while the Owner answers the interview questions.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from factory.claude import run_session, session_command
from factory.config import Config
from factory.run import GIT_READ
from factory.skills import INSTALLED, build_plugin, local_name
from factory.tracker import Tracker

BOOTSTRAP = "egm:egm-bootstrap"
BOOTSTRAP_TOOLS = (
    "Agent",
    "Read",
    "Glob",
    "Grep",
    "Write",
    "Edit",
    "TodoWrite",
    *GIT_READ,
    "Bash(git ls-files*)",
    "Bash(mkdir*)",
    "Bash(npx --yes prettier@3.3.3*)",  # egm-bootstrap formats its EGM_DOC.md files with the owner's md-style
)


def chain(*, spec: bool) -> tuple[str, ...]:
    """The skills of Planning after the bootstrap, in order."""
    review_and_cut = ("egm:egm-review-loop", "mattpocock-skills:to-tickets")
    if spec:
        return review_and_cut
    return ("mattpocock-skills:grill-with-docs", "mattpocock-skills:to-spec", *review_and_cut)


PLANNING_SKILLS = (BOOTSTRAP, *chain(spec=False))


def planning_rules(cfg: Config, spec: Path | None, steps: tuple[str, ...]) -> str:
    numbered = "\n".join(f"{i}. {local_name(s)}" for i, s in enumerate(steps, 1))
    source = f"The Spec is {spec}." if spec else "There is no Spec yet: the chain below writes one."
    return f"""You are the Planning session of the Software Factory for this Project. The Owner is here and answers
your questions. {source}

Walk through these skills in order. Invoke each one yourself with the Skill tool once the previous one is finished,
and tell the Owner which step you are on:

{numbered}

Rules for the result
- The issue tracker is local files. /to-tickets writes the Tickets with its tickets.py into `{cfg.tickets_dir}`
  exactly, not into another .scratch directory.
- After Planning, every Ticket is implemented unattended: one Session each, about ${cfg.budget_usd:.0f} and
  {cfg.timeout_minutes} minutes. Keep Tickets small and clear, with acceptance criteria a test can check, and resolve
  every open question now: no Session can ask the Owner.
- A Ticket that needs the Owner (a go-ahead, cloud resources, money, credentials) says "Owner's go-ahead" in its text,
  so the Run skips it.
- At the end, commit the Spec, the docs and the Tickets on the current branch, and tell the Owner to run
  `factory run` on this Project.
"""


class Planner:
    def __init__(
        self,
        project: Path,
        cfg: Config,
        *,
        claude: str = "claude",
        python: str = "python3",
        skills: tuple[str, ...] | None = None,
        installed: Path = INSTALLED,
    ) -> None:
        self.project = project.resolve()
        self.cfg = cfg
        self.claude = claude
        self.tracker = Tracker(self.project, cfg.tickets_dir, python)
        self.skills = PLANNING_SKILLS if skills is None else skills
        self.installed = installed
        self.state = self.project / ".factory"

    def say(self, msg: str) -> None:
        print(f"factory: {msg}", flush=True)

    def bootstrap(self) -> bool:
        log = self.state / "logs" / "plan-bootstrap.jsonl"
        self.say(f"running /{BOOTSTRAP} unattended (up to $3), log {log.relative_to(self.project)}")
        cmd = session_command(
            f"/{BOOTSTRAP}",
            system="",
            allowed=BOOTSTRAP_TOOLS,
            disallowed=("Bash(git push*)", "Bash(git commit*)"),
            budget_usd=3.0,
            model=self.cfg.model,
            plugin_dir=None,
            permission_mode="acceptEdits",
            name=f"factory {self.project.name} plan-bootstrap",
            claude=self.claude,
        )
        res = run_session(cmd, self.project, log, 30 * 60)
        self.say(f"bootstrap {'finished' if res.ok else 'failed: ' + res.text}, ${res.cost_usd:.2f}")
        self.commit_egm_docs()
        return res.ok

    def commit_egm_docs(self) -> None:
        """The unattended bootstrap may not commit, so the Factory commits the docs it wrote, and only those."""
        ls = subprocess.run(
            ["git", "ls-files", "--others", "--modified", "--exclude-standard", "--", ":(glob)**/EGM_DOC.md"],
            cwd=self.project,
            capture_output=True,
            text=True,
        )
        docs = ls.stdout.splitlines()
        if ls.returncode or not docs:
            return
        subprocess.run(["git", "add", "--", *docs], cwd=self.project, check=True)
        msg = "factory: EGM_DOC.md files from /egm-bootstrap"
        subprocess.run(["git", "commit", "-q", "-m", msg, "--", *docs], cwd=self.project, check=True)
        self.say(f"committed {len(docs)} EGM_DOC.md files")

    def plan(self, spec: Path | None, *, bootstrap: bool) -> int:
        if self.tracker.exists():
            self.say(f"Tickets already exist in {self.cfg.tickets_dir}: run `factory run {self.project}`")
            return 0
        steps = chain(spec=spec is not None)
        if not (bootstrap and self.bootstrap()):
            steps = (BOOTSTRAP, *steps)
        cmd = [self.claude, "--name", f"factory {self.project.name} plan"]
        cmd += ["--append-system-prompt", planning_rules(self.cfg, spec, steps)]
        if self.skills:
            cmd += ["--plugin-dir", str(build_plugin(self.skills, self.state / "plan-plugin", self.installed))]
        if self.cfg.model:
            cmd += ["--model", self.cfg.model]
        self.say("opening the Planning session. Steps: " + " → ".join(f"/{local_name(s)}" for s in steps))
        self.say("if a step does not start by itself, type its command")
        subprocess.run([*cmd, "Start Planning."], cwd=self.project)
        if self.tracker.exists():
            self.say(f"Tickets are ready. Next: `factory run {self.project} --dry-run`, then without --dry-run")
            return 0
        self.say(f"no Tickets in {self.cfg.tickets_dir} yet: run `factory plan` again to continue")
        return 1
