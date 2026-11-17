# `dev` deploys on every push to `main` without a click

## Context

The Owner's rule says anything that creates cloud resources or costs money needs the Owner's go-ahead. A `dev` deploy on
every merge costs a little each time, and with `merge = "green"` merges happen unattended.

## Decision

`dev` deploys automatically. The go-ahead is given once, when the Owner creates the `dev` environment, its credentials
and the infra; before that the `dev` job fails on missing credentials and deploys nothing. Infra changes
(`terraform apply`) stay Owner-run Tickets, skipped by `skip_pattern`. Only `prd` waits for a click.

## Consequences

- Every merge gets a real deploy and `make smoke` before anyone is asked to approve prd.
- A Run with `merge = "green"` deploys `dev` several times in a row; the Owner bounds the cost in the cloud budget, not
  in the Factory.
- No separate staging environment (YAGNI for one Owner and small Projects).
