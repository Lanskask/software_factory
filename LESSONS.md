# Lessons

Failures seen in real Runs, what caused them, and the rule the Factory now follows. Add one entry per new failure class.

## A pull request needs its base on origin

- **Failure:** `gh pr create` printed
  `GraphQL: Head sha can't be blank, Base sha can't be blank, No commits between X and Y, Base ref must be a branch (createPullRequest)`.
  The Run stopped.
- **Cause:** the base branch existed only in the local repository. Two ways it happened: the previous Ticket's push had
  failed but the tracker already marked it done, and a hand-made branch was checked out when the Run started, so it
  became the base.
- **Rule:** the base is chosen from the Factory's own branches (`stack_tip`), never from the checked-out branch.
  `publish` checks `git ls-remote --heads origin <base>` and pushes the base first when it is missing. A failed publish
  leaves `.factory/unpublished/` so the next Run retries it.
- **Proof:** `tests/test_run_e2e.py`, tests `test_next_run_stacks_on_the_factory_branches_not_on_the_checked_out_branch`
  and `test_publish_pushes_a_base_branch_that_is_missing_on_origin`.

## Nobody else may use the working tree during a Run

- **Failure:** a branch switch made by hand during a Run made the live Session report that its branch had changed, and
  the Ticket was marked Blocked.
- **Rule:** while `factory run` is going, do not switch branches or edit files in the Project. Work in a second clone or
  `git worktree` instead.
