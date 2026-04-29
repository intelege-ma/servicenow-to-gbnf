"""Shared pytest fixtures for servicenow-to-gbnf tests."""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def incident_yaml_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "servicenow-incident.yaml"
