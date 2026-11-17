# Deploy stage: grill of the `stable` branch idea

Written 2026-11-17 with the `grill-with-docs` skill. Nobody was available to answer, so the agent played the Owner and
answered each question from the repo (README, `docs/factory-analysis.md` P7 and P9, `docs/DECISION-LOG.md`, the Owner's
`CLAUDE.md`) and from common practice. Facts about GitHub marked "unverified" come from memory, not from a run.

## The idea as proposed

Code reaches production (prd) only after a human approval. A long-lived `stable` branch controls prd: a pull request
`main` -> `stable` titled "Deploy to PRD" is opened, someone approves and merges it, and the merge starts an automatic
deploy.

## Outcome in short

- Keep the goal (human approval before prd, automatic deploy after it, a readable list of what goes out).
- Drop the `stable` branch and the Deploy PR. The gate is a GitHub Environment `prd` with the Owner as required
  reviewer, on a deploy workflow that runs on every push to `main`: build once, deploy `dev`, `make smoke` on `dev`,
  wait for approval, deploy the same build to `prd`, `make smoke` on `prd`. See ADR 0001.
- The Factory writes the workflow template and shows deploy state in `factory status`. It never merges to a deploy
  branch, triggers a deploy, approves one or runs a deploy command. See ADR 0002.
- `dev` deploys without a click on every push to `main`; the Owner's go-ahead is given once, when the Owner sets up the
  `dev` environment and its credentials. See ADR 0003.

## Round 1: the gate itself

### Q1 Who approves, and can that person approve a Deploy PR?

The Owner is the only human. GitHub does not let a pull request's author approve it, and the Factory opens pull requests
with the Owner's `gh` login, so the Owner would be the author of every Deploy PR.

Answer: a required approval on the Deploy PR is impossible for this Owner. It would end as an admin merge that bypasses
the rule, so the "approval" would be just the merge click. A GitHub Environment's required reviewer can approve a run
the reviewer started, unless "prevent self-review" is on (unverified: check on the first Project). This alone moves the
gate off the pull request.

### Q2 Branch per environment (`stable`) or promotion of one build through environments?

Options:

- A. `stable` branch, merge triggers deploy (the idea).
- B. Tag or `workflow_dispatch`, the prd job sits behind Environment `prd` with a required reviewer.
- C. One workflow per push to `main`: build, `dev`, then the `prd` job behind Environment `prd`.

Drawbacks of A, each real:

- A GitHub merge never fast-forwards: a merge commit or squash makes a new SHA on `stable`, so prd runs a commit CI
  never tested, and a rebuild, not the build `dev` ran. Squash also makes `stable` diverge from `main`, so the next
  Deploy PR shows old commits again or conflicts.
- A hotfix made on `stable` must be merged back to `main`, or the next deploy drops it. Two long-lived branches drift.
- `merge = "green"` already calls `gh pr merge --auto`. One wrong base branch and the Factory auto-merges a Deploy PR,
  which deploys prd with nobody's approval.
- Secrets: with A, prd secrets must be readable by any workflow run on `stable`. Environment secrets are handed only to
  the job that passed the approval.

What A has that B and C lack: a diff of what goes out. C gets it back with a compare link between the SHA live on `prd`
(from the GitHub deployments record) and the SHA waiting for approval, printed by `factory status`.

Answer: C. B stays as the manual path for rollback (Q8). Recorded in ADR 0001.

### Q3 What is a "deploy" to the Factory: something it does, or something it watches?

Answer: something it watches. The deploy runs in GitHub Actions, outside the Factory. The Factory's jobs are: write the
workflow template once, print the state and the next command, and keep Sessions from deploying from the host. Recorded
in ADR 0002.

## Round 2: what hangs off C

### Q4 How does the Factory stay unable to merge or deploy by itself?

The Factory runs `gh` with the Owner's token, so GitHub cannot tell the Factory from the Owner. Any rule GitHub enforces
(branch protection, Environment reviewers) can in principle be passed with that token through `gh api`.

Answer, in layers:

1. The Factory process has no code path that calls `gh workflow run`, `gh api .../pending_deployments`, `gh pr merge`
   for a non-Ticket PR, `make deploy` or a cloud CLI. A test with the fake `gh` pins the full list of `gh` calls a Run
   makes.
2. Sessions already cannot run `gh`, `git push` or `git merge` (`NEVER` in `run.py`). Add the deploy commands: a Session
   runs on the host, where the Owner's `gcloud` and `fly` credentials live, so `make deploy` from a Session would reach
   prd today. Deny `Bash(make deploy*)`, `Bash(gcloud *)`, `Bash(terraform apply*)`, `Bash(terraform destroy*)`,
   `Bash(fly *)`, `Bash(modal *)`.
