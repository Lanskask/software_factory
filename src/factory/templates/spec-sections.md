# Spec sections

Every Spec has these four sections, after its user stories. Write "None." under a section that has nothing, and say
why.

## Alternatives

The options considered for each big choice (language, storage, hosting, libraries), the one chosen, and why the others
lost.

## Risks

What could go wrong (cost, data loss, security, an unproven library, a limit of the platform), how likely it is, and
what the Spec does about it.

## Local stand-ins

For each external service the Project uses (database, auth, storage, queue, mail, payments, other HTTP APIs), the local
stand-in that replaces it while the Factory builds and tests: for example a `postgres` container, the Firebase
emulators, `fake-gcs-server`, Mailpit, `stripe-mock`. Write "none: owner checks by hand" for a service with no
stand-in. A stand-in cannot emulate IAM, billing, quotas or real tokens, so the real dev deploy stays. A Project with no
external services writes "None.".

## Deploy preflight

Checked before the first deploy Ticket runs, one line each with the command that checks it. A Project that does not
deploy writes "None.".

- Billing: on for the cloud project or account, with a budget alert.
- Auth and quota project: the CLI is logged in, and the application-default credentials name a quota project.
- Image architecture: images are built for the platform's CPU (for example `linux/amd64` on Cloud Run, not an arm64
  build from a Mac).
- State bucket: the Terraform state bucket exists before `terraform init`.
- Deletion protection: which resources have it on, and how a Ticket turns it off when it must replace one.
- `make smoke`: the exact command and the live URL it checks. Every deploy Ticket's acceptance ends with it passing.
  The same `make smoke` passes against `compose` before the dev deploy, so a deploy only finds what a stand-in cannot.
