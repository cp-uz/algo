#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cpuz.build import build_repository  # noqa: E402
from cpuz.metadata import MetadataError  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the deterministic CP.UZ static site.")
    parser.add_argument("--check", action="store_true", help="Verify generated outputs without modifying them.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        result = build_repository(args.root, check=args.check)
    except (MetadataError, OSError, RuntimeError, ValueError) as exc:
        print(f"BUILD FAILED\n{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    verb = "Verified" if args.check else "Rendered"
    print(f"{verb} {result.article_count} articles and {result.page_count} HTML pages in {result.output}.")


if __name__ == "__main__":
    main()
