from __future__ import annotations

import base64
import re
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx


class GitHubError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class CommitResult:
    ref: str
    commit_sha: str
    url: str
    pull_request_number: int | None = None
    pull_request_state: str | None = None
    merged: bool | None = None


class GitHubClient:
    api_base = "https://api.github.com"

    def __init__(
        self,
        *,
        token: str,
        repository: str,
        base_branch: str,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
        api_base: str | None = None,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("GitHub repository must be owner/name")
        if not base_branch:
            raise ValueError("GitHub base branch is required")
        self.repository = repository
        self.owner = repository.split("/", 1)[0]
        self.base_branch = base_branch
        self.api_base = (api_base or self.api_base).rstrip("/")
        self.client = httpx.Client(
            timeout=timeout,
            transport=transport,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "cpuz-algorithms-editor",
            },
        )

    def close(self) -> None:
        self.client.close()

    def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            return self.client.request(method, self.api_base + path, **kwargs)
        except httpx.HTTPError as exc:
            raise GitHubError(f"GitHub API request failed: {exc}") from exc

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._send(method, path, **kwargs)
        if response.status_code >= 400:
            detail = response.text[:1000]
            raise GitHubError(
                f"GitHub API {method} {path} returned {response.status_code}: {detail}",
                status_code=response.status_code,
            )
        if response.status_code == 204:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise GitHubError(
                f"GitHub API {method} {path} returned invalid JSON",
                status_code=response.status_code,
            ) from exc

    def _get_optional(self, path: str, **kwargs: Any) -> Any | None:
        response = self._send("GET", path, **kwargs)
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise GitHubError(
                f"GitHub API GET {path} returned {response.status_code}: {response.text[:1000]}",
                status_code=response.status_code,
            )
        try:
            return response.json()
        except ValueError as exc:
            raise GitHubError(
                f"GitHub API GET {path} returned invalid JSON",
                status_code=response.status_code,
            ) from exc

    def get_text(self, path: str, *, ref: str | None = None) -> str:
        encoded = quote(path, safe="/")
        data = self._request(
            "GET",
            f"/repos/{self.repository}/contents/{encoded}",
            params={"ref": ref or self.base_branch},
        )
        if not isinstance(data, dict) or data.get("type") != "file":
            raise GitHubError(f"{path} is not a regular file in {self.repository}")
        content = str(data.get("content", "")).replace("\n", "")
        try:
            return base64.b64decode(content, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise GitHubError(f"could not decode {path} from GitHub") from exc

    def _text_matches(self, path: str, text: str, *, ref: str) -> bool:
        encoded = quote(path, safe="/")
        response = self._send(
            "GET",
            f"/repos/{self.repository}/contents/{encoded}",
            params={"ref": ref},
        )
        if response.status_code == 404:
            return False
        if response.status_code >= 400:
            raise GitHubError(
                f"GitHub API GET contents returned {response.status_code}: {response.text[:1000]}",
                status_code=response.status_code,
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise GitHubError(
                f"GitHub API GET contents returned invalid JSON",
                status_code=response.status_code,
            ) from exc
        if not isinstance(data, dict) or data.get("type") != "file":
            return False
        encoded_content = str(data.get("content", "")).replace("\n", "")
        try:
            current = base64.b64decode(encoded_content, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise GitHubError(f"could not decode {path} from GitHub") from exc
        return current == text

    def user_in_org(self, login: str, organization: str) -> bool:
        response = self._send(
            "GET", f"/orgs/{quote(organization)}/members/{quote(login)}"
        )
        if response.status_code == 204:
            return True
        if response.status_code == 404:
            return False
        if response.status_code >= 400:
            raise GitHubError(
                f"GitHub organization check returned {response.status_code}: {response.text[:500]}",
                status_code=response.status_code,
            )
        return False

    @staticmethod
    def _safe_branch_component(value: str, *, maximum: int = 72) -> str:
        cleaned = re.sub(r"[^a-z0-9-]+", "-", value.casefold()).strip("-")
        return (cleaned or "proposal")[:maximum].rstrip("-")

    def _branch_ref(self, branch: str) -> dict[str, Any] | None:
        return self._get_optional(
            f"/repos/{self.repository}/git/ref/heads/{quote(branch, safe='')}"
        )

    def _pull_for_branch(self, branch: str) -> dict[str, Any] | None:
        pulls = self._request(
            "GET",
            f"/repos/{self.repository}/pulls",
            params={
                "state": "all",
                "head": f"{self.owner}:{branch}",
                "base": self.base_branch,
                "per_page": 10,
            },
        )
        if not isinstance(pulls, list):
            raise GitHubError("GitHub pull-request listing returned an unexpected response")
        if not pulls:
            return None
        # GitHub returns newest first. A branch should normally have only one PR.
        return pulls[0] if isinstance(pulls[0], dict) else None

    def _result_from_pull(
        self,
        *,
        branch: str,
        commit_sha: str,
        pull: dict[str, Any],
    ) -> CommitResult:
        state = str(pull.get("state") or "open")
        merged = bool(pull.get("merged_at") or pull.get("merged"))
        if state == "closed" and not merged:
            raise GitHubError(
                f"the existing pull request for {branch} was closed without merge; "
                "reject or revise the proposal before trying again"
            )
        return CommitResult(
            ref=branch,
            commit_sha=commit_sha,
            url=str(pull["html_url"]),
            pull_request_number=int(pull["number"]),
            pull_request_state=state,
            merged=merged,
        )

    def _existing_pr_result(
        self,
        *,
        branch: str,
        pull_request_title: str,
        pull_request_body: str,
    ) -> CommitResult | None:
        ref_data = self._branch_ref(branch)
        if ref_data is None:
            return None
        commit_sha = str(ref_data["object"]["sha"])
        pull = self._pull_for_branch(branch)
        if pull is None:
            pull = self._request(
                "POST",
                f"/repos/{self.repository}/pulls",
                json={
                    "title": pull_request_title,
                    "head": branch,
                    "base": self.base_branch,
                    "body": pull_request_body,
                    "maintainer_can_modify": True,
                },
            )
        return self._result_from_pull(branch=branch, commit_sha=commit_sha, pull=pull)

    def commit_files(
        self,
        files: dict[str, str],
        *,
        message: str,
        mode: str,
        branch_hint: str,
        pull_request_title: str | None = None,
        pull_request_body: str | None = None,
        idempotency_key: str | None = None,
    ) -> CommitResult:
        if not files:
            raise ValueError("at least one file is required")
        if mode not in {"github_direct", "github_pr"}:
            raise ValueError("mode must be github_direct or github_pr")

        title = pull_request_title or message
        body = pull_request_body or ""
        deterministic_branch: str | None = None
        if mode == "github_pr" and idempotency_key:
            deterministic_branch = "cpuz/" + self._safe_branch_component(idempotency_key)
            existing = self._existing_pr_result(
                branch=deterministic_branch,
                pull_request_title=title,
                pull_request_body=body,
            )
            if existing is not None:
                return existing

        ref_data = self._request(
            "GET",
            f"/repos/{self.repository}/git/ref/heads/{quote(self.base_branch, safe='')}",
        )
        base_sha = str(ref_data["object"]["sha"])

        # A retry after a direct push, or after a PR was merged and its branch
        # was automatically deleted, must not create another commit/PR. Comparing
        # the requested canonical files with the base branch makes the operation
        # safely idempotent across those crash windows.
        if all(
            self._text_matches(path, text, ref=self.base_branch)
            for path, text in sorted(files.items())
        ):
            return CommitResult(
                ref=self.base_branch,
                commit_sha=base_sha,
                url=f"https://github.com/{self.repository}/commit/{base_sha}",
                merged=True if mode == "github_pr" else None,
            )

        base_commit = self._request(
            "GET", f"/repos/{self.repository}/git/commits/{base_sha}"
        )
        tree_entries: list[dict[str, str]] = []
        for path, text in sorted(files.items()):
            blob = self._request(
                "POST",
                f"/repos/{self.repository}/git/blobs",
                json={"content": text, "encoding": "utf-8"},
            )
            tree_entries.append(
                {"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]}
            )
        tree = self._request(
            "POST",
            f"/repos/{self.repository}/git/trees",
            json={"base_tree": base_commit["tree"]["sha"], "tree": tree_entries},
        )
        commit = self._request(
            "POST",
            f"/repos/{self.repository}/git/commits",
            json={"message": message, "tree": tree["sha"], "parents": [base_sha]},
        )
        commit_sha = str(commit["sha"])

        if mode == "github_direct":
            self._request(
                "PATCH",
                f"/repos/{self.repository}/git/refs/heads/{quote(self.base_branch, safe='')}",
                json={"sha": commit_sha, "force": False},
            )
            return CommitResult(
                ref=self.base_branch,
                commit_sha=commit_sha,
                url=f"https://github.com/{self.repository}/commit/{commit_sha}",
            )

        branch = deterministic_branch or (
            "cpuz/"
            + self._safe_branch_component(branch_hint, maximum=48)
            + "-"
            + secrets.token_hex(4)
        )
        try:
            self._request(
                "POST",
                f"/repos/{self.repository}/git/refs",
                json={"ref": f"refs/heads/{branch}", "sha": commit_sha},
            )
        except GitHubError as exc:
            # Two workers can race between the initial branch lookup and branch
            # creation. For deterministic operations, recover the existing PR
            # rather than creating a duplicate branch/PR.
            if deterministic_branch and exc.status_code == 422:
                existing = self._existing_pr_result(
                    branch=branch,
                    pull_request_title=title,
                    pull_request_body=body,
                )
                if existing is not None:
                    return existing
            raise

        pull = self._request(
            "POST",
            f"/repos/{self.repository}/pulls",
            json={
                "title": title,
                "head": branch,
                "base": self.base_branch,
                "body": body,
                "maintainer_can_modify": True,
            },
        )
        return self._result_from_pull(branch=branch, commit_sha=commit_sha, pull=pull)
