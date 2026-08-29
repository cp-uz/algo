from __future__ import annotations

from typing import Any

from .metadata import MetadataError, effective_review_status
from .util import utc_now


def empty_review() -> dict[str, Any]:
    return {
        "status": "pending",
        "reviewer": None,
        "reviewed_at": None,
        "notes": None,
        "content_sha256": None,
        "source_commit": None,
    }


def append_history(
    article: dict[str, Any],
    *,
    event: str,
    actor: str,
    at: str,
    notes: str | None = None,
    content_sha256: str | None = None,
    source_commit: str | None = None,
    **extra: Any,
) -> None:
    if not actor.strip():
        raise MetadataError("an actor/reviewer name is required for audit history")
    entry: dict[str, Any] = {
        "event": event,
        "actor": actor.strip(),
        "at": at,
        "notes": notes.strip() if isinstance(notes, str) and notes.strip() else None,
        "content_sha256": content_sha256,
        "source_commit": source_commit,
    }
    for key, value in extra.items():
        if value is not None:
            entry[key] = value
    article["review_history"].append(entry)


def _reset_review(
    article: dict[str, Any],
    review_type: str,
    *,
    actor: str,
    at: str,
    reason: str,
    content_sha256: str,
) -> bool:
    previous = article["reviews"][review_type]
    if previous["status"] == "pending" and all(
        previous.get(field) is None
        for field in ("reviewer", "reviewed_at", "notes", "content_sha256", "source_commit")
    ):
        return False
    append_history(
        article,
        event=f"{review_type}_review_invalidated",
        actor=actor,
        at=at,
        notes=reason,
        content_sha256=content_sha256,
        source_commit=article["source"]["commit"],
        previous_status=previous.get("status"),
        previous_reviewer=previous.get("reviewer"),
        previous_reviewed_at=previous.get("reviewed_at"),
    )
    article["reviews"][review_type] = empty_review()
    return True


def _update_ready_state(article: dict[str, Any], body_sha256: str, *, actor: str, at: str) -> None:
    publication = article["publication"]
    if publication["status"] in {"published", "deprecated"}:
        return
    technical = effective_review_status(article, "technical", body_sha256)
    language = effective_review_status(article, "language", body_sha256)
    desired = (
        "ready"
        if technical == "approved"
        and language == "approved"
        and article["upstream"]["status"] == "current"
        else "draft"
    )
    if publication["status"] != desired:
        publication["status"] = desired
        publication["changed_at"] = at
        publication["changed_by"] = actor


