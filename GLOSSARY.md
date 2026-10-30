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
