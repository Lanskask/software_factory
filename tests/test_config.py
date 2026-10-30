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
