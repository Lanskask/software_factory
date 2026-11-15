What this change does: It adds a new command, `factory retro PROJECT`. The command reads the Owner's Claude Code chat transcripts for a project, counts typed messages in 11 regex buckets, and appends one line per bucket to `.factory/LESSONS.md`. The counting code moves out of `experiments/tt_interventions.py` into `src/factory/retro.py`. `Factory.run` now keeps the `- retro` lines when it resets LESSONS.md at the start of a Run. Assumed load: one person running a CLI by hand.

## Must fix

1. **The command says it appended a table when it wrote nothing** (`src/factory/retro.py:L104`, `src/factory/cli.py:L148`)
   - **What this is:** `retro()` returns early with the path when no messages were found (`total == 0`).
   - **Problem:** The CLI then always prints "✔ appended a retro table to ...". With a wrong project path, a project with no transcripts, or a transcript folder that was cleaned up, the owner sees a success message and nothing was written. The file may not even exist.
   - **Fix:** Return `None` in the empty case, and have the CLI print "no transcripts found in <dir>" and return 1. Or let `retro()` raise an error with that text.
   - **If we skip it:** The owner thinks the retro ran. A typo in the project path is silent.

## Should fix

2. **"Resolved" can be a false signal** (`src/factory/retro.py:L108-110`)
   - **What this is:** An old `[open]` line becomes `[resolved]` when the new absolute count of that bucket is lower than the old one.
   - **Problem:** Counts are absolute, not a share of all messages. They drop when old transcripts disappear, not only when the owner really intervenes less. As far as I know, Claude Code deletes transcripts after about 30 days by default (I did not verify this). Then every bucket looks "resolved" even though nothing improved. The counts also only grow while the owner keeps typing, so a real drop is rare.
   - **Fix:** Compare the share (`n / total`) instead of `n`. The old line already holds both numbers (`5 of 9`), so the regex needs one more group. Or drop the auto-resolve and let the owner close lines by hand (YAGNI).
   - **If we skip it:** The history says "resolved" for buckets that were just purged.

3. **Every retro run adds about 11 lines that every Session reads** (`src/factory/retro.py:L113`, `src/factory/run.py:L294-299`)
   - **What this is:** The file is the Run's "lessons" file, which each Ticket's Session reads. `reset_lessons` now keeps the retro lines across Runs.
   - **Problem:** Retro lines are statistics about the Owner, not lessons about a failure. They are appended on every call even if nothing changed, and they are never removed. After ten retros, the agent prompt carries 110 lines of counts. This costs tokens and adds noise to every Session. I did not read `lessons()` callers, so I cannot say how much of the file is injected.
   - **Fix:** Write the retro table to its own file (for example `.factory/RETRO.md`), so the `lesson()` and `reset_lessons` code stays untouched. That also deletes `reset_lessons` and its test.
   - **If we skip it:** The Session prompt grows with each retro. Retro lines can also be mixed up with failure lessons.

4. **`reset_lessons` is hard to test and uses a ternary as a statement** (`src/factory/run.py:L299`, `tests/test_retro.py:L371-378`)
   - **What this is:** `path.write_text(...) if keep else path.unlink()` uses a conditional expression only for its side effects. The test builds a `Factory` with `object.__new__` to skip `__init__`.
   - **Problem:** It is easy to misread, and the test depends on how `Factory` is built. If `__init__` changes, the test may break for an unrelated reason.
   - **Fix:** Use a plain `if keep: ... else: ...`. If the retro lines move to their own file (finding 3), this goes away.
   - **If we skip it:** Small cost, but it is a fragile test.

## Nice to have

5. **Dead sort** (`src/factory/retro.py:L65`)
   - **What this is:** Files are sorted by modification time.
   - **Problem:** The old script printed the session id and date, so order mattered. Now `messages()` yields only text and `count` sums, so the order has no effect. It is also an extra `stat` call per file.
   - **Fix:** `for f in directory.glob("*.jsonl"):`. This saves a line and a lambda.
   - **If we skip it:** Nothing breaks.

6. **The experiment script lost its examples output** (`experiments/tt_interventions.py:L19-31`)
   - **What this is:** The old script printed up to 3 example messages per bucket. Its docstring told the reader to "read the examples it prints" because the regexes are heuristics (about +/-10 %).
   - **Problem:** The new version prints only counts, so the owner can no longer check what a bucket really matched. The docstring also lost the "see examples" advice, so this is a quiet drop of a feature.
   - **Fix:** Either accept the loss on purpose and note it in the docstring, or yield `(text)` with the matched label in `count` and print a few. For YAGNI, accepting the loss is fine; just say so.
   - **If we skip it:** Bucket quality is harder to judge by eye.

7. **Reads a whole transcript into memory and crashes on bad bytes** (`src/factory/retro.py:L66`)
   - **What this is:** `f.read_text().splitlines()` loads each file fully with the default encoding.
   - **Problem:** A transcript that is very large uses a lot of memory. One non-UTF-8 byte raises `UnicodeDecodeError` and the whole retro fails. The old script had the same risk, but it is now a shipped command.
   - **Fix:** `with f.open(encoding="utf-8", errors="replace") as fh: for line in fh:`.
   - **If we skip it:** A rare crash on odd input. Fine for one person.

Verdict: fix 1 first; decide on 2 and 3 (they come from the same design choice of using LESSONS.md); the rest can wait.
Lean: -8 lines possible (finding 3 would remove `reset_lessons`, its call site change, ROW-based resolve and one test; findings 4 and 5 are 1-2 lines each).
Not checked: the callers of `lessons()` and whether `Factory.state` is the same folder as `project/.factory` (I only had the diff); the real default for transcript cleanup in Claude Code; whether `rel()` exists in `cli.py`.
