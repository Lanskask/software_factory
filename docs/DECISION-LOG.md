# Decision log

## 2026-10-30 Own Python CLI on the host, not sandcastle

Reason: owner's requirement and a measured fact. Sandcastle runs each agent in Docker, where `~/.claude` (skills,
plugins, hooks) is absent unless mounted, and it is configured per repo in TypeScript. The Factory must use the owner's
installed skills and work across Projects. Sandcastle's ideas (completion signal, idle timeout, branch strategy) are
borrowed instead.

## 2026-10-30 The Factory pushes and opens draft pull requests, never merges

Reason: owner's requirement. The Factory process runs `git push` and `gh pr create --draft`; the Session is not given
push permission, so an agent cannot push work the Factory has not checked.

## 2026-10-30 A failed Ticket is marked Blocked and the Run continues

Reason: owner's requirement. The Run skips every Ticket that depends on a Blocked Ticket and stops after N Blocked
Tickets.

## 2026-10-30 Handoff is an uncommitted file; the Brief stays in the Ticket

Reason: owner's requirement. Loose ends do not belong in pull requests; what a Ticket produced does.

## 2026-10-30 Planning is interactive; the Run is unattended

Reason: measured fact. Every planning skill the owner named (`grill-with-docs`, `to-spec`, `to-tickets`,
`egm-brainstorm`, `egm-draft`, `egm-review-loop`) has `disable-model-invocation: true`, so an agent cannot call them;
only the Owner can.
