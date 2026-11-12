# Factory analysis: what building terminal-task-tracker teaches the Factory

Written 2026-11-12. Source: all 61 Claude Code transcripts of `terminal-task-tracker` (158 MB, 2026-10-14 to
2026-11-12), its process files (`.claude/`, `.scratch/task-tracker/issues/`, `docs/DECISION-LOG.md`, memory) and this
repository. This is a proposal: nothing in `src/` has changed yet.

## How the numbers were made

- **Interventions.** `experiments/tt_interventions.py` reads every top-level user turn that the owner typed: 311
  messages. It skips tool results, slash-command echoes and `!` shell echoes. It labels each message with regexes. One
  message can get several labels, because the owner usually sends a numbered list. The counts are heuristic. I spot-read
  the examples, and they are good to about ±10 % per bucket.
- **Agent waste.** Counted from the same transcripts: tool calls, tool errors, auto-mode classifier denials and
  compactions (each from a per-session digest).
- **Stages.** Session start and end times, git commit dates, and the `started`/`finished` stamps that
  `tickets.py status` prints. Those stamps were backfilled from git on 2026-11-06, so Epic 1's "10 minutes" really means
  "committed in one burst".
- **Not covered.** No transcript exists before 2026-10-14. The domain glossary and the core CLI and TUI (Epic 1, 34
  commits on 2026-10-13) were built in sessions I could not read.

Totals: 61 sessions, 3,996 tool calls, 142 tool errors (3.6 %), 40 automatic compactions, 54 `/compact` commands typed
by the owner, 43 `/handoff` calls, and 33 sessions that began by pasting a handoff path.

## 1. Findings table

Ordered by count. The "Cause" column uses your five groups (missing spec, missing check, unclear convention, tool
failure, scope creep). It adds two more where none of the five fit: **session plumbing** (the owner carrying state
between sessions by hand) and **human decision** (the owner is the right one to answer).

| Intervention                                                        | Cause                          | Count | Example (session, date: quote)                                                                      | Fix (proposal item)                                                    |
| ------------------------------------------------------------------- | ------------------------------ | ----: | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Git and PR choreography: push, open PR, stack, merge, worktree      | unclear convention             |    91 | `4dd78d9f` 10-29: "Each ticket should have it's own branch … push it to GH, and create a PR for it" | P2 rules template, P8 merge policy; the Run already does push and PR   |
| Answering a design or product question, approving a proposal        | human decision                 |    72 | `5f3f0321` 10-16: "q4: local files + sync. Start with last-write-wins per Ticket"                   | P1 interview at the start, batched grill rounds                        |
| Visual review against screenshots or Penpot boards                  | human decision + missing check |    65 | `235cef29` 11-05: "There should be margin between "! Sync failed" panel and borders"                | P6 design stage: automatic margin, contrast and alignment checks first |
| Echoing the agent's own "Skipped / I haven't" list back as an order | missing check                  |    48 | `56fce026` 10-29: "push them > - Nothing pushed. The new branches … are local only."                | Run rule exists; P3 extends it to interactive sessions and [low] items |
| Pasting an error for the agent to solve (CI, Docker, Terraform)     | missing check / tool failure   |    43 | `a73aeedf` 11-07: "src/main.tsx(10,29): error TS2307: Cannot find module './ui/RecoveryKey'"        | P4 `checks` = CI, P7 deploy preflight                                  |
| Plugin, MCP, hook or context-size trouble                           | tool failure                   |    43 | `c7340b07` 11-02: "How to connect penpot mcp … What should I do?"                                   | P10 `doctor` line in `factory status` (low priority)                   |
| Relaying a handoff document into a new session                      | session plumbing               |    41 | `cd218441` 10-29: "this is the handof doc … read it and follow it"                                  | P5 fixed handoff path, loaded at session start                         |
| Repeating a standing rule ("don't forget", "always")                | unclear convention             |    27 | `a4b4c536` 11-05: "Don't be blind!!! Always validate with penpot!!"                                 | P2 project rules template                                              |
| Asking "what next / is it finished / what is left"                  | unclear convention             |    26 | `d08bace5` 11-07: "What tickets should be done until the website be able to work on 100%?"          | P9 stage line in `factory status`                                      |
| Mirroring tickets to Linear, then to GitHub issues                  | scope creep (process)          |    21 | `cd218441` 10-29: "JOH-78 (ticket 04) still says Todo in Linear, while the local ticket is done"    | P1: one interview answer, default "local only"                         |
| Adding scope mid-session (new epic, ticket or feature)              | scope creep (owner)            |    19 | `5f3f0321` 10-26: "Add epic/tickets to add packages for windows choko, macos brew, linux flatpack"  | P2 rule: new ideas go to the Backlog epic, the session goes on         |
| Telling the agent to check facts it guessed                         | missing check                  |    10 | `cd218441` 10-29: mockio was called "a Kotlin/JVM mocking library"; owner: "It's in go"             | P2 rule: no claim from memory; review Session catches the rest         |
| Granting autonomy ("do it yourself", "continue until the end")      | unclear convention             |     7 | `63b05707` 11-08: "continue all untill the end. If required - create new branches and PRs"          | P1 interview answer, P2 template                                       |

