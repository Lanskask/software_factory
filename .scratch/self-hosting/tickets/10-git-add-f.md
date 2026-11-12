# 10: Review git add -f in commit()

**What to build:** A recorded decision on whether `commit()` keeps `git add -f` (the Owner's global gitignore has
`.claude/`). Lane B. Closes #25.

**Blocked by:** None (can start immediately)

**Status:** todo

## Tasks

- [ ] Check what git add -f can add by mistake in commit()
  - src/factory/cli.py commit()
  - it only adds the paths the Factory wrote
- [ ] Keep or change it, with a test for the chosen behaviour
  - tests/
- [ ] Record the decision and its reason
  - docs/DECISION-LOG.md

## Acceptance

- [ ] The decision is in docs/DECISION-LOG.md
- [ ] A test pins the chosen behaviour; make test and make lint pass
