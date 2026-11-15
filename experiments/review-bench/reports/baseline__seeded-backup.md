# Review: backup.py / test_backup.py

1. src/backup.py:17 - HIGH (security/bug). `subprocess.run(f"tar czf {dest} -C {src} .", shell=True)` interpolates
   unquoted paths into a shell string. A src or dest_dir containing spaces breaks the command, and one containing
   `;`, `$(...)` or backticks runs arbitrary commands. Fix: pass a list, no shell:
   `subprocess.run(["tar", "czf", str(dest), "-C", src, "."], check=True)`.

2. src/backup.py:24 - HIGH (off-by-one, data loss). `files[: len(files) - keep + 1]` deletes one backup too many: it
   keeps only `keep - 1`. With 5 files and keep=3 it deletes 3 and leaves 2. With keep=1 it deletes everything. It
   should be `files[: len(files) - keep]`. Also, if keep == 0 it must delete everything, and the slice for
   len(files) < keep-1 is a negative stop index, which silently selects a wrong subset (e.g. 2 files, keep=5:
   `files[:-2]` = [] by luck, but 3 files, keep=5 gives `files[:-1]` and deletes 1 file although fewer than `keep`
   exist). Use `max(0, len(files) - keep)` and validate `keep >= 0`.

3. src/backup.py:23 - MEDIUM. The glob `*.tar.gz` matches every archive in dest_dir, not only backups made by
   make_backup, so unrelated archives are deleted. Sorting by mtime is also unreliable (copied or restored files
   change mtime). The timestamp in the name has only 1 second resolution: two backups in the same second overwrite
   each other (make_backup, line 16).

4. src/backup.py:27-31 - MEDIUM. `except Exception: pass` swallows every unlink error (permissions, etc.) silently.
   The caller is told only about successes and cannot tell that pruning failed, so disk usage can grow unnoticed.
   Catch `OSError` at most and log or re-raise. Also `FileNotFoundError` from `p.stat()` inside the sort key (file
   removed concurrently) is not handled.

5. src/backup.py:16-17 - MEDIUM. dest_dir is not created or checked; a failed tar can leave a partial archive at
   `dest` that a later prune counts as a valid backup (and may keep it while deleting good ones). Writing to a temp
   name and renaming on success avoids this. If dest_dir lies inside src, the archive includes itself.

6. tests/test_backup.py:1-12 - MEDIUM (missing tests). `prune` has no test at all, which is why finding 2 went
   unnoticed. Needed: keep N of M, keep >= M (deletes nothing), keep=0, non-backup files left alone, unlink failure.
   `make_backup` test only checks that the file exists, not that it contains a.txt; no test for paths with spaces
   (finding 1). The test imports `backup` with no visible path or conftest config; it works only if `src` is on
   sys.path.
