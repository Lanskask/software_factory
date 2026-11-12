"""Hidden acceptance tests of slugify-cli, one per rule of SPEC.md. `factory.score` copies them in after a Run."""

import subprocess
import sys

import pytest
from slugify_cli import slugify


@pytest.mark.parametrize(
    ("text", "slug"),
    [
        ("Hello World", "hello-world"),
        ("  --Hello,   World!!  ", "hello-world"),
        ("README Title", "readme-title"),
        ("v2.0 release", "v2-0-release"),
        ("Crème Brûlée", "creme-brulee"),
        ("日本 abc", "abc"),
        ("", ""),
    ],
)
def test_slug(text: str, slug: str) -> None:
    assert slugify(text) == slug


def test_sep() -> None:
    assert slugify("Hello World", sep="_") == "hello_world"


@pytest.mark.parametrize(
    ("text", "max_len", "slug"),
    [
        ("the quick brown fox", 12, "the-quick"),
        ("the quick brown fox", 9, "the-quick"),
        ("the quick brown fox", 100, "the-quick-brown-fox"),
        ("abcdefgh", 3, "abc"),
    ],
)
def test_max_len(text: str, max_len: int, slug: str) -> None:
    assert slugify(text, max_len=max_len) == slug


def cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "slugify_cli", *args], capture_output=True, text=True)


def test_cli_prints_the_slug() -> None:
    r = cli("Hello", "World")
    assert (r.returncode, r.stdout) == (0, "hello-world\n")


def test_cli_options() -> None:
    assert cli("--sep", "_", "--max-len", "9", "the", "quick", "brown").stdout == "the_quick\n"


def test_cli_empty_slug() -> None:
    r = cli("!!!")
    assert (r.returncode, r.stdout, r.stderr.strip()) == (1, "", "slugify: empty slug")