Read the table this way. About **230 of the 311 messages** (the git, echo, error, handoff, rule, next, tracker, check-it
and autonomy rows; some messages fall in several rows) are plumbing a machine could do. The other ~150 labels
(decisions, visual taste, new ideas) are real owner input. The Factory should batch those, not remove them.

### Where the agent lost time

| Waste                                    | Evidence                                                                                                                                                                                                                                                          |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| One giant session before tickets existed | `5f3f0321` ran 13 days (10-16 to 10-29): 1,020 tool calls, 17 compactions, 195 user turns, spec, infra and Epic 6 all in one context.                                                                                                                             |
| Compaction churn                         | 40 automatic compactions plus 54 typed `/compact`. Several handoffs were written only to escape a full context (`d08bace5` 11-07: "Watch that the session context should be <= 160k tokens").                                                                     |
| Local checks weaker than CI              | At least 6 failures surfaced only on GitHub or at deploy: TS2307 missing modules and the Docker build reaching outside `web/` (`a73aeedf`), the e2e key tests (`63b05707`, `04471787`), the axe contrast check and the `deploy-prod` design-B check (`4811dcd6`). |
| Infra by trial and error                 | 10-17, in one evening: 12 pasted errors in a row (state bucket missing, billing disabled, ADC quota project, Neon retention limit, `deletion_protection`, an arm64 image on Cloud Run, an empty `service_url`) before `make smoke` passed at 20:07.               |
| Design and pages drifting apart          | The owner asked three handoffs in a row to list "deviation between local webpages and what is in the penpot board" (`d08bace5`, `4d9a2053`, `aa7c80b1`).                                                                                                          |
| Factory preparation that never ran       | 6 sessions, 10-29 to 11-02 (`ece3af08`, `5638462f`, `eff8ce3f`, `2fc1dacd`, `4c658913`, `ed9f1020`), prepared a Run. Transcripts show only `factory run … --dry-run` (4 times). `.factory/` in the project holds only `config.toml`: no logs, no handoffs.        |
| Permission walls                         | 13 auto-mode classifier denials (3 "Merge Without Review", 2 "Git Destructive", 2 "Irreversible Local Destruction"). 25 context-mode redirects of WebFetch and curl. A PAT without merge rights (`a73aeedf` 11-07).                                               |
| The proof gate was switched off          | `verify-gate.sh` was deleted in checkpoint `ae17f1e` (11-06) after it blocked `tickets.py` work (`84f62c06`: "I removed hooks"). `.claude/settings.json` still calls it, so since 11-06 the hook fails open on every Edit and Write.                              |

### What worked, and the stage it belongs to

