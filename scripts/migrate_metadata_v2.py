#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cpuz.markdown import (  # noqa: E402
    MUTABLE_MIRROR_KEYS,
    assemble_document,
    extract_h1,
    split_document,
    strip_legacy_generated_sections,
)
from cpuz.metadata import dump_manifest, validate_manifest  # noqa: E402
from cpuz.util import atomic_write_text, sha256_bytes, sha256_file, sha256_text, stable_json  # noqa: E402
from cpuz.workflow import empty_review  # noqa: E402


def scalar(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [scalar(item) for item in value]
    if isinstance(value, dict):
        return {key: scalar(item) for key, item in value.items()}
    return value


def backup_files(root: Path, destination: Path, article_paths: list[str]) -> None:
    if destination.exists():
        raise SystemExit(f"backup destination already exists: {destination}")
    for relative in ["data/articles.yml", "data/articles.json", "data/review_queue.csv"]:
        source = root / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for relative in article_paths:
        source = root / "docs" / relative
        target = destination / "docs" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def review_from_legacy(article: dict[str, Any], review_type: str) -> dict[str, Any]:
    status = article.get(f"{review_type}_review", "pending")
    if status == "pending":
        return empty_review()
    reviewers = article.get("reviewers") or []
    reviewer = str(reviewers[0]) if reviewers else "Legacy reviewer (name not recorded)"
    translated_at = str(article.get("translated_at") or "1970-01-01")
    return {
        "status": status if status in {"approved", "changes_requested"} else "pending",
        "reviewer": reviewer,
        "reviewed_at": f"{translated_at}T00:00:00Z",
        "notes": "Migrated from the legacy flat review fields; exact review time was not recorded.",
        "content_sha256": None,
        "source_commit": article.get("source_commit"),
    }


def migrate(root: Path, *, backup_dir: Path | None) -> dict[str, Any]:
    raw = scalar(yaml.safe_load((root / "data" / "articles.yml").read_text(encoding="utf-8")))
    if isinstance(raw, dict) and raw.get("schema_version") == 2:
        raise SystemExit("data/articles.yml is already schema version 2")
    if not isinstance(raw, list):
        raise SystemExit("legacy data/articles.yml must contain a list")

    if backup_dir is not None:
        backup_files(root, backup_dir, [str(item["path"]) for item in raw])

    migrated_articles: list[dict[str, Any]] = []
    new_documents: dict[Path, str] = {}
    report_rows: list[dict[str, Any]] = []

    for position, legacy in enumerate(raw, 1):
        relative = str(legacy["path"])
        document_path = root / "docs" / relative
        original_bytes = document_path.read_bytes()
        original = split_document(original_bytes.decode("utf-8"))
        cleaned_body, cleanup_changes = strip_legacy_generated_sections(original.body)
        title = extract_h1(cleaned_body)
        legacy_title = str(legacy["title_uz"])
        extras = {
            key: value
            for key, value in original.front_matter.items()
            if key not in MUTABLE_MIRROR_KEYS
        }
        source_snapshot = root / "upstream" / relative.replace(".md", ".md")
        # Bundled snapshots live under upstream/src/<path>.
        source_snapshot = root / "upstream" / "src" / relative
        source_sha = sha256_file(source_snapshot) if source_snapshot.is_file() else None

        technical = review_from_legacy(legacy, "technical")
        language = review_from_legacy(legacy, "language")
        body_hash = sha256_text(cleaned_body)
        for review in (technical, language):
            if review["status"] != "pending":
                review["content_sha256"] = body_hash

        translation_status = str(legacy["translation_status"])
        publication_status = "published" if translation_status == "published" else "draft"
        if publication_status == "published" and not (
            technical["status"] == "approved" and language["status"] == "approved"
        ):
            publication_status = "draft"

        migrated_articles.append(
            {
                "index": position,
                "id": str(legacy["id"]),
                "path": relative,
                "route": str(legacy["route"]),
                "category": str(legacy["category"]),
                "category_uz": str(legacy["category_uz"]),
                "subcategory": str(legacy["subcategory"]),
                "subcategory_uz": str(legacy["subcategory_uz"]),
                "source": {
                    "title": str(legacy["source_title"]),
                    "url": str(legacy["source_url"]),
                    "file": str(legacy["source_file"]),
                    "repo": str(legacy["source_repo"]),
                    "commit": str(legacy["source_commit"]),
                    "license": str(legacy["source_license"]),
                    "sha256": source_sha,
                    "extra_front_matter": extras,
                },
                "translation": {
                    "title": title,
                    "idea": str(legacy.get("idea_uz") or ""),
                    "complexity": str(legacy.get("complexity_uz") or ""),
                    "uses": str(legacy.get("uses_uz") or ""),
                    "status": translation_status,
                    "scope": str(legacy["translation_scope"]),
                    "fidelity": str(legacy["translation_fidelity"]),
                    "full_prose_translated": bool(legacy["full_prose_translated"]),
                    "translators": [str(value) for value in legacy.get("translators", [])],
                    "translated_at": str(legacy["translated_at"]) if legacy.get("translated_at") else None,
                    "changes": str(legacy.get("changes") or ""),
                },
                "upstream": {
                    "status": "current" if legacy.get("upstream_status") == "pinned" else "current",
                    "detected_commit": None,
                    "detected_sha256": None,
                    "checked_at": None,
                    "changed_at": None,
                },
                "publication": {
                    "status": publication_status,
                    "changed_at": None,
                    "changed_by": None,
                },
                "reviews": {"technical": technical, "language": language},
                "review_history": [],
            }
        )
        new_document = assemble_document(str(legacy["id"]), cleaned_body)
        if split_document(new_document).body != cleaned_body:
            raise SystemExit(f"{relative}: migration changed article body unexpectedly")
        new_documents[document_path] = new_document
        report_rows.append(
            {
                "path": relative,
                "original_file_sha256": sha256_bytes(original_bytes),
                "original_body_sha256": sha256_text(original.body),
                "canonical_body_sha256": body_hash,
                "migrated_file_sha256": sha256_text(new_document),
                "cleanup": cleanup_changes,
                "legacy_title": legacy_title,
                "canonical_title": title,
                "title_metadata_corrected_from_h1": legacy_title != title,
                "body_preserved_after_generated_metadata_cleanup": True,
            }
        )

    canonical = {"schema_version": 2, "articles": migrated_articles}

    # Validate the in-memory records first. Documents are written only after all
    # article transformations have succeeded, then validated again atomically.
    for path, text in new_documents.items():
        atomic_write_text(path, text)
    atomic_write_text(root / "data" / "articles.yml", dump_manifest(canonical))
    validate_manifest(root, canonical, validate_documents=True)

    report = {
        "schema_from": 1,
        "schema_to": 2,
        "article_count": len(migrated_articles),
        "documents_changed_only_by_front_matter_and_generated-section_cleanup": True,
        "articles": report_rows,
    }
    atomic_write_text(root / "reports" / "migration-v2.json", stable_json(report))
    return canonical


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate the legacy flat article metadata to schema v2.")
    parser.add_argument(
        "--root", type=Path, default=ROOT, help="Repository root (defaults to this checkout)."
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        help="Optional directory in which to copy every affected source file before migration.",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    backup = args.backup_dir.resolve() if args.backup_dir else None
    migrated = migrate(root, backup_dir=backup)
    print(f"Migrated {len(migrated['articles'])} articles to schema version 2.")
    if backup:
        print(f"Backup: {backup}")


if __name__ == "__main__":
    main()
