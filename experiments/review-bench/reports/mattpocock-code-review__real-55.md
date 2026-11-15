# Code review: real-55.diff (`factory retro`)

Method note: the skill's two-axis flow needs git refs, an issue tracker and repo standards docs. The brief allowed only
the diff, so the fixed-point and spec lookup were skipped and no sub-agents were spawned. The Standards axis was done
by hand against the skill's smell baseline (judgement calls). The Spec axis is skipped: "no spec available". Line
numbers are new-file lines (derived from the diff hunks).

## Standards

Severity: HIGH, MEDIUM, LOW. All smells are judgement calls.

1. MEDIUM (bug) src/factory/retro.py:104 and src/factory/cli.py:149. When `total == 0`, `retro()` returns `path`
   without writing, and the CLI still prints "appended a retro table to ...". The message is false, and the path may
   not exist. Return a flag, or have the CLI print "no transcripts found" and a non-zero or distinct result.

2. MEDIUM (design) src/factory/run.py:~297-301 (`reset_lessons`). The retro lines are kept in LESSONS.md, which
   `lessons()` / `lesson()` document as "read by every later Ticket's Session". So every Session prompt now carries
   about 11 owner-metrics lines per past `retro` run. They add tokens and noise, and the agent cannot act on them.
   They also grow without bound, because nothing prunes `[resolved]` lines or old runs. Store retro output in a
   separate file (for example `.factory/RETRO.md`), which also removes the coupling between `reset_lessons` and the
   `- retro ` prefix. Possible Divergent Change: LESSONS.md now serves two purposes.

3. MEDIUM (logic) src/factory/retro.py:110. A bucket is marked `[resolved]` when `counts[k] < old_count`, which
   compares raw counts. Transcripts only grow, so counts almost never shrink. A genuinely improved rate (fewer
   interventions per message) is not detected. It also resolves when a transcript is deleted or moved. Compare rates
   (n / total), or drop the "resolved" feature (YAGNI, the spec for it is not visible here). The older line already
   carries its own total, so a rate comparison is cheap.

4. MEDIUM (speculative / overfit) src/factory/retro.py:24-56 (`PATTERNS`). The regexes are the author's own phrases
   and typos ("aggree", "youself", "Fix all!", "JOH-\d+", "Do all designes", "Penpot", "reload-skills"). They were
   moved from a one-off experiment into a shipped CLI command. For any other Project the counts are mostly noise,
   yet they are written into project state. Possible Speculative Generality / Primitive Obsession (labels are bare
   regex strings). Consider keeping them in the experiment, or making them configurable, and say so in the help text.

5. LOW (naming/consistency) The command help, CLI message and test docstring say "table", but the output is a list of
   `- retro ...` lines, not a table. Possible Mysterious Name: `ECHO`, `ROW`, `PATTERNS` and `LABELS` (two dicts for
   one idea; build `LABELS` once and drop `PATTERNS`), single-letter `c`, `d`, `t`, `m`, `ln`, `k`, `n`.

6. LOW src/factory/run.py:~301. `path.write_text(...) if keep else path.unlink()` is a conditional expression used as a
   statement for side effects. Use a plain `if/else`.

7. LOW src/factory/retro.py:65-66. `sorted(..., key=st_mtime)` is now dead work: order no longer matters because
   session id and timestamp were dropped. `f.read_text()` has no `encoding` and no error handling, so one
   non-UTF-8 or unreadable transcript aborts the whole command. Use `encoding="utf-8", errors="replace"`, and
   iterate lines instead of loading whole files.

8. LOW src/factory/retro.py:113. `path.write_text` rewrites LESSONS.md non-atomically. A running Factory appends via
   `lesson()`, so a concurrent run can lose lines. Low odds, but a read-modify-write on shared state.

9. LOW Re-running `retro` on the same day appends a duplicate set of lines (the test asserts this as intended).
   Repeated runs also keep stacking `[open]` lines, and an older `[open]` line per bucket gets resolved only when
   the new count is lower than that line's count.

10. LOW experiments/tt_interventions.py:20-30. The script now runs at import time (no `main()` guard), loses the
    per-bucket example output that the old docstring told readers to read, and its docstring still says "Answer
    (run 2026-11-12...)" for numbers the new code was not shown to reproduce. The path
    `Path.home() / "Programming/My_Projects/terminal-task-tracker"` is hard-coded to the owner's machine (it was
    before too, via the expanduser default).

11. LOW (tests) tests/test_retro.py:
    - `test_run_keeps_retro_lines` builds a `Factory` with `object.__new__`, bypassing `__init__`, which couples the
      test to the one attribute (`state`) that `reset_lessons` uses.
    - `test_retro_appends_dated_table` patches `Path.home` globally and compares to `date.today()` (a midnight
      flake). Pass `today=` instead.
    - No test covers the CLI message for the no-transcripts case (finding 1), and none covers the
      `counts[k] < old` boundary (equal count stays `[open]`).

## Spec

Skipped: no spec available (no issue or spec text was provided and the brief limited input to the diff). The diff
references "docs/factory-analysis.md section 3, P10", which was not read.

## Summary

Standards: 11 findings (4 MEDIUM, 7 LOW). Worst: retro lines living in the per-Run, Session-visible LESSONS.md
(finding 2), together with the misleading "appended" message when nothing was written (finding 1). Spec: not
reviewed.
