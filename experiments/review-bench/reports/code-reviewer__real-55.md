# Code review: real-55.diff

## Summary
Intent: move the owner-intervention counter from an experiment script into `factory.retro`, add a `factory retro PROJECT`
command that appends per-bucket count lines to `.factory/LESSONS.md`, and make `Factory.run` keep those lines when it
resets lessons. Overall: sound and small, but a few correctness gaps around the LESSONS.md lifecycle and the
`[resolved]` logic.

## Critical issues
None.

## Major issues
1. src/factory/retro.py:275-277 (major) - `[resolved]` logic compares only against the new count, but every run
   appends new `[open]` lines, and old `[open]` lines of a bucket that did NOT shrink stay `[open]` forever. After N
   retros each bucket has N `[open]` lines. Combined with the test asserting "appends, never overwrites", the file
   grows without bound and stale open lines are indistinguishable from the current one. Consider marking all older
   lines of a bucket superseded (or replacing them), not only shrunk ones.
2. src/factory/retro.py:277 (major) - a bucket that disappears entirely from `counts` (count 0) has `counts.get(m[1], 0)`
   = 0 < old, so it resolves: right. But a bucket with an equal count is left [open] while a new equal [open] line is
   appended, producing duplicates (see 1).
3. src/factory/run.py:304-305 (major/minor) - `path.write_text(...) if keep else path.unlink()` is a conditional
   expression used as a statement; hard to read. Use an if/else. Also, `reset_lessons` keeps `- retro ` lines that the
   Session-facing `lessons()` reader (run.py:~291) will now feed to every Ticket's Session as "mistakes not to repeat".
   Retro counts of owner interventions are not failure lessons; verify the prompt consumer tolerates or filters them,
   otherwise it injects noise into every Session prompt.

## Minor issues
4. src/factory/retro.py:233 (minor) - `f.read_text()` uses the default encoding and no `errors=`; a transcript with
   non-UTF-8 bytes raises UnicodeDecodeError and aborts the whole retro. Use `encoding="utf-8", errors="replace"`.
   Large transcripts are also read fully into memory; iterate the file instead.
5. src/factory/retro.py:240 (minor) - `d.get("message", {})` raises AttributeError if `message` is present but not a
   dict (e.g. null); also `d` may be a non-dict JSON line (a bare number parses fine) and `.get` fails. Guard with
   `isinstance(d, dict)`.
6. src/factory/retro.py:270-271 (minor) - when `total == 0` the CLI still prints "appended a retro table to ..." (cli.py
   ~148) though nothing was written, and the path may not exist. Return None or print a different message.
7. src/factory/retro.py:228 (minor) - `transcript_dir` depends on Claude Code's undocumented directory-naming scheme
   (non-alphanumerics -> `-`); fragile if that changes. Fine for now, but note it in a comment as an assumption.
8. src/factory/retro.py:279 (minor) - the line format is the contract between `retro()` and `ROW` (line 261) and
   `reset_lessons` (`"- retro "` prefix); the three are not tied together by a shared constant. A format tweak would
   silently break resolution.
9. src/factory/retro.py:277 - `ln.replace("[open]", "[resolved]", 1)` is fine since the regex anchors it, but the
   `m` walrus-less double use is slightly clumsy; minor.
10. experiments/tt_interventions.py:26 (minor) - the script lost the per-bucket example output and the session id /
    timestamp tracking (`messages()` now yields only text). That was the stated reason to "read the examples it
    prints" in the old docstring; the behavior regression is not mentioned. Also `sys.path.insert` + module-level
    execution with no `main()`/`__main__` guard means importing it runs it. The default path is also changed to
    `~/Programming/My_Projects/terminal-task-tracker` resolved through `transcript_dir`, which depends on that dir
    existing for `resolve()` symlink behavior (macOS /private prefixes could differ from the original hardcoded name).
11. src/factory/cli.py:147-149 (minor) - help text says "append a table" but lines are a bullet list, not a table
    (also the commit/docstring says "table"). Naming mismatch only.
12. src/factory/retro.py:259 `LABELS` vs `PATTERNS` - two near-identical module globals; compile inline instead.

## Tests
13. tests/test_retro.py:334-358 (minor) - monkeypatches `Path.home` globally via `setattr(Path, "home", lambda: ...)`;
    works but `lambda` ignoring `cls` is OK for classmethod replacement only when called as `Path.home()`; fine.
    The test asserts `date.today()` rather than injecting `today`, which can flake around midnight; use the `today`
    parameter (only reachable via `retro()`, not `main`).
14. Missing tests: (a) equal-count bucket stays open and duplicates; (b) `reset_lessons` with no retro lines unlinks the
    file; (c) `reset_lessons` when the file is absent; (d) malformed JSON shapes (item 5); (e) multiple `.jsonl` files /
    ordering; (f) CLI with a project lacking transcripts (item 6).
15. tests/test_retro.py:371-378 - constructs `Factory` via `object.__new__`, bypassing `__init__`; brittle if
    `reset_lessons` ever uses another attribute. Acceptable, but consider a small fixture.
16. The `run()` call site (run.py:209) is not covered by a test that `Factory.run` actually calls `reset_lessons`; only
    the method is tested.

## Positive feedback
- Good consolidation: one counter in the package, the experiment reduced to a thin caller.
- `total == 0` guard avoids falsely resolving buckets when transcripts are missing, and it has a test.
- The `[open]`/`[resolved]` line format is simple and greppable; the `retro()` function takes `directory` and `today`
  for testability.
- The tests cover the append behavior, resolution, and the Run-preserves-retro-lines interaction.

## Questions for author
- Should repeated retros replace the previous lines of a bucket rather than accumulate? What reads these lines?
- Do the retro lines get injected into Session prompts via `lessons()`? Is that intended?
- Is dropping the examples output from the experiment script intentional?

## Verdict
Comment / Request Changes (light): fix item 3 (confirm prompt injection) and item 1 (unbounded duplicate [open] lines);
the rest are minor hardening.
