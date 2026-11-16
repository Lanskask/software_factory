# Review: [low] loose ends become Backlog ticket lines (real-56.diff)

Verdict: Request changes (2 Required, rest optional). Review read from the diff only; tests were not run.

## Required

1. src/factory/run.py:268-270 (`run`) - Early exits lose loose ends forever. `file_backlog` runs only on the normal
   loop exit. The `return 1` paths (resolver failed on a `[high]` loose end, line ~265) skip it, and the next Run sets
   a new `logged_before = loose_ends_size()`, so the `[low]` items already logged this Run are never filed. Those are
   exactly the Runs where the Owner most needs the Backlog. Fix: call `file_backlog` in a `try/finally` around the loop,
   or file right after each `log_loose_ends`. Add a test with a Run that stops on `[high]` and still has `[low]`.

2. src/factory/run.py:134-138 (`file_backlog`) - If the Owner hand-edits BACKLOG.md and leaves no trailing newline,
   `have + "- [ ] ..."` glues the new line onto the last one and corrupts both (status then shows one merged item).
   Fix: `if have and not have.endswith("\n"): have += "\n"`.

## Optional

3. tests/test_run_e2e.py:196-198 - The "dropped stays dropped / never filed twice" half of the test is weak. The second
   Run logs no new loose ends, so `file_backlog` returns at the `size <= start` guard and the `line not in
   have.splitlines()` filter (run.py:137) is never exercised. Removing that filter keeps the test green. Add a case where
   a later Run logs the same line again (same Ticket re-run), or delete the filter if the offset already guarantees
   once-only (YAGNI).

4. src/factory/run.py:137 - `new` is only deduped against `have`, not against itself, so a duplicate line within one
   Run is written twice. Minor; fold into item 3.

5. src/factory/prompts.py:71 vs src/factory/run.py:~326 - `_SOURCE` regex is an implicit contract with the header
   string f-string in `log_loose_ends`. Changing either silently yields zero items (no error). Share one format
   constant, or at least add a comment at the writer pointing to the regex.

6. src/factory/prompts.py:74-91 (`low_loose_ends`) - Two parallel states (`source`, `in_item`) plus `items[-1]`
   mutation is a small state machine; readable enough, but `items: list[list[str]]` with `[text, source]` positional
   fields is easy to misuse. A `(text, source)` tuple list rebuilt, or building the final string directly, is clearer.

7. Test gaps in tests/test_prompts.py:162 - Not covered: a wrapped line following a `[high]` item (should be dropped,
   code does drop it via the else branch), a `[low]` before any header (ignored via `source == ""`), and a blank line
   ending a wrapped item. Behavior looks right; one more assertion each is cheap.

## Nit

8. src/factory/cli.py:53 - The one-line conditional comprehension is 119 columns and hard to scan. Split into
   `items = []` / `if backlog.exists(): items = [...]`.

9. Naming - "Backlog tickets" / "ticket lines" vs. real tickets in the tracker (the DECISION-LOG explicitly says they are
   not tickets). The run message (run.py:117) and README say "filed as Backlog tickets"; "Backlog items" would avoid
   confusion with tracker Tickets.

10. src/factory/run.py:125-127 - `loose_ends_size` reads the whole file just to get a length (it must be characters to
    match the `str` slice, so `stat().st_size` would be wrong for non-ASCII). Fine; a one-line comment saying why would
    prevent a "cleanup" that breaks the offset.

## FYI

- Security: Handoff text is written by an LLM Session and copied into BACKLOG.md, then read by the factory skill, which
  asks the user. It is untrusted text but is only listed, never executed or fed unreviewed into a Session; the status
  output prints it raw to the terminal (control characters possible, low risk).
- Performance: all file reads are small and once per Run/status; no concern.
- Docs/decision log (README.md, docs/DECISION-LOG.md, skills/factory/SKILL.md) are consistent with the code and give
  reasons; good.
- Size: about 190 changed lines across 8 files, one logical change; acceptable.
