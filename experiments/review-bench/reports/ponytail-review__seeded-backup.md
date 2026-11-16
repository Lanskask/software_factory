What this change does:
It adds `src/backup.py` with two functions. `make_backup` packs a folder into a timestamped `.tar.gz` using the `tar` command. `prune` deletes old backups and keeps only the newest N. One test covers `make_backup` only. I assumed one person running this as a script or cron job.

## Must fix

1. **Shell injection and broken paths** (`src/backup.py:L17`)
   - **What this is:** `make_backup` builds one command string and runs it through the shell (`shell=True`).
   - **Problem:** `src` and `dest_dir` go into the string without quoting. A folder named `my project` breaks the command. A folder named `x; rm -rf ~` runs the `rm`. Any path from a user, a config file or a folder listing can do this.
   - **Fix:** Pass a list and drop the shell: `subprocess.run(["tar", "czf", str(dest), "-C", src, "."], check=True)`. One line, same result.
   - **If we skip it:** Paths with spaces fail. A hostile path runs commands as the user running the backup.

2. **`prune` keeps the wrong number of files, and can delete everything it should keep** (`src/backup.py:L24`)
   - **What this is:** `prune` sorts backups oldest first and slices off the ones to delete.
   - **Problem:** The slice `files[: len(files) - keep + 1]` is off by one. With 5 files and `keep=3`, it deletes 3 and leaves 2. With 3 files and `keep=5`, the slice is `files[:-1]`, so it deletes the oldest file even though fewer than 5 exist. Both cases destroy backups the caller wanted to keep.
   - **Fix:** `old = files[: max(len(files) - keep, 0)]`. Do not write `files[:-keep]`, because `keep=0` would then delete nothing.
   - **If we skip it:** The newest backup is lost on every prune, and a young backup set loses its oldest copy too. This is the data you are trying to protect.

## Should fix

3. **Errors are swallowed, and it deletes files it does not own** (`src/backup.py:L21-31`)
   - **What this is:** The loop deletes each old file and ignores any failure.
   - **Problem:** `except Exception: pass` hides a permission error or a read-only disk. The caller sees a normal return and thinks the pruning worked, so the disk fills up unnoticed. Also, the glob `*.tar.gz` matches every archive in the folder, including backups of other projects or files someone put there by hand.
   - **Fix:** Catch only `OSError` if you want to keep going, and log or re-raise it. Better, let it raise (delete the `try`). Match only this project's files, for example by passing the name and globbing `f"{name}-*.tar.gz"`.
   - **If we skip it:** Silent disk-full later, and another project's backups get deleted.

4. **`prune` has no test** (`tests/test_backup.py`)
   - **What this is:** The only test checks that `make_backup` creates a file.
   - **Problem:** `prune` deletes data and already has an off-by-one bug (finding 2). No test would have caught it.
   - **Fix:** One test: create 5 files with increasing mtimes, call `prune(dir, 3)`, assert the 3 newest remain and 2 paths were returned. Add a case with fewer files than `keep` that asserts nothing is deleted.
   - **If we skip it:** The bug in finding 2 comes back with any later edit.

## Nice to have

5. **Same-second backups overwrite each other** (`src/backup.py:L16`)
   - **What this is:** The file name uses `int(time.time())`, which counts whole seconds.
   - **Problem:** Two backups of the same folder in the same second get the same name, and the second overwrites the first. `dest_dir` must also exist already, or `tar` fails, and a failed `tar` can leave a half-written archive that `prune` later counts as a backup.
   - **Fix:** Use `time.strftime("%Y%m%d-%H%M%S")` or `time.time_ns()`. Optionally add `Path(dest_dir).mkdir(parents=True, exist_ok=True)`.
   - **If we skip it:** Rare, only with fast repeated calls. Low risk for a daily cron job.

Verdict: fix 1 and 2 first, then 3 and 4.
Lean: -0 lines possible. The code is small. Findings 1 and 3 change a line each.
Not checked: how callers use these functions, since only the diff was provided. Whether the `backup` import in the test resolves (needs `src` on the path).
