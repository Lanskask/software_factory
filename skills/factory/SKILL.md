---
name: factory
description:
  Use when the user wants to run the Software Factory on a project, "run the factory", plan or implement tickets
  unattended, check what stage a project is at, or open stacked draft PRs from tickets. Covers the `factory` CLI
  commands and its cost rules.
---

# Software Factory

`factory` plans a git Project once, then implements every Ticket unattended, one fresh `claude -p` session each, with a
stacked draft PR per Ticket. It never merges. Each Session is separate from this one and shares no context.

## Commands (`PROJECT` is the repo path)

| Command                              | Cost | What it does                                                         |
| ------------------------------------ | ---- | -------------------------------------------------------------------- |
| `factory bootstrap PROJECT`          | free | write `.factory/config.toml`, create the tickets folder, print stage |
| `factory plan PROJECT [--spec FILE]` | paid | interactive: bootstrap docs, grill, spec, review, tickets            |
| `factory run PROJECT --dry-run`      | free | next Ticket and its exact `claude` command                           |
| `factory run PROJECT`                | paid | implement every READY Ticket, review it, open draft PRs              |
| `factory status PROJECT`             | free | Tickets, Blocked Tickets, loose ends                                 |

## Rules

- Start with `factory bootstrap PROJECT` and follow the "Next:" line it prints.
- `factory plan` is interactive: it cannot run inside another Claude session. Tell the user to run it themselves.
- `factory run` spends money (defaults: $5 per implementation, $2 per review, 10 Tickets). Always run `--dry-run` first,
  show the user the command, and wait for their go-ahead before the real run.
- Run it in the background and tell the user where the logs are: `PROJECT/.factory/logs/` (stream-json).
- After a run, read `PROJECT/.factory/LOOSE-ENDS.md` and `PROJECT/.factory/blocked/` and report them. A `[high]` item
  stopped the Run on purpose.
- Requires a clean git tree on `base_branch` (default `main`), and `gh` logged in for the draft PRs.
