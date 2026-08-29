#!/usr/bin/env python3
"""Validate canonical metadata, generated outputs, links, safety and source fidelity."""
from __future__ import annotations

import html
import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SITE = ROOT / "site"
UPSTREAM = ROOT / "upstream" / "src"
sys.path.insert(0, str(ROOT))

from cpuz.build import compare_generated_site  # noqa: E402
from cpuz.checksum import validate_manifest_file  # noqa: E402
from cpuz.markdown import load_document  # noqa: E402
from cpuz.metadata import (  # noqa: E402
    MetadataError,
    articles,
    generated_articles,
    generated_articles_json,
    generated_review_queue_csv,
    load_manifest,
)
from cpuz.rendering import render_markdown  # noqa: E402
from cpuz.util import sha256_file  # noqa: E402

SUPPORT_DOCS = {"index.md", "status.md", "glossary.md", "attribution.md"}
SERVICE_PREFIXES = ("edit", "moderation")
errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    parts = text.split("---\n", 2)
    return parts[2] if len(parts) == 3 else text


def fenced_blocks(markdown: str) -> list[tuple[str, str]]:
    lines = markdown.splitlines(keepends=True)
    result: list[tuple[str, str]] = []
    index = 0
    while index < len(lines):
        opening = re.match(r"^\s*(`{3,}|~{3,})([^\r\n]*)(?:\r?\n)?$", lines[index])
        if not opening:
            index += 1
            continue
        marker = opening.group(1)
        info = opening.group(2).strip()
        closing = re.compile(rf"^\s*{re.escape(marker[0])}{{{len(marker)},}}\s*(?:\r?\n)?$")
        end = index + 1
        while end < len(lines) and not closing.match(lines[end]):
            end += 1
        if end >= len(lines):
            raise ValueError("unterminated fenced code block")
        result.append((info, "".join(lines[index + 1 : end])))
        index = end + 1
    return result


def display_math_blocks(markdown: str) -> list[str]:
    return re.findall(r"\$\$(.*?)\$\$", markdown, flags=re.DOTALL)


def markdown_link_targets(markdown: str) -> list[str]:
    return re.findall(
        r"!?\[[^\]]*\]\(([^\s)]+)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\)", markdown
    )


def inline_code_tokens(markdown: str) -> list[str]:
    without_fences = re.sub(
        r"^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", "", markdown, flags=re.MULTILINE | re.DOTALL
    )
    return re.findall(r"(?<!`)`([^`\n]+)`(?!`)", without_fences)


def local_asset_targets(markdown: str) -> list[str]:
    without_fences = re.sub(
        r"^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", "", markdown, flags=re.MULTILINE | re.DOTALL
    )
    values = re.findall(
        r'<(?:img|source)\b[^>]*?\bsrc=["\']([^"\']+)["\']',
        without_fences,
        flags=re.IGNORECASE,
    )
    values.extend(
        re.findall(
            r'!\[[^\]]*\]\(\s*([^\s)]+)(?:\s+(?:"[^"]*"|\'[^\']*\'))?\s*\)',
            without_fences,
        )
    )
    return values


def sequence_is_subsequence(needed: list[str], available: list[str]) -> bool:
    iterator = iter(available)
    return all(any(candidate == value for candidate in iterator) for value in needed)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.ids: list[str] = []
        self.h1_count = 0
        self.inline_handlers: list[str] = []
        self.script_sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {key: value or "" for key, value in attrs}
        for key in data:
            if key.casefold().startswith("on"):
                self.inline_handlers.append(f"{tag}[{key}]")
        if tag == "a" and data.get("href"):
            self.links.append(("href", data["href"]))
        elif tag in {"img", "script"} and data.get("src"):
            self.links.append(("src", data["src"]))
            if tag == "script":
                self.script_sources.append(data["src"])
        elif tag == "link" and data.get("href"):
            self.links.append(("href", data["href"]))
        if data.get("id"):
            self.ids.append(data["id"])
        if tag == "h1":
            self.h1_count += 1


page_cache: dict[Path, PageParser] = {}


def parse_html(path: Path) -> PageParser:
    if path not in page_cache:
        parser = PageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        page_cache[path] = parser
    return page_cache[path]


def resolve_local_target(current: Path, raw_url: str) -> tuple[Path, str] | None:
    decoded_url = html.unescape(raw_url)
    if decoded_url.startswith("//"):
        return None
    parts = urlsplit(decoded_url)
    if parts.scheme or parts.netloc:
        return None
    path = unquote(parts.path)
    if not path:
        return current, unquote(parts.fragment)
    target = (SITE / path.lstrip("/")) if path.startswith("/") else (current.parent / path)
    target = target.resolve()
    # The editor and moderator routes are served by the FastAPI service rather
    # than by the static output. Resolve first so ../../edit/... is recognized.
    try:
        service_relative = target.relative_to(SITE.resolve()).as_posix()
    except ValueError:
        service_relative = ""
    if any(
        service_relative == prefix or service_relative.startswith(prefix + "/")
        for prefix in SERVICE_PREFIXES
    ):
        return None
    try:
        target.relative_to(SITE.resolve())
    except ValueError:
        fail(f"{current.relative_to(ROOT)}: URL escapes site root: {raw_url!r}")
        return None
    if path.endswith("/") or target.is_dir():
        target = target / "index.html"
    elif not target.exists() and target.suffix == "":
        candidate = target / "index.html"
        if candidate.exists():
            target = candidate
    return target, unquote(parts.fragment)


