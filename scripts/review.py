#!/usr/bin/env python3
"""Manage article reviews without editing generated metadata by hand."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cpuz.markdown import extract_h1, load_document  # noqa: E402
from cpuz.metadata import (  # noqa: E402
    MetadataError,
    article_by_path,
    article_path,
    generated_articles,
    load_manifest,
)
from cpuz.persistence import persist_manifest_bundle  # noqa: E402
from cpuz.workflow import (  # noqa: E402
    append_history,
    deprecate_article,
    publish_article,
    set_review_status,
    unpublish_article,
)
from cpuz.util import ensure_relative_posix, utc_now  # noqa: E402


def normalize_article(value: str) -> str:
    value = value.replace("\\", "/")
    if value.startswith("docs/"):
        value = value[5:]
    return ensure_relative_posix(value, suffix=".md")


def persist(manifest: dict) -> None:
    persist_manifest_bundle(ROOT, manifest)


def sync_title(article: dict, body: str, *, actor: str) -> None:
    title = extract_h1(body)
    old = article["translation"]["title"]
    if title == old:
        return
    article["translation"]["title"] = title
    append_history(
        article,
        event="article_title_synced",
        actor=actor,
        at=utc_now(),
        notes=f"Canonical title changed from {old!r} to {title!r} after a Markdown edit.",
        content_sha256=load_document(article_path(ROOT, article)).body_sha256,
        source_commit=article["source"]["commit"],
    )


def review_command(args: argparse.Namespace) -> None:
    manifest = load_manifest(ROOT, validate=True, validate_documents=False)
    article = article_by_path(manifest, normalize_article(args.article))
    document = load_document(article_path(ROOT, article))
    sync_title(article, document.body, actor=args.reviewer)
    action_to_status = {
        "approve": "approved",
        "request-changes": "changes_requested",
        "pending": "pending",
    }
    set_review_status(
        article,
        review_type=args.type,
        status=action_to_status[args.action],
        reviewer=args.reviewer,
        body_sha256=document.body_sha256,
        notes=args.notes,
    )
    persist(manifest)
    print(
        f"{article['path']}: {args.type} review -> {action_to_status[args.action]} "
        f"({args.reviewer})"
    )


def publication_command(args: argparse.Namespace) -> None:
    manifest = load_manifest(ROOT, validate=True, validate_documents=False)
    article = article_by_path(manifest, normalize_article(args.article))
    document = load_document(article_path(ROOT, article))
    sync_title(article, document.body, actor=args.actor)
    if args.action == "publish":
        publish_article(
            article,
            actor=args.actor,
            body_sha256=document.body_sha256,
            notes=args.notes,
        )
    elif args.action == "unpublish":
        unpublish_article(
            article,
            actor=args.actor,
            body_sha256=document.body_sha256,
            notes=args.notes,
        )
    else:
        deprecate_article(
            article,
            actor=args.actor,
            body_sha256=document.body_sha256,
            notes=args.notes,
        )
    persist(manifest)
    print(f"{article['path']}: publication -> {article['publication']['status']}")


def status_command(args: argparse.Namespace) -> None:
    manifest = load_manifest(ROOT)
    rows = generated_articles(ROOT, manifest)
    if args.article:
        wanted = normalize_article(args.article)
        rows = [row for row in rows if row["path"] == wanted]
        if not rows:
            raise MetadataError(f"unknown article path: {wanted}")
    print(
        f"{'ARTICLE':52} {'STAGE':29} {'TECHNICAL':18} {'LANGUAGE':18}"
    )
    print("-" * 122)
    for row in rows:
        print(
            f"{row['path'][:52]:52} {row['workflow_stage'][:29]:29} "
            f"{row['technical_review'][:18]:18} {row['language_review'][:18]:18}"
        )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Approve reviews and manage article publication from canonical metadata."
    )
    sub = result.add_subparsers(dest="action", required=True)
    for action in ("approve", "request-changes", "pending"):
        command = sub.add_parser(action)
        command.add_argument("article", help="Article path, with or without docs/")
        command.add_argument("--type", choices=("technical", "language"), required=True)
        command.add_argument("--reviewer", required=True)
        command.add_argument("--notes")
        command.set_defaults(handler=review_command)
    for action in ("publish", "unpublish", "deprecate"):
        command = sub.add_parser(action)
        command.add_argument("article")
        command.add_argument("--actor", required=True)
        command.add_argument("--notes")
        command.set_defaults(handler=publication_command)
    command = sub.add_parser("status")
    command.add_argument("article", nargs="?")
    command.set_defaults(handler=status_command)
    return result


def main() -> None:
    args = parser().parse_args()
    try:
        args.handler(args)
    except (MetadataError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
