from __future__ import annotations

import csv
import io
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import jsonschema
import yaml

from .markdown import MUTABLE_MIRROR_KEYS, extract_h1, load_document
from .util import atomic_write_bytes, atomic_write_text, ensure_relative_posix, stable_json

SCHEMA_VERSION = 2
REVIEW_TYPES = ("technical", "language")
REVIEW_STATUSES = {"pending", "approved", "changes_requested"}
EFFECTIVE_REVIEW_STATUSES = REVIEW_STATUSES | {"stale"}


class MetadataError(ValueError):
    pass


def _normalize_yaml_scalars(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _normalize_yaml_scalars(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_yaml_scalars(item) for item in value]
    return value


def schema_path(root: Path) -> Path:
    return root / "data" / "schema" / "articles.schema.json"


def manifest_path(root: Path) -> Path:
    return root / "data" / "articles.yml"


def load_schema(root: Path) -> dict[str, Any]:
    import json

    return json.loads(schema_path(root).read_text(encoding="utf-8"))


def load_manifest(root: Path, *, validate: bool = True, validate_documents: bool = True) -> dict[str, Any]:
    path = manifest_path(root)
    try:
        data = _normalize_yaml_scalars(yaml.safe_load(path.read_text(encoding="utf-8")))
    except Exception as exc:  # pragma: no cover - exact parser message is external
        raise MetadataError(f"could not parse {path.relative_to(root)}: {exc}") from exc
    if not isinstance(data, dict):
        raise MetadataError("data/articles.yml must contain a mapping")
    if validate:
        validate_manifest(root, data, validate_documents=validate_documents)
    return data


def dump_manifest(data: dict[str, Any]) -> str:
    return yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        width=120,
        default_flow_style=False,
    )


def save_manifest(root: Path, data: dict[str, Any], *, validate: bool = True) -> None:
    if validate:
        validate_manifest(root, data, validate_documents=True)
    atomic_write_text(manifest_path(root), dump_manifest(data))


def articles(data: dict[str, Any]) -> list[dict[str, Any]]:
    value = data.get("articles")
    if not isinstance(value, list):
        raise MetadataError("data/articles.yml must contain an articles list")
    return value


def article_by_path(data: dict[str, Any], path: str) -> dict[str, Any]:
    normalized = ensure_relative_posix(path, suffix=".md")
    for article in articles(data):
        if article.get("path") == normalized:
            return article
    raise MetadataError(f"unknown article path: {normalized}")


def article_by_id(data: dict[str, Any], article_id: str) -> dict[str, Any]:
    for article in articles(data):
        if article.get("id") == article_id:
            return article
    raise MetadataError(f"unknown article id: {article_id}")


def article_path(root: Path, article: dict[str, Any]) -> Path:
    relative = ensure_relative_posix(str(article["path"]), suffix=".md")
    path = (root / "docs" / relative).resolve()
    docs_root = (root / "docs").resolve()
    try:
        path.relative_to(docs_root)
    except ValueError as exc:
        raise MetadataError(f"article path escapes docs/: {relative}") from exc
    return path


def current_body_hash(root: Path, article: dict[str, Any]) -> str:
    return load_document(article_path(root, article)).body_sha256


def effective_review_status(
    article: dict[str, Any], review_type: str, body_sha256: str
) -> str:
    if review_type not in REVIEW_TYPES:
        raise MetadataError(f"unknown review type: {review_type}")
    review = article["reviews"][review_type]
    status = review["status"]
    if status != "approved":
        return status
    if article["upstream"]["status"] != "current":
        return "stale"
    if review.get("content_sha256") != body_sha256:
        return "stale"
    if review.get("source_commit") != article["source"]["commit"]:
        return "stale"
    return "approved"


def workflow_stage(article: dict[str, Any], body_sha256: str) -> str:
    publication = article["publication"]["status"]
    if publication == "deprecated" or article["translation"]["status"] == "deprecated":
        return "deprecated"
    if article["upstream"]["status"] == "changed":
        return "upstream_changed"
    if article["upstream"]["status"] == "missing":
        return "upstream_missing"
    technical = effective_review_status(article, "technical", body_sha256)
    language = effective_review_status(article, "language", body_sha256)
    if technical == "stale" or language == "stale":
        return "needs_re_review"
    if technical == "changes_requested":
        return "technical_changes_requested"
    if technical == "pending":
        return "technical_review_pending"
    if language == "changes_requested":
        return "language_changes_requested"
    if language == "pending":
        return "language_review_pending"
    if publication == "published":
        return "published"
    return "ready_to_publish"