3. Real separation (a GitHub App or a bot account for the Factory, so the Owner's approval is a different identity) is
   left out until a second human or a shared repo appears. Said so in ADR 0002.

### Q5 What comes before prd?

Answer: `dev`, deployed automatically by the same run, then `make smoke` against `dev`. The `prd` job needs both green
jobs. No separate staging: one Owner and small Projects do not pay for a third environment (YAGNI). ADR 0003.

### Q6 Does auto-deploying `dev` break the Owner's rule "anything that creates cloud resources needs a go-ahead"?

Deploying a new revision to an existing service is not creating resources, but it costs a little each time. The Owner
gives the go-ahead once: by creating the `dev` environment, its secrets or Workload Identity binding, and the infra.
Until then the `dev` job fails fast on missing credentials and deploys nothing. Infra changes (`terraform apply`) stay
Owner-run Tickets, skipped by `skip_pattern`. ADR 0003.

### Q7 Smoke check after deploy?

Answer: `make smoke ENV=<env>` right after each deploy job, as `docs/factory-analysis.md` P7 and the spec template's
Deploy preflight already require. A red smoke on `dev` stops the run before the approval. A red smoke on `prd` fails the
run and GitHub mails the Owner. No automatic rollback (YAGNI): the Owner decides, with Q8.

### Q8 Rollback?

Answer: deploy an older SHA through the same gate. The template has `workflow_dispatch` with an input `ref`; the `prd`
job still waits for approval. `factory status` prints the last successful `prd` SHA, so the command is
`gh workflow run deploy.yml -f ref=<sha>`, printed for the Owner, never run by the Factory. The Owner can also re-run an
older run's `prd` job in the Actions page.

### Q9 Hotfixes?

Answer: trunk-based, like everything else: a fix lands on `main` through a normal PR, then goes `dev` -> approval ->
`prd`. With no `stable` branch there is no back-merge to forget.

### Q10 Database migrations?

Answer: expand and contract. A migration runs in the deploy job before the new code and must work with the code that is
live now, so a rollback (Q8) needs no down-migration. A destructive step (drop a column) ships one deploy later. This is
a rule for the spec's Deploy preflight section and for deploy Tickets, not Factory code.

### Q11 Secrets?

Answer: Environment secrets on `dev` and `prd`, and GCP Workload Identity Federation (OIDC) instead of JSON keys where
the cloud supports it. `prd` secrets reach only the job that passed the approval. The Factory never reads or writes
secrets; it prints the `gh` commands to set up the environments.

### Q12 Several merges wait for approval at once. Which one deploys?

Answer: the newest. The `prd` job has `concurrency: deploy-prd` with `cancel-in-progress: false`; GitHub keeps one
pending job per group and cancels the older pending one (unverified for jobs waiting on an Environment: check on the
first Project). Approving deploys everything merged up to that SHA, and the compare link (Q2) shows it.

### Q13 If `stable` were kept anyway, merge commit or squash for the promotion PR?

Answer, for the record: a merge commit, never squash or rebase, so `stable` stays an ancestor of `main` and the next PR
shows only new commits. It still makes a new SHA (Q2), which is one reason the idea was dropped.

## Round 3: the Factory side

### Q14 Stage name and what `bootstrap` and `status` print?

Answer: a new stage `deploy` after `verify` in `next_step()`, shown only when `deploy_environment` is set (a Project
that does not deploy, such as a CLI, keeps ending at `verify`). The Factory has no PR or merge data, so the line stays
coarse:

```text
Stage: deploy (12/12 tickets), Next: merge the PRs, then approve the prd deployment in GitHub Actions
```

`factory status` adds one line from `gh api repos/{owner}/{repo}/deployments?environment=prd`, like the Doctor line:

```text
Deploy: prd at 1a2b3c4 (5 commits behind main), compare: https://github.com/o/r/compare/1a2b3c4...9f8e7d6
```

When `gh` fails or there is no deployment yet, it prints `Deploy: prd unknown` or `Deploy: prd never deployed`, never a
guess.

### Q15 Which config keys?

Answer: one key, `deploy_environment = ""` (default: no deploy stage). Set it to `"prd"` to opt in. No `dev` key: the
template names it, and the Owner edits the workflow. No `deploy_command` key: the workflow calls `make deploy ENV=...`
and `make smoke ENV=...`, the Owner's Makefile convention.

### Q16 What does the Factory create?

Answer: only `.github/workflows/deploy.yml`, from `src/factory/templates/deploy.yml`, written by `factory bootstrap`
when `deploy_environment` is set and the file does not exist, and committed like the other templates. It never creates
the GitHub Environments: it prints the `gh api -X PUT repos/{owner}/{repo}/environments/prd` command with the reviewer
for the Owner to run. No Deploy PR, no tag, no workflow run.

### Q17 What must it never do?

Answer: merge into or push to any deploy branch, push tags, run `gh workflow run`, approve a pending deployment, run
`make deploy`, `terraform apply`, `gcloud`, `fly` or `modal`, or write secrets. Sessions are denied the same commands.

### Q18 Which tests come first (TDD)?

1. `tests/test_config.py`: `deploy_environment` loads, defaults to `""`, rejects a non-string.
2. `tests/test_run_e2e.py`: the implementation Session's `--disallowedTools` holds the deploy denies (Q4 layer 2).
3. `tests/test_run_e2e.py`: the fake `gh` log of a whole Run holds no `workflow run`, `pending_deployments` or
   `pr merge` of a PR whose base is not `base_branch` (Q4 layer 1).
4. `tests/test_bootstrap.py`: `next_step()` returns `deploy` only with `deploy_environment` set and every Ticket done;
   the template is copied only then and never overwrites.
5. `tests/test_doctor.py` style: the Deploy line for a fake deployments response, an empty one and a failing `gh`.
6. A template test: the workflow has `environment: prd` on the prd job, `needs:` on the dev smoke job, and
   `workflow_dispatch` with `ref`.

## Open for the Owner

- Whether Environment required reviewers are available for the Owner's private repos on the current GitHub plan
  (unverified; this repo is public, where they are). If not, the fallback is B: the `prd` job runs only on
  `workflow_dispatch`, and the Owner's own dispatch is the approval.
- Whether a separate GitHub identity for the Factory is worth it (Q4 layer 3).
