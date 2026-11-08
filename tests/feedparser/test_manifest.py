"""Tests for the manifest of the integration."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).parents[2]
MANIFEST = json.loads((ROOT / "custom_components" / "feedparser" / "manifest.json").read_text(encoding="utf-8"))
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_manifest_does_not_list_requests() -> None:
    """Test that the manifest leaves out requests: Home Assistant provides it and hassfest refuses it."""
    assert not [requirement for requirement in MANIFEST["requirements"] if requirement.split("=")[0] == "requests"]


def test_manifest_requirements_are_the_runtime_dependencies() -> None:
    """Test that every requirement of the manifest is a dependency of the project, with the same specifier."""
    assert set(MANIFEST["requirements"]) <= set(PYPROJECT["project"]["dependencies"])
