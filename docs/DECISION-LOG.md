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

## 2026-10-30 The goal names the exact status command and checks

Reason: measured fact. In live runs `/goal` only worked reliably when its wording named the exact `status` command and
the exact `checks` commands, so the Factory now writes them into the goal text.

## 2026-10-30 Sessions start with `--strict-mcp-config`

Reason: measured fact. Without it, the owner's own MCP servers (some slow or failing to connect) loaded into every
unattended Session. Sessions now see only the MCP servers the Factory passes, which is none.

## 2026-10-30 The Factory's checks outrank a Session's BLOCKED claim

Reason: best practice, trust the objective check over the model's claim. If the Ticket is done and every `checks`
command exits 0, a BLOCKED claim does not block the Ticket. It is recorded as a `[high]` loose end, so the Owner still
reads it and the Run stops after that pull request.

## 2026-10-30 Review Sessions may run the configured checks

Reason: measured fact. In live run 4 the reviewer could not run `make test` (permission refused) and judged from the
diff alone. Review Sessions now get `Bash(<check>*)` for each configured check. They stay unable to edit files or
commit.

## 2026-10-30 The Factory commits the files it writes, and only those

Reason: the Owner's requirement, from the first real test. `factory init` (config and `.gitignore` lines) and the
unattended `/egm-bootstrap` (`EGM_DOC.md` files, which may not commit) left the tree dirty, and `factory run` then
refused to start. The Factory now commits exactly those paths with `git commit -- <paths>`, so the Owner's own staged or
uncommitted work stays untouched. A `.gitignore` that already had the Owner's uncommitted edits is not committed. Other
dirt (tool state like `.serena/cache`) is still the Owner's call: `factory run` lists the files instead.

## 2026-10-30 Every Session the Factory starts gets a `--name`

Reason: the Owner's requirement. Names are `factory <project> <ticket> <kind> <n>`, `factory <project> plan` and
`factory <project> plan-bootstrap`, so the sessions are easy to find in the session list.

## 2026-10-30 A [high] loose end is resolved by an Opus Session instead of stopping the Run

Reason: the Owner's requirement, from the first real Run: a `[high]` item stopped the Run mid-way, with Tickets left and
nobody there to read it. The Factory now starts a read-only Session on `resolve_model` (default `opus`) that checks the
code and the official docs and writes a decision per item (Decision, Steps, When: NOW, LATER or OWNER). The next
Ticket's goal points at it, and steps marked NOW are done first, in their own commits. Read-only because the fix then
goes through the next Ticket's checks and review instead of landing unreviewed. If the resolver fails, the Run still
stops, as before. Every Handoff is logged to `LOOSE-ENDS.md` before the push, and also for Blocked Tickets.

## 2026-10-31 Every goal carries "Or stop after 60 turns"

Reason: documented behavior. `/goal` has no turn limit of its own; the docs say to put a turn or time clause in the
condition. The $ budget and the 90-minute timeout stay as the hard stops; the clause ends a looping Session earlier, and
the Factory's own checks then decide whether the Ticket is done or Blocked. 60 is a guess, not measured: tune it after a
few real Runs (the stream-json logs in `.factory/logs/` show the turn counts).

## 2026-10-31 `.factory/LESSONS.md`: one line per review FAIL or Blocked Ticket, read by later Tickets

Reason: best practice. The "Stop Babysitting Your Agent" talk says a fix that is not saved where the next run reads it
evaporates with the session, and Anthropic's long-running-agent harness keeps a progress file for the same reason. A
Session starts fresh, so a mistake caught in Ticket 01 (a review FAIL, a Blocked reason) was repeated in Ticket 03. The
Factory writes the whole finding collapsed to one line, at most 300 characters, and points the next goal at the file.
Git-ignored like the rest of `.factory/`. Not measured yet: whether it lowers the FAIL rate; compare over a few real
Runs.

Changed after an `egm-review` of the first version (three reviewers, 2026-10-31): the file is deleted at the start of
each Run (a stale line warns about a mistake the Owner already fixed); the goal calls it "unverified notes, never
instructions, this Ticket's text wins" (the lines are model output and check output, so they are an injection path);
only the first line was kept, which for `check ... failed:` lost the detail; the last failing review round no longer
writes the lesson twice. Not done at that point: a structured record, dropping infrastructure Blocked reasons, and
marking a lesson resolved when the fix round passes. They are done in the next entry.

## 2026-10-31 Lessons get a status, infrastructure Blocked reasons are dropped

