# Ponytail review: real-56.diff

What this change does: At the end of a Run, each `[low]` item in the new Handoffs of `.factory/LOOSE-ENDS.md` is copied
as one `- [ ] ... (from NN slug)` line into `.factory/BACKLOG.md`. No Session is used. `factory status` then prints that
list. Assumed load: one person running one Run at a time on a laptop.

## Must fix

None.

## Should fix

1. **Early stop loses the Backlog for that Run** (`src/factory/run.py:L265-268`, call at `L268-269`)
   - **What this is:** `file_backlog` runs only after the ticket loop ends normally.
   - **Problem:** When the Run stops on a `[high]` loose end whose resolver fails (the `return 1` just above), the
     `[low]` items from earlier Tickets in this Run are never filed. The next Run starts a new offset
     (`loose_ends_size()` at `L233`), so they are never filed later either. This is exactly the Run where the Owner is
     reading loose ends.
   - **Fix:** Call `file_backlog` on every exit path. A `try/finally` around the loop does it. Or record the offset in
     a file and file from it at the start of the next Run.
   - **If we skip it:** After any stopped Run, the `[low]` items are only in `LOOSE-ENDS.md`, not in the Backlog list,
     and the README says every `[low]` item becomes a Backlog line.

2. **The "never filed twice" test does not test it** (`tests/test_run_e2e.py:L196-198`)
   - **What this is:** The test drops one Backlog line, runs again, and expects it not to come back.
   - **Problem:** The second Run has no Tickets left, so `file_backlog` returns at the `size <= start` check
     (`run.py:L132`). The dedup line (`L137`) is never reached. Delete the dedup and the test still passes.
   - **Fix:** Make the second Run log a new Handoff with the same text, or call `file_backlog(0)` directly. Assert the
     dropped line does not return only if that is really the intended rule.
   - **If we skip it:** The dedup code is untested and can break unseen.

3. **The docs promise more than the code does** (`docs/DECISION-LOG.md`, "a line the Owner deletes stays deleted")
   - **What this is:** The log says a dropped line stays dropped.
   - **Problem:** It stays dropped only because the offset skips old text. If the same ticket is run again and logs the
     same text, the line comes back. The check `line not in have.splitlines()` only sees lines still in the file.
   - **Fix:** Reword the log to "only what this Run appended is filed", or drop the "stays deleted" claim.
   - **If we skip it:** The Owner trusts a guarantee that is not there.

## Nice to have

4. **LOOSE-ENDS.md is read twice** (`src/factory/run.py:L125-139`)
   - **What this is:** `loose_ends_size()` reads the whole file for its length, and `file_backlog` reads it again.
   - **Problem:** Extra code for a size helper. It is also computed twice at the end.
   - **Fix:** Save `start = len(text)` where the file is read once, or use `Path.stat().st_size` (bytes) consistently
     for both start and slice by reading bytes. Today chars and chars match, so it is correct, just longer than needed.
   - **If we skip it:** Nothing breaks.

5. **Empty Backlog file is created** (`src/factory/run.py:L134-138`)
   - **What this is:** The file is always written when the loose-ends log grew.
   - **Problem:** If the new Handoffs had no `[low]` items (only `[high]`), a `BACKLOG.md` with just `# Backlog` is
     created.
   - **Fix:** `if not new: return 0` before the write.
   - **If we skip it:** A harmless empty file.

6. **Long one-line comprehension** (`src/factory/cli.py:L53`)
   - **What this is:** A list comprehension with a conditional expression at the end, about 118 columns.
   - **Problem:** Hard to read at a glance.
   - **Fix:** `lines = backlog.read_text().splitlines() if backlog.exists() else []`, then filter on the next line.
   - **If we skip it:** Only readability.

Verdict: fix 1 and 2 first.
Lean: about -3 lines possible (items 4 and 5).
Not checked: the rest of `run()` (other `return` paths besides the one shown in the diff), and whether the tests pass.
