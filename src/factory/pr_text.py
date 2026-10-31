"""Text of a pull request: a Conventional-Commit title from the Ticket, and code shown as code."""

from __future__ import annotations

import re

_EXT = r"(?:py|md|html|json|toml|sh|txt|ya?ml|js|ts|go|rs)"
# A test id (`a.py::test_x`), a path ending in a known extension, or an absolute path such as `/api/config`.
# Not after a word character, `(`, `/`, `:`, `.`, `-` or a backtick: URLs, links and code spans stay as they are.
_PATH = rf"(?:[\w.\-]+/)*[\w.\-]+\.{_EXT}(?:::[\w\[\]\-]+)*"
_CODE = re.compile(rf"(?<![\w(/:.`-])({_PATH}|/(?:[\w.\-]+/?)+|[\w/.\-]+::[\w:\[\]\-]+)(?![\w`])")
_SKIP = re.compile(r"(```.*?```|`[^`\n]*`)", re.DOTALL)


def pr_title(ticket: str, num: str, slug: str) -> str:
    """`feat: [08] Page changes for Hosted mode`; the type is the Ticket's `**Type:**` line, default `feat`."""
    heading = re.match(r"#\s*[^:\n]+:\s*(.+)", ticket)
    kind = re.search(r"^\*\*Type:\*\*\s*(\w+)", ticket, re.MULTILINE)
    return f"{kind.group(1) if kind else 'feat'}: [{num}] {heading.group(1).strip() if heading else slug}"


def code_quote(text: str) -> str:
    """Wrap test ids and file paths in backticks, outside code fences and code spans."""
    parts = _SKIP.split(text)  # odd items are the code to keep as they are
    return "".join(p if i % 2 else _CODE.sub(r"`\1`", p) for i, p in enumerate(parts))
