#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cpuz.metadata import load_manifest  # noqa: E402
from cpuz.persistence import refresh_generated_bundle  # noqa: E402


def main() -> None:
    manifest = load_manifest(ROOT)
    refresh_generated_bundle(ROOT, manifest)
    print(f"Generated articles.json and review_queue.csv for {len(manifest['articles'])} articles.")


if __name__ == "__main__":
    main()