| Practice                                                           | Stage            | Evidence it paid off                                                                                                                                                                     |
| ------------------------------------------------------------------ | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `grill-with-docs` rounds (q1 to q16) before any spec               | spec             | Decisions such as "server is a dumb store of versioned blobs" held to the end; `docs/DECISION-LOG.md` grew to 1,509 lines. (I did not check every later session for reopened decisions.) |
| `egm-review` of the spec                                           | spec review      | `a2f99e70` found two Blockers (no Alternatives, no Risks section) and a config record missing from the data model, before any code was written.                                          |
| Local tickets with `tickets.py` (status, show, tick, brief)        | tickets/build    | 256 agent calls; 68 of 101 tickets done; a brief from each blocker reaches the next ticket.                                                                                              |
| Small tickets (about 5 files or 200 lines) and a branch per ticket | build            | The owner overrode the cap only once, for page-by-page web work (`a4b4c536`).                                                                                                            |
| TDD with `make test` and `make lint` run by the agent              | build            | 105 and 136 runs. The memory note "run make targets freely" removed permission prompts for them.                                                                                         |
| Handoff document at session end                                    | between sessions | 33 sessions began from one, and each picked up without re-explaining the project. The relay itself was manual (see P5).                                                                  |
| `make web-e2e` with screenshots that the agent opens               | verify           | 89 runs; it caught layout and a11y regressions the unit tests missed.                                                                                                                    |
| Penpot variants plus owner approval, CHOSEN/REJECTED labels        | design           | The owner approved boards in batches (guess: about 25; not counted) (`235cef29`, `a4b4c536`); pages were built from approved boards.                                                     |
| `make smoke` against the live service                              | deploy           | It turned "is it deployed?" into one command; `deploy-prod` refuses a release where the landing page lacks design B.                                                                     |
| PR template plus the `github-cli` skill                            | publish          | One template replaced per-PR wording requests (11-01, `5638462f`); I did not count later corrections.                                                                                    |

### The real stage sequence

| Stage                                      | When (wall clock)                  | Notes                                                                                       |
| ------------------------------------------ | ---------------------------------- | ------------------------------------------------------------------------------------------- |
| Idea, glossary, core CLI and TUI (Epic 1)  | 10-13 (one day)                    | No transcript; 34 commits.                                                                  |
| Online service: grill, spec, tickets       | 10-16 01:11 to 04:21 (3 h)         | `5f3f0321`.                                                                                 |
| Build sync client and service (Epics 2, 3) | 10-16 04:23 to 22:48 (~18 h)       | `implement-spec`, then a separate code-review worktree.                                     |
| Deploy infra (Epic 4)                      | 10-16 22:00 to 10-17 20:07 (~22 h) | The owner ran every paid command; 12 errors pasted.                                         |
| Sync hardening (Epic 6)                    | 10-18 (one day)                    |                                                                                             |
| Web: grill, design, spec review            | 10-19 to 10-29 (10 days, sparse)   | Impeccable, Penpot, `egm-review`; the web goal grew from read-only to full parity on 10-21. |
| Web build, first tickets (TDD)             | 10-29 to 11-01                     | 3 sessions, one ticket each.                                                                |
| Factory and harness detour                 | 10-29 to 11-02                     | 6 sessions; no real Run.                                                                    |
| Landing page and environments              | 11-02 to 11-06 01:39               | The landing page was deployed on 11-06.                                                     |
| Design every page, then build pages        | 11-04 to 11-07 19:52               | 11 sessions; Epic 10 was finished at 19:52.                                                 |
| Live testing, review, polish, hardening    | 11-07 22:20 to 11-10 20:43         | 7 sessions; `deploy-prod` passed on 11-10.                                                  |
| Release pipeline (12/01)                   | 11-10                              | Not finished in Epic 12 (0/8 done).                                                         |

From idea to a deployed web app took 25 days (10-13 to 11-07). By my rough estimate, a little under half of the sessions
were spent on process and tooling rather than product: plugins, the context, hooks, the factory, Linear, GitHub projects
and Penpot setup.

## 2. Gap analysis: what each intervention becomes

