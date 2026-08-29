#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up the CP.UZ moderation database.")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(os.environ.get("CPUZ_DATABASE_PATH", ROOT / "var" / "proposals.sqlite3")),
    )
    parser.add_argument("--output", type=Path, default=ROOT / "backups")
    args = parser.parse_args()
    if not args.database.is_file():
        raise SystemExit(f"database does not exist: {args.database}")
    from datetime import datetime, timezone

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output / stamp
    output.mkdir(parents=True, exist_ok=False)
    target = output / "proposals.sqlite3"
    with sqlite3.connect(args.database) as source, sqlite3.connect(target) as destination:
        source.backup(destination)
        source.row_factory = sqlite3.Row
        proposals = [dict(row) for row in source.execute("SELECT * FROM proposals ORDER BY id")]
        events = [dict(row) for row in source.execute("SELECT * FROM proposal_events ORDER BY id")]
    (output / "proposals.json").write_text(
        json.dumps({"proposals": proposals, "events": events}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Backup created: {output}")


if __name__ == "__main__":
    main()
