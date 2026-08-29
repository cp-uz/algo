from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cpuz.markdown import load_document
from web.app import create_app
from web.config import ConfigurationError, Settings


def csrf(text: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', text)
    assert match
    return match.group(1)


def login(client: TestClient, login_name: str, role: str) -> None:
    response = client.post(
        "/dev/login",
        data={"login": login_name, "name": login_name.title(), "role": role, "next": "/"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_editor_requires_auth_csrf_sanitizes_preview_and_blocks_self_approval(
    repo_copy: Path, tmp_path: Path
) -> None:
    settings = Settings.from_env(
        overrides={
            "CPUZ_ENV": "test",
            "CPUZ_REPO_ROOT": str(repo_copy),
            "CPUZ_DATABASE_PATH": str(tmp_path / "security.sqlite3"),
            "CPUZ_AUTO_BUILD": "false",
            "CPUZ_APPLY_MODE": "local",
            "CPUZ_ALLOW_SELF_APPROVAL": "false",
        }
    )
    app = create_app(settings)
    client = TestClient(app)
    unauthenticated = client.get("/edit/algebra/binary-exp.md", follow_redirects=False)
    assert unauthenticated.status_code == 303

    login(client, "same-user", "contributor")
    page = client.get("/edit/algebra/binary-exp.md")
    token = csrf(page.text)
    original = load_document(repo_copy / "docs/algebra/binary-exp.md").body
    malicious = original + '\n<script>alert(1)</script>\n<img src=x onerror="alert(2)">\n'
    preview = client.post(
        "/preview/algebra/binary-exp.md",
        headers={"X-CSRF-Token": token},
        json={"body": malicious},
    )
    assert preview.status_code == 200
    rendered = preview.json()["html"].casefold()
    assert "<script" not in rendered
    assert "onerror" not in rendered

    bad_csrf = client.post(
        "/edit/algebra/binary-exp.md",
        data={"csrf_token": "wrong", "body": malicious, "summary": "bad csrf"},
    )
    assert bad_csrf.status_code == 403

    submitted = client.post(
        "/edit/algebra/binary-exp.md",
        data={"csrf_token": token, "body": malicious, "summary": "security test"},
        follow_redirects=False,
    )
    proposal_id = int(submitted.headers["location"].rsplit("/", 1)[1])

    # Development role switching lets the test exercise the production rule:
    # identity is stable, so the submitter still cannot approve their own edit.
    login(client, "same-user", "moderator")
    detail = client.get(f"/moderation/{proposal_id}")
    response = client.post(
        f"/moderation/{proposal_id}/decision",
        data={"csrf_token": csrf(detail.text), "action": "approve", "feedback": ""},
    )
    assert response.status_code == 400
    assert load_document(repo_copy / "docs/algebra/binary-exp.md").body == original
    client.close()


def test_production_configuration_rejects_insecure_or_incomplete_setup(tmp_path: Path) -> None:
    base = {
        "CPUZ_ENV": "production",
        "CPUZ_REPO_ROOT": str(tmp_path),
        "CPUZ_DATABASE_PATH": str(tmp_path / "db.sqlite3"),
        "CPUZ_PUBLIC_URL": "https://editor.example.test",
        "CPUZ_GITHUB_CLIENT_ID": "client",
        "CPUZ_GITHUB_CLIENT_SECRET": "secret",
        "CPUZ_GITHUB_TOKEN": "token",
        "CPUZ_MODERATOR_GITHUB_LOGINS": "moderator",
    }
    try:
        Settings.from_env(overrides={**base, "CPUZ_APPLY_MODE": "local"})
    except ConfigurationError as exc:
        assert "github_pr or github_direct" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("insecure production local mode was accepted")

    with pytest.raises(ConfigurationError, match="WEBHOOK_SECRET is required"):
        Settings.from_env(overrides={**base, "CPUZ_APPLY_MODE": "github_pr"})

    with pytest.raises(ConfigurationError, match="at least 32 bytes"):
        Settings.from_env(
            overrides={
                **base,
                "CPUZ_APPLY_MODE": "github_pr",
                "CPUZ_GITHUB_WEBHOOK_SECRET": "too-short",
            }
        )

    valid = Settings.from_env(
        overrides={
            **base,
            "CPUZ_APPLY_MODE": "github_pr",
            "CPUZ_GITHUB_WEBHOOK_SECRET": "a" * 32,
        }
    )
    assert valid.cookie_secure is True
    assert valid.approval_claim_timeout_minutes == 15


def test_configuration_rejects_ambiguous_booleans_and_out_of_range_limits(
    tmp_path: Path,
) -> None:
    base = {
        "CPUZ_ENV": "test",
        "CPUZ_REPO_ROOT": str(tmp_path),
        "CPUZ_DATABASE_PATH": str(tmp_path / "db.sqlite3"),
        "CPUZ_APPLY_MODE": "local",
    }
    with pytest.raises(ConfigurationError, match="must be true or false"):
        Settings.from_env(overrides={**base, "CPUZ_AUTO_BUILD": "perhaps"})
    with pytest.raises(ConfigurationError, match="between 1 and 1440"):
        Settings.from_env(
            overrides={**base, "CPUZ_APPROVAL_CLAIM_TIMEOUT_MINUTES": "0"}
        )


def test_moderation_page_allows_safe_takeover_only_after_claim_timeout(
    repo_copy: Path, tmp_path: Path
) -> None:
    settings = Settings.from_env(
        overrides={
            "CPUZ_ENV": "test",
            "CPUZ_REPO_ROOT": str(repo_copy),
            "CPUZ_DATABASE_PATH": str(tmp_path / "stale-claim.sqlite3"),
            "CPUZ_AUTO_BUILD": "false",
            "CPUZ_APPLY_MODE": "local",
            "CPUZ_APPROVAL_CLAIM_TIMEOUT_MINUTES": "1",
        }
    )
    app = create_app(settings)
    database = app.state.database
    snapshot = app.state.service.snapshot("algebra/binary-exp.md")
    contributor = database.upsert_user(
        github_id="dev:claim-contributor",
        login="claim-contributor",
        display_name="Claim Contributor",
        email=None,
        avatar_url=None,
        role="contributor",
    )
    proposal_id = database.create_proposal(
        article_id=snapshot.article["id"],
        article_path=snapshot.article["path"],
        base_content_sha256=snapshot.document.body_sha256,
        old_body=snapshot.document.body,
        new_body=snapshot.document.body + "\nStale claim UI testi.\n",
        summary="Stale claim UI test",
        user=contributor,
    )
    first = database.upsert_user(
        github_id="dev:first-moderator",
        login="first-moderator",
        display_name="First Moderator",
        email=None,
        avatar_url=None,
        role="moderator",
    )
    database.claim_proposal(
        proposal_id,
        moderator=first,
        takeover_after_minutes=settings.approval_claim_timeout_minutes,
    )

    client = TestClient(app)
    login(client, "second-moderator", "moderator")
    active = client.get(f"/moderation/{proposal_id}")
    assert active.status_code == 200
    assert 'disabled aria-disabled="true"' in active.text
    assert "Jarayonni qabul qilib olish va qo‘llash" not in active.text

    with database.connect() as connection:
        connection.execute(
            "UPDATE proposal_claims SET claimed_at=? WHERE proposal_id=?",
            ("2000-01-01T00:00:00Z", proposal_id),
        )
    stale = client.get(f"/moderation/{proposal_id}")
    assert stale.status_code == 200
    assert "uzilib qolgan bo‘lishi mumkin" in stale.text
    assert "Jarayonni qabul qilib olish va qo‘llash" in stale.text
    assert 'disabled aria-disabled="true"' not in stale.text
    client.close()


def test_review_result_link_is_restricted_to_configured_github_repository(
    repo_copy: Path, tmp_path: Path
) -> None:
    settings = Settings.from_env(
        overrides={
            "CPUZ_ENV": "test",
            "CPUZ_REPO_ROOT": str(repo_copy),
            "CPUZ_DATABASE_PATH": str(tmp_path / "result-link.sqlite3"),
            "CPUZ_AUTO_BUILD": "false",
            "CPUZ_APPLY_MODE": "local",
            "CPUZ_GITHUB_REPOSITORY": "cp-uz/algo",
        }
    )
    app = create_app(settings)
    client = TestClient(app)
    login(client, "reviewer-link", "reviewer")

    unsafe = client.get(
        "/moderation/article/algebra/binary-exp.md",
        params={"applied": "applied", "result_url": "javascript:alert(1)"},
    )
    assert unsafe.status_code == 200
    assert "javascript:alert" not in unsafe.text

    wrong_repo = client.get(
        "/moderation/article/algebra/binary-exp.md",
        params={
            "applied": "approved_pending_merge",
            "result_url": "https://github.com/attacker/repo/pull/1",
        },
    )
    assert "attacker/repo" not in wrong_repo.text

    allowed = client.get(
        "/moderation/article/algebra/binary-exp.md",
        params={
            "applied": "approved_pending_merge",
            "result_url": "https://github.com/cp-uz/algo/pull/42",
        },
    )
    assert 'href="https://github.com/cp-uz/algo/pull/42"' in allowed.text
    client.close()
