## PR Reviewer Guide 🔍

Here are some key observations to aid the review process:

<table>
<tr><td>⏱️&nbsp;<strong>Estimated effort to review</strong>: 2 🔵🔵⚪⚪⚪</td></tr>
<tr><td>🧪&nbsp;<strong>No relevant tests</strong></td></tr>
<tr><td>🔒&nbsp;<strong>Security concerns</strong><br><br>

<strong>Command injection:</strong><br> `make_backup` runs `subprocess.run(f"tar czf {dest} -C {src} .", shell=True)` with unsanitized `src` and `dest_dir`. If either value comes from user-controlled input, an attacker can execute arbitrary shell commands, for example with a `src` like `x; rm -rf ~`. Use an argument list without `shell=True`.</td></tr>
<tr><td>⚡&nbsp;<strong>Recommended focus areas for review</strong><br><br>

<strong>Command Injection</strong><br>`make_backup` builds a shell command via an f-string with `shell=True`, interpolating `src` and `dest` unquoted. A path containing spaces breaks the command, and a path containing shell metacharacters (e.g. `;`, `$(...)`, backticks) executes arbitrary commands. Pass an argument list without `shell=True`: `subprocess.run(["tar", "czf", str(dest), "-C", src, "."], check=True)`.

<strong>Off-by-one Deletion</strong><br>`files[: len(files) - keep + 1]` deletes one backup too many, so only `keep - 1` backups remain instead of `keep`. For example, with 5 files and `keep=3`, the slice is `files[:3]`, deleting 3 and leaving 2. When `keep=0` the slice is `files[:len+1]`, which still works, but for `keep > len(files)` the slice end is `<= 0` or negative-adjusted: with 2 files and `keep=5` it becomes `files[:-2]`, which is empty here, but with 3 files and `keep=3` it is `files[:1]` and deletes one backup even though nothing should be pruned. The correct slice is `files[: max(len(files) - keep, 0)]`.

<strong>Swallowed Errors</strong><br>The bare `except Exception: pass` silently ignores failed deletions (e.g. permission errors), so failures to prune go unnoticed and backups accumulate without any signal. Catch `OSError` and log it or re-raise. The docstring says it returns deleted paths, so skipping failures is acceptable only if it is surfaced.

</td></tr>
</table>

