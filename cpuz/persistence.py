from __future__ import annotations

from pathlib import Path
from typing import Any

from .checksum import write_manifest
from .metadata import manifest_path, save_manifest, write_derived_metadata
from .util import atomic_write_bytes


def _snapshot(paths: tuple[Path, ...]) -> dict[Path, bytes | None]:
    return {path: path.read_bytes() if path.is_file() else None for path in paths}


def _restore(snapshot: dict[Path, bytes | None]) -> None:
    for path, content in snapshot.items():
        if content is None:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        else:
            atomic_write_bytes(path, content)


def generated_bundle_paths(root: Path) -> tuple[Path, ...]:
    return (
        root / "data" / "articles.json",
        root / "data" / "review_queue.csv",
        root / "MANIFEST.sha256",
    )


def refresh_generated_bundle(root: Path, manifest: dict[str, Any]) -> None:
    """Regenerate JSON/CSV/checksums as one recoverable operation."""

    paths = generated_bundle_paths(root)
    previous = _snapshot(paths)
    try:
        write_derived_metadata(root, manifest)
        write_manifest(root)
    except BaseException:
        _restore(previous)
        raise


def persist_manifest_bundle(root: Path, manifest: dict[str, Any]) -> None:
    """Persist canonical metadata and its derived files transactionally.

    This does not touch ``docs/`` or ``site/``. Callers that changed a Markdown
    document must restore that document themselves if this operation fails.
    """

    paths = (manifest_path(root), *generated_bundle_paths(root))
    previous = _snapshot(paths)
    try:
        save_manifest(root, manifest)
        write_derived_metadata(root, manifest)
        write_manifest(root)
    except BaseException:
        _restore(previous)
        raise