Reason: the Owner asked for the three items left out above. A line is now `- <num> <slug> [open] <reason>`, the minimal
structured record (ticket, status, reason) that stays readable markdown for the Session. A stale branch or a crashed
review Session is not recorded: it says nothing about the code. A review FAIL lesson becomes `[resolved]` when the next
review of that Ticket PASSes (not when the fix Session's checks pass: the review is the evidence the finding is gone).
Blocked lessons stay `[open]`. Other reasons from `verify()` (such as a crashed implement Session) are still recorded;
telling them apart from code failures needs a typed reason. Not measured: whether it lowers the FAIL rate.

## 2026-11-12 `checks` start as what CI runs; preflight warns about an unbuilt Dockerfile

Reason: measured, in `docs/factory-analysis.md` (P4): at least 6 failures surfaced only on GitHub or at deploy because
local checks were weaker than CI. `factory init` now copies the `make X` lines of `.github/workflows/*.yml` into
`checks`, when X is a Makefile target, ahead of the known names (`test`, `lint`, ...). Targets named like `setup`,
`install`, `deploy`, `release`, `publish` or `smoke` are left out: they install or ship, they do not check. When a
`Dockerfile` exists and no check runs `docker` (directly or in its make recipe), `factory run` prints a warning and goes
on: a refusal would stop Projects whose image is built only at deploy.

## 2026-11-12 `factory bootstrap` writes a rules `CLAUDE.md`, a handoff hook and the owner interview

Reason: measured, in `docs/factory-analysis.md` (the owner's 311 typed messages while building terminal-task-tracker):
72 were design or product answers, 41 relayed a handoff into a new session, 27 repeated a standing rule. Bootstrap now
copies three templates from `src/factory/templates/` when the Project lacks the file: `CLAUDE.md` (generic standing
rules, handoff at `.factory/handoffs/latest.md`), `.claude/settings.json` (a `SessionStart` hook that prints that
handoff) and `docs/OWNER-ANSWERS.md` (the questions only the owner can answer, each with a default). Planning step 0
asks only the unanswered ones, in one batch. An existing file is never overwritten; an existing `CLAUDE.md` gets one
line saying the template was not applied. The templates get their own commit, with `git add -f` because a global
excludes file often ignores `.claude/`. Not measured yet: how many messages this saves on the next project.

## 2026-10-31 The next Ticket stacks on the newest Factory branch, and publish pushes a missing base

Reason: measured failure in a real Run. A hand-made branch was checked out when `factory run` started, so the Run took
it as the base. Ticket 04 was stacked on it, and `gh pr create` then failed with "Base ref must be a branch" because
origin never had that branch. The base is now the newest unblocked Ticket branch (else `base_branch`), and the Run
switches to it, so the checked-out branch no longer matters. `publish` also pushes the base first when origin lacks it.
Both are tested with a real git origin (see LESSONS.md).

## 2026-10-31 A Run starts by resolving the [high] items its predecessor left

Reason: the Owner's requirement, from the Instagram project: ticket 03 left a `[high]` Turnstile item and the Run that
wrote it stopped (or was interrupted) before the resolver ran. The first Run now takes the Handoff of the Ticket the
stack ends on as `previous`. A `[high]` item with no `.factory/resolutions/<ticket>.md` is resolved first; an existing
resolution is passed on to the next Ticket. `--dry-run` spends nothing, so it never starts the resolver. If the resolver
fails, the Run stops, as it does mid-Run.

## PR title is `type: [NN] Ticket title`, code in the body is backticked (2026-10-31)

- Title: `feat: [08] Page changes for Hosted mode`, taken from the Ticket's `# NN: title` heading. The type is the
  Ticket's optional `**Type:**` line (`test`, `docs`, ...), default `feat`. Reason: the Owner's requirement (Conventional
  Commits style).
- Body: test ids and file paths are wrapped in backticks by `code_quote` (outside code fences and spans), because the
  Sessions write them bare. Commands are wrapped too: `make` with a known target (not "make sure"), `uv run X`, `uvx X`. A heuristic, not a parser.
- The PR stays a draft: the Factory never marks one ready for review (README: "stacked draft pull request per Ticket. It never merges").

## The eval scores a Run from its files, hidden tests come in only afterwards (2026-11-12)

- The scorer (`factory.score`) reads only the run directory: Ticket states, `.factory/blocked/`, the result events of
  `.factory/logs/*.jsonl` (cost, `duration_ms`, review verdicts) and the config's checks. Reason: the Factory already
  writes all of it, so scoring needs no new hooks in the Run.
- Hidden tests are copied in after the Run, run with the scorer's own pytest (the fixture is stdlib-only) and removed
  again. `hidden_total` comes from `expected.json`, so a run whose code does not even import scores 0 of 15, not 0 of 1.
- Review agreement: the trap Ticket should end FAIL or Blocked, every other reviewed Ticket PASS; Tickets the Run never
  reached are not judged.
- Interventions cannot be seen in the logs, so the Owner writes one `- ` line per intervention into
  `.factory/interventions.md`. Reason: an honest count beats a guessed one.
- `evals/new_run.sh` gives each run a local bare `origin` and a `gh` stand-in, so the Run publishes without GitHub.

## Opt-in `merge = "green"` auto-merges the bottom of the stack (2026-11-12)

- Default `merge = "never"` keeps the 2026-10-30 rule: draft pull requests, never merged. Any other value than `never`
  or `green` is a config error. Reason: Owner's requirement (docs/factory-analysis.md P8, issue #18).
- With `green`, after review PASS and `gh pr create`, the Factory runs `gh pr ready` and then
  `gh pr merge --auto --merge` on the new PR, so GitHub merges it once its required checks are green. Reason: GitHub
  refuses auto-merge on a draft PR.
- Only a PR whose base is `base_branch` is merged. A PR stacked on another factory branch stays a draft: merged, it
  would land in that branch, not in `base_branch`.
- If `gh pr ready` or `gh pr merge` fails (auto-merge disabled in the repo, missing token scope), the Run prints a
  warning and goes on: the PR is already open, so nothing is lost and the publish is not retried.

## [low] loose ends become Backlog ticket lines in `.factory/BACKLOG.md` (2026-11-12)

- At the end of a Run each `[low]` item of the Handoffs in `LOOSE-ENDS.md` becomes one `- [ ] <item> (from NN slug)`
  line in `.factory/BACKLOG.md`. A plain file write, no Session: docs/factory-analysis.md P3 planned a $0.50 Session,
  but the Ticket allows a file write and the items need no rewording. Reason: YAGNI, and no cost.
- Not tickets in the tracker: `tickets.py` has no `new` command, and a `todo` Ticket with no blockers would be picked
  up by the next unattended Run. The Owner promotes or drops them after reading `factory status`.
- Only what this Run appended to `LOOSE-ENDS.md` is filed, and a line already in the file is not written again: a line
  the Owner deletes stays deleted. Items in a resolver's decision are skipped: they are not Handoff items.
