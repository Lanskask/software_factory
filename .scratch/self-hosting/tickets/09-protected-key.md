# 09: Add a real protected config key

**What to build:** A `protected` config key (list of paths) feeds `--disallowedTools` for Sessions, and the Protected
section of the rules template reads from it. Source: decision in commit 28e26e9. Lane B. Closes #23.

**Blocked by:** None (can start immediately)

**Status:** todo

## Tasks

- [ ] Add protected to Config and the config template
  - src/factory/config.py
- [ ] Turn each path into Edit/Write disallowed entries
  - src/factory/run.py command(); src/factory/claude.py session_command()
- [ ] Make the Protected section of the rules template read from it
  - src/factory/templates/CLAUDE.md
  - src/factory/bootstrap.py copy_templates()

## Acceptance

- [ ] A protected config key feeds --disallowedTools
- [ ] The Protected section of the rules template reads from it
- [ ] Tests cover it; make test and make lint pass
