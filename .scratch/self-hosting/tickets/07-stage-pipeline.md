# 07: Show the stage pipeline in next_step() and factory status

**What to build:** `next_step()` and `factory status` follow the stage table in docs/factory-analysis.md section 3, P9
("The stage pipeline"), e.g. `Stage: build (34/50 tickets), Next: factory run .` Lane B. Closes #19.

**Blocked by:** None (can start immediately)

**Status:** todo

## Tasks

- [ ] Implement the stages with their entry and exit checks
  - src/factory/bootstrap.py next_step()
  - stages that need data the Factory lacks may stay coarse; say which in the decision log
- [ ] Print the stage line in factory status
  - src/factory/cli.py cmd_status()

## Acceptance

- [ ] next_step() and factory status follow the stage table
- [ ] Tests cover each stage; make test and make lint pass
