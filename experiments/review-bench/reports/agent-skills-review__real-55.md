# Review: `factory retro` (retro.py, cli.py, run.py, tt_interventions.py, tests/test_retro.py)

Scope: only the diff real-55.diff was read. Nothing was run, so every claim below is from reading the diff. Callers of
LESSONS.md outside the diff were not inspected.

Verdict: Request changes (two Required items, the rest optional). The shape is sound: small, tested, and it
deletes the duplicate counter from the experiment script.

## Required

1. src/factory/cli.py:147-159 (with src/factory/retro.py:271-272) - Wrong success message when nothing is written.
   `retro()` returns early with `path` when `total == 0` (no transcripts, folder missing, or only echoes). The CLI then
   prints "appended a retro table to ...", although no file was touched. A mistyped project path or a Project with no
   transcripts looks like success. Fix: have `retro` return `None` (or raise a `ConfigError`-style error) when there is
   nothing to count, and print "no transcripts found in <dir>" with a non-zero or at least distinct message. The test
   `test_retro_without_transcripts_leaves_lessons_alone` pins the no-write behavior but not what the user is told.

2. src/factory/retro.py:261-281 and src/factory/run.py:289-305 - Retro lines now live in the file that every later
   Ticket's Session reads as "failure lessons" (see `lesson()` docstring: "read by every later Ticket's Session in this
   Run"). Unverified, because the consumer is outside the diff: if the file is injected into prompts, each Session now
   receives up to 12 lines per retro run of owner-intervention statistics that are not about a Ticket failure. That is
   token cost plus noise, and a wrong signal for the agent. Also, anything that parses "- N slug [open] ..." lines
   (the failure-lesson format) must tolerate the `- retro BUCKET [open] ...` shape. Fix: confirm what reads LESSONS.md;
   if it feeds prompts, filter out `- retro ` lines there, or keep retro output in its own file (for example
   `.factory/RETRO.md`), which would also remove the need for `reset_lessons` entirely (net deletion of code).

## Optional

3. src/factory/retro.py:275-279 - Open lines accumulate without bound. Every run appends a fresh `[open]` line per
   bucket, and an older line only flips to `[resolved]` when the new count is strictly lower. A stable or growing
   bucket leaves N identical-bucket `[open]` lines after N runs (the test even asserts `count == 2` as intended
   behavior). Consider: replace the older `[open]` line of the bucket instead of appending when the count is not lower,
   or document why history is wanted. Also, a bucket that grows then shrinks resolves only the lines with a higher
   count, which is correct but not covered by a test.

4. src/factory/retro.py:191-222 - Owner-specific heuristics shipped in a general factory module: `JOH-\d+`, "Ok, np",
   the typos "aggree", "youself", "Do all designes", "Fix all!". Fine for the one project the counts came from, but
   `factory retro` runs on any Project and will mislabel or miss for everyone else. Consider: keep the pattern table in
   the experiment, or make it config, when a second Project needs it. At minimum, say so in the module docstring (the
   "+/-10 %" claim applies only to terminal-task-tracker).

5. src/factory/retro.py:231 - `sorted(..., key=mtime)` is dead work now: the old script printed session id and
   timestamp, the new `messages()` yields only text, and the counts are order-independent. Drop the sort and the
   `stat()` calls: `for f in directory.glob("*.jsonl")`. (YAGNI.)

6. src/factory/retro.py:233 - `f.read_text().splitlines()` loads each whole transcript into memory (these files can be
   tens of MB) and decodes with the locale default encoding; a stray bad byte raises `UnicodeDecodeError` and aborts the
   whole retro. Iterate the file (`for line in f.open(encoding="utf-8", errors="replace")`) instead.

7. src/factory/retro.py:205, 211 - Patterns with a bare `.*` (`is .* finished`, `Consider .* approved`) under `re.I`
   run per start position over each line, so a long pasted log with many "is " occurrences is quadratic. Counts are
   bounded by message size, so this is a slowdown, not a hang; cap the span (`.{0,80}`) if retro ever feels slow.

8. experiments/tt_interventions.py - Behavior regression versus the old script: the per-bucket example lines (session
   id, date, snippet) are gone, yet the old docstring told the reader to "read the examples it prints" to sanity-check
   the regex labels, and the new script no longer says so. Also the script now runs at import time with no
   `if __name__ == "__main__":` guard and uses a `sys.path.insert` hack, while the docstring says
   `python3 -I` (works only because of the explicit insert). Acceptable for an experiment; either restore examples or
   note that the sanity-check was dropped.

9. tests/test_retro.py:371-378 - `object.__new__(Factory)` plus setting `r.state` bypasses the constructor and will
   break silently if `reset_lessons` ever touches another attribute. `reset_lessons` only needs a path, so making it a
   small function taking `state: Path` (or testing through a real `Factory`) is sturdier. Coverage gaps to add: an
   `[open]` line whose count is not lower stays open; a `[resolved]` line is not re-matched; `reset_lessons` with no
   retro lines deletes the file; CLI output when there is no data (item 1).

## Nit

10. src/factory/run.py:305 - `path.write_text("".join(keep)) if keep else path.unlink()` is a conditional expression
    used as a statement. Write it as a plain `if keep: ... else: ...`.

11. tests/test_retro.py:355 - asserts `date.today()`, which can flake across midnight (the test calls `main`, so `today`
    cannot be injected). Use `freezegun` only if already a dependency; otherwise assert with a regex for a date.

12. src/factory/retro.py:1,264 and cli.py:147 - the text says "table", but the output is a list of `- retro ...` lines.
    Say "lines" so the help text matches the file.

13. src/factory/cli.py:147-149 - the `sub.add_parser(...).add_argument(...)` chain wrapped over three lines is hard to
    read; match how `status` is written or give `retro` its own variable.

## Axis summary

- Correctness: Required items 1 and 3 (message honesty, accumulation). Resolve logic and the `total == 0` guard are
  reasoned correctly and tested.
- Readability: clear names; items 10, 12, 13.
- Architecture: `retro` is correctly handled before `load_config`, and the duplicate counter is deleted from the
  experiment (good). Concern: item 2 (mixing two kinds of record in LESSONS.md) and item 4.
- Security: no injection or secret flow; only counts, no message text, are written. Transcripts are private files that
  are read locally, and the output path is fixed under the project. No findings.
- Performance: items 5, 6, 7; none are blocking at the stated scale (61 files).

## Verification story

Not run: tests and linter were not executed in this review (diff-only). The author should show `make test` and lint
output, including the new tests/test_retro.py.
