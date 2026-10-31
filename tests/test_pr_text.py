"""PR title and body text: Conventional-Commit title from the Ticket, code shown as code."""

from factory.pr_text import code_quote, pr_title

TICKET = "# 08: Page changes for Hosted mode\n\n**What to build:** x\n"


def test_title_is_type_ticket_number_and_ticket_title() -> None:
    assert pr_title(TICKET, "08", "page") == "feat: [08] Page changes for Hosted mode"


def test_title_takes_the_type_from_a_type_line() -> None:
    assert pr_title(TICKET + "**Type:** test\n", "08", "page") == "test: [08] Page changes for Hosted mode"


def test_title_falls_back_to_the_slug_without_a_heading() -> None:
    assert pr_title("no heading", "08", "page") == "feat: [08] page"


def test_code_quote_wraps_test_ids_and_paths() -> None:
    text = "ran tests/test_server.py::test_make_server_serves_page and edited index.html, /api/config too."
    assert code_quote(text) == (
        "ran `tests/test_server.py::test_make_server_serves_page` and edited `index.html`, `/api/config` too."
    )


def test_code_quote_leaves_code_urls_and_links_alone() -> None:
    text = "`a/b.py` https://x.com/a/b.py [l](docs/a.md)\n```\ntests/x.py::t\n```\n"
    assert code_quote(text) == text
