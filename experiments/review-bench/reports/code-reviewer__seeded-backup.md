# Code review: src/backup.py and tests/test_backup.py (seeded-backup.diff)

## 1. Summary

The change adds `make_backup` (tar.gz a folder into a timestamped file) and `prune` (delete all but the newest N
backups), plus one test for `make_backup`. Overall: not mergeable. `prune` has an off-by-one that deletes a backup it
should keep, `make_backup` is open to shell injection, and `prune` has no tests at all.

## 2. Critical issues

### C1. Shell injection and breakage on special characters (src/backup.py:17) - Critical (security, correctness)

```python
subprocess.run(f"tar czf {dest} -C {src} .", shell=True, check=True)
```

`src` and `dest_dir` are interpolated unquoted into a shell command. A path containing a space, `;`, `$(...)`,
backticks or `&` either breaks the command or runs arbitrary commands (OWASP A03 Injection). Even with benign input,
a project folder named `my project` fails. Fix: no shell, argument list:

```python
subprocess.run(["tar", "czf", str(dest), "-C", src, "."], check=True)
```

### C2. Off-by-one in prune keeps `keep - 1` backups (src/backup.py:24) - Critical (data loss)

```python
old = files[: len(files) - keep + 1]
```

With 5 files and `keep=5`, this is `files[:1]`, so it deletes the oldest file even though nothing should be deleted.
With `keep=3`, only 2 survive. The docstring says "all but the newest `keep`", so the slice must be
`files[: len(files) - keep]`. Related edge cases that the current expression handles badly:

- `keep > len(files)`: the negative slice end is only harmless by accident (it yields an empty list for some values
  and a wrong one for others, e.g. 5 files and `keep=5`).
- `keep < 0`: slice end exceeds `len(files)`, so everything is deleted. Validate `keep >= 0`.
- `keep == 0` with the fixed formula works (`files[:len]`), but with the buggy formula it relies on slice clamping.

Suggested fix:

```python
if keep < 0:
    raise ValueError("keep must be >= 0")
old = files[: max(len(files) - keep, 0)]
```

This deletes backups, so the bug is irreversible data loss.

## 3. Major issues

### M1. Silent swallowing of all deletion errors (src/backup.py:27-31) - Major

`except Exception: pass` hides permission errors, missing files and I/O problems. The caller cannot tell why a backup
was not pruned and disk usage grows silently. At minimum catch `OSError`, and log or collect failures; the return
value documents "the deleted paths", so a failure should not look like success. Consider `except FileNotFoundError:`
(already gone, fine) and letting other `OSError`s propagate.

### M2. prune deletes any `*.tar.gz` in the directory (src/backup.py:23) - Major (data loss)

The glob matches every `.tar.gz` in `dest_dir`, including backups of other projects or unrelated archives that share
the directory. `make_backup` names files `<name>-<timestamp>.tar.gz`, so `prune` should take the project name (or a
prefix) and glob `f"{name}-*.tar.gz"`. Ordering by `st_mtime` is also fragile (copying or restoring files changes
mtime); the timestamp is already in the filename.

### M3. Two backups in the same second overwrite each other (src/backup.py:16) - Major

`int(time.time())` has 1-second resolution, so a second call in the same second silently overwrites the first
archive. Use a finer or formatted timestamp (`time.strftime("%Y%m%d-%H%M%S")`, plus microseconds or an existence
check).

### M4. No test for `prune`, the destructive function (tests/test_backup.py) - Major

`prune` is untested, which is how C2 got through. Add tests: N files with `keep=N` deletes nothing; `keep=2` of 5
leaves the 2 newest; `keep=0`; fewer files than `keep`; empty directory; unrelated files untouched. Set mtimes with
`os.utime` for deterministic ordering.

## 4. Minor issues

- tests/test_backup.py:12: the test only asserts the file exists. Check that the archive is valid and contains
  `a.txt` (`tarfile.open(...).getnames()`). Add a case with a space in the source name; it would have caught C1.
- src/backup.py:14: `dest_dir` is not created or checked. If it does not exist, `tar` fails with an unhelpful error;
  `Path(dest_dir).mkdir(parents=True, exist_ok=True)` is cheap.
- src/backup.py:14-17: if `dest_dir` is inside `src`, the archive includes itself or earlier backups. Worth
  documenting or guarding against.
- src/backup.py:14,21: parameters typed `str` while `Path` is used internally; accept `str | Path` and drop the
  `str()` calls in tests.
- src/backup.py:17: `check=True` raises `CalledProcessError`; a partially written archive is left behind on failure.
  Consider removing `dest` on error. Alternatively use the stdlib `tarfile` module, which removes the external
  dependency on `tar` and the shell entirely.

## 5. Positive feedback

- Small, focused module with clear docstrings stating the contract (name format, "all but the newest `keep`").
- `check=True` makes failures loud instead of returning a path to a missing archive.
- Test uses `tmp_path`, so it is isolated and leaves nothing behind.
- Sorting by an explicit key and returning the deleted paths makes `prune` easy to assert on.

## 6. Questions for author

1. Is `dest_dir` ever shared across projects? If yes, M2 is a real data-loss path today.
2. Should `prune` run automatically after `make_backup`? If so, C2 means every call loses one extra backup.
3. Is `tar` guaranteed on the target platform (it is BSD tar on macOS, GNU tar on Linux)? `tarfile` would avoid the
   question.

## 7. Verdict

Request Changes. Must fix before merge: C1 (shell injection), C2 (off-by-one deleting a backup that should be
kept), and M4 (tests for `prune`). M1-M3 should be fixed in the same change as they are small.
