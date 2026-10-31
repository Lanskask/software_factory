from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory.skills import SkillError, build_plugin, find_skill, local_name, strip_user_only


def make_plugin(root: Path, plugin: str, skill: str, *, user_only: bool, nested: str = "") -> Path:
    d = root / plugin / "1.0" / "skills" / nested / skill
    d.mkdir(parents=True)
    flag = "disable-model-invocation: true\n" if user_only else ""
    (d / "SKILL.md").write_text(f"---\nname: {skill}\ndescription: d\n{flag}---\n\nBody of {skill}.\n")
    (d / "scripts").mkdir()
    (d / "scripts" / "helper.py").write_text("print(1)\n")
    return d


def installed(root: Path, plugins: dict[str, str]) -> Path:
    path = root / "installed_plugins.json"
    data = {"version": 2, "plugins": {k: [{"installPath": str(root / v / "1.0")}] for k, v in plugins.items()}}
    path.write_text(json.dumps(data))
    return path


def test_strip_user_only_removes_only_the_flag() -> None:
    text = "---\nname: x\ndisable-model-invocation: true\ndescription: d\n---\n\nbody\n"
    assert strip_user_only(text) == "---\nname: x\ndescription: d\n---\n\nbody\n"


def test_find_skill_resolves_plugin_ref_through_installed_plugins(tmp_path: Path) -> None:
    d = make_plugin(tmp_path, "mp", "to-spec", user_only=True, nested="engineering")
    reg = installed(tmp_path, {"mattpocock-skills@mattpocock": "mp"})
    assert find_skill("mattpocock-skills:to-spec", reg) == d


def test_find_skill_ignores_distribution_copies(tmp_path: Path) -> None:
    d = make_plugin(tmp_path, "egm", "egm-draft", user_only=True)
    make_plugin(tmp_path, "egm", "egm-draft", user_only=True, nested="../distributions/claude/skills")
    reg = installed(tmp_path, {"egm@egm": "egm"})
    assert find_skill("egm:egm-draft", reg) == d


def test_find_skill_unknown_names_the_ref(tmp_path: Path) -> None:
    reg = installed(tmp_path, {})
    with pytest.raises(SkillError, match="nope:x"):
        find_skill("nope:x", reg)


def test_build_plugin_copies_skills_model_invocable_with_their_files(tmp_path: Path) -> None:
    make_plugin(tmp_path, "mp", "implement", user_only=True)
    make_plugin(tmp_path, "mp", "tdd", user_only=False)
    reg = installed(tmp_path, {"mattpocock-skills@mattpocock": "mp"})
    out = build_plugin(["mattpocock-skills:implement", "mattpocock-skills:tdd"], tmp_path / "out", reg)
    manifest = json.loads((out / ".claude-plugin" / "plugin.json").read_text())
    assert manifest["name"] == "factory"
    skill = (out / "skills" / "implement" / "SKILL.md").read_text()
    assert "disable-model-invocation" not in skill and "Body of implement." in skill
    assert (out / "skills" / "implement" / "scripts" / "helper.py").exists()
    assert (out / "skills" / "tdd" / "SKILL.md").exists()


def test_build_plugin_refuses_two_skills_with_one_name(tmp_path: Path) -> None:
    make_plugin(tmp_path, "a", "review", user_only=False)
    make_plugin(tmp_path, "b", "review", user_only=False)
    reg = installed(tmp_path, {"a@a": "a", "b@b": "b"})
    with pytest.raises(SkillError, match="review"):
        build_plugin(["a:review", "b:review"], tmp_path / "out", reg)


def test_local_name_is_the_factory_namespace() -> None:
    assert local_name("mattpocock-skills:implement") == "factory:implement"