def validate_site_links() -> None:
    for page in sorted(SITE.rglob("*.html")):
        parser = parse_html(page)
        duplicates = [item for item, count in Counter(parser.ids).items() if count > 1]
        if duplicates:
            fail(f"{page.relative_to(ROOT)}: duplicate HTML IDs {duplicates[:5]}")
        if parser.inline_handlers:
            fail(f"{page.relative_to(ROOT)}: inline event handlers found {parser.inline_handlers[:5]}")
        if parser.h1_count != 1 and page.name != "404.html":
            fail(f"{page.relative_to(ROOT)}: expected exactly one H1, got {parser.h1_count}")
        for attribute, raw_url in parser.links:
            lower = raw_url.strip().casefold()
            if lower.startswith("javascript:"):
                fail(f"{page.relative_to(ROOT)}: unsafe JavaScript URL in {attribute}")
                continue
            if lower.startswith(("mailto:", "tel:", "data:")):
                continue
            resolved = resolve_local_target(page, raw_url)
            if resolved is None:
                continue
            target, fragment = resolved
            if not target.is_file():
                fail(f"{page.relative_to(ROOT)}: broken local {attribute} {raw_url!r}")
                continue
            if fragment and target.suffix.lower() in {".html", ".htm"}:
                if fragment not in parse_html(target).ids:
                    fail(
                        f"{page.relative_to(ROOT)}: missing fragment #{fragment} in "
                        f"{target.relative_to(ROOT)}"
                    )


def validate_source_fidelity(canonical: list[dict]) -> None:
    for article in canonical:
        if not article["translation"]["full_prose_translated"]:
            continue
        upstream_path = UPSTREAM / article["path"]
        if not upstream_path.is_file():
            continue
        translated = load_document(DOCS / article["path"]).body
        source = strip_frontmatter(upstream_path.read_text(encoding="utf-8"))
        label = article["path"]
        try:
            if fenced_blocks(source) != fenced_blocks(translated):
                fail(f"{label}: fenced code differs from bundled pinned upstream source")
        except ValueError as exc:
            fail(f"{label}: code fence parse error: {exc}")
        if not sequence_is_subsequence(display_math_blocks(source), display_math_blocks(translated)):
            fail(f"{label}: pinned upstream display formulas are not preserved in order")
        source_links = Counter(markdown_link_targets(source))
        translated_links = Counter(markdown_link_targets(translated))
        if any(translated_links[value] < count for value, count in source_links.items()):
            missing = list((source_links - translated_links).elements())
            fail(f"{label}: pinned upstream link targets missing: {missing[:5]}")
        source_inline = Counter(inline_code_tokens(source))
        translated_inline = Counter(inline_code_tokens(translated))
        if any(translated_inline[value] < count for value, count in source_inline.items()):
            missing = list((source_inline - translated_inline).elements())
            fail(f"{label}: pinned upstream inline-code tokens missing: {missing[:5]}")
        source_headings = len(re.findall(r"^#{1,6}\s+", source, flags=re.MULTILINE))
        translated_headings = len(re.findall(r"^#{1,6}\s+", translated, flags=re.MULTILINE))
        if translated_headings != source_headings:
            fail(
                f"{label}: heading count differs from bundled source "
                f"({translated_headings} translated, {source_headings} source)"
            )


def validate_assets(canonical: list[dict]) -> None:
    for article in canonical:
        source_page = DOCS / article["path"]
        built_page = SITE / article["route"]
        if not built_page.is_file():
            fail(f"missing generated article route: {article['route']}")
            continue
        body = load_document(source_page).body
        for raw in local_asset_targets(body):
            parts = urlsplit(html.unescape(raw))
            if parts.scheme or parts.netloc or not parts.path:
                continue
            relative = Path(unquote(parts.path))
            source_asset = (source_page.parent / relative).resolve()
            built_asset = (built_page.parent / relative).resolve()
            try:
                source_asset.relative_to(DOCS.resolve())
                built_asset.relative_to(SITE.resolve())
            except ValueError:
                fail(f"{article['path']}: unsafe local asset path {raw!r}")
                continue
            if not source_asset.is_file():
                fail(f"{article['path']}: missing source asset {raw!r}")
            elif not built_asset.is_file():
                fail(f"{article['path']}: generated asset missing {raw!r}")
            elif sha256_file(source_asset) != sha256_file(built_asset):
                fail(f"{article['path']}: generated asset differs from source {raw!r}")


