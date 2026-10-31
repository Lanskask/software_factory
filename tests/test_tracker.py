from __future__ import annotations

from factory.tracker import Ticket, parse_status

FLAT = "01\tdone\t\tlogin-form\n02\ttodo\tREADY\tsession-cookie\n03\ttodo\t\tlogout\n"
EPICS = """== Epic 10: Web app (2/4 done)
10/01\tdone\t\tgenerate-go-server
10/13\ttodo\tREADY\treproducible-web-build
"""


def test_parse_status_reads_flat_tickets() -> None:
    assert parse_status(FLAT) == [
        Ticket("01", "done", False, "login-form"),
        Ticket("02", "todo", True, "session-cookie"),
        Ticket("03", "todo", False, "logout"),
    ]


def test_parse_status_skips_epic_headers_and_keeps_epic_numbers() -> None:
    assert [t.num for t in parse_status(EPICS)] == ["10/01", "10/13"]


def test_branch_name_replaces_the_slash_of_epic_numbers() -> None:
    assert Ticket("10/13", "todo", True, "web-build").branch("factory/") == "factory/10-13-web-build"
    assert Ticket("02", "todo", True, "cookie").branch("f/") == "f/02-cookie"
