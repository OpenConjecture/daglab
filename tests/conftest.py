"""Pytest configuration and fixtures for daglab."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def clean_env(monkeypatch):
    """Remove all daglab environment variables for clean test environment."""
    # Remove any existing daglab_ environment variables
    env_vars = list(os.environ.keys())
    for var in env_vars:
        if var.lower().startswith('daglab_'):
            monkeypatch.delenv(var, raising=False)
    yield