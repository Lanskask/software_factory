# Rules for every session in this Project

Written by `factory bootstrap`. Edit freely; the Factory never overwrites this file.

## Start

The `SessionStart` hook prints `.factory/handoffs/latest.md` when it exists. Pick up from it; do not ask the owner to
paste it again. The owner's standing answers are in `docs/OWNER-ANSWERS.md`: do not ask those questions again.

## Work

- One branch per ticket, named after it. Never commit a ticket's work on the base branch.
- When `.github/pull_request_template.md` exists, the PR body follows it.
- Write the failing test first. Run the project's checks (the `checks` in `.factory/config.toml`) yourself and show
  their output before you say "done".
- An in-scope item you skipped is done now, not listed for later.
- A new idea or an out-of-scope problem becomes one ticket in the Backlog epic, made with the tickets tool
  (`tickets.py new`). Then carry on with the current ticket.
- Never state a fact from memory that you could check: read the code, run the command, or open the docs.
- Name things with their meaning: a ticket by number and title, a board by what it shows, never a bare code.
- In Markdown, everything that is code goes in backticks: paths, commands, flags, functions.
- Never touch anything listed under "Protected" below.

## Protected

Shared data no session may write, wipe or migrate (for example a dev database other people use). Empty until the owner
fills it in.

## End

At session end, write the handoff to `.factory/handoffs/latest.md`: what was done (commits, numbers), what is left, open
questions, and the next step. The next session reads it first.
