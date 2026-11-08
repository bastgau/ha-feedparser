"""Tests for the manifest of the integration."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib

from custom_components.rss_feedparser.const import DOMAIN

ROOT = Path(__file__).parents[2]
MANIFEST = json.loads((ROOT / "custom_components" / "rss_feedparser" / "manifest.json").read_text(encoding="utf-8"))
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_the_domain_is_the_same_everywhere() -> None:
    """Test that the folder, the manifest, the constant, the project variables and the tests agree on the domain."""
    project_variables = dict(
        line.split("=", 1) for line in (ROOT / ".devcontainer" / ".common-env").read_text().splitlines() if "=" in line
    )
    folders = [
        path.name for path in (ROOT / "custom_components").iterdir() if path.is_dir() and path.name != "__pycache__"
    ]

    assert folders == [MANIFEST["domain"]]
    assert MANIFEST["domain"] == DOMAIN
    assert project_variables["INTEGRATION_DOMAIN"] == MANIFEST["domain"]
    assert (ROOT / "tests" / MANIFEST["domain"]).is_dir()
    assert project_variables["CLIENT_TESTS_PATH"].startswith(f"tests/{MANIFEST['domain']}/")


def test_manifest_does_not_list_requests() -> None:
    """Test that the manifest leaves out requests: Home Assistant provides it and hassfest refuses it."""
    assert not [requirement for requirement in MANIFEST["requirements"] if requirement.split("=")[0] == "requests"]


def test_manifest_requirements_are_the_runtime_dependencies() -> None:
    """Test that every requirement of the manifest is a dependency of the project, with the same specifier."""
    assert set(MANIFEST["requirements"]) <= set(PYPROJECT["project"]["dependencies"])
