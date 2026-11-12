# 05: Add a merge = never | green config

**What to build:** An opt-in `merge` config key: with `green`, the Factory turns on GitHub auto-merge after review PASS.
See docs/factory-analysis.md section 3, P8. Lane A. Closes #18.

**Blocked by:** None (can start immediately)

**Status:** todo

## Tasks

- [ ] Add merge to Config (never default, green) and to the config template
  - src/factory/config.py; reject other values
- [ ] With green, run gh pr merge --auto --merge after review PASS
  - src/factory/run.py publish()
  - only for a PR whose base is base_branch (the bottom of the stack); a PR stacked on another branch would merge into
    that branch
  - record the choice in docs/DECISION-LOG.md

## Acceptance

- [ ] merge accepts never (default) and green and rejects anything else
- [ ] With green, gh pr merge --auto runs after review PASS; with never, it does not
- [ ] Tests cover both values; make test and make lint pass
