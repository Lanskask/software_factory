# 12: Add factory retro PROJECT

**What to build:** `factory retro PROJECT` generalises `experiments/tt_interventions.py` and appends a dated table to
`LESSONS.md`. See docs/factory-analysis.md section 3, P10. Lane B. Closes #20.

**Blocked by:** None (can start immediately)

**Status:** todo

## Tasks

- [ ] Move the counter into src/factory/retro.py, taking any Project's transcripts
  - experiments/tt_interventions.py
- [ ] Add the retro subcommand
  - src/factory/cli.py
- [ ] Append a dated table to LESSONS.md
  - keep the [open]/[resolved] status format of LESSONS.md

## Acceptance

- [ ] factory retro PROJECT appends a dated table to LESSONS.md
- [ ] Tests cover it with a canned transcript; make test and make lint pass
