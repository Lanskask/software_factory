# 04: Make checks follow CI: copy make targets from workflows

**What to build:** `factory init` copies the make targets that `.github/workflows/*.yml` runs into `checks`, and
`preflight` warns when a `Dockerfile` exists and no check builds it. See docs/factory-analysis.md section 3, P4. Lane A.
Closes #15.

**Blocked by:** None (can start immediately)

**Status:** todo

## Tasks

- [ ] Read run: make X lines from the workflows in config.template()
  - src/factory/config.py template()
- [ ] Warn in preflight when a Dockerfile exists and no check builds it
  - src/factory/run.py preflight(); a warning, not a refusal

## Acceptance

- [ ] factory init copies the make targets from .github/workflows/*.yml into checks
- [ ] preflight warns when a Dockerfile exists and no check builds it
- [ ] Tests cover both; make test and make lint pass