| Intervention bucket     | Becomes                                                                                                 | Kind                 |
| ----------------------- | ------------------------------------------------------------------------------------------------------- | -------------------- |
| Git/PR choreography     | The Run already branches, pushes and opens stacked draft PRs; merging gets one interview answer         | automate + rule      |
| Echo of skipped items   | Rule: in scope means do it now; out of scope means a Backlog ticket. The Run already has the first half | rule                 |
| Pasted errors (CI)      | `checks` must equal CI, including `docker build` when a `Dockerfile` exists                             | check                |
| Pasted errors (infra)   | A "Deploy preflight" section in the spec template and a `make smoke` exit check                         | template + checklist |
| Handoff relay           | Handoff at a fixed path, read at session start                                                          | hook + rule          |
| Repeated rules          | A project `CLAUDE.md` template written by `factory bootstrap`                                           | template             |
| What next               | `factory status` prints the stage and the next command                                                  | automate             |
| Tracker mirroring       | One interview answer (default: local tickets only)                                                      | human, once          |
| Scope added mid-session | Rule: one `tickets.py new` call into Backlog, then carry on                                             | rule                 |
| Check-it-yourself       | Rule plus the existing review Session                                                                   | rule                 |
| Visual review           | Automatic layout checks first (axe, 16 px margin, phone width); the owner then sees one batch           | check + human        |
| Decisions               | Up-front interview, then grill rounds batched per stage                                                 | human                |
| Tooling trouble         | A `doctor` line (needed MCP servers, `gh` scopes) in `factory status`                                   | check                |

**Human-only decisions.** This is the only list the Factory may ask about.

1. **The idea and who it is for.** One paragraph, the first user, and what v1 must do (the MVP cut).
2. **License and openness.** Private or commercial, open source or closed (`c9042dfe` 10-14).
3. **Hosting and money.** Which cloud, a hard monthly cap, free tier only or not.
4. **Data sensitivity.** What must be end-to-end encrypted, what the server may see, and retention.
5. **Identity.** Who signs in and with which provider.
6. **Stack overrides.** Only where the owner's defaults (Go backend; TS, Bun and Vite web) do not fit.
7. **Clients and UI.** CLI, TUI, web, mobile; whether a design stage runs; the style and palette.
8. **Design picks.** One batch per stage, chosen from variants that already pass the automatic checks.
9. **Spend go-ahead.** Each command that creates cloud resources or costs money (your global rule).
10. **Credentials and accounts.** Billing, `gcloud auth`, API keys, DNS, PAT scopes: only the owner can act.
11. **Product-policy numbers.** Caps, rate limits, retention days. 13/04 merged a 100 MiB cap "without your answer".
12. **Merge policy.** May the Factory merge a PR after its review passes and CI is green?
13. **Going public.** Landing-page claims (for example, whether to mention AI) and the public release.

Items 1 to 7 and 12 are asked once, at the start. Items 8 to 11 and 13 come up during the project, batched at a stage
gate.

## 3. Proposal for `software_factory`

Ordered by saving divided by effort. "Saves" is the share of the 311 TT messages the change would have removed. It is an
estimate.

