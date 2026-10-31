"""Question: does a failed push/PR on ticket 01 still make ticket 02's PR fail with "Base ref must be a branch"?

Replays the real incident: the remote is unreachable during the first Run, then fixed, then the Run is repeated. The
fake `gh` refuses a base branch that is missing on origin, as GitHub does. Usage:
    uv run python experiments/failed_publish_replay.py            # compares commit 2d52c24 with the working tree
Answer (2026-10-30): old commit -> second Run opens only 02's PR and fails with the incident's error (exit 1);
working tree -> second Run opens PR 01 (base main) then PR 02 (base factory/01-a), exit 0.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
OLD = "2d52c24"  # last commit before the retry fix

GH = """
import subprocess, sys
a = sys.argv[1:]; base = a[a.index("--base") + 1]
if subprocess.run(["git", "ls-remote", "--exit-code", "--heads", "origin", base], capture_output=True).returncode:
    print("GraphQL: Base ref must be a branch (createPullRequest)", file=sys.stderr); sys.exit(1)
print("PR created: base", base, "head", a[a.index("--head") + 1])
"""


def scenario(src: Path) -> None:
    """Runs inside a child process whose PYTHONPATH is `src`, so the Factory under test is the one in that tree."""
    import json

    import test_run_e2e as t

    from factory.config import Config
    from factory.run import Factory

    tmp = Path(tempfile.mkdtemp())
    origin = tmp / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    p = tmp / "proj"
    p.mkdir()
    for a in (["init", "-q", "-b", "main"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        t.git(p, *a)
    (p / "t").mkdir()
    (p / "t" / "tickets.py").write_text(t.FAKE_TICKETS)
    (p / ".gitignore").write_text(".factory/*\n!.factory/config.toml\n.review-*\n")
    (p / "t" / "tickets.json").write_text(
        json.dumps(
            {
                "01": {"slug": "a", "state": "todo", "blocked_by": []},
                "02": {"slug": "b", "state": "todo", "blocked_by": ["01"]},
            }
        )
    )
    t.git(p, "add", "-A")
    t.git(p, "commit", "-qm", "tickets")
    t.git(p, "remote", "add", "origin", str(tmp / "no-such-remote.git"))  # the incident: no usable remote yet
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    t.executable(bin_dir / "claude", t.FAKE_CLAUDE)
    t.executable(bin_dir / "gh", GH)
    os.environ.update(PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}", FAKE_LOG=str(tmp / "claude.log"))
    cfg = Config(tickets_dir="t", checks=("test -f t/tickets.json",), implement_skills=(), review_skills=())
    print(f"--- Run 1, remote broken: exit {Factory(p, cfg, python=sys.executable).run()}")
    t.git(p, "remote", "set-url", "origin", str(origin))
    t.git(p, "push", "-q", "origin", "main")
    print(f"--- Run 2, remote fixed: exit {Factory(p, cfg, python=sys.executable).run()}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        scenario(Path(sys.argv[1]))
        sys.exit()
    work = Path(tempfile.mkdtemp())
    subprocess.run(["git", "worktree", "add", "-q", "--detach", str(work / "old"), OLD], cwd=ROOT, check=True)
    for label, tree in (("OLD " + OLD, work / "old"), ("NEW working tree", ROOT)):
        print(f"===== {label}")
        env = {**os.environ, "PYTHONPATH": str(tree / "src")}
        subprocess.run([sys.executable, __file__, str(tree)], env=env, cwd=work)
    subprocess.run(["git", "worktree", "remove", "--force", str(work / "old")], cwd=ROOT)
