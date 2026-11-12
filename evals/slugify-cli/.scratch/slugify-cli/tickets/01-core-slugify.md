# 01: Slugify ASCII text

**What to build:** `slugify_cli.slugify(text)` returns the lowercase slug of ASCII text, as `SPEC.md` S1 and S2 say.

**Blocked by:** None (can start immediately)

**Status:** todo

## Tasks

- [ ] Write slugify(text, sep="-", max_len=None) for ASCII text
  - slugify_cli/__init__.py
  - SPEC.md S1, S2
- [ ] Test every example of S2
  - tests/test_slugify.py

## Acceptance

- [ ] When the text is `Hello World`, slugify shall return `hello-world`
- [ ] When the text is `  --Hello,   World!!  `, slugify shall return `hello-world`
- [ ] When sep is `_`, slugify shall join the words with `_`
- [ ] make test and make lint pass
