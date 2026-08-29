#!/usr/bin/env python3
"""Detect cp-algorithms changes and flag translations without overwriting them."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cpuz.checksum import write_manifest  # noqa: E402
from cpuz.metadata import articles, load_manifest, save_manifest, write_derived_metadata  # noqa: E402
from cpuz.util import atomic_write_text, sha256_bytes, stable_json, utc_now  # noqa: E402
from cpuz.workflow import mark_upstream_changed  # noqa: E402


def request_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "cpuz-upstream-sync/2",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not query GitHub compare API: {exc}") from exc


def fetch_source(commit: str, path: str, *, source_dir: Path | None = None) -> bytes:
    if source_dir is not None:
        local = source_dir / path
        if not local.is_file():
            raise FileNotFoundError(f"target source is missing from {source_dir}: {path}")
        return local.read_bytes()
    url = f"https://raw.githubusercontent.com/cp-algorithms/cp-algorithms/{commit}/src/{path}"
    request = urllib.request.Request(url, headers={"User-Agent": "cpuz-upstream-sync/2"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise FileNotFoundError(f"target source does not exist at {commit}: {path}") from exc
        raise RuntimeError(f"GitHub returned HTTP {exc.code} while fetching {path}") from exc
    except (OSError, urllib.error.URLError) as exc:
        # A network outage must abort the sync, not falsely mark an upstream
        # article as deleted.
        raise RuntimeError(f"could not fetch target source {path}: {exc}") from exc


def changed_paths(from_commit: str, to_commit: str, *, compare_json: Path | None) -> set[str]:
    if compare_json:
        data = json.loads(compare_json.read_text(encoding="utf-8"))
    else:
        data = request_json(
            f"https://api.github.com/repos/cp-algorithms/cp-algorithms/compare/{from_commit}...{to_commit}"
        )
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, list):
        raise RuntimeError("GitHub compare result does not contain a files list")
    result: set[str] = set()
    for item in files:
        if isinstance(item, dict) and isinstance(item.get("filename"), str):
            result.add(item["filename"])
        if isinstance(item, dict) and isinstance(item.get("previous_filename"), str):
            result.add(item["previous_filename"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--to-commit", required=True, help="Full 40-character target commit SHA")
    parser.add_argument("--compare-json", type=Path, help="Offline GitHub compare API fixture")
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Read target src/ files from this directory instead of the network (useful in CI/tests)",
    )
    parser.add_argument("--apply", action="store_true", help="Record stale flags in canonical metadata")
    parser.add_argument("--actor", default="upstream-sync")
    args = parser.parse_args()
    if len(args.to_commit) != 40 or any(character not in "0123456789abcdef" for character in args.to_commit):
        raise SystemExit("--to-commit must be a lowercase 40-character SHA")

    manifest = load_manifest(ROOT)
    source_commits = {article["source"]["commit"] for article in articles(manifest)}
    if len(source_commits) != 1:
        raise SystemExit("this command currently requires one shared baseline commit")
    from_commit = next(iter(source_commits))
    paths = changed_paths(from_commit, args.to_commit, compare_json=args.compare_json)
    affected: list[dict[str, Any]] = []
    checked_at = utc_now()
    for article in articles(manifest):
        if article["source"]["file"] not in paths:
            if args.apply:
                article["upstream"].update(
                    {
                        "status": "current",
                        "detected_commit": args.to_commit,
                        "detected_sha256": article["source"].get("sha256"),
                        "checked_at": checked_at,
                        "changed_at": None,
                    }
                )
            continue
        try:
            source = fetch_source(args.to_commit, article["path"], source_dir=args.source_dir)
            digest = sha256_bytes(source)
            missing = False
        except FileNotFoundError:
            digest = "0" * 64
            missing = True
        affected.append(
            {
                "path": article["path"],
                "source_file": article["source"]["file"],
                "old_commit": article["source"]["commit"],
                "new_commit": args.to_commit,
                "new_sha256": None if missing else digest,
                "missing_at_target": missing,
            }
        )
        if args.apply:
            if missing:
                article["upstream"].update(
                    {
                        "status": "missing",
                        "detected_commit": args.to_commit,
                        "detected_sha256": None,
                        "checked_at": checked_at,
                        "changed_at": checked_at,
                    }
                )
                article["translation"]["status"] = "needs_retranslation"
                article["publication"].update(
                    {"status": "draft", "changed_at": checked_at, "changed_by": args.actor}
                )
            else:
                mark_upstream_changed(
                    article,
                    detected_commit=args.to_commit,
                    detected_sha256=digest,
                    actor=args.actor,
                    at=checked_at,
                )

    report = {
        "from_commit": from_commit,
        "to_commit": args.to_commit,
        "checked_at": checked_at,
        "changed_repository_paths": len(paths),
        "affected_articles": affected,
        "applied": args.apply,
        "canonical_markdown_overwritten": False,
    }
    short_from, short_to = from_commit[:8], args.to_commit[:8]
    json_path = ROOT / "reports" / f"upstream-sync-{short_from}-{short_to}.json"
    md_path = ROOT / "reports" / f"upstream-sync-{short_from}-{short_to}.md"
    atomic_write_text(json_path, stable_json(report))
    lines = [
        f"# Upstream sync {short_from} → {short_to}",
        "",
        f"Affected translated articles: **{len(affected)}**",
        "",
        "The Uzbek files under `docs/` were not modified.",
        "",
    ]
    lines.extend(f"- `{item['path']}`" for item in affected)
    atomic_write_text(md_path, "\n".join(lines) + "\n")
    if args.apply:
        save_manifest(ROOT, manifest)
        write_derived_metadata(ROOT, manifest)
        write_manifest(ROOT)
    print(f"Compared {short_from}..{short_to}; {len(affected)} article(s) affected.")
    print(f"Reports: {json_path.relative_to(ROOT)}, {md_path.relative_to(ROOT)}")
    print("Applied stale flags." if args.apply else "Dry run only; no canonical file changed.")


if __name__ == "__main__":
    main()
