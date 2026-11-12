"""Reference solution of SPEC.md: the canned run of tests/test_score.py passes every hidden test with it."""

import re
import unicodedata


def slugify(text: str, sep: str = "-", max_len: int | None = None) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", ascii_text.lower())
    slug = sep.join(words)
    if max_len is None or len(slug) <= max_len:
        return slug
    cut = ""
    for w in words:
        longer = f"{cut}{sep}{w}" if cut else w
        if len(longer) > max_len:
            break
        cut = longer
    return cut or words[0][:max_len]
