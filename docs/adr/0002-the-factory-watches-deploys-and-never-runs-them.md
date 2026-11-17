# The Factory watches deploys and never runs or approves them

Status: accepted by the Owner on 2026-11-17.

## Context

The Factory runs `gh` with the Owner's token, so GitHub cannot tell a Factory call from the Owner's click: any branch
protection or Environment rule can be passed with that token through `gh api`. Sessions run on the host, where the
Owner's `gcloud` and `fly` credentials live, so a Session's `make deploy` would reach prd today.

## Decision

The Factory writes the workflow template once and reports deploy state. "Never" covers `prd`: with `merge = "green"` the
Factory's merges to `main` already start `dev` deploys unattended (ADR 0003). It never triggers a workflow, approves a
pending deployment, merges or pushes to anything but its own Ticket branches, pushes tags, writes secrets or runs a
deploy or cloud command. Sessions are denied (`DEPLOY_NEVER` in `src/factory/run.py`) `make deploy`, `gcloud`,
`terraform apply`, `terraform destroy`, `fly` and `modal`. A test pins the full list of `gh` calls a Run makes. A
separate GitHub identity for the Factory is left out.

## Consequences

- The guarantee is the Factory's own code and tests, not GitHub. Anyone who changes the Factory can break it; the test
  is what makes that visible.
- A second human or a shared repo is the trigger to give the Factory its own GitHub App or bot account.
- Ticket checks that need a cloud CLI (rare) must run in CI, not in a Session.
