# Owner answers

The questions only the owner can answer, asked once at the start of Planning. Each has a default: an empty answer means
the default holds. Later sessions read this file and never ask these questions again. The Planning session also appends each answer to `docs/DECISION-LOG.md`.

## 1. Idea and first user

What is the idea, who is the first user, and what must v1 do (the MVP cut)?

Default: none, this one must be answered.

Answer:

## 2. License and openness

Private or commercial? Open source (which license) or closed?

Default: private, closed source, no license file.

Answer:

## 3. Hosting and money

Which cloud or host? What is the hard monthly cost cap? Free tier only?

Default: local only, no cloud; if hosted later, free tier only and a cap of $0 a month.

Answer:

## 4. Data sensitivity

What data must be end-to-end encrypted, what may the server see, and how long is data kept?

Default: no personal data; nothing encrypted beyond TLS; no retention limit.

Answer:

## 5. Identity

Who signs in, and with which identity provider?

Default: no sign-in (single user, local).

Answer:

## 6. Stack

Which parts of the owner's default stack do not fit this project, and what replaces them?

Default: the owner's defaults (from the global `CLAUDE.md`) with no overrides.

Answer:

## 7. Clients and UI

Which clients (CLI, TUI, web, mobile)? Does a design stage run before UI tickets? Which style and palette?

Default: CLI only, no design stage.

Answer:

## 8. Merge policy

May the Factory merge a pull request after its review passes and CI is green?

Default: never; the owner merges.

Answer:

## 9. External tracker

Should tickets be mirrored to an external tracker (Linear, GitHub issues)?

Default: none; local tickets only.

Answer:
