from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .util import atomic_write_text, sha256_file

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "mkdocs-site",
    "qa-bin",
    "var",
    ".build",
}
EXCLUDED_PREFIXES = (".site-build-", ".build-stage-", ".site-old-")
EXCLUDED_SUFFIXES = (".pyc", ".pyo", ".db", ".db-shm", ".db-wal")


def should_include(relative: Path) -> bool:
    if relative.name == "MANIFEST.sha256":
        return False
    if relative.name.startswith(EXCLUDED_PREFIXES):
        return False
    if relative.name.endswith(EXCLUDED_SUFFIXES):
        return False
    for part in relative.parts:
        if part in EXCLUDED_PARTS or part.startswith(EXCLUDED_PREFIXES):
            return False
    return True


def manifest_rows(root: Path) -> list[str]:
    rows: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if not should_include(relative):
            continue
        rows.append(f"{sha256_file(path)}  {relative.as_posix()}")
    return rows


def manifest_text(root: Path) -> str:
    return "\n".join(manifest_rows(root)) + "\n"


def write_manifest(root: Path) -> None:
    atomic_write_text(root / "MANIFEST.sha256", manifest_text(root))


def parse_manifest(text: str) -> dict[str, str]:
    import re

    result: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise ValueError(f"malformed checksum row {line_number}")
        digest, relative = match.groups()
        if relative in result:
            raise ValueError(f"duplicate checksum path {relative}")
        result[relative] = digest
    return result


def validate_manifest_file(root: Path) -> list[str]:
    path = root / "MANIFEST.sha256"
    if not path.is_file():
        return ["missing MANIFEST.sha256"]
    try:
        recorded = parse_manifest(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"MANIFEST.sha256: {exc}"]
    current: dict[str, str] = {}
    for row in manifest_rows(root):
        digest, relative = row.split("  ", 1)
        current[relative] = digest
    errors: list[str] = []
    missing = sorted(set(current) - set(recorded))
    stale = sorted(set(recorded) - set(current))
    if missing:
        errors.append(f"MANIFEST.sha256 has {len(missing)} unlisted files; first: {missing[:5]}")
    if stale:
        errors.append(f"MANIFEST.sha256 has {len(stale)} stale paths; first: {stale[:5]}")
    mismatches = sorted(path for path in set(current) & set(recorded) if current[path] != recorded[path])
    if mismatches:
        errors.append(f"MANIFEST.sha256 has {len(mismatches)} checksum mismatches; first: {mismatches[:5]}")
    return errors
