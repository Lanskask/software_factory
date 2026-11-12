# 06: Triage [low] loose ends into Backlog tickets at the end of a Run

**What to build:** At the end of a Run each `[low]` loose end becomes a Backlog ticket, and `factory status` lists them
as one list. See docs/factory-analysis.md section 3, P3. Lane A. Closes #14.

**Blocked by:** None (can start immediately)

**Status:** todo

## Tasks

- [ ] At the end of a Run, file each [low] loose end as a Backlog ticket
  - src/factory/run.py end of run(); .factory/LOOSE-ENDS.md
  - a plain file write is enough if no Session is needed
- [ ] List them in factory status as one list
  - src/factory/cli.py cmd_status()

## Acceptance

- [ ] At the end of a Run each [low] loose end becomes a Backlog ticket
- [ ] factory status lists them as one list
- [ ] Tests cover both; make test and make lint pass
