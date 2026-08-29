from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from cpuz.build import build_repository, compare_generated_site
from cpuz.checksum import validate_manifest_file
from cpuz.markdown import load_document
from cpuz.metadata import article_by_path, load_manifest
from web.app import create_app
from web.config import Settings


def login(client: TestClient, *, login_name: str, display: str, role: str) -> None:
    response = client.post(
        "/dev/login",
        data={"login": login_name, "name": display, "role": role, "next": "/"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def csrf_from(text: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', text)
    assert match
    return match.group(1)


def test_binary_exponentiation_end_to_end_and_rejection(repo_copy: Path, tmp_path: Path) -> None:
    settings = Settings.from_env(
        overrides={
            "CPUZ_ENV": "test",
            "CPUZ_REPO_ROOT": str(repo_copy),
            "CPUZ_DATABASE_PATH": str(tmp_path / "proposals.sqlite3"),
            "CPUZ_AUTO_BUILD": "false",
            "CPUZ_APPLY_MODE": "local",
            "CPUZ_ALLOW_SELF_APPROVAL": "false",
        }
    )
    app = create_app(settings)
    client = TestClient(app)
    login(client, login_name="contributor", display="Contributor", role="contributor")

    edit = client.get("/edit/algebra/binary-exp.md")
    assert edit.status_code == 200
    csrf = csrf_from(edit.text)
    original = load_document(repo_copy / "docs" / "algebra" / "binary-exp.md").body
    proposed = original + "\nBu satr web-tahrirlash end-to-end testi orqali qo‘shildi.\n"
    preview = client.post(
        "/preview/algebra/binary-exp.md",
        headers={"X-CSRF-Token": csrf},
        json={"body": proposed},
    )
    assert preview.status_code == 200
    assert "web-tahrirlash" in preview.json()["html"]

    submitted = client.post(
        "/edit/algebra/binary-exp.md",
        data={"csrf_token": csrf, "body": proposed, "summary": "Web editor test edit"},
        follow_redirects=False,
    )
    assert submitted.status_code == 303
    proposal_id = int(submitted.headers["location"].rsplit("/", 1)[1])
    proposal = app.state.database.get_proposal(proposal_id)
    assert proposal and proposal["status"] == "pending"
    # Submission is moderated and does not change canonical Markdown immediately.
    assert load_document(repo_copy / "docs" / "algebra" / "binary-exp.md").body == original

    login(client, login_name="moderator", display="Moderator Name", role="moderator")
    detail = client.get(f"/moderation/{proposal_id}")
    assert detail.status_code == 200
    assert "submitted" in detail.text
    mod_csrf = csrf_from(detail.text)
    requested = client.post(
        f"/moderation/{proposal_id}/decision",
        data={"csrf_token": mod_csrf, "action": "request_changes", "feedback": "Please clarify the final sentence."},
        follow_redirects=False,
    )
    assert requested.status_code == 303
    assert app.state.database.get_proposal(proposal_id)["status"] == "changes_requested"

    login(client, login_name="contributor", display="Contributor", role="contributor")
    status_page = client.get(f"/proposals/{proposal_id}")
    contributor_csrf = csrf_from(status_page.text)
    revised_body = proposed.replace("qo‘shildi.", "qo‘shildi va tekshirildi.")
    revised = client.post(
        f"/proposals/{proposal_id}/revise",
        data={"csrf_token": contributor_csrf, "body": revised_body, "summary": "Clarified as requested"},
        follow_redirects=False,
    )
    assert revised.status_code == 303
    assert app.state.database.get_proposal(proposal_id)["status"] == "pending"

    login(client, login_name="moderator", display="Moderator Name", role="moderator")
    detail = client.get(f"/moderation/{proposal_id}")
    mod_csrf = csrf_from(detail.text)
    approved = client.post(
        f"/moderation/{proposal_id}/decision",
        data={"csrf_token": mod_csrf, "action": "approve", "feedback": "Approved."},
        follow_redirects=False,
    )
    assert approved.status_code == 303
    assert app.state.database.get_proposal(proposal_id)["status"] == "applied"
    assert load_document(repo_copy / "docs" / "algebra" / "binary-exp.md").body == revised_body

    # Review decisions are managed from the UI and recorded with identity/time/hash.
    review_page = client.get("/moderation/article/algebra/binary-exp.md")
    review_csrf = csrf_from(review_page.text)
    technical = client.post(
        "/moderation/article/algebra/binary-exp.md/review",
        data={
            "csrf_token": review_csrf,
            "review_type": "technical",
            "status": "approved",
            "notes": "Implementation and complexity checked.",
        },
        follow_redirects=False,
    )
    assert technical.status_code == 303
    assert "applied=applied" in technical.headers["location"]
    review_page = client.get(technical.headers["location"])
    assert "Review qarori canonical metama’lumotga qo‘llandi" in review_page.text
    review_csrf = csrf_from(review_page.text)
    language = client.post(
        "/moderation/article/algebra/binary-exp.md/review",
        data={
            "csrf_token": review_csrf,
            "review_type": "language",
            "status": "approved",
            "notes": "Uzbek wording checked.",
        },
        follow_redirects=False,
    )
    assert language.status_code == 303
    assert "applied=applied" in language.headers["location"]
    manifest = load_manifest(repo_copy)
    article = article_by_path(manifest, "algebra/binary-exp.md")
    assert article["reviews"]["technical"]["reviewer"] == "Moderator Name"
    assert article["reviews"]["language"]["status"] == "approved"
    assert article["review_history"]

    # A second proposal can be rejected and never reaches canonical content.
    login(client, login_name="contributor", display="Contributor", role="contributor")
    current = load_document(repo_copy / "docs" / "algebra" / "binary-exp.md").body
    edit = client.get("/edit/algebra/binary-exp.md")
    csrf = csrf_from(edit.text)
    rejected_body = current + "\nBu rad etilishi kerak bo‘lgan satr.\n"
    submitted2 = client.post(
        "/edit/algebra/binary-exp.md",
        data={"csrf_token": csrf, "body": rejected_body, "summary": "Reject this"},
        follow_redirects=False,
    )
    proposal2 = int(submitted2.headers["location"].rsplit("/", 1)[1])
    login(client, login_name="moderator", display="Moderator Name", role="moderator")
    detail2 = client.get(f"/moderation/{proposal2}")
    mod_csrf = csrf_from(detail2.text)
    rejected = client.post(
        f"/moderation/{proposal2}/decision",
        data={"csrf_token": mod_csrf, "action": "reject", "feedback": "Not an improvement."},
        follow_redirects=False,
    )
    assert rejected.status_code == 303
    assert app.state.database.get_proposal(proposal2)["status"] == "rejected"
    assert load_document(repo_copy / "docs" / "algebra" / "binary-exp.md").body == current

    # Close the single TestClient portal before spawning the repository build.
    client.close()

    # Build in-process after closing TestClient portals. Forking a Python child
    # from an AnyIO/TestClient process can deadlock on inherited library locks.
    # The public CLI is exercised by the repository-level Makefile/CI test.
    result = build_repository(repo_copy)
    assert result.article_count == 163
    assert compare_generated_site(repo_copy) == []
    assert validate_manifest_file(repo_copy) == []
    built = (repo_copy / "site" / "algebra" / "binary-exp" / "index.html").read_text(encoding="utf-8")
    assert "web-tahrirlash end-to-end testi" in built
    assert "Texnik: tasdiqlangan" in built
