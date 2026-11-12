# Plan: local stand-ins and sandboxed Sessions

Written 2026-11-12. Based on web research on that date; links are in the "Sources" section. Nothing here is built yet.

## Answers in short

- **Sandbox the Sessions: yes.** A Run starts unattended `claude -p` Sessions on the host with edit rights. Anthropic
  itself says the built-in per-command sandbox is "not sufficient for fully unattended runs". A microVM (Docker
  Sandboxes, `sbx`) gives each Session its own kernel, a private Docker daemon, a deny-by-default network and no raw
  credentials inside.
- **Local stand-ins: yes, with a limit.** They remove "deploy and wait" from the build loop. In terminal-task-tracker
  that loop cost about a day (2026-10-17: 12 pasted errors) plus at least 6 red CI runs. They cannot emulate IAM,
  billing, quotas, real auth tokens or the image architecture, so one real dev deploy plus `make smoke` stays the exit
  check of the deploy stage.
- **Can the Factory use them: yes, cheaply.** To the Factory they are only "start these before the checks and pass these
  env vars". No Session needs to know more.

## What to use (owner's stack)

| Need                              | Use                                                                                                | Avoid, and why                                                           |
| --------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| GitHub Actions                    | `act` (v0.2.97, MIT)                                                                               | n/a. It is approximate: runner images, cache and OIDC differ             |
| Firebase Auth, Firestore, Storage | Firebase Emulator Suite (`firebase-tools` 15.36)                                                   | Expecting real IAM or Identity Platform behaviour: not emulated          |
| GCS, Pub/Sub, other GCP           | `fake-gcs-server`, `gcloud beta emulators`; `floci-gcp` (MIT, v0.12) when many services are needed | `floci-gcp` is young (v0.x); try it on one project first                 |
| Postgres (Neon)                   | a plain `postgres:17` container                                                                    | Neon Local: it is a proxy to cloud Neon, not a local database            |
| AWS                               | `floci` (MIT, drop-in for LocalStack's port 4566)                                                  | LocalStack OSS is archived; the free tier is for non-commercial use only |
| S3                                | `floci` S3                                                                                         | MinIO: the repo is archived                                              |
| Mail, Stripe, any HTTP API        | Mailpit, `stripe-mock`, WireMock                                                                   |                                                                          |
| Terraform                         | `terraform validate`, `tflint`, `terraform test` with `mock_provider` (1.7+)                       | `tflocal`: AWS and LocalStack only                                       |
| Cloud Run                         | `docker run` of the image built with `--platform linux/amd64`                                      | no official emulator exists                                              |

## Steps

Each step is one ticket of about 5 files or 200 lines, test-first, with fake `claude` and `gh` like
`tests/test_run_e2e.py`.

1. **Probe, owner go-ahead, about $0.05.** Add `experiments/probe_sandbox.sh` to `experiments/`. It runs the existing
   print-mode probe inside `sbx` (clone mode) and inside `srt`. It records whether `claude -p`, `git commit` and a
   `make test` that starts a Docker container work, and how long startup takes.
   - Acceptance: the docstring states the answer per tool.
   - Why first: headless `claude -p` under `sbx` is not documented, so the plan's shape depends on this result.
2. **`sandbox` setting.** In `config.py`, add `sandbox = "none" | "srt" | "sbx"`, default `none`.
   - In `claude.py` `session_command()`, prefix the command with the wrapper. `run.py` `preflight()` refuses to start
     when the tool is missing (`shutil.which`).
   - For `srt`, also refuse when its settings allow unsandboxed commands (fail-open).
   - Tests: the exact command for each mode, and a refusal when the tool is missing.
3. **`services` setting.** In `config.py`, add `services = "docker compose up -d --wait"` (optional) and an `[env]`
   table.
   - `run.py` runs `services` once before the first Ticket, passes `env` to every Session and check, and runs
     `docker compose down` at the end of the Run, including after a failure.
   - Tests: the order of calls (services, sessions, checks, teardown), and that a failing `services` stops the Run
     before any money is spent.
4. **`factory init` detects the stand-ins.** In `config.py` `template()`:
   - When `compose.yaml` exists, write `services` and the known env vars (`FIREBASE_AUTH_EMULATOR_HOST`,
     `FIRESTORE_EMULATOR_HOST`, `STORAGE_EMULATOR_HOST`, `PUBSUB_EMULATOR_HOST`, `DATABASE_URL`) as comments.
   - When `.github/workflows/` exists, add `act` to `checks` as a comment. This also closes P4 of
     `docs/factory-analysis.md`.
   - Tests: the template output for each fixture layout.
5. **The spec asks for stand-ins.** In `templates/` (from the first slice), add a "Local stand-ins" section to the spec
   template: each external service maps to its stand-in from the table above, or to "none: owner checks by hand".
   - The `to-tickets` rules then make the first ticket of any project with services "`compose.yaml` and `make dev` with
     every stand-in up".
   - Acceptance: a planning-rules test that greps the new line.
6. **The deploy stage keeps one real check.** No code: the stage table in `docs/factory-analysis.md` already ends deploy
   with `make smoke` against the live URL. Add a sentence there that the same `make smoke` must first pass against
   `compose`.

Order: 1, then 2 and 3 (they are independent, so they can run in parallel worktrees), then 4, then 5. Decisions go in
`docs/DECISION-LOG.md` with each step.

## Not decided (owner)

- Whether a Run may need Docker Hub or npm access inside `sbx`. That sets the network policy (Balanced or Locked).
- Whether `sandbox = "sbx"` becomes the default once step 1 passes.

## Sources

- Claude Code sandboxing: <https://code.claude.com/docs/en/sandboxing>, comparison
  <https://code.claude.com/docs/en/sandbox-environments.md>; `srt`:
  <https://github.com/anthropic-experimental/sandbox-runtime>
- Docker Sandboxes: <https://docs.docker.com/ai/sandboxes/>, <https://docs.docker.com/ai/sandboxes/security/>
- floci: <https://github.com/floci-io/floci>, <https://floci.io/gcp>; LocalStack archive:
  <https://github.com/localstack/localstack>; MinIO archive: <https://github.com/minio/minio>
- Firebase emulators: <https://firebase.google.com/docs/emulator-suite>; Neon Local:
  <https://neon.com/docs/local/neon-local>; `fake-gcs-server`: <https://github.com/fsouza/fake-gcs-server>
- Terraform tests: <https://developer.hashicorp.com/terraform/language/tests>; `act`: <https://github.com/nektos/act>
