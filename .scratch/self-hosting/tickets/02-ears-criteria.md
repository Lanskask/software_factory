# 02: Write acceptance criteria in EARS form

**What to build:** Planning writes every acceptance criterion as "When X, the system shall Y", each criterion gets a
test, and the review checks that every criterion has one. Lane A. Closes #33.

**Blocked by:** None (can start immediately)

**Status:** todo

## Tasks

- [ ] Add the EARS rule to the planning rules for /to-tickets
  - src/factory/plan.py planning_rules()
- [ ] Tell the implementation Session to write one test per criterion
  - src/factory/prompts.py
- [ ] Make the review prompt check that every criterion has a test
  - src/factory/prompts.py review prompt

## Acceptance

- [ ] When planning rules are built, the system shall tell /to-tickets to write criteria as "When X, the system shall Y"
- [ ] When a review prompt is built, the system shall ask the reviewer to FAIL a Ticket whose criterion has no test
- [ ] Tests in tests/ cover both; make test and make lint pass
