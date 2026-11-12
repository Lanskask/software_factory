# 13: Add an optional design stage and design checklist

**What to build:** An optional design stage in Planning with a design checklist. See docs/factory-analysis.md section 3,
P6. Lane B. Closes #16.

**Blocked by:** None (can start immediately)

**Status:** todo

## Tasks

- [ ] Add an optional design stage to chain()
  - src/factory/plan.py chain(); on when interview Q7 says there is a UI
- [ ] Write the design checklist
  - src/factory/templates/design-checklist.md
  - 16 px margin, a button for every hotkey, no hotkey help on phones, labelled boards, Penpot call rules
- [ ] Exit check: every UI Ticket has a Design: line

## Acceptance

- [ ] plan.py chain() has an optional design stage
- [ ] templates/design-checklist.md has the five rules
- [ ] The stage exits only when every UI Ticket has a Design: line
- [ ] Tests cover it; make test and make lint pass
