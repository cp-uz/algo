from __future__ import annotations

import html
import json
import os
import shutil
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .checksum import write_manifest
from .markdown import load_document
from .metadata import (
    MetadataError,
    articles,
    generated_articles,
    generated_articles_json,
    generated_review_queue_csv,
    load_manifest,
)
from .rendering import local_asset_sources, render_markdown, slugify
from .util import atomic_write_bytes, atomic_write_text, sha256_file

STAGE_LABELS = {
    "technical_review_pending": "Texnik review kutilmoqda",
    "technical_changes_requested": "Texnik o‘zgartirish so‘ralgan",
    "language_review_pending": "Til reviewi kutilmoqda",
    "language_changes_requested": "Til bo‘yicha o‘zgartirish so‘ralgan",
    "ready_to_publish": "Nashrga tayyor",
    "published": "Nashr qilingan",
    "upstream_changed": "Upstream o‘zgargan",
    "upstream_missing": "Upstream topilmadi",
    "needs_re_review": "Qayta review kerak",
    "deprecated": "Eskirgan",
}
REVIEW_LABELS = {
    "pending": "kutilmoqda",
    "approved": "tasdiqlangan",
    "changes_requested": "o‘zgartirish so‘ralgan",
    "stale": "eskirgan — qayta review kerak",
}


@dataclass(frozen=True)
class BuildResult:
    article_count: int
    page_count: int
    output: Path


