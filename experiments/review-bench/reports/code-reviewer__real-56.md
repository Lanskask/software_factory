# Code review: real-56.diff

Line references are to the diff file (real-56.diff) with the source file named.

## 1. Summary

Intent: at the end of a Run, each `[low]` loose end this Run logged in `LOOSE-ENDS.md` is written as one
`- [ ] <item> (from NN slug)` line in `.factory/BACKLOG.md`, and `factory status` lists them. Overall the change is small
and sensible, but the "never filed twice / a dropped line stays dropped" guarantee is not actually tested, and items
from a Run that stops early are lost for good.

## 2. Critical issues

None.

## 3. Major issues

- **[Major] src/factory/run.py:116-117 (diff lines 116-117) and the early `return 1` at diff line 265: a Run that
  stops early never files its `[low]` items, and a later Run never will either.** `file_backlog` is only reached when
  the loop finishes normally. The resolver-failed "Stopping" path (and any other early return or exception in the loop)
  skips it. The next Run starts with `logged_before = self.loose_ends_size()`, which is already past those lines, so
  the `[low]` items logged by the stopped Run are silently dropped from the Backlog forever (they remain only in
  `LOOSE-ENDS.md`). That contradicts "at the end of the Run each `[low]` item becomes one Backlog ticket line".
  Suggest wrapping the loop in `try/finally` that calls `file_backlog(logged_before)`, or persisting the "filed up to"
  offset in `.factory/` instead of an in-memory size.

- **[Major] tests/test_run_e2e.py:189-203 (diff lines 189-203): the test does not prove the dedup / "dropped stays
  dropped" claim.** The second `factory(project).run()` very likely has no `todo` Tickets left, so nothing is appended
  to `LOOSE-ENDS.md`, `file_backlog` returns 0 at the `size <= start` guard, and the `count == 1` assertion passes
  without ever exercising the `line not in have.splitlines()` check. Both the offset guard and the dedup are
  untested. Add a Run that logs the same `[low]` text again from the same ticket (for example a re-opened Ticket) and
  assert it is not re-filed unless intended; also a unit test of `file_backlog` with a pre-existing line.
  Also assert the second Run's return code instead of discarding it.

## 4. Minor issues

- **[Minor] src/factory/run.py:136-138 (diff 136-138): dedup only against the existing file, not within `new`.** If the
  same Ticket logs two identical `[low]` lines in one Run (two Handoffs after a retry, or two identical bullets), both
  are written, contradicting "never filed twice". Also `have.splitlines()` is recomputed per item (O(n*m)); compute a
  `set` once and add to it as you go.

- **[Minor] src/factory/run.py:138: read-whole-file then `write_text` instead of append.** If the Owner is editing
  `BACKLOG.md` while a Run is in flight, their edits are overwritten with the stale `have`. Opening with `"a"` and
  writing the header only when the file is new avoids the race and is shorter. It also rewrites the file (and creates
  it with only the header) even when `new` is empty, for example when the Run logged only `[high]` lines.

- **[Minor] src/factory/prompts.py:71 (diff 71): `_SOURCE` duplicates the header format written by
  `log_loose_ends` in run.py.** The coupling is only a comment; if the header format changes, `low_loose_ends`
  silently returns nothing (the `source` stays empty and every item is skipped). Either build the header from a shared
  constant/function or add a test that round-trips `log_loose_ends` output through `low_loose_ends` (the e2e test
  partly does).

- **[Minor] src/factory/prompts.py:87 (diff 87): continuation detection treats any indented non-blank line as a
  wrapped line.** An indented sub-bullet (`  - detail`) under a `[low]` item is merged into the item text. Also an
  empty item (`- [low] ` with nothing after) produces `- [ ]  (from ...)`. Cheap to guard with `if text`.

- **[Minor] src/factory/cli.py:100-105 (diff 100-105): status counts only lines starting `- [ ]`.** Items the Owner
  ticks `- [x]` disappear from status (probably intended), but ticked lines also no longer match the dedup check in
  `file_backlog`, so an identical later item would be re-filed. Decide and document.

- **[Minor] Duplicate reporting:** `cmd_status` now prints both "Loose ends: N low" and "Backlog: M [low]"; the two
  counts can legitimately differ and may confuse. A one-line note in the README would do.

## 5. Positive feedback

- Plain file write, no Session, no cost; the DECISION-LOG entry gives reasons (YAGNI, no cost, `tickets.py` has no
  `new`, unattended pickup risk) and explicitly states what is skipped.
- Offset-based "only what this Run appended" is a simple way to keep resolver text and old Runs out.
- `low_loose_ends` is a pure function with a focused unit test that covers wrapped lines, `[high]` skipping, a second
  section, and resolver-decision comments.
- Docs (README, SKILL.md, DECISION-LOG) updated together with code.

## 6. Questions for author

1. Is it intended that a Run stopped by a `[high]` / resolver failure loses its `[low]` items from the Backlog?
2. Is `.factory/` git-ignored? The Run requires a clean tree; a newly created tracked `BACKLOG.md` would dirty it
   (LOOSE-ENDS.md has the same property, so presumably fine).
3. Is the character-offset (`len(text)`) approach safe if the Owner edits `LOOSE-ENDS.md` between Runs? It is only
   in-memory per Run, so it appears so, but a truncation mid-run would make `[start:]` skip content.

## 7. Verdict

Request Changes (light): fix the early-stop loss (or document it as intended) and make the e2e test really exercise
the dedup path. Everything else is minor.
