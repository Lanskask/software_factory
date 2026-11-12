# 01: Build the eval fixture (slugify-cli)

**What to build:** A small Python `slugify-cli` fixture Project that the Factory can be run on to score a change, plus a
script that scores a finished Run. Build only: this Ticket runs no paid Session; the 3 paid repeats are a later step the
Owner starts. Lane A. Closes #32.

**Blocked by:** None (can start immediately)

**Status:** todo

## Tasks

- [ ] Write the fixture Project with a spec and 4 Tickets plus 1 trap Ticket that contradicts the spec
  - evals/slugify-cli/ (fixture), in the /to-tickets format with tickets.py
  - trap: the review should FAIL or Block it
- [ ] Keep hidden acceptance tests outside the fixture; a script copies them in after the Run and runs them
  - evals/hidden/slugify-cli/
- [ ] Write the scorer: one JSON line per run
  - fields: tickets done/blocked, checks green, hidden tests passed/total, review-verdict agreement, cost, minutes, fix
    Sessions, interventions
  - read cost and Session counts from .factory/logs/*.jsonl of the run
- [ ] Document in README how to run the eval (the 3 repeats on haiku/sonnet, about $0.5 per Ticket) and add a make target

## Acceptance

- [ ] The fixture has 4 Tickets and 1 trap Ticket that contradicts the spec
- [ ] Hidden acceptance tests live outside the fixture and are copied in only after a Run
- [ ] The scorer prints one JSON line per run with every field above; a test runs it on a canned run directory
- [ ] make test and make lint pass
