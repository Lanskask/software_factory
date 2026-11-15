# Code review: seeded-backup.diff (mattpocock-skills:code-review)

Notes on method: the skill assumes a git fixed point, an issue tracker and repo standards docs. The task limited me to
the diff file, so no git commands were run, no standards docs were read and no spec was available. The Spec sub-agent
was skipped ("no spec available"). The two axes are reported separately and not reranked. Both axes were checked by me
directly, without spawning sub-agents.

## Standards

No documented repo standards were available. Findings come from the smell baseline plus general correctness and safety.

1. src/backup.py:17 - HIGH (hard). Shell injection and breakage on special characters. `subprocess.run(f"tar czf {dest}
   -C {src} .", shell=True, ...)` interpolates unquoted caller-supplied paths into a shell string. A `src` or
   `dest_dir` with spaces breaks the command, and one containing `;`, `$(...)` or backticks runs arbitrary commands.
   Fix: drop the shell and pass a list, `subprocess.run(["tar", "czf", str(dest), "-C", src, "."], check=True)`.

2. src/backup.py:30-31 - MEDIUM (hard). `except Exception: pass` silently swallows every unlink failure
   (permissions, file busy, etc.). The caller gets no signal that old backups were not removed, so disk usage can grow
   unnoticed. Fix: catch only `OSError` and log or collect the failure, or let it raise.

3. src/backup.py:16 - LOW. Timestamp resolution is 1 second (`int(time.time())`). Two backups of the same folder in
   the same second get the same filename, and the second silently overwrites the first. Use a finer timestamp or
   `time.time_ns()`.

4. src/backup.py:14-18 - LOW. `make_backup` does not create `dest_dir`. If it is missing, tar fails with an unhelpful
   error. A failed tar can also leave a partial archive that `prune` later treats as a valid backup. If `dest_dir` is
   inside `src`, the archive is included in itself.

5. src/backup.py:23 - LOW. `prune` globs every `*.tar.gz` in `dest_dir`, not only files made by `make_backup`. Unrelated
   archives in the same folder can be deleted. It also sorts by mtime, which can be changed by copying or touching a
   file, instead of using the timestamp in the name.

6. Smell baseline (judgement calls only):
   - Primitive Obsession (possible), src/backup.py:14 and :21. Paths are passed as `str` and converted to `Path` inside
     the function. Accepting `Path` directly would avoid the shell-quoting problem and the conversions.
   - No other baseline smells found (the diff is small, with no duplication or speculative generality).

## Spec

Skipped: no spec or issue was supplied. The only intent available is the module docstring ("Archive a project folder
and keep only the newest backups") and the `prune` docstring ("Delete all but the newest `keep` backups"). Checked
against those:

7. src/backup.py:24 - HIGH (correctness bug, off-by-one). `old = files[: len(files) - keep + 1]` selects one file too
   many. With 5 files and `keep=3`, the slice is `files[:3]`, so 3 files are deleted and only 2 are kept. The docstring
   promises to keep `keep`. Correct form: `files[: max(len(files) - keep, 0)]`.

8. src/backup.py:24 - HIGH (correctness bug, negative slice). When `keep > len(files)` the slice end can go negative and
   Python then counts from the end. Example: 3 files and `keep=5` gives `files[:-1]`, which deletes 1 file even though
   fewer than `keep` exist. A negative `keep` also deletes everything. The `max(..., 0)` guard in finding 7, plus
   validation that `keep >= 0`, fixes both.

9. tests/test_backup.py:1-12 - MEDIUM (test gap). `prune` has no tests at all, which is why findings 7 and 8 went
   unnoticed. The only test checks that `make_backup` returns a path that exists. It does not check the archive's
   contents, and it does not cover filenames with spaces (finding 1). Add tests for: keeps exactly `keep` newest,
   fewer files than `keep` deletes nothing, `keep=0`, and a path with a space.

## Summary

- Standards: 6 findings (smell baseline counted as one); worst: shell injection via `shell=True` (src/backup.py:17).
- Spec: 3 findings (spec file absent, judged against docstrings); worst: `prune` off-by-one deletes one backup too many
  (src/backup.py:24).