def set_review_status(
    article: dict[str, Any],
    *,
    review_type: str,
    status: str,
    reviewer: str,
    body_sha256: str,
    notes: str | None = None,
    at: str | None = None,
) -> None:
    if review_type not in {"technical", "language"}:
        raise MetadataError("review type must be 'technical' or 'language'")
    if status not in {"pending", "approved", "changes_requested"}:
        raise MetadataError("review status must be pending, approved, or changes_requested")
    reviewer = reviewer.strip()
    if not reviewer:
        raise MetadataError("reviewer is required")
    now = at or utc_now()
    source_commit = article["source"]["commit"]

    if article["publication"]["status"] == "deprecated":
        raise MetadataError("deprecated articles cannot be reviewed")
    if article["upstream"]["status"] == "deprecated":
        raise MetadataError("an article with deprecated upstream source cannot be reviewed")

    if review_type == "language" and status in {"approved", "changes_requested"}:
        technical = effective_review_status(article, "technical", body_sha256)
        if technical != "approved":
            raise MetadataError(
                "language review requires a current approved technical review for the same content"
            )

    previous_review = article["reviews"][review_type]
    previous_was_current = (
        previous_review.get("status") == status
        and previous_review.get("content_sha256") == body_sha256
        and previous_review.get("source_commit") == source_commit
        and previous_review.get("reviewer") == reviewer
    )
    if previous_review.get("status") != "pending" and not previous_was_current:
        append_history(
            article,
            event=f"{review_type}_review_superseded",
            actor=reviewer,
            at=now,
            notes="A newer review decision replaced the previous review record.",
            content_sha256=body_sha256,
            source_commit=source_commit,
            previous_status=previous_review.get("status"),
            previous_reviewer=previous_review.get("reviewer"),
            previous_reviewed_at=previous_review.get("reviewed_at"),
            previous_content_sha256=previous_review.get("content_sha256"),
        )
        if article["publication"]["status"] == "published":
            article["publication"].update(
                {"status": "draft", "changed_at": now, "changed_by": reviewer}
            )

    if status == "pending":
        _reset_review(
            article,
            review_type,
            actor=reviewer,
            at=now,
            reason=notes or "Review reset to pending.",
            content_sha256=body_sha256,
        )
        if review_type == "technical":
            _reset_review(
                article,
                "language",
                actor=reviewer,
                at=now,
                reason="Technical review was reset; language approval is no longer valid.",
                content_sha256=body_sha256,
            )
        if article["publication"]["status"] != "deprecated":
            article["publication"].update(
                {"status": "draft", "changed_at": now, "changed_by": reviewer}
            )
        append_history(
            article,
            event=f"{review_type}_review_set_pending",
            actor=reviewer,
            at=now,
            notes=notes,
            content_sha256=body_sha256,
            source_commit=source_commit,
        )
        return

    article["reviews"][review_type] = {
        "status": status,
        "reviewer": reviewer,
        "reviewed_at": now,
        "notes": notes.strip() if isinstance(notes, str) and notes.strip() else None,
        "content_sha256": body_sha256,
        "source_commit": source_commit,
    }
    append_history(
        article,
        event=f"{review_type}_review_{status}",
        actor=reviewer,
        at=now,
        notes=notes,
        content_sha256=body_sha256,
        source_commit=source_commit,
    )

    if review_type == "technical":
        if status == "changes_requested":
            _reset_review(
                article,
                "language",
                actor=reviewer,
                at=now,
                reason="Technical changes were requested.",
                content_sha256=body_sha256,
            )
        elif status == "approved":
            language = article["reviews"]["language"]
            if language["status"] == "approved" and (
                language.get("content_sha256") != body_sha256
                or language.get("source_commit") != source_commit
            ):
                _reset_review(
                    article,
                    "language",
                    actor=reviewer,
                    at=now,
                    reason="Technical review was approved for newer content.",
                    content_sha256=body_sha256,
                )

    if status == "changes_requested":
        article["publication"].update(
            {"status": "draft", "changed_at": now, "changed_by": reviewer}
        )
    else:
        _update_ready_state(article, body_sha256, actor=reviewer, at=now)


def approve_review(
    article: dict[str, Any],
    *,
    review_type: str,
    reviewer: str,
    body_sha256: str,
    notes: str | None = None,
    at: str | None = None,
) -> None:
    set_review_status(
        article,
        review_type=review_type,
        status="approved",
        reviewer=reviewer,
        body_sha256=body_sha256,
        notes=notes,
        at=at,
    )


def request_changes(
    article: dict[str, Any],
    *,
    review_type: str,
    reviewer: str,
    body_sha256: str,
    notes: str | None = None,
    at: str | None = None,
) -> None:
    set_review_status(
        article,
        review_type=review_type,
        status="changes_requested",
        reviewer=reviewer,
        body_sha256=body_sha256,
        notes=notes,
        at=at,
    )


def record_content_change(
    article: dict[str, Any],
    *,
    actor: str,
    old_body_sha256: str,
    new_body_sha256: str,
    new_title: str,
    summary: str | None = None,
    proposal_id: int | None = None,
    at: str | None = None,
) -> None:
    now = at or utc_now()
    if old_body_sha256 == new_body_sha256:
        raise MetadataError("the proposed content is identical to the current article")
    _reset_review(
        article,
        "technical",
        actor=actor,
        at=now,
        reason="Article content changed and requires technical re-review.",
        content_sha256=new_body_sha256,
    )
    _reset_review(
        article,
        "language",
        actor=actor,
        at=now,
        reason="Article content changed and requires language re-review.",
        content_sha256=new_body_sha256,
    )
    article["translation"]["title"] = new_title
    if article["translation"]["status"] not in {"needs_retranslation", "deprecated"}:
        # Preserve the documented translation scope while making it clear that a
        # human has now touched the draft.
        article["translation"]["status"] = "human_translation_draft"
    article["publication"].update(
        {"status": "draft", "changed_at": now, "changed_by": actor}
    )
    append_history(
        article,
        event="article_content_changed",
        actor=actor,
        at=now,
        notes=summary,
        content_sha256=new_body_sha256,
        source_commit=article["source"]["commit"],
        previous_content_sha256=old_body_sha256,
        proposal_id=proposal_id,
    )


