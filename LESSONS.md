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

## A Session that ends on an API error is not a success

- **Failure:** a credit-limit error and an HTTP 429 were reported as "session ended with success". Four Tickets were
  Blocked and their work discarded.
- **Cause:** the stream-json `result` event has `subtype: success` and `is_error: true` with an `api_error_status`
  field. The Factory read only `subtype`.
- **Rule:** the Session reports the error message, not "success". A rate-limited Session (429) waits 15 minutes and runs
  again, up to 6 hours, instead of Blocking the Ticket.
- **Proof:** the tests of the PRs "Show the API error when a Session fails on one" and "Wait out a rate limit instead of
  blocking the Ticket".

## A Run dies with the chat session that started it

- **Failure:** a Run was waiting out a rate limit when the interactive Claude Code session ended. The Run process ended
  with it, and its last Ticket was done but never published.
- **Rule:** start a Run that must outlive a chat from a terminal you own (`nohup factory run . &`), not from a session.
  A finished-but-unpublished Ticket with no file in `.factory/unpublished/` needs a hand publish.

## The review is right when it Blocks a Ticket

- **Seen:** the review Blocked three Tickets for real defects: `gh repo view` ran in the wrong directory and a token
  login was called "missing scopes"; a retro marked old lessons `[resolved]` when no transcripts existed; a
  plan-bootstrap Session ignored `protected`. Each was fixed by hand in minutes.
- **Rule:** a Blocked Ticket is a cheap hand fix on its branch, not a reason to doubt the review. This supports
  acceptance criteria with a test each. `max_blocked = 2` stopped a Run before its last Ticket although the two Blocked
  Tickets were independent: use `--max-blocked 4` for a retry Run.