def _review_invariants(label: str, review_type: str, review: dict[str, Any], errors: list[str]) -> None:
    status = review.get("status")
    if status not in REVIEW_STATUSES:
        errors.append(f"{label}: invalid {review_type} review status {status!r}")
        return
    identity_fields = (
        review.get("reviewer"),
        review.get("reviewed_at"),
        review.get("content_sha256"),
        review.get("source_commit"),
    )
    if status == "pending":
        if any(value is not None for value in identity_fields):
            errors.append(
                f"{label}: pending {review_type} review must not carry reviewer/time/hash/source fields"
            )
    else:
        if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
            errors.append(f"{label}: {review_type} {status} requires a reviewer")
        if not review.get("reviewed_at"):
            errors.append(f"{label}: {review_type} {status} requires reviewed_at")
        if not review.get("content_sha256"):
            errors.append(f"{label}: {review_type} {status} requires content_sha256")
        if not review.get("source_commit"):
            errors.append(f"{label}: {review_type} {status} requires source_commit")


def validate_manifest(
    root: Path,
    data: dict[str, Any],
    *,
    validate_documents: bool = True,
) -> None:
    errors: list[str] = []
    try:
        validator = jsonschema.Draft202012Validator(
            load_schema(root), format_checker=jsonschema.FormatChecker()
        )
        for error in sorted(validator.iter_errors(data), key=lambda item: list(item.absolute_path)):
            location = ".".join(str(part) for part in error.absolute_path) or "root"
            errors.append(f"schema {location}: {error.message}")
    except OSError as exc:
        errors.append(f"could not load metadata schema: {exc}")

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    try:
        values = articles(data)
    except MetadataError as exc:
        errors.append(str(exc))
        values = []

    identifiers: set[str] = set()
    paths: set[str] = set()
    routes: set[str] = set()
    for position, article in enumerate(values, 1):
        label = str(article.get("path") or f"article #{position}")
        if article.get("index") != position:
            errors.append(f"{label}: index must be {position}, got {article.get('index')!r}")
        identifier = article.get("id")
        if identifier in identifiers:
            errors.append(f"{label}: duplicate article id {identifier!r}")
        if isinstance(identifier, str):
            identifiers.add(identifier)
        relative = article.get("path")
        if relative in paths:
            errors.append(f"{label}: duplicate article path")
        if isinstance(relative, str):
            paths.add(relative)
        route = article.get("route")
        if route in routes:
            errors.append(f"{label}: duplicate article route")
        if isinstance(route, str):
            routes.add(route)

        if isinstance(relative, str):
            expected_route = str(Path(relative).with_suffix("")).replace("\\", "/") + "/index.html"
            if route != expected_route:
                errors.append(f"{label}: route must be {expected_route!r}")
            source = article.get("source", {})
            if source.get("file") != f"src/{relative}":
                errors.append(f"{label}: source.file must be src/{relative}")

        reviews = article.get("reviews", {})
        for review_type in REVIEW_TYPES:
            review = reviews.get(review_type)
            if isinstance(review, dict):
                _review_invariants(label, review_type, review, errors)
        language = reviews.get("language", {})
        technical = reviews.get("technical", {})
        if language.get("status") == "approved" and technical.get("status") != "approved":
            errors.append(f"{label}: language review cannot be approved before technical review")

        upstream = article.get("upstream", {})
        if upstream.get("status") == "changed":
            for field in ("detected_commit", "detected_sha256", "changed_at"):
                if not upstream.get(field):
                    errors.append(f"{label}: upstream changed status requires {field}")

        if validate_documents and isinstance(relative, str):
            try:
                document = load_document(article_path(root, article))
                if document.article_id != identifier:
                    errors.append(
                        f"{label}: front matter article_id {document.article_id!r} does not match {identifier!r}"
                    )
                mirrored = sorted(MUTABLE_MIRROR_KEYS & set(document.front_matter))
                if mirrored:
                    errors.append(
                        f"{label}: mutable metadata mirrors are forbidden in front matter: {mirrored}"
                    )
                unexpected = sorted(set(document.front_matter) - {"article_id"})
                if unexpected:
                    errors.append(f"{label}: unsupported front matter keys: {unexpected}")
                title = extract_h1(document.body)
                expected_title = article.get("translation", {}).get("title")
                if title != expected_title:
                    errors.append(
                        f"{label}: Markdown H1 {title!r} differs from canonical title {expected_title!r}"
                    )
                body_hash = document.body_sha256
                technical_effective = effective_review_status(article, "technical", body_hash)
                language_effective = effective_review_status(article, "language", body_hash)
                publication = article.get("publication", {}).get("status")
                if publication in {"ready", "published"}:
                    if technical_effective != "approved" or language_effective != "approved":
                        errors.append(
                            f"{label}: {publication} article requires current technical and language approvals"
                        )
                    if upstream.get("status") != "current":
                        errors.append(f"{label}: {publication} article cannot have stale upstream source")
            except (OSError, ValueError, MetadataError) as exc:
                errors.append(f"{label}: {exc}")

    if errors:
        raise MetadataError("\n".join(errors))


