# 04: Command line

**What to build:** `python3 -m slugify_cli [--sep SEP] [--max-len N] TEXT...` prints the slug, as `SPEC.md` S5 says.

**Blocked by:** 03 Cut long slugs at a word boundary

**Status:** todo

## Tasks

- [ ] Write the command line with argparse
  - slugify_cli/__main__.py
  - SPEC.md S5
- [ ] Test it by running python3 -m slugify_cli in a subprocess
  - tests/test_cli.py

## Acceptance

- [ ] When run with `Hello World`, the command shall print `hello-world` and exit 0
- [ ] When run with `--sep _ --max-len 9 the quick brown`, the command shall print `the_quick`
- [ ] When the slug is empty, the command shall print `slugify: empty slug` to stderr and exit 1
- [ ] make test and make lint pass
