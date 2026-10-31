# Software Factory

Point it at a git Project. You plan with Claude once (Spec and Tickets); then the Factory implements every Ticket
unattended, one fresh Claude Code session each, and opens a stacked draft pull request per Ticket. It never merges.
Terms are defined in [GLOSSARY.md](GLOSSARY.md), decisions and their reasons in
[docs/DECISION-LOG.md](docs/DECISION-LOG.md).

## Install

```bash
make setup      # dev environment
make install    # global `factory` command (uv tool, editable)
```

Needs `claude`, `gh` (logged in), `git`, `python3`, and the plugins
[`mattpocock-skills`](https://github.com/mattpocock/skills),
[`egm`](https://github.com/google/elephant-goldfish-model/tree/main) and
[`agent-skills`](https://github.com/addyosmani/agent-skills).

## Use

```bash
factory bootstrap ~/code/app        # init + tickets folder, then prints the stage and the next command
factory install-skill               # copy the `factory` skill into ~/.claude/skills
factory init ~/code/app             # .factory/config.toml and .gitignore lines; edit `checks`, then commit
factory plan ~/code/app             # no Spec: bootstrap, grill, to-spec, review, to-tickets (interactive)
factory plan ~/code/app --spec docs/spec.md   # a Spec exists: bootstrap, review, to-tickets
factory run ~/code/app --dry-run    # next Ticket and its exact claude command; spends nothing
factory run ~/code/app              # the unattended Run
factory status ~/code/app           # Tickets, Blocked Tickets, loose ends
```

If the Project already has Tickets in the `/to-tickets` format, skip `plan`.

## What a Run does per Ticket

1. Branch `factory/<num>-<slug>` from the last Ticket that reached a pull request (or the current branch).
2. Implementation Session: `/goal` with the `implement`, `tdd` and `diagnosing-bugs` skills. It commits, ticks the
   tasks, marks the Ticket done with a Brief, and writes a Handoff to `.factory/handoffs/<num>.md`.
3. The Factory checks for itself: Ticket done, clean tree, new commits, Handoff written, every `checks` command exits 0.
4. Review Session, fresh, cannot edit files, may run the `checks`: `code-review` (plus `security-and-hardening` where it
   applies), ending in `VERDICT: PASS|FAIL`. A FAIL gets one fix Session and another review.
5. The Factory runs `git push` and `gh pr create --draft`, with the previous Ticket's branch as the base.
6. The Handoff is appended to `.factory/LOOSE-ENDS.md` (also for a Blocked Ticket, and before the push). A `[high]` item
   does not stop the Run: a read-only Session on `resolve_model` (default `opus`, with web research) decides what to do,
   its answer goes to `.factory/resolutions/` and `LOOSE-ENDS.md`, and the next Ticket's Session does the steps marked
   `NOW` first. If the resolver itself fails, the Run stops.

A Session's BLOCKED claim does not override the checks: if the Ticket is done and every check passes, the claim becomes
a `[high]` loose end instead. Sessions load no MCP servers (`--strict-mcp-config`).

Every review FAIL and every Blocked Ticket adds a line to `.factory/LESSONS.md`; later Tickets' goals tell their
Session to read it first.

A Ticket that fails any step becomes Blocked: the reason goes to `.factory/blocked/<num>.md`, its work stays committed
on its unpushed branch, and Tickets that depend on it are not run. Two Blocked Tickets stop the Run. Delete the file to
let a later Run retry (rename the old branch first).

Tickets whose text mentions a go-ahead or cloud tooling (`skip_pattern`) are skipped. Sessions cannot push, merge,
switch branches or run `gh`; protect `main` on GitHub as the real lock.

## Cost and time

Defaults per Ticket: implementation up to $5, each review up to $2, each Session up to 90 minutes. Up to 10 Tickets per
Run. Override in `.factory/config.toml` or with `--budget-usd`, `--timeout-minutes`, `--max-tickets`, `--max-blocked`.
Session logs (stream-json) are in `.factory/logs/`.

## Develop

```bash
make test       # fake claude and gh, real git: no money, no network
make lint       # ruff and ty
make probe      # re-run the paid print-mode probe (about $0.03)
```
