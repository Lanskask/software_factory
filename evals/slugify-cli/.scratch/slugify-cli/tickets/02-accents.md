# 02: Drop accents

**What to build:** Accented Latin letters lose their accents and other non-ASCII characters act as separators, as
`SPEC.md` S3 says.

**Blocked by:** 01 Slugify ASCII text

**Status:** todo

## Tasks

- [ ] Fold accents with unicodedata NFKD
  - slugify_cli/__init__.py
  - SPEC.md S3
- [ ] Test the examples of S3
  - tests/test_slugify.py

## Acceptance

- [ ] When the text is `Crème Brûlée`, slugify shall return `creme-brulee`
- [ ] When the text is `日本 abc`, slugify shall return `abc`
- [ ] make test and make lint pass
