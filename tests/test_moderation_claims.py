from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from web.db import Database, ProposalStateError, User


def user(database: Database, number: int, role: str, name: str) -> User:
    return database.upsert_user(
        github_id=str(number),
        login=name.casefold().replace(" ", "-"),
        display_name=name,
        email=None,
        avatar_url=None,
        role=role,
    )


def proposal(database: Database, submitter: User) -> int:
    return database.create_proposal(
        article_id="algebra--binary-exp",
        article_path="algebra/binary-exp.md",
        base_content_sha256="a" * 64,
        old_body="# Old\n",
        new_body="# New\n",
        summary="claim test",
        user=submitter,
    )


def test_moderator_claim_is_exclusive_retryable_and_recoverable(tmp_path: Path) -> None:
    database = Database(tmp_path / "claims.sqlite3")
    database.initialize()
    submitter = user(database, 1, "contributor", "Submitter")
    first = user(database, 2, "moderator", "First Moderator")
    second = user(database, 3, "moderator", "Second Moderator")
    proposal_id = proposal(database, submitter)

    first_claim = database.claim_proposal(
        proposal_id, moderator=first, takeover_after_minutes=15
    )
    assert first_claim["moderator_user_id"] == first.id

    # The same moderator may safely retry the interrupted operation.
    retry = database.claim_proposal(
        proposal_id, moderator=first, takeover_after_minutes=15
    )
    assert retry == first_claim

    # A second moderator cannot race the application or reject it while the
    # first moderator owns the active claim.
    with pytest.raises(ProposalStateError, match="First Moderator"):
        database.claim_proposal(
            proposal_id, moderator=second, takeover_after_minutes=15
        )
    with pytest.raises(ProposalStateError, match="being processed"):
        database.moderate(
            proposal_id,
            status="rejected",
            moderator=second,
            feedback="racing rejection",
            event="rejected",
        )

    old = (datetime.now(timezone.utc) - timedelta(minutes=30)).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")
    with database.connect() as connection:
        connection.execute(
            "UPDATE proposal_claims SET claimed_at=? WHERE proposal_id=?",
            (old, proposal_id),
        )

    recovered = database.claim_proposal(
        proposal_id, moderator=second, takeover_after_minutes=15
    )
    assert recovered["moderator_user_id"] == second.id
    assert recovered["moderator_name"] == "Second Moderator"

    # The former owner cannot finish the recovered claim.
    with pytest.raises(ProposalStateError, match="claim changed"):
        database.finish_claim(
            proposal_id,
            status="applied",
            moderator=first,
            feedback=None,
            applied_ref="local",
            applied_url=None,
            applied_pr_number=None,
            applied_commit_sha="b" * 64,
            event="approved",
        )

    database.finish_claim(
        proposal_id,
        status="applied",
        moderator=second,
        feedback="Recovered and approved.",
        applied_ref="local",
        applied_url=None,
        applied_pr_number=None,
        applied_commit_sha="b" * 64,
        event="approved",
    )
    result = database.get_proposal(proposal_id)
    assert result is not None
    assert result["status"] == "applied"
    assert result["claim"] is None
    events = [item["event"] for item in result["events"]]
    assert events.count("approval_claimed") == 1
    assert events.count("approval_claim_taken_over") == 1
    assert events[-1] == "approved"


def test_claim_release_requires_owner_and_allows_later_moderation(tmp_path: Path) -> None:
    database = Database(tmp_path / "release.sqlite3")
    database.initialize()
    submitter = user(database, 11, "contributor", "Submitter")
    owner = user(database, 12, "moderator", "Owner")
    other = user(database, 13, "moderator", "Other")
    proposal_id = proposal(database, submitter)

    database.claim_proposal(proposal_id, moderator=owner, takeover_after_minutes=15)
    database.release_claim(proposal_id, moderator=other, reason="not mine")
    assert database.get_proposal(proposal_id)["claim"]["moderator_user_id"] == owner.id

    database.release_claim(proposal_id, moderator=owner, reason="external API failed")
    assert database.get_proposal(proposal_id)["claim"] is None
    database.moderate(
        proposal_id,
        status="rejected",
        moderator=other,
        feedback="Rejected after the claim was released.",
        event="rejected",
    )
    result = database.get_proposal(proposal_id)
    assert result is not None and result["status"] == "rejected"
    assert "approval_claim_released" in [item["event"] for item in result["events"]]
