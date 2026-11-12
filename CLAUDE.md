## Agent skills

### Issue tracker

Issues and specs are local markdown files under `.scratch/<feature-slug>/`; tickets live in its `tickets/` folder. A
Project that already has a folder holding `tickets.py` (for example `.scratch/task-tracker/issues/`) keeps it:
`factory init` writes that folder into `tickets_dir`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See
`docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
