#!/usr/bin/env python3
"""Compatibility entry point for the canonical CP.UZ static builder.

Historically this file contained a second renderer that read generated JSON and
could reintroduce the fragile metadata mirrors. Keeping this thin wrapper avoids
breaking old automation while guaranteeing that every build now uses the same
canonical implementation as ``scripts/build_static.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cpuz.build import build_repository  # noqa: E402
from cpuz.metadata import MetadataError  # noqa: E402


def main() -> None:
    try:
        result = build_repository(ROOT)
    except (MetadataError, OSError, RuntimeError, ValueError) as exc:
        print(f"BUILD FAILED\n{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(
        f"Rendered {result.article_count} articles and {result.page_count} HTML pages "
        f"in {result.output}."
    )


if __name__ == "__main__":
    main()
