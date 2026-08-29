#!/usr/bin/env python3
"""Fetch exact pinned cp-algorithms Markdown without touching Uzbek articles."""
from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cpuz.metadata import articles, load_manifest  # noqa: E402
from cpuz.util import atomic_write_bytes  # noqa: E402


def download(url: str, destination: Path, retries: int = 3) -> None:
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "cpuz-upstream-fetch/2"})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
            atomic_write_bytes(destination, data)
            return
        except (OSError, urllib.error.URLError) as exc:
            if attempt + 1 == retries:
                raise RuntimeError(f"failed to fetch {url}: {exc}") from exc
            time.sleep(2**attempt)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", default=(ROOT / "UPSTREAM_PIN").read_text().strip())
    parser.add_argument("--output", type=Path, default=ROOT / "upstream" / "src")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    manifest = load_manifest(ROOT)
    base = f"https://raw.githubusercontent.com/cp-algorithms/cp-algorithms/{args.commit}/src/"
    values = articles(manifest)
    for index, article in enumerate(values, 1):
        destination = args.output / article["path"]
        if destination.exists() and not args.force:
            print(f"[{index:03}/{len(values)}] exists {article['path']}")
            continue
        print(f"[{index:03}/{len(values)}] fetch  {article['path']}")
        download(base + article["path"], destination)
    download(base + "navigation.md", args.output / "navigation.md")
    print("Upstream snapshots fetched; docs/ was not modified.")


if __name__ == "__main__":
    main()
