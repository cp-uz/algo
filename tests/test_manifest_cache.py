from __future__ import annotations

from pathlib import Path

import web.service as service_module
from cpuz.metadata import dump_manifest, load_manifest
from cpuz.util import atomic_write_text
from web.config import Settings
from web.db import Database
from web.service import EditorService


def test_local_manifest_cache_returns_copies_and_invalidates_external_writes(
    repo_copy: Path, tmp_path: Path, monkeypatch
) -> None:
    settings = Settings.from_env(
        overrides={
            "CPUZ_ENV": "test",
            "CPUZ_REPO_ROOT": str(repo_copy),
            "CPUZ_DATABASE_PATH": str(tmp_path / "cache.sqlite3"),
            "CPUZ_APPLY_MODE": "local",
            "CPUZ_AUTO_BUILD": "false",
        }
    )
    database = Database(settings.database_path)
    database.initialize()

    real_load = service_module.load_manifest
    calls = 0

    def counted_load(*args, **kwargs):
        nonlocal calls
        calls += 1
        return real_load(*args, **kwargs)

    monkeypatch.setattr(service_module, "load_manifest", counted_load)
    service = EditorService(settings, database)
    try:
        first = service.manifest_for_listing()
        original_idea = first["articles"][0]["translation"]["idea"]
        first["articles"][0]["translation"]["idea"] = "request-local mutation"

        second = service.manifest_for_listing()
        assert second["articles"][0]["translation"]["idea"] == original_idea
        assert calls == 1

        # Snapshot content is always read directly even while metadata is cached.
        snapshot = service.snapshot("algebra/binary-exp.md")
        assert snapshot.document.article_id == snapshot.article["id"]
        assert calls == 1

        changed = load_manifest(
            repo_copy, validate=True, validate_documents=False
        )
        changed["articles"][0]["translation"]["idea"] = "external cache invalidation marker"
        atomic_write_text(
            repo_copy / "data" / "articles.yml", dump_manifest(changed)
        )

        refreshed = service.manifest_for_listing()
        assert (
            refreshed["articles"][0]["translation"]["idea"]
            == "external cache invalidation marker"
        )
        assert calls == 2
    finally:
        service.close()
