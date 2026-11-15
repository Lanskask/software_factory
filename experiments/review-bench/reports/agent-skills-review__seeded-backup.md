# Review: seeded-backup.diff (src/backup.py, tests/test_backup.py)

Verdict: REQUEST CHANGES. Two Critical bugs, several Required items.

## Critical

1. [Security] src/backup.py:17 - Shell injection / breakage on odd paths.
   `subprocess.run(f"tar czf {dest} -C {src} .", shell=True)` interpolates unquoted, caller-controlled
   `src` and `dest_dir`. A path with spaces breaks it; one containing `;`, `$(...)` or backticks runs
   arbitrary commands.
   Fix: `subprocess.run(["tar", "czf", str(dest), "-C", src, "."], check=True)` (no shell).

2. [Correctness] src/backup.py:24 - Off-by-one in `prune`; it keeps `keep - 1` backups, not `keep`.
   `files[: len(files) - keep + 1]` marks one too many for deletion (10 files, keep=3 deletes 8, keeps 2).
   Data loss: the docstring promises "all but the newest `keep`".
   Fix: `old = files[: max(len(files) - keep, 0)]`.
   Also, when `keep > len(files)` the slice end goes negative and deletes from the wrong end
   (3 files, keep=5 gives `files[:-1]`, deleting 2 of 3). The `max(..., 0)` guard fixes this.
   Validate `keep >= 0` (negative keep deletes everything or raises confusingly).

## Required

3. [Correctness/Security] src/backup.py:23 - `prune` globs every `*.tar.gz` in `dest_dir`, not just this
   project's backups. A shared backup dir means pruning project A deletes project B's archives and any
   unrelated tarball. Fix: take the project name/prefix and glob `f"{name}-*.tar.gz"`.

4. [Correctness] src/backup.py:27-31 - `except Exception: pass` silently swallows every unlink error
   (permissions, I/O). The caller cannot tell the retention policy failed, and disk space quietly grows.
   Fix: catch `OSError` only (or `FileNotFoundError` to tolerate races), and log or re-raise the rest.

5. [Correctness] src/backup.py:16 - Name uses `int(time.time())`, so two backups in the same second get
   the same path and the second overwrites the first. Fix: use a finer timestamp (`time.time_ns()` or
   `%Y%m%dT%H%M%S` plus a uniqueness check) or open with exclusive creation.

6. [Correctness] src/backup.py:16-17 - If `dest_dir` is inside `src`, the archive includes itself
   (tar warns "file changed as we read it"/grows). `dest_dir` is also never created, and
   `make_backup` raises a `CalledProcessError` with no useful message when it is missing.
   Fix: `Path(dest_dir).mkdir(parents=True, exist_ok=True)`; reject or exclude a `dest_dir` inside `src`.
   A partial/failed archive is also left on disk when tar fails; remove it in an `except`.

7. [Tests] tests/test_backup.py:1-12 - `prune` has no tests at all, and it is where both Critical bugs are.
   Add: keeps exactly N newest; keep > count deletes nothing; keep=0; ignores non-matching files;
   unlink failure behavior. Write the off-by-one test first, since it currently fails.
   `make_backup` is only checked with `.exists()`: assert the archive lists `a.txt`
   (`tarfile.open(...).getnames()`), and add a test with a space in the path (fails today because of #1).
   Note: `from backup import make_backup` only works if `src/` is on `sys.path` (pytest `pythonpath`
   config not in this diff); confirm it is set.

## Optional

8. [Readability/Architecture] src/backup.py:14,21 - Parameters typed `str`; accept `Path | str`
   and convert once. In `prune`, `sorted(..., key=mtime)` is fine, but mtime ties (same-second backups)
   give nondeterministic order; sort by `(st_mtime_ns, name)` for stability.
9. [Architecture] src/backup.py:1-32 - `make_backup` and `prune` are independent and must both be
   called by the user with consistent `dest_dir`; consider a small `backup_and_prune(src, dest_dir, keep)`
   only if a caller needs it (YAGNI otherwise).
10. [Security] src/backup.py:17 - Use Python's `tarfile`/`shutil.make_archive` instead of spawning `tar`;
    removes the external dependency and the quoting problem entirely (alternative to fix #1).

## Nit

11. src/backup.py:25-31 - Build `deleted` through the loop is fine, but a bare `pass` hides intent;
    add a comment or log line when skipping.
12. src/backup.py:7 - `time` import is only used for the name; if switching to `datetime`, tidy imports.

## Performance
No concerns: one directory glob and one `stat` per file; fine at realistic backup counts.
