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
