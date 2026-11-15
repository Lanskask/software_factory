# Judge report: 6 blind code-review methods on 3 diffs

Judge: Opus, 2026-11-14. Inputs: 18 reports `reviewer-{A..F}__{seeded-backup,real-56,real-55}.md`, the 3 diffs,
`ground-truth.md`, and the PR branches `origin/factory/06-low-loose-ends` (PR 56) and `origin/factory/12-retro` (PR 55)
for checking findings outside the ground truth. Which method is behind which letter is unknown to the judge.

## Classification rules

- **TP**: matches a ground-truth defect (S1-S4, R56, R55).
- **valid-extra**: not in the ground truth, but true when checked against the diff or the branch code.
- **invalid**: a false positive, contradicted by the code or the environment.
- **noise**: style, naming, readability, a restatement of another finding, or a speculative worry with no defect.
- Counted as findings: numbered items and bullet items under issue headings. Not counted: summaries, "positive
  feedback", "questions for author", FYI and axis summaries.
- A finding that bundles a TP with an extra point counts once, as TP.

All six reviewers cite line numbers of the **diff file**, not of the source file (for example `backup.py:17` for the
`subprocess.run` that is line 11 of `backup.py`). This holds for every reviewer, so it does not discriminate.

## 1. Per-report findings

### seeded-backup.diff

| Rev | Findings and class                                                                                           |
| --- | ------------------------------------------------------------------------------------------------------------ |
| A   | 1 S1 TP; 2 S2 TP; 3 glob matches any `*.tar.gz` + same-second name clash, valid; 4 S3 TP; 5 no `mkdir`,      |
|     | partial archive, dest inside src, valid; 6 S4 TP                                                             |
| B   | 1 S1 TP; 2 S2 TP; 3 S3 TP (+ glob, valid); 4 S4 TP; 5 same-second clash + `mkdir`, valid                     |
| C   | 1 S1 TP; 2 S3 TP; 3 timestamp clash, valid; 4 `mkdir`/partial archive, valid; 5 glob, valid; 6 Primitive     |
|     | Obsession, noise; 7 S2 TP; 8 S2 negative slice, valid (split of S2); 9 S4 TP                                 |
| D   | C1 S1 TP; C2 S2 TP; M1 S3 TP; M2 glob, valid; M3 timestamp, valid; M4 S4 TP; minor: test checks only         |
|     | `.exists()` valid, `mkdir` valid, dest inside src valid, `str` vs `Path` noise, partial archive valid        |
| E   | S1 TP (security block and focus area, counted once); S2 TP; S3 TP. S4 missed: the badge "No relevant tests"  |
|     | names no gap and does not mention `prune`                                                                    |
| F   | 1 S1 TP; 2 S2 TP; 3 glob valid; 4 S3 TP; 5 timestamp valid; 6 `mkdir`/dest in src valid; 7 S4 TP; 8 typing + |
|     | mtime ties noise; 9 `backup_and_prune` wrapper noise; 10 `tarfile` alternative (repeat of 1) noise; 11, 12   |
|     | nits noise                                                                                                   |

Arithmetic check on S2 (3 files, `keep=5` gives `files[:-1]`, which deletes **2** files): A, B and C say it deletes 1
file; F says 2 (correct). D labels the case "`keep > len(files)`, e.g. 5 files and `keep=5`" (not greater). The
direction and the fix are right in every report, so these slips do not change the class.

### real-56.diff (PR 56)

Checked on the branch: the loop in `run()` has two early `return 1` paths that skip `file_backlog` (`PushError` and the
resolver failure); a Blocked Ticket uses `continue` / `break`, so it does reach `file_backlog`. The e2e fakes mark each
Ticket `done`, so the second `run()` in the new test finds no Ticket, appends nothing, and returns at the
`size <= start` guard: the dedup line is never exercised.

