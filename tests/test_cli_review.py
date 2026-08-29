from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cpuz.build import build_repository, compare_generated_site
from cpuz.checksum import validate_manifest_file
from cpuz.metadata import article_by_path, load_manifest


def test_review_cli_updates_only_canonical_metadata_then_builds(repo_copy: Path) -> None:
    command = [
        sys.executable,
        "scripts/review.py",
        "approve",
        "algebra/binary-exp.md",
        "--type",
        "technical",
        "--reviewer",
        "CLI Reviewer",
        "--notes",
        "Checked proof and complexity.",
    ]
    completed = subprocess.run(
        command,
        cwd=repo_copy,
        text=True,
        capture_output=True,
        check=True,
        timeout=120,
    )
    assert "technical review -> approved" in completed.stdout
    manifest = load_manifest(repo_copy)
    article = article_by_path(manifest, "algebra/binary-exp.md")
    assert article["reviews"]["technical"]["status"] == "approved"
    assert article["reviews"]["technical"]["reviewer"] == "CLI Reviewer"
    generated = json.loads((repo_copy / "data" / "articles.json").read_text(encoding="utf-8"))
    binary = next(item for item in generated if item["path"] == "algebra/binary-exp.md")
    assert binary["technical_review"] == "approved"

    build_repository(repo_copy)
    assert compare_generated_site(repo_copy) == []
    assert validate_manifest_file(repo_copy) == []
