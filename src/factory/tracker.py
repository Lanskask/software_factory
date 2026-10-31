"""Tickets in the `/to-tickets` file format, read and changed only through the Project's own `tickets.py`."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Ticket:
    num: str  # "02", or "10/13" (epic/number) in repos that group Tickets by epic
    state: str  # todo | in_progress | done
    ready: bool  # todo with every blocking Ticket done
    slug: str

    def branch(self, prefix: str) -> str:
        return f"{prefix}{self.num.replace('/', '-')}-{self.slug}"

    @property
    def file_key(self) -> str:
        return self.num.replace("/", "-")


def parse_status(out: str) -> list[Ticket]:
    """Rows of `tickets.py status`: number, state, READY or empty, slug, tab-separated. Other lines are headers."""
    tickets = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 4:
            tickets.append(Ticket(num=parts[0], state=parts[1], ready=parts[2] == "READY", slug=parts[3]))
    return tickets


class Tracker:
    def __init__(self, project: Path, tickets_dir: str, python: str = "python3") -> None:
        self.project = project
        self.dir = tickets_dir
        self.python = python

    @property
    def command(self) -> str:
        """The command line a Session uses, relative to the Project root."""
        return f"{self.python} -I {self.dir}/tickets.py --dir {self.dir}"

    def exists(self) -> bool:
        if not (self.project / self.dir / "tickets.py").exists():
            return False
        try:
            return bool(self.status())
        except subprocess.CalledProcessError:  # tickets.py exits 1 when the directory has no Tickets
            return False

    def _run(self, *args: str) -> str:
        cmd = [self.python, "-I", f"{self.dir}/tickets.py", "--dir", self.dir, *args]
        return subprocess.run(cmd, cwd=self.project, check=True, capture_output=True, text=True).stdout

    def status(self) -> list[Ticket]:
        return parse_status(self._run("status"))

    def show(self, num: str) -> str:
        return self._run("show", num)

    def is_done(self, num: str) -> bool:
        return any(t.num == num and t.state == "done" for t in self.status())
