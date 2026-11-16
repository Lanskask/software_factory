# Review of real-56.diff

1. src/factory/run.py:268 (diff lines 116-117), severity medium. Low loose ends are lost permanently when a Run
   exits early.
   - `file_backlog` runs only on the normal fall-through at the end of `run()`.
   - The early `return 1` paths skip it. One is the resolver failing on a `[high]` loose end. Any other early return
     or exception in the loop does the same.
   - The next Run takes a fresh `logged_before = loose_ends_size()`, which is already past those Handoffs.
   - So the `[low]` items logged by the stopped Run are never filed. This contradicts the README claim "At the end of
     the Run each [low] item becomes one Backlog line". It also contradicts the DECISION-LOG claim that it is "never
     filed twice" and not lost.
   - Fix: wrap the loop in try/finally, or file on every exit path. Alternatively persist the offset, or scan the
     whole LOOSE-ENDS.md and rely on the existing dedup. The dedup already makes a full scan safe, but it would
     resurrect items the Owner deleted from BACKLOG.md.
   - No test covers an early-stop Run.

2. src/factory/run.py:136-137 (diff lines 136-138), severity low. Duplicates inside one Run are not deduplicated.
   - `have.splitlines()` is computed once per line and is never updated with the lines already chosen in `new`.
   - Two identical `[low]` items in one Handoff, or two Handoffs from the same ticket and slug, are both written.
   - This contradicts the "never filed twice" claim.
   - The membership test is also O(n*m). Use a set that grows as lines are accepted.

3. src/factory/run.py:125-139, severity low. The offset logic is fragile.
   - `start` is a character offset into LOOSE-ENDS.md, taken at Run start.
   - If the Owner edits or trims LOOSE-ENDS.md while the Run is in progress, the slice `[start:]` misaligns. It may begin mid-line or skip new items.
   - If the file is shortened, `loose_ends_size() <= start` returns 0 and the Run's items are silently not filed.

4. src/factory/prompts.py:84-90, severity low. Parsing is too loose.
   - The continuation rule joins any indented non-empty line after a `[low]` item.
   - Nested sub-bullets, or an indented code fence, are glued into the item text.
   - A `- [low]` inside a fenced code block in a Handoff is also treated as an item.
   - There is no test for nested bullets or a continuation line followed by a non-indented line.

5. src/factory/cli.py:100-105, severity low. Status counts only lines starting with `- [ ]`.
   - Items the Owner ticks as `- [x]` vanish from status without being "dropped".
   - A missing header or other text is ignored silently. This is acceptable but undocumented.
   - Status also prints the full text of every item. A large backlog floods the output, and there is no cap.

6. tests/test_run_e2e.py:189-203, severity low. The test is weak on its dropped-item claim.
   - The test overwrites `config.toml` mid-test only to make `status` work. That suggests an unrelated fixture gap.
   - The second `factory(project).run()` is not asserted to have actually executed or logged anything.
   - So "a later Run files neither the same nor a dropped loose end again" may pass vacuously, if the second Run
     finds no tickets or logs no new Handoff.
   - The test should assert that the second Run produced a new loose-end entry in LOOSE-ENDS.md.
