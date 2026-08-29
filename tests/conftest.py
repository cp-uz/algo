from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))


@pytest.fixture
def repo_copy(tmp_path: Path) -> Path:
    destination = tmp_path / "algo"
    ignored = shutil.ignore_patterns(
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".site-build-*",
        ".site-old-*",
        "var",
        "backups",
        "qa-bin",
        "*.pyc",
    )
    shutil.copytree(SOURCE_ROOT, destination, ignore=ignored)
    return destination
