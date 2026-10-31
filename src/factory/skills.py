"""Model-invocable copies of installed skills, loaded only into Factory sessions with `claude --plugin-dir`.

Many planning and implementation skills are user-only (`disable-model-invocation: true`). Copying them into a
throwaway plugin without that flag lets a Factory session call them, while the owner's own setup stays unchanged.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

PLUGIN_NAME = "factory"
INSTALLED = Path.home() / ".claude" / "plugins" / "installed_plugins.json"


class SkillError(Exception):
    pass


def strip_user_only(text: str) -> str:
    head, sep, body = text.partition("\n---\n")
    kept = [line for line in head.split("\n") if not line.startswith("disable-model-invocation:")]
    return "\n".join(kept) + sep + body


def local_name(ref: str) -> str:
    """How a Session calls the copy of `plugin:skill`."""
    return f"{PLUGIN_NAME}:{ref.split(':')[-1]}"


def _install_paths(installed: Path, plugin: str) -> list[Path]:
    data = json.loads(installed.read_text())
    return [
        Path(e["installPath"])
        for key, entries in data.get("plugins", {}).items()
        if key.split("@")[0] == plugin
        for e in entries
    ]


def find_skill(ref: str, installed: Path = INSTALLED) -> Path:
    """The directory of skill `plugin:name` in its installed plugin, skipping packaged copies under distributions/."""
    plugin, _, name = ref.partition(":")
    for root in _install_paths(installed, plugin):
        hits = sorted(
            (p.parent for p in root.glob(f"skills/**/{name}/SKILL.md") if "distributions" not in p.parts),
            key=lambda p: len(p.parts),
        )
        if hits:
            return hits[0]
    raise SkillError(f"skill {ref} not found in the installed plugins ({installed})")


def build_plugin(refs: list[str] | tuple[str, ...], dest: Path, installed: Path = INSTALLED) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    (dest / ".claude-plugin").mkdir(parents=True)
    manifest = {"name": PLUGIN_NAME, "description": "Model-invocable copies of skills for Software Factory sessions"}
    (dest / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest, indent=2))
    seen: dict[str, str] = {}
    for ref in refs:
        name = ref.split(":")[-1]
        if name in seen:
            raise SkillError(f"skills {seen[name]} and {ref} share the name {name}")
        seen[name] = ref
        target = dest / "skills" / name
        shutil.copytree(find_skill(ref, installed), target)
        skill_md = target / "SKILL.md"
        skill_md.write_text(strip_user_only(skill_md.read_text()))
    return dest