def validate_renderer_security(canonical: list[dict]) -> None:
    probe = """# Probe\n\n<script>alert(1)</script>\n<img src=x onerror=alert(2)>\n[bad](javascript:alert(3))\n\n```cpp\nif (a < b && c > d) return 1;\n```\n"""
    rendered = render_markdown(probe).html.casefold()
    for forbidden in ("<script", "onerror", 'href="javascript:'):
        if forbidden in rendered:
            fail(f"Markdown sanitizer failed security probe for {forbidden!r}")
    if "&lt;" not in rendered or "&amp;" not in rendered or "&gt;" not in rendered:
        fail("code renderer does not safely escape <, > and &")


def validate_design() -> None:
    css_path = ROOT / "assets" / "style.css"
    if not css_path.is_file():
        fail("missing assets/style.css")
        return
    css = css_path.read_text(encoding="utf-8").casefold()
    if "--surface-code:" not in css:
        fail("code background design token --surface-code is missing")
    match = re.search(r"--surface-code:\s*([^;]+)", css)
    if match and match.group(1).strip() in {"#000", "#000000", "black", "rgb(0, 0, 0)"}:
        fail("code blocks still use a black background")
    for required in (".code-block", ".copy-code", "overflow-x: auto", ".article-layout"):
        if required not in css:
            fail(f"site stylesheet is missing required rule {required}")
    for asset in ("cpuz-logo.webp", "cpuz-mark.webp", "favicon.webp"):
        if not (ROOT / "assets" / asset).is_file():
            fail(f"missing logo asset assets/{asset}")


def main() -> None:
    try:
        manifest = load_manifest(ROOT)
    except (MetadataError, OSError, ValueError) as exc:
        print(f"VALIDATION FAILED\n- {exc}")
        raise SystemExit(1) from exc

    canonical = articles(manifest)
    flattened = generated_articles(ROOT, manifest)
    known = {article["path"] for article in canonical}
    document_paths = {path.relative_to(DOCS).as_posix() for path in DOCS.rglob("*.md")}
    unknown = sorted(document_paths - known - SUPPORT_DOCS)
    missing = sorted(known - document_paths)
    if unknown:
        fail(f"docs/ has unregistered article Markdown files: {unknown[:10]}")
    if missing:
        fail(f"canonical metadata references missing Markdown files: {missing[:10]}")

    expected_json = generated_articles_json(ROOT, manifest)
    expected_csv = generated_review_queue_csv(ROOT, manifest)
    for relative, expected in (
        ("data/articles.json", expected_json),
        ("data/review_queue.csv", expected_csv),
    ):
        path = ROOT / relative
        if not path.is_file():
            fail(f"missing generated file {relative}; run make build")
        elif path.read_text(encoding="utf-8") != expected:
            fail(f"{relative} is out of date; run make build")

    if not SITE.is_dir():
        fail("missing generated site/; run make build")
    else:
        for message in compare_generated_site(ROOT, manifest):
            fail(message)
        search_index = SITE / "assets" / "articles.json"
        if not search_index.is_file():
            fail("missing site/assets/articles.json")
        else:
            try:
                if len(json.loads(search_index.read_text(encoding="utf-8"))) != len(canonical):
                    fail("site search index article count differs from canonical manifest")
            except (OSError, json.JSONDecodeError) as exc:
                fail(f"invalid site search index: {exc}")
        expected_pages = len(canonical) + 6
        actual_pages = len(list(SITE.rglob("*.html")))
        if actual_pages != expected_pages:
            fail(f"site page count: expected {expected_pages}, got {actual_pages}")

    for article, flat in zip(canonical, flattened, strict=True):
        if article["source"]["commit"] != (ROOT / "UPSTREAM_PIN").read_text().strip():
            fail(f"{article['path']}: source commit differs from UPSTREAM_PIN")
        if flat["workflow_stage"] == "published" and flat["publication_status"] != "published":
            fail(f"{article['path']}: inconsistent published workflow stage")
        if not article["translation"]["full_prose_translated"] and article["translation"]["scope"] == "full_upstream_article":
            fail(f"{article['path']}: full scope is marked as not fully translated")

    validate_source_fidelity(canonical)
    validate_assets(canonical)
    validate_site_links()
    validate_renderer_security(canonical)
    validate_design()
    for message in validate_manifest_file(ROOT):
        fail(message)

    if errors:
        print(f"VALIDATION FAILED ({len(errors)} errors)")
        for message in errors:
            print(f"- {message}")
        raise SystemExit(1)

    counts = Counter(item["workflow_stage"] for item in flattened)
    print(
        f"OK: {len(canonical)} canonical articles; schema and review transitions valid; "
        f"{len(list(SITE.rglob('*.html')))} deterministic HTML pages; local links/assets valid; "
        f"generated JSON/CSV/checksums synchronized; stages={dict(sorted(counts.items()))}."
    )


if __name__ == "__main__":
    main()
