# 05: Keep the case of the input

**What to build:** Users want readable slugs for titles: `slugify` keeps uppercase letters, so `Hello World` becomes
`Hello-World` and `README Title` becomes `README-Title`.

**Blocked by:** 04 Command line

**Status:** todo

## Tasks

- [ ] Stop lowercasing in slugify
  - slugify_cli/__init__.py
- [ ] Update the tests to expect the input's case
  - tests/test_slugify.py
  - tests/test_cli.py

## Acceptance

- [ ] When the text is `Hello World`, slugify shall return `Hello-World`
- [ ] When run with `README Title`, the command shall print `README-Title`
- [ ] make test and make lint pass
