# 03: Add Alternatives, Risks and Deploy preflight to the spec template

**What to build:** Specs written by Planning have Alternatives, Risks and Deploy preflight sections, and deploy Tickets
end in `make smoke`. See docs/factory-analysis.md section 3, P7. Lane A. Closes #17.

**Blocked by:** None (can start immediately)

**Status:** todo

## Tasks

- [ ] Add src/factory/templates/spec-sections.md with the three sections
  - Deploy preflight: billing on, auth and quota project, image architecture, state bucket, deletion protection, the
    exact make smoke
- [ ] Make the planning rules point /to-spec at it and require deploy Tickets to end in make smoke
  - src/factory/plan.py planning_rules()
  - deploy Tickets keep needing the Owner (skip_pattern)

## Acceptance

- [ ] The spec template has the three sections
- [ ] The planning rules require every deploy Ticket's acceptance to end in make smoke
- [ ] Tests cover both; make test and make lint pass