def _environment(root: Path) -> Environment:
    environment = Environment(
        loader=FileSystemLoader(root / "templates" / "site"),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return environment


def _load_site_config(root: Path) -> dict[str, Any]:
    path = root / "data" / "site.yml"
    if not path.is_file():
        return {
            "site_name": "CP.UZ Algoritmlar",
            "editor_base_url": "",
            "repository_url": "https://github.com/cp-uz/algo",
        }
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MetadataError("data/site.yml must contain a mapping")
    return value


def route_prefix(route: str) -> str:
    return "../" * (len(Path(route).parts) - 1)


def service_url(editor_base_url: str, relative: str, *, prefix: str) -> str:
    relative = relative.lstrip("/")
    base = editor_base_url.strip()
    if not base:
        return prefix + relative
    return base.rstrip("/") + "/" + relative


def _review_detail(article: dict[str, Any], review_type: str) -> str:
    effective = article[f"{review_type}_review"]
    record = article[f"{review_type}_review_record"]
    label = REVIEW_LABELS.get(effective, effective)
    if record.get("reviewer") and record.get("reviewed_at"):
        return f"{label} — {record['reviewer']}, {record['reviewed_at']}"
    return label


def _copy_article_assets(
    *,
    root: Path,
    output_root: Path,
    article: dict[str, Any],
    rendered_html: str,
) -> None:
    source_dir = (root / "docs" / article["path"]).parent.resolve()
    output_dir = (output_root / article["route"]).parent.resolve()
    docs_root = (root / "docs").resolve()
    site_root = output_root.resolve()
    for raw_src in local_asset_sources(rendered_html):
        parts = urlsplit(raw_src)
        if parts.scheme or parts.netloc or not parts.path:
            continue
        relative = Path(parts.path)
        source = (source_dir / relative).resolve()
        destination = (output_dir / relative).resolve()
        try:
            source.relative_to(docs_root)
            destination.relative_to(site_root)
        except ValueError as exc:
            raise MetadataError(f"unsafe asset path {raw_src!r} in {article['path']}") from exc
        if not source.is_file():
            raise MetadataError(f"missing local asset {raw_src!r} referenced by {article['path']}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _render_site(root: Path, output: Path, manifest: dict[str, Any]) -> BuildResult:
    environment = _environment(root)
    config = _load_site_config(root)
    flattened = generated_articles(root, manifest)
    canonical_by_path = {item["path"]: item for item in articles(manifest)}
    flat_by_path = {item["path"]: item for item in flattened}
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(root / "assets", output / "assets", dirs_exist_ok=True)

    search_data = [
        {
            "title": item["title_uz"],
            "source_title": item["source_title"],
            "category": item["category_uz"],
            "summary": item["idea_uz"],
            "status": item["workflow_stage"],
            "url": item["route"],
        }
        for item in flattened
    ]
    atomic_write_text(output / "assets" / "articles.json", json.dumps(search_data, ensure_ascii=False, indent=2) + "\n")

    common = {
        "repository_url": config.get("repository_url", "https://github.com/cp-uz/algo"),
    }
    editor_base = str(os.environ.get("CPUZ_EDITOR_BASE_URL", config.get("editor_base_url", "")))

    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for item in flattened:
        enriched = dict(item)
        enriched["stage_label"] = STAGE_LABELS.get(item["workflow_stage"], item["workflow_stage"])
        groups.setdefault(item["category_uz"], []).append(enriched)
    group_values = [
        {"name": name, "slug": slugify(name), "articles": values}
        for name, values in groups.items()
    ]
    stats = {
        "total": len(flattened),
        "full": sum(1 for item in flattened if item["full_prose_translated"]),
        "reviewed": sum(
            1
            for item in flattened
            if item["technical_review"] == "approved" and item["language_review"] == "approved"
        ),
        "published": sum(1 for item in flattened if item["publication_status"] == "published"),
    }
    home = environment.get_template("index.html").render(
        title="Bosh sahifa",
        description=config.get("site_description", "CP.UZ algoritmlar"),
        prefix="",
        moderation_url=service_url(editor_base, "moderation/", prefix=""),
        groups=group_values,
        stats=stats,
        **common,
    )
    atomic_write_text(output / "index.html", home)

    article_template = environment.get_template("article.html")
    for index, item in enumerate(flattened):
        canonical = canonical_by_path[item["path"]]
        document = load_document(root / "docs" / item["path"])
        rendered = render_markdown(
            document.body,
            article=canonical,
            article_by_path=canonical_by_path,
            remove_h1=True,
        )
        _copy_article_assets(
            root=root, output_root=output, article=item, rendered_html=rendered.html
        )
        prefix = route_prefix(item["route"])
        edit_path = "edit/" + quote(item["path"], safe="/")
        page = article_template.render(
            title=item["title_uz"],
            description=item["idea_uz"],
            body_class="article-page",
            prefix=prefix,
            moderation_url=service_url(editor_base, "moderation/", prefix=prefix),
            edit_url=service_url(editor_base, edit_path, prefix=prefix),
            article=item,
            rendered_html=rendered.html,
            toc=rendered.toc,
            category_slug=slugify(item["category_uz"]),
            stage_label=STAGE_LABELS.get(item["workflow_stage"], item["workflow_stage"]),
            technical_label=REVIEW_LABELS.get(item["technical_review"], item["technical_review"]),
            language_label=REVIEW_LABELS.get(item["language_review"], item["language_review"]),
            technical_detail=_review_detail(item, "technical"),
            language_detail=_review_detail(item, "language"),
            previous=flattened[index - 1] if index else None,
            following=flattened[index + 1] if index + 1 < len(flattened) else None,
            **common,
        )
        destination = output / item["route"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(destination, page)

    status_stats = {
        "total": len(flattened),
        "technical_approved": sum(1 for item in flattened if item["technical_review"] == "approved"),
        "language_approved": sum(1 for item in flattened if item["language_review"] == "approved"),
        "stale": sum(
            1
            for item in flattened
            if item["workflow_stage"] in {"needs_re_review", "upstream_changed", "upstream_missing"}
        ),
    }
    status_articles: list[dict[str, Any]] = []
    for item in flattened:
        enriched = dict(item)
        enriched.update(
            {
                "stage_label": STAGE_LABELS.get(item["workflow_stage"], item["workflow_stage"]),
                "technical_label": REVIEW_LABELS.get(item["technical_review"], item["technical_review"]),
                "language_label": REVIEW_LABELS.get(item["language_review"], item["language_review"]),
            }
        )
        status_articles.append(enriched)
    status = environment.get_template("status.html").render(
        title="Review holati",
        prefix="../",
        moderation_url=service_url(editor_base, "moderation/", prefix="../"),
        articles=status_articles,
        stats=status_stats,
        **common,
    )
    (output / "status").mkdir(exist_ok=True)
    atomic_write_text(output / "status" / "index.html", status)

    glossary_data = yaml.safe_load((root / "data" / "glossary.yml").read_text(encoding="utf-8"))
    if not isinstance(glossary_data, list):
        raise MetadataError("data/glossary.yml must contain a list")
    glossary = environment.get_template("glossary.html").render(
        title="Terminologiya lug‘ati",
        prefix="../",
        moderation_url=service_url(editor_base, "moderation/", prefix="../"),
        glossary=glossary_data,
        **common,
    )
    (output / "glossary").mkdir(exist_ok=True)
    atomic_write_text(output / "glossary" / "index.html", glossary)

    attribution = environment.get_template("attribution.html").render(
        title="Manba va litsenziya",
        prefix="../",
        moderation_url=service_url(editor_base, "moderation/", prefix="../"),
        **common,
    )
    (output / "attribution").mkdir(exist_ok=True)
    atomic_write_text(output / "attribution" / "index.html", attribution)

    contribute = environment.get_template("contribute.html").render(
        title="Hissa qo‘shish",
        prefix="../",
        moderation_url=service_url(editor_base, "moderation/", prefix="../"),
        **common,
    )
    (output / "contribute").mkdir(exist_ok=True)
    atomic_write_text(output / "contribute" / "index.html", contribute)

    not_found = environment.get_template("not_found.html").render(
        title="Sahifa topilmadi",
        prefix="",
        moderation_url=service_url(editor_base, "moderation/", prefix=""),
        **common,
    )
    atomic_write_text(output / "404.html", not_found)

    page_count = len(list(output.rglob("*.html")))
    return BuildResult(article_count=len(flattened), page_count=page_count, output=output)


def _tree_hashes(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def compare_generated_site(root: Path, manifest: dict[str, Any] | None = None) -> list[str]:
    canonical = manifest if manifest is not None else load_manifest(root)
    with tempfile.TemporaryDirectory(prefix=".site-build-check-", dir=root) as temporary:
        expected_root = Path(temporary) / "site"
        _render_site(root, expected_root, canonical)
        expected = _tree_hashes(expected_root)
        actual = _tree_hashes(root / "site")
    errors: list[str] = []
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    changed = sorted(path for path in set(expected) & set(actual) if expected[path] != actual[path])
    if missing:
        errors.append(f"site/ is missing {len(missing)} generated files; first: {missing[:5]}")
    if extra:
        errors.append(f"site/ has {len(extra)} stale generated files; first: {extra[:5]}")
    if changed:
        errors.append(f"site/ has {len(changed)} out-of-date files; first: {changed[:5]}")
    return errors


def build_repository(root: Path, *, check: bool = False) -> BuildResult:
    """Build all derived outputs without ever mutating canonical docs/.

    A normal build stages the complete site first, then atomically swaps it and
    updates JSON/CSV/checksums as one recoverable transaction. Any failure,
    including a final source-integrity check, restores every previously
    committed generated artifact.
    """

    root = root.resolve()
    docs_before = _tree_hashes(root / "docs")
    manifest = load_manifest(root, validate=True, validate_documents=True)
    expected_json = generated_articles_json(root, manifest)
    expected_csv = generated_review_queue_csv(root, manifest)

    temporary = Path(tempfile.mkdtemp(prefix=".site-build-", dir=root))
    staged_site = temporary / "site"
    try:
        result = _render_site(root, staged_site, manifest)
        if _tree_hashes(root / "docs") != docs_before:
            raise RuntimeError("build attempted to modify canonical docs/ Markdown or assets")

        if check:
            errors = compare_generated_site(root, manifest)
            generated_expectations = {
                root / "data" / "articles.json": expected_json,
                root / "data" / "review_queue.csv": expected_csv,
            }
            for path, expected in generated_expectations.items():
                if not path.is_file():
                    errors.append(f"missing generated file {path.relative_to(root)}")
                elif path.read_text(encoding="utf-8") != expected:
                    errors.append(
                        f"{path.relative_to(root)} is not generated from data/articles.yml"
                    )
            if errors:
                raise MetadataError("\n".join(errors))
            return BuildResult(result.article_count, result.page_count, root / "site")

        generated_paths = (
            root / "data" / "articles.json",
            root / "data" / "review_queue.csv",
            root / "MANIFEST.sha256",
        )
        previous_files: dict[Path, bytes | None] = {
            path: path.read_bytes() if path.is_file() else None
            for path in generated_paths
        }
        site = root / "site"
        old_site = temporary / "old-site"
        had_site = site.exists()
        if had_site:
            os.replace(site, old_site)

        try:
            os.replace(staged_site, site)
            atomic_write_text(root / "data" / "articles.json", expected_json)
            atomic_write_text(root / "data" / "review_queue.csv", expected_csv)
            write_manifest(root)
            if _tree_hashes(root / "docs") != docs_before:
                raise RuntimeError("build changed canonical docs/ after output replacement")
        except BaseException:
            if site.exists():
                shutil.rmtree(site)
            if had_site and old_site.exists():
                os.replace(old_site, site)
            for path, previous in previous_files.items():
                if previous is None:
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        pass
                else:
                    atomic_write_bytes(path, previous)
            raise

        return BuildResult(result.article_count, result.page_count, site)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
