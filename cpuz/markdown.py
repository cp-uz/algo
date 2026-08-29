from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .util import atomic_write_text, sha256_text

FRONT_MATTER_BOUNDARY = "---\n"
MUTABLE_MIRROR_KEYS = {
    "title",
    "source_title",
    "source_url",
    "source_file",
    "source_commit",
    "source_license",
    "upstream_status",
    "translation_status",
    "translation_scope",
    "translation_fidelity",
    "full_prose_translated",
    "technical_review",
    "language_review",
    "translators",
    "reviewers",
    "translated_at",
    "changes",
}


@dataclass(frozen=True)
class ArticleDocument:
    front_matter: dict[str, Any]
    body: str

    @property
    def article_id(self) -> str:
        value = self.front_matter.get("article_id")
        return value if isinstance(value, str) else ""

    @property
    def body_sha256(self) -> str:
        return sha256_text(self.body)


def split_document(text: str) -> ArticleDocument:
    if not text.startswith(FRONT_MATTER_BOUNDARY):
        raise ValueError("article is missing YAML front matter")
    parts = text.split(FRONT_MATTER_BOUNDARY, 2)
    if len(parts) != 3:
        raise ValueError("article has unterminated YAML front matter")
    parsed = yaml.safe_load(parts[1])
    if not isinstance(parsed, dict):
        raise ValueError("article front matter must be a mapping")
    return ArticleDocument(front_matter=parsed, body=parts[2])


def load_document(path: Path) -> ArticleDocument:
    return split_document(path.read_text(encoding="utf-8"))


def dump_front_matter(front_matter: dict[str, Any]) -> str:
    rendered = yaml.safe_dump(
        front_matter,
        allow_unicode=True,
        sort_keys=False,
        width=1000,
        default_flow_style=False,
    )
    return f"{FRONT_MATTER_BOUNDARY}{rendered}{FRONT_MATTER_BOUNDARY}"


def assemble_document(article_id: str, body: str) -> str:
    if not article_id:
        raise ValueError("article_id is required")
    if body.startswith(FRONT_MATTER_BOUNDARY):
        raise ValueError("editable article body must not contain YAML front matter")
    if not body.endswith("\n"):
        body += "\n"
    return dump_front_matter({"article_id": article_id}) + body


def write_document(path: Path, article_id: str, body: str) -> None:
    atomic_write_text(path, assemble_document(article_id, body))


def extract_h1(body: str) -> str:
    matches = re.findall(r"^#\s+(.+?)\s*$", body, flags=re.MULTILINE)
    if not matches:
        raise ValueError("article body must contain one level-one heading")
    if len(matches) != 1:
        raise ValueError(f"article body must contain exactly one level-one heading; found {len(matches)}")
    title = re.sub(r"\s+\{[^{}]*\}\s*$", "", matches[0]).strip()
    if not title:
        raise ValueError("article title is empty")
    return title


def validate_editable_body(body: str, *, max_bytes: int = 1_000_000) -> str:
    encoded = body.encode("utf-8")
    if len(encoded) > max_bytes:
        raise ValueError(f"article body exceeds the {max_bytes}-byte limit")
    if body.startswith(FRONT_MATTER_BOUNDARY):
        raise ValueError("front matter is managed by CP.UZ and cannot be submitted from the editor")
    if "\x00" in body:
        raise ValueError("article body contains a NUL byte")
    extract_h1(body)
    return body if body.endswith("\n") else body + "\n"


def strip_legacy_generated_sections(body: str) -> tuple[str, list[str]]:
    """Remove only the old machine-generated status header and attribution footer.

    The function is intentionally narrow. It leaves the article's prose, examples,
    warnings, formulas and code untouched.
    """
    changes: list[str] = []
    original = body
    body, count = re.subn(
        r"\A(\s*#\s+[^\n]+\n+)"
        r"> \*\*Tarjima holati:\*\*[^\n]*(?:\n>[^\n]*)*\n+",
        r"\1",
        body,
        count=1,
    )
    if count:
        changes.append("removed legacy generated translation-status block")

    footer = re.search(r"\n## Asl maqola va litsenziya\s*\n.*\Z", body, flags=re.DOTALL)
    if footer:
        body = body[: footer.start()] + "\n"
        changes.append("removed legacy generated attribution footer")

    if not body.endswith("\n"):
        body += "\n"
    if body == original and not changes:
        return body, []
    return body, changes
