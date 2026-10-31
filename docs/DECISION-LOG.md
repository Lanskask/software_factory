# Decision log

## 2026-10-30 Own Python CLI on the host, not sandcastle

Reason: owner's requirement and a measured fact. Sandcastle runs each agent in Docker, where `~/.claude` (skills,
plugins, hooks) is absent unless mounted, and it is configured per repo in TypeScript. The Factory must use the owner's
installed skills and work across Projects. Sandcastle's ideas (completion signal, idle timeout, branch strategy) are
borrowed instead.

## 2026-10-30 The Factory pushes and opens draft pull requests, never merges

Reason: owner's requirement. The Factory process runs `git push` and `gh pr create --draft`; the Session is denied push
permission, so an agent cannot push work the Factory has not checked.

## 2026-10-30 A failed Ticket is marked Blocked and the Run continues

Reason: owner's requirement. The Run skips every Ticket that depends on a Blocked Ticket and stops after N Blocked
Tickets.

## 2026-10-30 Handoff is an uncommitted file; the Brief stays in the Ticket

Reason: owner's requirement. Loose ends do not belong in pull requests; what a Ticket produced does.

## 2026-10-30 Planning is interactive; the Run is unattended

Reason: measured fact. Every planning skill the owner named (`grill-with-docs`, `to-spec`, `to-tickets`,
`egm-brainstorm`, `egm-draft`, `egm-review-loop`) has `disable-model-invocation: true`, so an agent cannot call them;
only the Owner can.

Measured with `experiments/probe_print_mode.sh` on Claude Code 2.1.314 (2026-10-30): such a skill does run when its
slash command is the first text of a `claude -p` prompt, the Skill tool refuses it inside a session, interview skills in
`-p` end at their first question, and `/goal` works in `-p`.

## 2026-10-30 Tickets use the `to-tickets` file format

Reason: owner's requirement. Blocked-Ticket skipping and the READY state need blocking edges, which only that format
has. See `terminal-task-tracker/docs/ticket-formats.md`.

## 2026-10-30 Planning chain

Reason: owner's requirement. No Spec: `/egm-bootstrap`, `/grill-with-docs`, `/to-spec`, `/egm-review-loop`,
`/to-tickets`. A Spec given: `/egm-bootstrap`, `/egm-review-loop`, `/to-tickets`. Tickets present: no Planning.

## 2026-10-30 Linear branch stack, config in the Project, limits

Reason: owner's requirement. Each Ticket branches from the last done Ticket's branch and its draft PR targets it.
Project settings live in `<project>/.factory/config.toml`; Handoffs in git-ignored `.factory/handoffs/`. Defaults: 2
Blocked Tickets stop a Run, $5 and 90 minutes per Session, 10 Tickets per Run.

## 2026-10-30 User-only skills become model-invocable inside Factory sessions only

Reason: owner's requirement (allow model invocation) and a measured fact. Editing `disable-model-invocation` in the
plugin cache is lost on every plugin update and would let Claude start interviews in all the owner's other sessions. The
Factory copies the skills it needs, without that flag, into `.factory/plugin` and loads it with `claude --plugin-dir`.
Measured 2026-10-30: the copy is listed as `factory:<name>` and the model invoked it.

## 2026-10-30 Skill roles

Reason: best practice, one skill per role so instructions do not conflict. Implement: `implement` (it asks for `tdd` and
a self-review), `diagnosing-bugs` when a check fails. Review, in a separate fresh Session: `code-review` (repo standards
plus the Ticket as spec) and `security-and-hardening` when the diff touches auth, input, secrets or crypto.
agent-skills' `test-driven-development` and `code-review-and-quality` overlap with these and can replace them in
`config.toml`.

## 2026-10-30 Independent review before every pull request

Reason: owner's requirement. After the Factory's own checks pass, a read-only Session reviews the diff and ends with
`VERDICT: PASS|FAIL`. A FAIL gets one fix Session, then another review; still FAIL makes the Ticket Blocked.

## 2026-10-30 Loose ends: in-scope work is never handed off; [high] items stop the Run

Reason: owner's requirement. A Handoff may only hold out-of-scope findings and Owner decisions, each tagged [high] or
[low]. The reviewer treats an in-scope item there as a finding. A [high] item stops the Run after its pull request, so
the Owner reads it before more work is stacked on top. A Session that needs an Owner decision must stop with BLOCKED
instead of guessing.

## 2026-10-30 Blocked state lives in the Factory, not in the Ticket

