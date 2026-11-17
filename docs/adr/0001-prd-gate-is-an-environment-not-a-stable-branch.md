# The prd gate is a GitHub Environment approval, not a `stable` branch

## Context

The Owner proposed a long-lived `stable` branch: a pull request `main` -> `stable` titled "Deploy to PRD" is approved
and merged, and the merge deploys prd. The Owner is the only human and the Factory opens pull requests with the Owner's
`gh` login, so the Owner would author every Deploy PR, and GitHub does not let an author approve their own pull request.
A GitHub merge also never fast-forwards, so `stable` gets a new SHA that CI never tested.

## Decision

One deploy workflow runs on every push to `main`: build once, deploy `dev`, `make smoke` on `dev`, then a `prd` job
behind GitHub Environment `prd` with the Owner as required reviewer, deploying the same build, then `make smoke` on
`prd`. No `stable` branch and no Deploy PR. `workflow_dispatch` with a `ref` input covers rollback through the same
gate.

## Consequences

- prd runs exactly the SHA and build that passed `dev`; there is no second branch to drift or back-merge hotfixes into.
- prd secrets are Environment secrets, handed only to the job that passed the approval.
- The pull request's diff view is lost; `factory status` prints a compare link from the live prd SHA instead.
- Environment reviewers on private repos depend on the GitHub plan (unverified). Fallback: the `prd` job runs only on
  `workflow_dispatch`, and the Owner's dispatch is the approval.
