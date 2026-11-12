# 03: Cut long slugs at a word boundary

**What to build:** `slugify(text, max_len=N)` cuts a long slug to whole words, as `SPEC.md` S4 says.

**Blocked by:** 01 Slugify ASCII text

**Status:** todo

## Tasks

- [ ] Cut the slug to the whole words that fit in max_len
  - slugify_cli/__init__.py
  - SPEC.md S4
- [ ] Test the examples of S4
  - tests/test_slugify.py

## Acceptance

- [ ] When the text is `the quick brown fox` and max_len is 12, slugify shall return `the-quick`
- [ ] When the text is `abcdefgh` and max_len is 3, slugify shall return `abc`
- [ ] When a slug is cut, it shall not end with sep
- [ ] make test and make lint pass