Reason: measured fact. `tickets.py` knows only todo, in_progress and done. A Blocked Ticket stays not-done, so its
dependents never become READY; the Factory records the reason in git-ignored `.factory/blocked/<num>.md` and commits the
half-done work on the Ticket's branch, which it does not push.

## 2026-10-30 The goal names the exact status command and checks

Reason: measured fact. In live runs `/goal` only worked reliably when its wording named the exact `status` command and
the exact `checks` commands, so the Factory now writes them into the goal text.

## 2026-10-30 Sessions start with `--strict-mcp-config`

Reason: measured fact. Without it, the owner's own MCP servers (some slow or failing to connect) loaded into every
unattended Session. Sessions now see only the MCP servers the Factory passes, which is none.

## 2026-10-30 The Factory's checks outrank a Session's BLOCKED claim

Reason: best practice, trust the objective check over the model's claim. If the Ticket is done and every `checks`
command exits 0, a BLOCKED claim does not block the Ticket. It is recorded as a `[high]` loose end, so the Owner still
reads it and the Run stops after that pull request.

## 2026-10-30 Review Sessions may run the configured checks

Reason: measured fact. In live run 4 the reviewer could not run `make test` (permission refused) and judged from the
diff alone. Review Sessions now get `Bash(<check>*)` for each configured check. They stay unable to edit files or
commit.

## 2026-10-30 The Factory commits the files it writes, and only those

Reason: the Owner's requirement, from the first real test. `factory init` (config and `.gitignore` lines) and the
unattended `/egm-bootstrap` (`EGM_DOC.md` files, which may not commit) left the tree dirty, and `factory run` then
refused to start. The Factory now commits exactly those paths with `git commit -- <paths>`, so the Owner's own staged
or uncommitted work stays untouched. A `.gitignore` that already had the Owner's uncommitted edits is not committed.
Other dirt (tool state like `.serena/cache`) is still the Owner's call: `factory run` lists the files instead.

## 2026-10-30 Every Session the Factory starts gets a `--name`

Reason: the Owner's requirement. Names are `factory <project> <ticket> <kind> <n>`, `factory <project> plan` and
`factory <project> plan-bootstrap`, so the sessions are easy to find in the session list.

## 2026-10-30 A [high] loose end is resolved by an Opus Session instead of stopping the Run

Reason: the Owner's requirement, from the first real Run: a `[high]` item stopped the Run mid-way, with Tickets left and
nobody there to read it. The Factory now starts a read-only Session on `resolve_model` (default `opus`) that checks the
code and the official docs and writes a decision per item (Decision, Steps, When: NOW, LATER or OWNER). The next
Ticket's goal points at it, and steps marked NOW are done first, in their own commits. Read-only because the fix then
goes through the next Ticket's checks and review instead of landing unreviewed. If the resolver fails, the Run still
stops, as before. Every Handoff is logged to `LOOSE-ENDS.md` before the push, and also for Blocked Tickets.

## 2026-10-31 The next Ticket stacks on the newest Factory branch, and publish pushes a missing base

Reason: measured failure in a real Run. A hand-made branch was checked out when `factory run` started, so the Run took
it as the base. Ticket 04 was stacked on it, and `gh pr create` then failed with "Base ref must be a branch" because
origin never had that branch. The base is now the newest unblocked Ticket branch (else `base_branch`), and the Run
switches to it, so the checked-out branch no longer matters. `publish` also pushes the base first when origin lacks it.
Both are tested with a real git origin (see LESSONS.md).

## 2026-10-31 A Run starts by resolving the [high] items its predecessor left

Reason: the Owner's requirement, from the Instagram project: ticket 03 left a `[high]` Turnstile item and the Run that
wrote it stopped (or was interrupted) before the resolver ran. The first Run now takes the Handoff of the Ticket the
stack ends on as `previous`. A `[high]` item with no `.factory/resolutions/<ticket>.md` is resolved first; an existing
resolution is passed on to the next Ticket. `--dry-run` spends nothing, so it never starts the resolver. If the resolver
fails, the Run stops, as it does mid-Run.

## PR title is `type: [NN] Ticket title`, code in the body is backticked (2026-10-31)

- Title: `feat: [08] Page changes for Hosted mode`, taken from the Ticket's `# NN: title` heading. The type is the
  Ticket's optional `**Type:**` line (`test`, `docs`, ...), default `feat`. Reason: the Owner's requirement (Conventional
  Commits style).
- Body: test ids and file paths are wrapped in backticks by `code_quote` (outside code fences and spans), because the
  Sessions write them bare. A heuristic, not a parser: commands such as `make test` are not wrapped.
- The PR stays a draft: the Factory never marks one ready for review (README: "stacked draft pull request per Ticket. It never merges").
