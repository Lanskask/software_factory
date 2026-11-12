# 08: Add a doctor line for MCP servers and gh scopes

**What to build:** A `doctor` line reports whether the needed MCP servers answer, whether `gh` has the `repo` and
`project` scopes, and whether the token can merge. See docs/factory-analysis.md section 3, P11. Lane B. Closes #21.

**Blocked by:** None (can start immediately)

**Status:** todo

## Tasks

- [ ] Write the checks behind an injectable runner so tests need no network
  - src/factory/bootstrap.py
  - gh auth status shows scopes; claude mcp list shows servers
- [ ] Print the doctor line in factory status
  - src/factory/cli.py cmd_status()

## Acceptance

- [ ] doctor reports MCP servers reachable, gh scopes (repo, project), and whether the PAT can merge
- [ ] Tests cover it with fake command output; make test and make lint pass