def flattened_article(root: Path, article: dict[str, Any]) -> dict[str, Any]:
    body_hash = current_body_hash(root, article)
    source = article["source"]
    translation = article["translation"]
    technical = article["reviews"]["technical"]
    language = article["reviews"]["language"]
    technical_effective = effective_review_status(article, "technical", body_hash)
    language_effective = effective_review_status(article, "language", body_hash)
    return {
        "index": article["index"],
        "id": article["id"],
        "path": article["path"],
        "route": article["route"],
        "category": article["category"],
        "category_uz": article["category_uz"],
        "subcategory": article["subcategory"],
        "subcategory_uz": article["subcategory_uz"],
        "source_title": source["title"],
        "title_uz": translation["title"],
        "idea_uz": translation["idea"],
        "complexity_uz": translation["complexity"],
        "uses_uz": translation["uses"],
        "source_url": source["url"],
        "source_file": source["file"],
        "source_repo": source["repo"],
        "source_commit": source["commit"],
        "source_license": source["license"],
        "source_sha256": source["sha256"],
        "upstream_status": article["upstream"]["status"],
        "translation_status": translation["status"],
        "translation_scope": translation["scope"],
        "translation_fidelity": translation["fidelity"],
        "full_prose_translated": translation["full_prose_translated"],
        "technical_review": technical_effective,
        "language_review": language_effective,
        "technical_review_record": deepcopy(technical),
        "language_review_record": deepcopy(language),
        "translators": deepcopy(translation["translators"]),
        "reviewers": sorted(
            {
                review["reviewer"]
                for review in (technical, language)
                if isinstance(review.get("reviewer"), str) and review["reviewer"]
            }
        ),
        "translated_at": translation["translated_at"],
        "changes": translation["changes"],
        "publication_status": article["publication"]["status"],
        "workflow_stage": workflow_stage(article, body_hash),
        "content_sha256": body_hash,
        "reviews": deepcopy(article["reviews"]),
        "review_history": deepcopy(article["review_history"]),
        "upstream": deepcopy(article["upstream"]),
        "publication": deepcopy(article["publication"]),
    }


def generated_articles(root: Path, data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    manifest = data if data is not None else load_manifest(root)
    return [flattened_article(root, article) for article in articles(manifest)]


def generated_articles_json(root: Path, data: dict[str, Any] | None = None) -> str:
    return stable_json(generated_articles(root, data))


REVIEW_QUEUE_FIELDS = [
    "index",
    "path",
    "title_uz",
    "workflow_stage",
    "translation_status",
    "publication_status",
    "upstream_status",
    "technical_review",
    "technical_reviewer",
    "technical_reviewed_at",
    "language_review",
    "language_reviewer",
    "language_reviewed_at",
    "source_commit",
    "content_sha256",
    "full_prose_translated",
]


def generated_review_queue_csv(root: Path, data: dict[str, Any] | None = None) -> str:
    values = generated_articles(root, data)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=REVIEW_QUEUE_FIELDS, lineterminator="\n")
    writer.writeheader()
    for article in values:
        technical = article["technical_review_record"]
        language = article["language_review_record"]
        writer.writerow(
            {
                "index": article["index"],
                "path": article["path"],
                "title_uz": article["title_uz"],
                "workflow_stage": article["workflow_stage"],
                "translation_status": article["translation_status"],
                "publication_status": article["publication_status"],
                "upstream_status": article["upstream_status"],
                "technical_review": article["technical_review"],
                "technical_reviewer": technical.get("reviewer") or "",
                "technical_reviewed_at": technical.get("reviewed_at") or "",
                "language_review": article["language_review"],
                "language_reviewer": language.get("reviewer") or "",
                "language_reviewed_at": language.get("reviewed_at") or "",
                "source_commit": article["source_commit"],
                "content_sha256": article["content_sha256"],
                "full_prose_translated": str(article["full_prose_translated"]).lower(),
            }
        )
    return buffer.getvalue()


def write_derived_metadata(root: Path, data: dict[str, Any] | None = None) -> None:
    manifest = data if data is not None else load_manifest(root)
    outputs = {
        root / "data" / "articles.json": generated_articles_json(root, manifest),
        root / "data" / "review_queue.csv": generated_review_queue_csv(root, manifest),
    }
    previous = {
        path: path.read_bytes() if path.is_file() else None for path in outputs
    }
    try:
        for path, text in outputs.items():
            atomic_write_text(path, text)
    except BaseException:
        for path, content in previous.items():
            if content is None:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
            else:
                atomic_write_bytes(path, content)
        raise


def review_counts(root: Path, data: dict[str, Any] | None = None) -> dict[str, int]:
    result: dict[str, int] = {}
    for article in generated_articles(root, data):
        for key in (
            article["workflow_stage"],
            f"technical:{article['technical_review']}",
            f"language:{article['language_review']}",
            f"publication:{article['publication_status']}",
        ):
            result[key] = result.get(key, 0) + 1
    return result


def clone_manifest(data: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(data)


def iter_article_paths(data: dict[str, Any]) -> Iterable[str]:
    for article in articles(data):
        yield article["path"]