| #   | File or folder                                                                                                                            | Change                                                                                                                                                                                                                                                                                                                                                                             | Fixes                                      | Saves (est.)                                 | Effort                  |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | -------------------------------------------- | ----------------------- |
| P1  | `src/factory/templates/interview.md` (new), `plan.py` `planning_rules()`                                                                  | Questions 1 to 7 and 12 above with defaults. Planning step 0 asks only the questions that `docs/OWNER-ANSWERS.md` does not answer yet, then writes the answers there and into the decision log. Later skills must not ask them again.                                                                                                                                              | decisions, tracker sync, autonomy          | 30 to 40 messages; most 10-16 grill rounds   | S (about 60 lines)      |
| P2  | `src/factory/templates/CLAUDE.md` (new), `bootstrap.py` copies it when the project has none                                               | Standing rules for interactive sessions: a branch per ticket; PR from `.github/pull_request_template.md`; run checks yourself; skipped in-scope items are done now; new ideas become `tickets.py new` in the Backlog epic; no claim from memory; name the thing (board, ticket and meaning); code in backticks; never touch the paths in `protected`. No TT specifics.             | repeated rules, scope added, check-it, git | 40 to 60 messages                            | S (about 70 lines)      |
| P3  | `prompts.py` `HANDOFF_FORMAT`, `run.py` end of Run                                                                                        | After the last Ticket, one cheap Session ($0.50) files the [low] loose ends as Backlog tickets. `factory status` prints them as one list with "ticket all / drop" next to it, so the owner answers once instead of item by item.                                                                                                                                                   | echo of skipped items                      | 25 to 35 messages                            | S to M                  |
| P4  | `config.py` `template()`, `run.py` `preflight()`                                                                                          | When `.github/workflows/*.yml` exists, `factory init` copies its `run:` make targets into `checks`. When a `Dockerfile` exists and no check builds it, `preflight` warns.                                                                                                                                                                                                          | pasted CI errors                           | about 10 messages; at least 6 red CI runs    | S                       |
| P5  | `templates/settings.json` (new; a `SessionStart` hook that prints `.factory/handoffs/latest.md`); P2 rule "the handoff goes to that path" | Interactive sessions resume without the owner pasting a path. Run Sessions already use `.factory/handoffs/<num>.md`.                                                                                                                                                                                                                                                               | handoff relay                              | 33 to 41 messages                            | S                       |
| P6  | `plan.py` `chain()`, `templates/design-checklist.md` (new)                                                                                | An optional design step when interview Q7 says there is a UI. Exit check: every UI ticket has a `Design:` line naming an approved board, and the e2e suite has axe, phone-width screenshots and a margin check. Generic rules only: 16 px margin, a button for every hotkey, no hotkey help on phones, labelled boards. The Penpot tool-use rules move here from TT's `CLAUDE.md`. | visual review, design-page drift           | 20 to 30 messages; about 3 design sessions   | M                       |
| P7  | `templates/spec-sections.md` (new), used by `to-spec` in the planning rules                                                               | A required "Deploy preflight" section (billing on, auth and quota project, image architecture, state bucket, deletion protection, the exact `make smoke`). Every deploy ticket's acceptance criteria end in `make smoke`. Deploy tickets stay owner go-ahead (`skip_pattern`).                                                                                                     | pasted infra errors                        | about 12 messages; about 1 day of wall clock | S                       |
| P8  | `config.py` (`merge = "never" \| "green"`), `run.py` `publish()`                                                                          | With `green`, after review PASS the Factory runs `gh pr merge --auto --merge` on the bottom of the stack. Default `never`. The answer comes from interview Q12. The 2026-10-30 decision stands as the default; this adds an opt-in.                                                                                                                                                | git/PR merge requests (45 mention merging) | 20 to 30 messages                            | M                       |
| P9  | `bootstrap.py` `next_step()`                                                                                                              | Stages, each with entry and exit checks (table below); `factory status` prints `Stage: build (34/50 tickets), Next: factory run .`                                                                                                                                                                                                                                                 | what next                                  | about 20 messages                            | S                       |
| P10 | `experiments/tt_interventions.py` becomes `factory retro PROJECT` (`src/factory/retro.py`)                                                | Runs the same counter on any project's transcripts and appends a dated table to `LESSONS.md`. Each lesson must name the template line it changed.                                                                                                                                                                                                                                  | self-improvement                           | the next project's rework                    | S                       |
| P11 | `bootstrap.py`                                                                                                                            | A `doctor` line: needed MCP servers answer, `gh` has the `repo` and `project` scopes, the PAT can merge.                                                                                                                                                                                                                                                                           | tooling trouble                            | about 10 messages                            | S; do it after the rest |

### The stage pipeline (P9)