| Rev | Findings and class                                                                                            |
| --- | ------------------------------------------------------------------------------------------------------------- |
| A   | 1 R56 TP; 2 no dedup within one Run, valid; 3 char offset breaks if the file is trimmed mid-Run, valid (low); |
|     | 4 nested bullets / fenced code glued into items, valid; 5 status hides `- [x]` / no cap, noise; 6 the test's  |
|     | second Run is vacuous, valid                                                                                  |
| B   | 1 R56 TP; 2 test never reaches the dedup, valid; 3 DECISION-LOG overpromises "stays deleted", valid; 4 file   |
|     | read twice, noise; 5 header-only `BACKLOG.md` created, valid; 6 long comprehension, noise                     |
| C   | Std 1 no trailing newline glues lines, valid; Std 2 O(n\*m) + no self-dedup, valid; Std 3 header-only file,   |
|     | valid; Std 4 `list[list]`, noise; Std 5 sub-bullets joined, valid; Std 6 path built 3 times, noise; Std 7     |
|     | long line, noise; Std 8 "tickets" wording, noise; Spec 1 R56 TP; Spec 2 duplicates / ticked items refiled,    |
|     | valid; Spec 3 trimmed file, valid (low); Spec 4 dates unverifiable, noise; Tests 1 dedup untested, valid;     |
|     | Tests 2 split the test, noise; Tests 3 missing cases incl. early stop, valid                                  |
| D   | Major 1 R56 TP; Major 2 dedup untested, valid; minor: no self-dedup valid; `write_text` overwrites Owner      |
|     | edits + header-only file valid; `_SOURCE` coupled to the writer's f-string valid (low); sub-bullets / empty   |
|     | item valid; `- [x]` refiled valid; two status counts confuse, noise                                           |
| E   | R56 TP (only finding)                                                                                         |
| F   | 1 R56 TP; 2 trailing newline glue, valid; 3 dedup untested, valid; 4 no self-dedup, valid; 5 `_SOURCE`        |
|     | coupling, valid (low); 6 `list[list]` noise; 7 test gaps where the code is right, noise; 8 long line noise; 9 |
|     | naming noise; 10 comment on `loose_ends_size` noise                                                           |

### real-55.diff (PR 55)

Checked on the branch: `prompts.goal()` tells every implementation Session "Read `LESSONS.md` first: unverified notes on
what went wrong in earlier Tickets" whenever the file exists, so retro lines kept by `reset_lessons` do reach every
Session (valid for A4, B3, C2, D3, F2). The transcript folder of this very repo is
`-Users-a1-Programming-My-Projects-software-factory`, so `My_Projects` maps to `My-Projects` exactly as `transcript_dir`
assumes (A6 invalid).

| Rev | Findings and class                                                                                             |
| --- | -------------------------------------------------------------------------------------------------------------- |
| A   | 1 older `[open]` lines never close, valid; 2 raw counts vs rate, valid; 3 locale encoding / non-dict JSON,     |
|     | valid (low); 4 retro lines fed to Sessions, valid; 5 R55 TP (ranked 5th, "low"); 6 underscore mapping          |
|     | "unverified", **invalid**; 7 experiment loses examples, silent 0, valid; 8 missing tests incl. CLI message,    |
|     | valid                                                                                                          |
| B   | 1 R55 TP; 2 raw counts vs rate, valid; 3 retro lines fed to Sessions, valid; 4 ternary statement +             |
|     | `object.__new__`, noise; 5 dead sort, noise; 6 experiment loses examples, valid; 7 encoding / memory, valid    |
| C   | 1 R55 TP; 2 Session injection, valid; 3 rate, valid; 4 owner-specific regexes in a shipped command, valid; 5   |
|     | "table" naming, noise; 6 ternary, noise; 7 encoding (+ dead sort), valid; 8 non-atomic rewrite vs `lesson()`   |
|     | append, valid (low); 9 `[open]` lines stack, valid; 10 experiment regression, valid; 11 tests incl. CLI, valid |
| D   | 1 `[open]` lines stack, valid; 2 equal count duplicates (restates 1), noise; 3 ternary + Session injection,    |
|     | valid; 4 encoding, valid; 5 non-dict JSON, valid; 6 R55 TP (ranked 6th, "minor"); 7 naming scheme              |
|     | assumption, noise; 8 shared constant, noise; 9 noise; 10 experiment regression, valid; 11 "table", noise; 12   |
|     | `LABELS` vs `PATTERNS`, noise; 13 `date.today()` flake, noise; 14 missing tests incl. CLI, valid; 15           |
|     | `object.__new__`, noise; 16 call site untested, noise                                                          |
| E   | R55 TP (only finding)                                                                                          |
| F   | 1 R55 TP; 2 Session injection, valid; 3 `[open]` lines stack, valid; 4 owner-specific regexes, valid; 5 dead   |
|     | sort, noise; 6 encoding / memory, valid; 7 `.*` regex slowdown, noise; 8 experiment regression, valid; 9       |
|     | tests incl. CLI, valid; 10 ternary, noise; 11 `date.today()`, noise; 12 "table", noise; 13 parser chain, noise |

