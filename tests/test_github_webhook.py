from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from web.app import create_app
from web.config import Settings
from web.db import Database, User


SECRET = "webhook-test-secret-that-is-long-enough-123456"


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()


def webhook_payload(
    number: int,
    *,
    merged: bool,
    repository: str = "cp-uz/algo",
    base: str = "main",
) -> dict[str, Any]:
    return {
        "action": "closed",
        "repository": {"full_name": repository},
        "pull_request": {
            "number": number,
            "merged": merged,
            "merge_commit_sha": "f" * 40 if merged else None,
            "html_url": f"https://github.com/cp-uz/algo/pull/{number}",
            "base": {"ref": base},
        },
        "sender": {"login": "maintainer"},
    }


def post_webhook(
    client: TestClient,
    payload: dict[str, Any],
    *,
    delivery: str,
    signature: str | None = None,
):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return client.post(
        "/webhooks/github",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": delivery,
            "X-Hub-Signature-256": signature or sign(body),
        },
    )


def create_pending_merge(database: Database, number: int) -> tuple[int, User]:
    submitter = database.upsert_user(
        github_id=f"submitter-{number}",
        login=f"submitter-{number}",
        display_name=f"Submitter {number}",
        email=None,
        avatar_url=None,
        role="contributor",
    )
    moderator = database.upsert_user(
        github_id="moderator-webhook",
        login="moderator-webhook",
        display_name="Webhook Moderator",
        email=None,
        avatar_url=None,
        role="moderator",
    )
    proposal_id = database.create_proposal(
        article_id="algebra--binary-exp",
        article_path="algebra/binary-exp.md",
        base_content_sha256="a" * 64,
        old_body="# Old\n",
        new_body="# New\n",
        summary="webhook test",
        user=submitter,
    )
    database.claim_proposal(
        proposal_id, moderator=moderator, takeover_after_minutes=15
    )
    database.finish_claim(
        proposal_id,
        status="approved_pending_merge",
        moderator=moderator,
        feedback="Approved; waiting for GitHub.",
        applied_ref=f"cpuz/proposal-{proposal_id}",
        applied_url=f"https://github.com/cp-uz/algo/pull/{number}",
        applied_pr_number=number,
        applied_commit_sha="e" * 40,
        event="approved",
    )
    return proposal_id, moderator


def test_signed_webhook_finalizes_merge_and_is_replay_safe(
    repo_copy: Path, tmp_path: Path
) -> None:
    settings = Settings.from_env(
        overrides={
            "CPUZ_ENV": "test",
            "CPUZ_REPO_ROOT": str(repo_copy),
            "CPUZ_DATABASE_PATH": str(tmp_path / "webhook.sqlite3"),
            "CPUZ_APPLY_MODE": "local",
            "CPUZ_AUTO_BUILD": "false",
            "CPUZ_GITHUB_WEBHOOK_SECRET": SECRET,
        }
    )
    app = create_app(settings)
    database = app.state.database
    proposal_id, _ = create_pending_merge(database, 41)

    with TestClient(app) as client:
        bad = post_webhook(
            client,
            webhook_payload(41, merged=True),
            delivery="delivery-bad",
            signature="sha256=" + "0" * 64,
        )
        assert bad.status_code == 401
        assert database.get_proposal(proposal_id)["status"] == "approved_pending_merge"

        merged = post_webhook(
            client,
            webhook_payload(41, merged=True),
            delivery="delivery-merged",
        )
        assert merged.status_code == 200
        assert merged.json() == {"status": "merged", "proposal_id": proposal_id}
        proposal = database.get_proposal(proposal_id)
        assert proposal is not None
        assert proposal["status"] == "applied"
        assert proposal["applied_commit_sha"] == "f" * 40
        assert proposal["events"][-1]["event"] == "pull_request_merged"

        duplicate = post_webhook(
            client,
            webhook_payload(41, merged=True),
            delivery="delivery-merged",
        )
        assert duplicate.status_code == 200
        assert duplicate.json() == {"status": "duplicate", "proposal_id": None}


def test_signed_webhook_handles_unmerged_close_and_rejects_wrong_repository(
    repo_copy: Path, tmp_path: Path
) -> None:
    settings = Settings.from_env(
        overrides={
            "CPUZ_ENV": "test",
            "CPUZ_REPO_ROOT": str(repo_copy),
            "CPUZ_DATABASE_PATH": str(tmp_path / "webhook-close.sqlite3"),
            "CPUZ_APPLY_MODE": "local",
            "CPUZ_AUTO_BUILD": "false",
            "CPUZ_GITHUB_WEBHOOK_SECRET": SECRET,
        }
    )
    app = create_app(settings)
    database = app.state.database
    proposal_id, _ = create_pending_merge(database, 42)

    with TestClient(app) as client:
        wrong_repository = post_webhook(
            client,
            webhook_payload(42, merged=False, repository="somebody/else"),
            delivery="delivery-wrong-repository",
        )
        assert wrong_repository.status_code == 400
        assert database.get_proposal(proposal_id)["status"] == "approved_pending_merge"

        closed = post_webhook(
            client,
            webhook_payload(42, merged=False),
            delivery="delivery-closed",
        )
        assert closed.status_code == 200
        assert closed.json() == {"status": "closed", "proposal_id": proposal_id}
        proposal = database.get_proposal(proposal_id)
        assert proposal is not None
        assert proposal["status"] == "rejected"
        assert "closed without being merged" in proposal["feedback"]
        assert proposal["events"][-1]["event"] == "pull_request_closed_without_merge"
