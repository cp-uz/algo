from __future__ import annotations

import json
from pathlib import Path

import pytest

import cpuz.build as build_module
import cpuz.persistence as persistence_module
from cpuz.build import build_repository, service_url
from cpuz.checksum import validate_manifest_file
from cpuz.metadata import generated_articles_json, load_manifest
from cpuz.persistence import persist_manifest_bundle
from cpuz.util import sha256_file
from cpuz.workflow import mark_upstream_changed


def hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root / "docs").as_posix(): sha256_file(path)
        for path in (root / "docs").rglob("*")
        if path.is_file()
    }


def tree_hashes(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in root.rglob("*")
        if path.is_file()
    }


def test_build_preserves_human_markdown_and_updates_generated_state(repo_copy: Path) -> None:
    target = repo_copy / "docs" / "algebra" / "binary-exp.md"
    before = hashes(repo_copy)
    marker = "\nBu jumla build xavfsizligi testi uchun inson tomonidan qo‘shildi.\n"
    target.write_text(target.read_text(encoding="utf-8") + marker, encoding="utf-8")

    result = build_repository(repo_copy)
    after = hashes(repo_copy)
    assert result.article_count == 163
    assert result.page_count == 169
    assert target.read_text(encoding="utf-8").endswith(marker)
    for relative, digest in before.items():
        if relative != "algebra/binary-exp.md":
            assert after[relative] == digest
    html = (repo_copy / "site" / "algebra" / "binary-exp" / "index.html").read_text(encoding="utf-8")
    assert "build xavfsizligi testi" in html
    manifest = load_manifest(repo_copy)
    assert (repo_copy / "data" / "articles.json").read_text(encoding="utf-8") == generated_articles_json(repo_copy, manifest)
    assert not validate_manifest_file(repo_copy)
    assert len(json.loads((repo_copy / "data" / "articles.json").read_text(encoding="utf-8"))) == 163


def test_upstream_change_flags_article_without_overwriting_translation(repo_copy: Path) -> None:
    target = repo_copy / "docs" / "algebra" / "binary-exp.md"
    original = target.read_bytes()
    manifest = load_manifest(repo_copy)
    article = manifest["articles"][0]
    mark_upstream_changed(
        article,
        detected_commit="f" * 40,
        detected_sha256="e" * 64,
        at="2026-08-29T12:00:00Z",
    )
    assert article["upstream"]["status"] == "changed"
    assert article["translation"]["status"] == "needs_retranslation"
    assert target.read_bytes() == original


def test_failed_late_build_restores_every_generated_output(
    repo_copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure after installing staged outputs must leave no partial build."""

    site_before = tree_hashes(repo_copy / "site")
    docs_before = tree_hashes(repo_copy / "docs")
    generated_paths = [
        repo_copy / "data" / "articles.json",
        repo_copy / "data" / "review_queue.csv",
        repo_copy / "MANIFEST.sha256",
    ]
    generated_before = {path: path.read_bytes() for path in generated_paths}

    def fail_after_touching_manifest(root: Path) -> None:
        (root / "MANIFEST.sha256").write_text(
            "deliberately incomplete\n", encoding="utf-8"
        )
        raise RuntimeError("simulated checksum failure")

    monkeypatch.setattr(build_module, "write_manifest", fail_after_touching_manifest)
    with pytest.raises(RuntimeError, match="simulated checksum failure"):
        build_repository(repo_copy)

    assert tree_hashes(repo_copy / "site") == site_before
    assert tree_hashes(repo_copy / "docs") == docs_before
    assert {path: path.read_bytes() for path in generated_paths} == generated_before
    assert not list(repo_copy.glob(".site-build-*"))


def test_failed_manifest_bundle_write_restores_canonical_and_derived_files(
    repo_copy: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tracked = [
        repo_copy / "data" / "articles.yml",
        repo_copy / "data" / "articles.json",
        repo_copy / "data" / "review_queue.csv",
        repo_copy / "MANIFEST.sha256",
    ]
    before = {path: path.read_bytes() for path in tracked}
    manifest = load_manifest(repo_copy)
    manifest["articles"][0]["translation"]["idea"] = "transaction failure marker"

    def fail_checksum(root: Path) -> None:
        (root / "MANIFEST.sha256").write_text("broken\n", encoding="utf-8")
        raise RuntimeError("simulated bundle checksum failure")

    monkeypatch.setattr(persistence_module, "write_manifest", fail_checksum)
    with pytest.raises(RuntimeError, match="bundle checksum failure"):
        persist_manifest_bundle(repo_copy, manifest)

    assert {path: path.read_bytes() for path in tracked} == before


def test_editor_service_urls_are_relative_locally_and_absolute_in_pages_builds() -> None:
    assert service_url("", "edit/algebra/binary-exp.md", prefix="../../") == (
        "../../edit/algebra/binary-exp.md"
    )
    assert service_url(
        "https://algo-editor.cp.uz/",
        "edit/algebra/binary-exp.md",
        prefix="../../",
    ) == "https://algo-editor.cp.uz/edit/algebra/binary-exp.md"
