# slugify-cli spec

`slugify-cli` turns any text into a URL slug: a Python package `slugify_cli` with a function and a command line. Only
the Python standard library is used.

## S1 The function

`slugify_cli.slugify(text: str, sep: str = "-", max_len: int | None = None) -> str` returns the slug of `text`.

## S2 Lowercase ASCII only

A slug is always lowercase. It holds only the characters `a-z`, `0-9` and `sep`. `slugify("Hello World")` is
`hello-world`. Every run of other characters becomes one `sep`, and a slug never starts or ends with `sep`:
`slugify("  --Hello,   World!!  ")` is `hello-world`.

## S3 Accents

Accented Latin letters lose their accents (Unicode NFKD, then the combining marks are dropped): `slugify("Crème Brûlée")`
is `creme-brulee`. Any other non-ASCII character counts as a separator: `slugify("日本 abc")` is `abc`.

## S4 Maximum length

With `max_len`, a slug longer than `max_len` is cut to the longest run of whole words (the parts between `sep`) that
fits in `max_len` characters: `slugify("the quick brown fox", max_len=12)` is `the-quick`. When even the first word is
longer than `max_len`, it is cut to `max_len` characters: `slugify("abcdefgh", max_len=3)` is `abc`. A cut slug never
ends with `sep`.

## S5 The command line

`python3 -m slugify_cli [--sep SEP] [--max-len N] TEXT...` joins the `TEXT` words with spaces, prints the slug and a
newline, and exits 0. When the slug is empty, it prints `slugify: empty slug` to stderr, prints nothing to stdout, and
exits 1.
