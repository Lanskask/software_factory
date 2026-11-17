# Software Factory

An unattended loop that takes a Project from a Spec to reviewed-ready pull requests, one Ticket at a time, without the
owner in the loop except at planning and review.

## Language

**Factory**: The tool itself, independent of any Project. _Avoid_: harness, runner, pipeline

**Project**: The git repository the Factory works on. _Avoid_: repo, target, workspace

**Owner**: The human who plans with the Factory and reviews its pull requests. _Avoid_: user, operator

**Spec**: The document describing what the Project should become; the source Tickets are cut from. _Avoid_: PRD, design
doc, plan

**Ticket**: One unit of work small enough for one Session, with a done state and the Tickets that block it. _Avoid_:
issue, task, story

**Ready Ticket**: A Ticket not yet done whose blocking Tickets are all done.

**Blocked Ticket**: A Ticket a Session gave up on, which needs the Owner before anything that depends on it can start.
_Avoid_: failed ticket

**Planning**: The interactive phase where the Owner and the Factory produce a Spec and its Tickets.

**Run**: One unattended pass of the Factory over a Project's Ready Tickets, until none are left or the failure limit is
hit.

**Session**: One fresh agent conversation that works on exactly one Ticket.

**Brief**: The short record a finished Ticket leaves of what it produced.

**Handoff**: The note a Session leaves for the next one: loose ends, open questions, skipped work. _Avoid_: progress
file

## Deploy

**Environment**: A place a Project runs, `dev` or `prd`, each with its own credentials. _Avoid_: stage (a stage is a
step of the Factory's pipeline), staging

**Promotion**: Moving one build that already passed `dev` on to `prd`, unchanged. _Avoid_: release, deploy PR, merge to
stable

**Deploy Approval**: The Owner's click that lets a waiting Promotion reach `prd`; the only human step of a deploy.
_Avoid_: deploy PR approval, sign-off

**Smoke check**: The short check against a live Environment right after a deploy, the Project's `make smoke`. _Avoid_:
health check, e2e

**Deploy PR**: Rejected: a pull request into a `stable` branch as the prd gate. Use Deploy Approval. _Avoid_ the term.

**Stable branch**: Rejected: a long-lived branch whose head is what runs on `prd`. Use Promotion. _Avoid_ the term.
