from __future__ import annotations

from pathlib import Path

import pytest

from factory.config import Config, ConfigError, load_config, template


def write(project: Path, text: str) -> None:
    (project / ".factory").mkdir(exist_ok=True)
    (project / ".factory" / "config.toml").write_text(text)


def test_load_config_reads_required_keys_and_keeps_defaults(tmp_path: Path) -> None:
    write(tmp_path, 'tickets_dir = ".scratch/app/tickets"\nchecks = ["make test", "make lint"]\n')
    cfg = load_config(tmp_path)
    assert cfg.tickets_dir == ".scratch/app/tickets"
    assert cfg.checks == ("make test", "make lint")
    assert (cfg.max_tickets, cfg.max_blocked, cfg.budget_usd, cfg.timeout_minutes) == (10, 2, 5.0, 90)
    assert cfg.base_branch == "main"


def test_load_config_rejects_unknown_keys_so_typos_do_not_pass_silently(tmp_path: Path) -> None:
    write(tmp_path, 'tickets_dir = "t"\nchecks = ["make test"]\nmax_ticket = 3\n')
    with pytest.raises(ConfigError, match="max_ticket"):
        load_config(tmp_path)


def test_load_config_requires_at_least_one_check(tmp_path: Path) -> None:
    write(tmp_path, 'tickets_dir = "t"\nchecks = []\n')
    with pytest.raises(ConfigError, match="checks"):
        load_config(tmp_path)


def test_load_config_rejects_wrong_types(tmp_path: Path) -> None:
    write(tmp_path, 'tickets_dir = "t"\nchecks = ["make test"]\nmax_tickets = "ten"\n')
    with pytest.raises(ConfigError, match="max_tickets"):
        load_config(tmp_path)


def test_load_config_missing_file_names_factory_init(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="factory init"):
        load_config(tmp_path)


def test_template_uses_makefile_targets_that_exist(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text("test:\n\tgo test ./...\nlint:\n\tgo vet ./...\n")
    write(tmp_path, template(tmp_path))
    cfg = load_config(tmp_path)
    assert cfg.checks == ("make test", "make lint")
    assert cfg.tickets_dir == f".scratch/{tmp_path.name}/tickets"


def test_config_defaults_are_a_valid_config() -> None:
    cfg = Config(tickets_dir="t", checks=("make test",))
    assert cfg.implement_skills and cfg.review_skills


def test_template_finds_the_existing_tickets_folder_under_scratch(tmp_path: Path) -> None:
    (tmp_path / ".scratch" / "task-tracker" / "issues").mkdir(parents=True)
    (tmp_path / ".scratch" / "task-tracker" / "issues" / "tickets.py").write_text("")
    (tmp_path / ".scratch" / "other").mkdir()  # no tickets.py: ignored
    write(tmp_path, template(tmp_path))
    assert load_config(tmp_path).tickets_dir == ".scratch/task-tracker/issues"


def test_template_adds_web_checks_and_bun_when_the_project_has_a_web_app(tmp_path: Path) -> None:
    makefile = "test:\n\tgo test\nweb-dev:\n\tbun dev\nweb-test:\n\tbun test\nweb-e2e:\n\tbun e2e\n"
    (tmp_path / "Makefile").write_text(makefile)
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "package.json").write_text("{}")
    write(tmp_path, template(tmp_path))
    cfg = load_config(tmp_path)
    assert cfg.checks == ("make test", "make web-test", "make web-e2e")  # web-dev never exits: not a check
    assert cfg.allowed_tools == ("Bash(bun *)",)


def test_template_leaves_allowed_tools_empty_without_a_web_app(tmp_path: Path) -> None:
    write(tmp_path, template(tmp_path))
    assert load_config(tmp_path).allowed_tools == ()