def publish_article(
    article: dict[str, Any],
    *,
    actor: str,
    body_sha256: str,
    notes: str | None = None,
    at: str | None = None,
) -> None:
    now = at or utc_now()
    if article["upstream"]["status"] != "current":
        raise MetadataError("cannot publish an article whose upstream source is not current")
    for review_type in ("technical", "language"):
        if effective_review_status(article, review_type, body_sha256) != "approved":
            raise MetadataError("both current technical and language approvals are required")
    article["publication"].update(
        {"status": "published", "changed_at": now, "changed_by": actor.strip()}
    )
    append_history(
        article,
        event="article_published",
        actor=actor,
        at=now,
        notes=notes,
        content_sha256=body_sha256,
        source_commit=article["source"]["commit"],
    )


def unpublish_article(
    article: dict[str, Any],
    *,
    actor: str,
    body_sha256: str,
    notes: str | None = None,
    at: str | None = None,
) -> None:
    now = at or utc_now()
    if article["publication"]["status"] == "deprecated":
        raise MetadataError("deprecated articles cannot be unpublished")
    article["publication"].update(
        {"status": "draft", "changed_at": now, "changed_by": actor.strip()}
    )
    _update_ready_state(article, body_sha256, actor=actor, at=now)
    append_history(
        article,
        event="article_unpublished",
        actor=actor,
        at=now,
        notes=notes,
        content_sha256=body_sha256,
        source_commit=article["source"]["commit"],
    )


def deprecate_article(
    article: dict[str, Any],
    *,
    actor: str,
    body_sha256: str,
    notes: str | None = None,
    at: str | None = None,
) -> None:
    now = at or utc_now()
    article["translation"]["status"] = "deprecated"
    article["publication"].update(
        {"status": "deprecated", "changed_at": now, "changed_by": actor.strip()}
    )
    append_history(
        article,
        event="article_deprecated",
        actor=actor,
        at=now,
        notes=notes,
        content_sha256=body_sha256,
        source_commit=article["source"]["commit"],
    )


def mark_upstream_changed(
    article: dict[str, Any],
    *,
    detected_commit: str,
    detected_sha256: str,
    actor: str = "upstream-sync",
    at: str | None = None,
) -> None:
    now = at or utc_now()
    if detected_commit == article["source"]["commit"] and detected_sha256 == article["source"].get(
        "sha256"
    ):
        article["upstream"].update(
            {
                "status": "current",
                "detected_commit": detected_commit,
                "detected_sha256": detected_sha256,
                "checked_at": now,
                "changed_at": None,
            }
        )
        return
    article["upstream"].update(
        {
            "status": "changed",
            "detected_commit": detected_commit,
            "detected_sha256": detected_sha256,
            "checked_at": now,
            "changed_at": now,
        }
    )
    article["translation"]["status"] = "needs_retranslation"
    if article["publication"]["status"] != "deprecated":
        article["publication"].update(
            {"status": "draft", "changed_at": now, "changed_by": actor}
        )
    append_history(
        article,
        event="upstream_source_changed",
        actor=actor,
        at=now,
        notes="Upstream content changed; the Uzbek article was preserved and flagged for comparison.",
        source_commit=article["source"]["commit"],
        detected_commit=detected_commit,
        detected_sha256=detected_sha256,
    )


def accept_upstream_version(
    article: dict[str, Any],
    *,
    new_commit: str,
    new_source_sha256: str,
    body_sha256: str,
    actor: str,
    notes: str | None = None,
    at: str | None = None,
) -> None:
    now = at or utc_now()
    previous_commit = article["source"]["commit"]
    article["source"]["commit"] = new_commit
    article["source"]["sha256"] = new_source_sha256
    article["upstream"].update(
        {
            "status": "current",
            "detected_commit": new_commit,
            "detected_sha256": new_source_sha256,
            "checked_at": now,
            "changed_at": None,
        }
    )
    article["translation"]["status"] = "human_translation_draft"
    _reset_review(
        article,
        "technical",
        actor=actor,
        at=now,
        reason="A newer upstream version was accepted.",
        content_sha256=body_sha256,
    )
    _reset_review(
        article,
        "language",
        actor=actor,
        at=now,
        reason="A newer upstream version was accepted.",
        content_sha256=body_sha256,
    )
    article["publication"].update(
        {"status": "draft", "changed_at": now, "changed_by": actor}
    )
    append_history(
        article,
        event="upstream_version_accepted",
        actor=actor,
        at=now,
        notes=notes,
        content_sha256=body_sha256,
        source_commit=new_commit,
        previous_source_commit=previous_commit,
    )
