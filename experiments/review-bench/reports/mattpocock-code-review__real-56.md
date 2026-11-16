# Code review: real-56.diff (mattpocock-skills:code-review)

Method note: the diff was reviewed directly, without the skill's two parallel sub-agents, because the task forbids
reading anything but the diff. No spec file was supplied, so the Spec axis is checked only against the claims the diff
makes about itself (README item 7, DECISION-LOG entry, SKILL.md). Line numbers refer to the diff file.

## Standards

Documented standards in the diff context: YAGNI and the decision-log rule (both met: the DECISION-LOG entry records
reason and rejected alternatives). The rest are baseline smells, so all are judgement calls.

1. [medium] real-56.diff:136-138 (`src/factory/run.py`, `file_backlog`): possible bug, not only style. `have` is
   `backlog.read_text()`; if the Owner's editor left no trailing newline, the first new line is glued onto the last
   existing line (`have + "".join(...)`). Fix: `have.rstrip("\n") + "\n"` before appending, or open in append mode.
2. [low] real-56.diff:137: `have.splitlines()` is recomputed for every candidate line (O(n*m)), and `new` is never
   checked against itself (see Spec 2). Compute `seen = set(have.splitlines())` once and add to it in the loop.
3. [low] real-56.diff:138: `backlog.write_text` runs even when `new` is empty, so a Run that logged only `[high]` items
   creates `BACKLOG.md` containing just the `# Backlog` header. Return early when `new` is empty.
4. [low] real-56.diff:76: possible Primitive Obsession / Data Clump: `items: list[list[str]]` with `[text, source]` and
   positional mutation `items[-1][0] += ...`. A tuple list rebuilt at the end, or a tiny dataclass, reads better.
5. [low] real-56.diff:80-90: the `in_item` / `source` two-flag state machine is easy to get wrong. A nested sub-bullet
   such as `  - detail` under a `[low]` item starts with a space and is joined into the item text as `- detail`.
   Probably rare, but unspecified.
6. [low] real-56.diff:125-136: possible Duplicated Code: `self.state / "LOOSE-ENDS.md"` is now built in three places
   (with the existing `log_loose_ends`). `loose_ends_size` returns a character count, not a size in bytes, which is
   fine for the slice but the name is slightly misleading.
7. [low] real-56.diff:53 (`src/factory/cli.py`): the one-line conditional comprehension is about 118 columns and
   dense; two plain statements would read better. `cmd_status` now also does file parsing that belongs next to the
   Backlog writer (the `- [ ]` format is known in two modules).
8. [low] real-56.diff:117: message says "filed as Backlog tickets" but they are lines in a markdown file, which the
   DECISION-LOG explicitly says are not tickets. Wording inconsistency.

## Spec

Against the claims in README item 7 and the DECISION-LOG entry:

1. [medium] real-56.diff:112-116 (`run`): "At the end of the Run each `[low]` item becomes one Backlog line". Filing only
   happens when the loop falls through. The existing early `return 1` (resolver failed, line 115) skips
   `file_backlog`, and so would any exception or Ctrl-C. Because the next Run sets `logged_before` to the current
   end of `LOOSE-ENDS.md`, the `[low]` items logged before the stop are never filed, ever (they stay only in
   `LOOSE-ENDS.md`). Fix: call `file_backlog` in a `finally`, or on every exit path; or use a persisted
   "filed up to" marker rather than the in-memory offset.
2. [medium] real-56.diff:137 and DECISION-LOG line 31 ("a line already in the file is not written again", README
   "never filed twice"): duplicates are only checked against the file as read before this call, not within `new`.
   Two identical `[low]` items from the same ticket (or a ticket retried and logged twice in one Run) are written
   twice. Across Runs, a retried ticket that re-logs the same Handoff re-files a line the Owner already deleted, so
   "a line the Owner deletes stays deleted" holds only while nothing new is logged for that ticket. Also an item the
   Owner ticks (`- [x]`) or rewords is refiled.
3. [low] real-56.diff:132: `if self.loose_ends_size() <= start: return 0` silently skips filing if the Owner trimmed
   `LOOSE-ENDS.md` during the Run (size drops below `start`), and slices wrong content if they edited it (offset no
   longer matches). Acceptable for a first slice but worth a note in the decision log.
4. [low] The DECISION-LOG date (2026-11-12) and the `docs/factory-analysis.md P3` reference could not be verified from
   the diff alone.

## Tests

1. [medium] real-56.diff:196-198: the "dropped line stays dropped" assertion does not exercise the dedup path. All
   tickets are already done on the second Run, so nothing new is appended to `LOOSE-ENDS.md` and `file_backlog`
   returns at the size check (line 132). Deleting the `line not in have.splitlines()` filter would not fail this
   test. Add a case where a new Handoff repeats a dropped item.
2. [low] real-56.diff:189-203: one test covers filing, dedup and `factory status` output, and rewrites
   `config.toml` mid-test to make `main(["status", ...])` work. Split into at least a filing test and a status
   test so a failure points at one behaviour.
3. [low] Missing cases: no trailing newline in an existing `BACKLOG.md`; early stop (resolver failure) with `[low]`
   items already logged; identical items in one Run; nested/indented sub-bullets in `low_loose_ends`.
   `test_low_loose_ends_joins_wrapped_items_and_skips_high_and_resolver_text` is otherwise a good focused unit test.

## Summary

Standards: 8 findings, all judgement calls; worst is the missing-trailing-newline concatenation in `file_backlog`.
Spec: 4 findings; worst is that an early stop of the Run permanently loses the already-logged `[low]` items from the
Backlog (contradicts "at the end of the Run" and "never lost"). Tests: the dedup path is untested.
