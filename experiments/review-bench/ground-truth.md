# Ground truth (never shown to the reviewers)

## seeded-backup.diff (planted by hand, 4 defects)

- S1 Shell injection: `subprocess.run(f"tar czf {dest} -C {src} .", shell=True)` with unquoted, caller-controlled `src`.
- S2 Off-by-one in `prune`: `files[: len(files) - keep + 1]` deletes one backup too many (keeps `keep - 1`); with
  `len(files) < keep - 1` the slice index turns negative and deletes files that should stay.
- S3 Swallowed exception: `except Exception: pass` in `prune`, so a failed delete is silently dropped.
- S4 Missing test: `prune` has no test at all; only the happy path of `make_backup` is tested.

## real-56.diff (PR #56, triage of `[low]` loose ends)

- R56 `file_backlog` runs only on the normal exit of `run()`; the early `return 1` paths (resolver failed, a Ticket
  blocked) skip it, and the next Run's offset skips those items, so they never reach `BACKLOG.md`. Confirmed by reading
  `run.py` on the branch (2026-11-14).

## real-55.diff (PR #55, `factory retro`)

- R55 `retro()` writes nothing when no transcripts exist, but the CLI prints "appended a retro table" and exits 0.
  Confirmed by reading `retro.py` and `cli.py` on the branch (2026-11-14).

Findings outside this list are not automatically false: the judge checks them against the code and marks them valid,
invalid or unverifiable.
