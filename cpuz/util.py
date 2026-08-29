from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def utc_now() -> str:
    """Return a compact RFC 3339 UTC timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def stable_json(value: Any, *, indent: int = 2) -> str:
    return json.dumps(value, ensure_ascii=False, indent=indent, sort_keys=False) + "\n"


def ensure_relative_posix(value: str, *, suffix: str | None = None) -> str:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
        raise ValueError(f"unsafe relative path: {value!r}")
    normalized = candidate.as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if suffix is not None and not normalized.endswith(suffix):
        raise ValueError(f"path must end with {suffix!r}: {value!r}")
    return normalized


def files_under(root: Path, *, excluded_parts: Iterable[str] = ()) -> dict[str, Path]:
    excluded = set(excluded_parts)
    result: dict[str, Path] = {}
    if not root.exists():
        return result
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in excluded for part in relative.parts):
            continue
        result[relative.as_posix()] = path
    return result
