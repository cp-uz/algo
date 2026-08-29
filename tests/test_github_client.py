from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from web.github import GitHubClient


def encoded_file(text: str) -> dict[str, str]:
    return {
        "type": "file",
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
    }


def payload(request: httpx.Request) -> dict[str, Any] | None:
    return json.loads(request.content) if request.content else None


def make_client(handler: httpx.MockTransport | Any) -> GitHubClient:
    transport = handler if isinstance(handler, httpx.MockTransport) else httpx.MockTransport(handler)
    return GitHubClient(
        token="server-only-token",
        repository="cp-uz/algo",
        base_branch="main",
        transport=transport,
        api_base="https://api.github.test",
    )


def test_github_pr_commit_uses_deterministic_server_side_git_data_api() -> None:
    calls: list[tuple[str, str, dict[str, Any] | None]] = []
    blob_index = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal blob_index
        body = payload(request)
        path = request.url.path
        calls.append((request.method, path, body))
        if request.method == "GET" and "git/ref/heads/cpuz" in path:
            return httpx.Response(404, json={"message": "Not Found"})
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "a" * 40}})
        if request.method == "GET" and "/contents/" in path:
            return httpx.Response(404, json={"message": "Not Found"})
        if path.endswith("/git/commits/" + "a" * 40):
            return httpx.Response(200, json={"tree": {"sha": "b" * 40}})
        if path.endswith("/git/blobs"):
            blob_index += 1
            return httpx.Response(201, json={"sha": f"{blob_index:040x}"})
        if path.endswith("/git/trees"):
            return httpx.Response(201, json={"sha": "c" * 40})
        if path.endswith("/git/commits"):
            return httpx.Response(201, json={"sha": "d" * 40})
        if path.endswith("/git/refs"):
            assert body is not None
            return httpx.Response(201, json={"ref": body["ref"]})
        if path.endswith("/pulls"):
            return httpx.Response(
                201,
                json={
                    "number": 17,
                    "state": "open",
                    "merged": False,
                    "html_url": "https://github.com/cp-uz/algo/pull/17",
                },
            )
        raise AssertionError(f"unexpected request {request.method} {path}")

    client = make_client(handler)
    try:
        result = client.commit_files(
            {"docs/algebra/binary-exp.md": "article", "data/articles.yml": "manifest"},
            message="Apply proposal",
            mode="github_pr",
            branch_hint="proposal-17-binary-exp",
            pull_request_title="Proposal 17",
            pull_request_body="Approved by moderator.",
            idempotency_key="proposal-17",
        )
    finally:
        client.close()

    assert result.pull_request_number == 17
    assert result.url.endswith("/pull/17")
    assert result.ref == "cpuz/proposal-17"
    assert result.commit_sha == "d" * 40
    blob_payloads = [body for method, path, body in calls if path.endswith("/git/blobs")]
    assert {item["content"] for item in blob_payloads if item is not None} == {
        "article",
        "manifest",
    }
    assert all("server-only-token" not in json.dumps(body or {}) for _, _, body in calls)


def test_retry_reuses_existing_deterministic_branch_and_pull_request() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append((request.method, path))
        if request.method == "GET" and "git/ref/heads/cpuz" in path:
            return httpx.Response(200, json={"object": {"sha": "e" * 40}})
        if request.method == "GET" and path.endswith("/pulls"):
            assert request.url.params["head"] == "cp-uz:cpuz/proposal-17"
            return httpx.Response(
                200,
                json=[
                    {
                        "number": 17,
                        "state": "open",
                        "merged": False,
                        "html_url": "https://github.com/cp-uz/algo/pull/17",
                    }
                ],
            )
        raise AssertionError(f"unexpected request {request.method} {path}")

    client = make_client(handler)
    try:
        result = client.commit_files(
            {"docs/a.md": "article"},
            message="retry",
            mode="github_pr",
            branch_hint="ignored",
            idempotency_key="proposal-17",
        )
    finally:
        client.close()

    assert result.ref == "cpuz/proposal-17"
    assert result.commit_sha == "e" * 40
    assert result.pull_request_number == 17
    assert result.merged is False
    assert len(calls) == 2


def test_retry_after_merge_and_branch_deletion_recognizes_base_files() -> None:
    requested = {
        "data/articles.yml": "manifest after merge",
        "docs/algebra/binary-exp.md": "article after merge",
    }
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append((request.method, path))
        if request.method == "GET" and "git/ref/heads/cpuz" in path:
            return httpx.Response(404, json={"message": "Not Found"})
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "f" * 40}})
        if request.method == "GET" and "/contents/" in path:
            relative = path.split("/contents/", 1)[1]
            return httpx.Response(200, json=encoded_file(requested[relative]))
        raise AssertionError(f"unexpected request {request.method} {path}")

    client = make_client(handler)
    try:
        result = client.commit_files(
            requested,
            message="retry after merge",
            mode="github_pr",
            branch_hint="ignored",
            idempotency_key="proposal-17",
        )
    finally:
        client.close()

    assert result.ref == "main"
    assert result.commit_sha == "f" * 40
    assert result.pull_request_number is None
    assert result.merged is True
    assert not any(path.endswith("/pulls") for _, path in calls)
    assert not any(path.endswith("/git/blobs") for _, path in calls)


def test_direct_retry_does_not_create_duplicate_commit_when_base_matches() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append((request.method, path))
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "1" * 40}})
        if request.method == "GET" and "/contents/" in path:
            return httpx.Response(200, json=encoded_file("already applied"))
        raise AssertionError(f"unexpected request {request.method} {path}")

    client = make_client(handler)
    try:
        result = client.commit_files(
            {"data/articles.yml": "already applied"},
            message="direct retry",
            mode="github_direct",
            branch_hint="unused",
        )
    finally:
        client.close()

    assert result.ref == "main"
    assert result.commit_sha == "1" * 40
    assert result.pull_request_number is None
    assert not any(path.endswith("/git/commits") for _, path in calls)