| Stage   | Entry check                 | Work                                                            | Exit check                                                                              |
| ------- | --------------------------- | --------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| idea    | none                        | the owner writes one paragraph                                  | `docs/IDEA.md` exists                                                                   |
| answers | `IDEA.md`                   | interview (P1)                                                  | `docs/OWNER-ANSWERS.md` answers Q1 to Q7 and Q12                                        |
| spec    | answers                     | `grill-with-docs`, `to-spec` with the required sections (P7)    | the spec has Alternatives, Risks and Deploy preflight; `egm-review-loop` has no Blocker |
| design  | the spec has UI (Q7)        | variants, owner picks in one batch (P6)                         | every UI story has an approved board                                                    |
| tickets | spec (plus design)          | `to-tickets`, at most about 5 files or 200 lines each           | `tickets.py status` shows READY tickets; cloud tickets carry "Owner's go-ahead"         |
| build   | READY tickets, clean `main` | `factory run` (exists)                                          | every non-skipped ticket done, `checks` (= CI) green, PRs open                          |
| verify  | build done                  | e2e with screenshots, review Session (exists)                   | review PASS; screenshots named in the Handoff                                           |
| deploy  | owner go-ahead (Q9)         | the owner runs the printed commands, or the agent with approval | `make smoke` passes against the live URL                                                |
| retro   | deployed                    | `factory retro` (P10)                                           | `LESSONS.md` entry, template changes proposed                                           |

### Generic or project-specific

| Goes into the template (generic)                                                                                           | Stays in the project (TT-specific)                                                         |
| -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `tickets.py` and its Makefile; epic folders; the brief and handoff format                                                  | the epic names, ticket text, `JOH-*` Linear ids                                            |
| `CLAUDE.md` rules (P2); hooks: `commit-on-stop`, `steer`, `kill-switch`, verify-gate with the evidence pattern from config | the evidence path `web/e2e/…`, `make web-e2e`                                              |
| The design checklist (P6): 16 px margin, buttons for hotkeys, board labels, Penpot call rules                              | Catppuccin Frappé, the VT323 font, Penpot file ids, board names (A1, N2 …)                 |
| The spec sections: Alternatives, Risks, Deploy preflight                                                                   | GCP, Neon and Firebase names, `us-east4`, the Cloud Run arm64 lesson (cited as an example) |
| The PR template, `github-cli` merge notes                                                                                  | `scripts/tickets_to_issues.py` (only if Q-tracker says GitHub)                             |
| A `protected` list in `.factory/config.toml` (shared data that is never touched)                                           | `tt_dev` as the protected database                                                         |

The owner's taste rules (16 px margin, "name the thing") are really owner-level. Keep them in `~/.claude` memory or the
design checklist, not in a project.

### Autonomy rules

- **Continue alone** when the ticket is READY, its `checks` exist and match CI, the budget is not spent, and the text
  has no owner go-ahead tag. A refused tool is not a stop: log it as [low] (the Run already does this).
- **Stop and ask** only for an item on the human-only list, or after 2 Blocked tickets (exists). Before stopping, batch
  every open question of the stage into one message.
- **Recover.** A failed check gets one fix Session and another review (exists). A [high] loose end goes to the Opus
  resolver (exists). An unpublished PR is retried on the next Run (exists). A context near 160k tokens triggers a
  handoff to the fixed path (P5), not a `/compact`.

### Guardrails

- **Tests first.** The `tdd` skill in Run Sessions (exists). The P2 rule carries it into interactive sessions.
- **Proof before done.** The Factory's own `verify` (exists). For UI tickets, the Handoff must name a screenshot that
  the review Session opens. That replaces TT's `verify-gate` hook, which the owner deleted because it blocked unrelated
  edits.
- **Cost.** Per-session `--max-budget-usd` and the ticket limit (exist). Cloud commands stay owner-only (exists).
  Interview Q3 adds a monthly cap, which deploy tickets name.
- **Shared data.** Paths in `protected` go to `--disallowedTools` patterns and into the P2 rule (TT memory: e2e wiped
  the shared `tt_dev` DB).

### Handoff

- **Between tickets.** The Brief goes in the ticket, the Handoff in `.factory/handoffs/<num>.md`, and the next ticket's
  goal reads both (exists).
- **Between interactive sessions.** `.factory/handoffs/latest.md`, printed by the `SessionStart` hook (P5). The owner no
  longer runs `/handoff` or pastes a path.

### How the Factory improves itself

