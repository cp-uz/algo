from __future__ import annotations

from copy import deepcopy

import pytest

from cpuz.metadata import MetadataError, effective_review_status, load_manifest, workflow_stage
from cpuz.workflow import approve_review, request_changes, set_review_status


def article_record():
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    return deepcopy(load_manifest(root)["articles"][0])


def test_review_state_machine_and_audit_history() -> None:
    article = article_record()
    content_hash = "a" * 64
    timestamp = "2026-08-29T10:00:00Z"

    with pytest.raises(MetadataError, match="language review requires"):
        approve_review(
            article,
            review_type="language",
            reviewer="Language Reviewer",
            body_sha256=content_hash,
            at=timestamp,
        )

    approve_review(
        article,
        review_type="technical",
        reviewer="Technical Reviewer",
        body_sha256=content_hash,
        notes="Algorithms checked.",
        at=timestamp,
    )
    technical = article["reviews"]["technical"]
    assert technical == {
        "status": "approved",
        "reviewer": "Technical Reviewer",
        "reviewed_at": timestamp,
        "notes": "Algorithms checked.",
        "content_sha256": content_hash,
        "source_commit": article["source"]["commit"],
    }
    assert workflow_stage(article, content_hash) == "language_review_pending"

    approve_review(
        article,
        review_type="language",
        reviewer="Language Reviewer",
        body_sha256=content_hash,
        at="2026-08-29T11:00:00Z",
    )
    assert workflow_stage(article, content_hash) == "ready_to_publish"
    assert article["publication"]["status"] == "ready"

    request_changes(
        article,
        review_type="technical",
        reviewer="Technical Reviewer 2",
        body_sha256=content_hash,
        notes="Fix the modular-overflow explanation.",
        at="2026-08-29T12:00:00Z",
    )
    assert article["reviews"]["technical"]["status"] == "changes_requested"
    assert article["reviews"]["language"]["status"] == "pending"
    assert article["publication"]["status"] == "draft"
    events = [event["event"] for event in article["review_history"]]
    assert "technical_review_approved" in events
    assert "language_review_approved" in events
    assert "technical_review_changes_requested" in events
    assert "language_review_invalidated" in events


def test_approval_becomes_stale_after_content_or_upstream_change() -> None:
    article = article_record()
    approved_hash = "b" * 64
    approve_review(
        article,
        review_type="technical",
        reviewer="Reviewer",
        body_sha256=approved_hash,
        at="2026-08-29T10:00:00Z",
    )
    assert effective_review_status(article, "technical", approved_hash) == "approved"
    assert effective_review_status(article, "technical", "c" * 64) == "stale"
    article["upstream"]["status"] = "changed"
    assert effective_review_status(article, "technical", approved_hash) == "stale"


def test_pending_reset_clears_mutable_review_record() -> None:
    article = article_record()
    content_hash = "d" * 64
    approve_review(
        article,
        review_type="technical",
        reviewer="Reviewer",
        body_sha256=content_hash,
        at="2026-08-29T10:00:00Z",
    )
    set_review_status(
        article,
        review_type="technical",
        status="pending",
        reviewer="Lead",
        body_sha256=content_hash,
        notes="Re-opened after discussion.",
        at="2026-08-29T11:00:00Z",
    )
    assert article["reviews"]["technical"] == {
        "status": "pending",
        "reviewer": None,
        "reviewed_at": None,
        "notes": None,
        "content_sha256": None,
        "source_commit": None,
    }