## 2. Metrics

Recall is over the 6 ground-truth defects. Precision = (TP + valid-extra) / all findings. Words per valid finding uses
`wc -w` over the three reports (E without the `pr_agent` log lines that leaked into its real-56 report). Severity
calibration: is the worst ground-truth defect of each diff at the top of the report (S1 or S2 for seeded)?

| Rev | Recall | Findings | Valid | Invalid | Noise | Precision | Action | Words / valid | Worst first |
| --- | ------ | -------- | ----- | ------- | ----- | --------- | ------ | ------------- | ----------- |
| A   | 6/6    | 20       | 18    | 1       | 1     | 90 %      | 4      | 86            | 2/3         |
| B   | 6/6    | 18       | 14    | 0       | 4     | 78 %      | 5      | 167           | 3/3         |
| C   | 6/6    | 35       | 26    | 0       | 9     | 74 %      | 4      | 89            | 2/3         |
| D   | 6/6    | 35       | 24    | 0       | 11    | 69 %      | 4      | 109           | 2/3         |
| E   | 5/6    | 5        | 5     | 0       | 0     | 100 %     | 3      | 109           | 3/3         |
| F   | 6/6    | 35       | 19    | 0       | 16    | 54 %      | 4      | 120           | 3/3         |

Notes on the softer columns:

- **Actionability**: B gets 5 (file:line, a one-line fix, a severity bucket, and "if we skip it" consequences for every
  item, plus a "fix 1 and 2 first" verdict). A, C, D, F give file:line, fixes and severity, but A drops the fix on a few
  items, C splits its order across two axes, and D and F bury real items among style points. E gives no file:line and no
  severity scale, only a focus area with a fix.
- **Calibration misses**: A ranks R55 5th as "low" and D ranks it 6th as "minor" while putting stale `[open]` lines and
  a ternary-as-statement above it. C labels S2 HIGH but places it 7th (in the Spec section), and its real-56 summary
  names the trailing-newline glue as the worst Standards issue.
- **Every reviewer found R56 and R55**, the two defects confirmed on real code. The benchmark discriminates on S4 (E
  missed it), on calibration, and on noise.
- **Best valid-extras**, all verified: the PR 56 test never reaches the dedup line (A, B, C, D, F); retro lines are fed
  to every Session as "what went wrong" notes (A, B, C, D, F); a hand-edited `BACKLOG.md` without a trailing newline
  gets the next item glued to its last line (C, F only).

## 3. Ranking

1. **B**: full recall, zero invalid, worst defect first in all three diffs, highest actionability. Costs more words per
   finding because every item carries "what this is / problem / fix / if we skip it".
2. **A**: full recall and the best density (90 % precision, 86 words per valid finding), but one false positive (A6) and
   R55 under-ranked as "low", so a reader who stops at the top items misses the confirmed bug.
3. **C**: the most valid findings (26) with modest noise, but the two-axis layout (Standards / Spec) scatters the order;
   severity is right per item, wrong as a reading order.
4. **E**: perfect precision and calibration, 5/6 recall, almost no extras. A good "top risk only" signal; it misses test
   gaps (S4, the dedup test) and every secondary bug.
5. **F**: full recall and calibration, but 16 of 35 findings are noise (nits, YAGNI notes, alternatives). Its Required /
   Optional / Nit tiers keep the noise below the fold, which limits the damage.