1. At the end of every project, run `factory retro PROJECT` (P10). It prints this document's findings table for the new
   project.
2. Each bucket that is still over about 5 % of messages becomes one `LESSONS.md` entry. The entry names the template
   file and line it changes, plus a test, in the format `LESSONS.md` already uses.
3. Owner taste rules found along the way go to `~/.claude` memory, not the template.

## Paper test: `liftlog`, a CLI that tracks gym workouts

| Stage   | What happens                                                                                                                              | The owner is asked                                                                  |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| idea    | The owner writes: "Log sets and reps from the terminal, see weekly volume and PRs."                                                       | the paragraph                                                                       |
| answers | Interview. Defaults offered: Go, local files, no cloud, no UI, private, `merge = green`, local tickets only.                              | 8 questions, most answered "default"; real choices: sync later? (no), license (MIT) |
| spec    | `grill-with-docs` asks only what the answers leave open (units, how to define a PR, the CSV export format); `to-spec`; `egm-review-loop`. | one batch of about 5 domain questions                                               |
| design  | Skipped: Q7 says no UI.                                                                                                                   | nothing                                                                             |
| tickets | `to-tickets` writes about 8 tickets; none is cloud.                                                                                       | nothing (the owner may skim)                                                        |
| build   | `factory run`: 8 Sessions, about $40 cap; stacked PRs; merged on green.                                                                   | one go-ahead for the paid Run                                                       |
| verify  | The review Sessions; `make test` and `make lint` = CI.                                                                                    | nothing, unless a [high] item gets past the resolver                                |
| deploy  | "Deploy" means a GoReleaser tag (as in TT 12/01) and a Homebrew tap.                                                                      | go-ahead to push the tag; create the tap repo and token (credentials)               |
| retro   | `factory retro` on liftlog's transcripts.                                                                                                 | accept or drop the proposed template edits                                          |

Total: about 4 sittings and roughly 20 answers, against 311 messages for TT. TT was a bigger product (e2e crypto, web,
cloud), so this is not a like-for-like comparison. Adding a web UI to liftlog would add the design stage (1 or 2 batch
reviews) and a cloud deploy (Q3, Q5 and Q9 go-aheads).

## What I skipped or could not verify

- Sessions before 2026-10-14 (Epic 1): no transcripts.
- Subagent (sidechain) transcripts: I counted only top-level turns. Agent waste inside subagents is not in the numbers.
- The labels are regexes. Counts are ±10 %, and a message can sit in several rows. The "Saves" column is an estimate,
  not a measurement.
- I did not check whether a real `factory run` happened outside these transcripts, from your own terminal. The missing
  `.factory/logs/` suggests it did not.
- Cost per session: the transcripts have no reliable dollar figures, so there are no cost numbers.
- Whether `gh pr merge --auto` works on your plan for a private repo (P8): not checked.

## Recommended first slice

**P2 + P5 + P1: the project rules template, the handoff at a fixed path, and the interview file.** Together they address
the largest plumbing buckets (rules, handoff relay, decisions, git conventions), roughly 100 of the 311 messages. They
change no Run logic. They touch 5 files and about 180 lines: `src/factory/templates/CLAUDE.md`,
`src/factory/templates/interview.md`, `src/factory/bootstrap.py` (copy templates), `src/factory/plan.py` (planning_rules
step 0) and `tests/test_bootstrap.py`. P4 (`checks` = CI) is the natural second slice, because it is small and stops the
red CI runs.

## Out-of-scope problems noticed

- TT: `.claude/settings.json` still calls the deleted `.claude/hooks/verify-gate.sh`, so proof-before-passing has been
  off since 2026-11-06, and project `CLAUDE.md` still describes the gate.
- TT: `make status` shows Epic 12 at 0/8 although 12/01 is committed on `12-01-release-pipeline`. The ticket is not
  marked done yet.
- Factory: `README.md` and `CLAUDE.md` disagree on the tickets folder name (`tickets/` in `CLAUDE.md`, `issues/` in TT).
  `config.py` already finds the existing folder, so this is a docs mismatch only.
