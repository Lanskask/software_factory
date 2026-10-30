from __future__ import annotations

import json

from factory.claude import parse_stream, session_command


def test_session_command_has_budget_tools_and_no_persistence() -> None:
    cmd = session_command(
        "/goal x",
        system="rules",
        allowed=("Bash(make test)", "Skill"),
        disallowed=("Bash(git push*)",),
        budget_usd=5.0,
        model=None,
        plugin_dir=None,
        permission_mode="acceptEdits",
    )
    assert cmd[:3] == ["claude", "-p", "/goal x"]
    assert cmd[cmd.index("--max-budget-usd") + 1] == "5.0"
    assert "Bash(make test)" in cmd and "Bash(git push*)" in cmd
    assert "--plugin-dir" not in cmd and "--model" not in cmd
    assert "--no-session-persistence" in cmd


def test_session_command_adds_plugin_dir_and_model_when_given(tmp_path: object) -> None:
    cmd = session_command(
        "p",
        system="s",
        allowed=(),
        disallowed=(),
        budget_usd=1,
        model="opus",
        plugin_dir="/x",
        permission_mode="default",
    )
    assert cmd[cmd.index("--plugin-dir") + 1] == "/x"
    assert cmd[cmd.index("--model") + 1] == "opus"


def test_parse_stream_takes_the_final_result_event() -> None:
    lines = [
        json.dumps({"type": "system", "subtype": "init"}),
        "not json, ignored",
        json.dumps({"type": "result", "subtype": "success", "result": "DONE", "total_cost_usd": 1.25}),
    ]
    r = parse_stream("\n".join(lines))
    assert r.ok and r.text == "DONE" and r.cost_usd == 1.25


def test_parse_stream_without_result_is_a_failure() -> None:
    r = parse_stream(json.dumps({"type": "system"}))
    assert not r.ok and r.text == ""


def test_parse_stream_error_subtype_is_a_failure() -> None:
    r = parse_stream(json.dumps({"type": "result", "subtype": "error_max_budget_usd", "total_cost_usd": 5.0}))
    assert not r.ok and "error_max_budget_usd" in r.text