6. **D**: full recall, 11 noise items, R55 ranked "minor", and a large fixed template (positive feedback, questions,
   verdict) that adds words without findings.

Ranks 3-6 are close and would likely reshuffle on another run.

### Structural features that drove the result

- **Explicit severity buckets with a forced order** ("Must fix / Should fix / Nice to have", "Required / Optional") put
  the worst defect first (B, F, E). Free numbering with per-item severity (A, D) let a confirmed bug drift down.
- **Concrete consequence per item** ("If we skip it", B) made severity self-checking: R55's consequence ("a typo in the
  project path is silent") is hard to file as "low".
- **Check the claims the diff makes about itself** (README, DECISION-LOG, docstrings) found R56 and the "never filed
  twice" overpromise; C did this explicitly as its Spec axis, B and A implicitly.
- **Test-gap check that asks "would this test fail if the code were deleted?"** found the vacuous dedup test (B, C, D,
  F) and S4. E has no such step and is the only reviewer that missed S4.
- **Stating what was not checked** (B, F) kept unverified claims labelled; F hedged the Session-injection point as
  unverified, which was right.
- **Noise producers**: smell catalogues (C's Primitive Obsession, Data Clump), a full five-axis sweep with Nit and
  Optional tiers (F), and fixed sections for positives and questions (D). None of these produced a TP.

## 4. Proposed combined method

```text
Review the diff. Read only what you need beyond it; say what you could not check.
1. One paragraph: what the change does and the assumed load (who runs it, how often).
2. Check, in order: security (injection, untrusted input), data loss (deletes, overwrites, lost writes on early
   exit / exception paths), user-visible lies (success messages, docs and docstrings that the code does not honour).
3. For every promise in README, decision log, docstrings or the test name: does the code keep it on every path?
4. Tests: for each new branch, would some test fail if that branch were deleted? Name the missing test.
5. Off-by-one, empty, negative and "fewer than N" inputs for every slice, count and loop bound; show the arithmetic.
6. Output buckets in this order: Must fix / Should fix / Nice to have. At most 3 Nice-to-have items. No style,
   naming or smell items unless they cause a bug.
7. Each item: `file:line` (source file, not diff line), problem, one concrete fix, "if we skip it".
8. Before writing, re-read each finding against the code: drop it if you cannot point at the line that breaks.
9. End with: verdict (which items first), and what was not checked.
```

**Does it beat the best single reviewer?** Probably only slightly. B already has items 1, 6 and 7 and most of 3 and 4;
the additions are a forced data-loss / early-exit pass (step 2), the "would a test fail" rule (step 4), shown arithmetic
(step 5, which would have avoided the slice-count slips in A, B and C), the cap on Nice-to-have items, and a
self-verification pass (step 8, which would have removed A6). These target the failure modes seen here, but this
benchmark cannot show that they help: B's recall is already 6/6. **Recommendation: use B as is, and adopt steps 4, 5 and
8 as a small patch to it**; promote the full combined prompt only if it beats B on a larger bench.

## 5. Limits of this benchmark

- **Sample size**: 3 diffs, 6 defects, one run per reviewer per diff. Five of six reviewers score 6/6, so recall
  separates nothing except E's S4 miss; one more run could flip that.
- **Ceiling effect**: the seeded defects are textbook (shell injection, off-by-one, bare `except`, missing test). The
  two real defects were found by everyone. The bench cannot tell which method finds hard bugs.
- **Judge subjectivity**: "valid-extra" vs "noise" and the actionability score are one judge's calls. Where a finding
  was borderline (low-probability races, coupling concerns) it was counted valid, which favours verbose reviewers (C, D,
  F) on both the "Valid" and the precision columns.
- **Ground truth completeness**: the valid-extras show the ground truth is not exhaustive (the dedup test and the
  Session-injection issue are arguably as important as R56 / R55). Recall measured only against the list.
- **Cost**: treated as equal per the brief; E's method also spends hidden `claude -p` tokens not counted here.
- **Not concluded**: whether any method finds bugs that need code outside the diff (all ran diff-only), and whether the
  ranking holds for other languages or larger diffs.
