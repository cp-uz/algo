from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

import yaml

from cpuz.build import build_repository
from cpuz.markdown import (
    ArticleDocument,
    assemble_document,
    extract_h1,
    load_document,
    split_document,
    validate_editable_body,
)
from cpuz.metadata import (
    MetadataError,
    article_by_path,
    article_path,
    articles,
    dump_manifest,
    load_manifest,
    save_manifest,
    validate_manifest,
)
from cpuz.persistence import persist_manifest_bundle
from cpuz.rendering import RenderedMarkdown, render_markdown
from cpuz.util import atomic_write_text, ensure_relative_posix, sha256_text
from cpuz.workflow import record_content_change, set_review_status

from .config import Settings
from .db import Database, User
from .github import CommitResult, GitHubClient


class ProposalConflict(MetadataError):
    pass


@dataclass(frozen=True)
class ArticleSnapshot:
    manifest: dict[str, Any]
    article: dict[str, Any]
    document: ArticleDocument


@dataclass(frozen=True)
class ApplyResult:
    status: str
    ref: str | None
    url: str | None
    pull_request_number: int | None = None
    commit_sha: str | None = None


_local_lock = threading.RLock()


@contextmanager
def repository_lock(root: Path) -> Iterator[None]:
    lock_path = root / "var" / "repository.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with _local_lock:
        handle = lock_path.open("a+")
        try:
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except ImportError:  # pragma: no cover - Windows fallback
                pass
            yield
        finally:
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except ImportError:  # pragma: no cover
                pass
            handle.close()


def _normalize_scalars(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _normalize_scalars(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_scalars(item) for item in value]
    return value


def _proposal_change_recorded(
    article: dict[str, Any], proposal_id: int, new_body_sha256: str
) -> bool:
    return any(
        event.get("event") == "article_content_changed"
        and event.get("proposal_id") == proposal_id
        and event.get("content_sha256") == new_body_sha256
        for event in article.get("review_history", [])
        if isinstance(event, dict)
    )


def _review_decision_recorded(
    article: dict[str, Any],
    *,
    review_type: str,
    status: str,
    reviewer: str,
    body_sha256: str,
    notes: str | None,
) -> bool:
    normalized_notes = notes.strip() if isinstance(notes, str) and notes.strip() else None
    current = article["reviews"][review_type]
    if status != "pending":
        return (
            current.get("status") == status
            and current.get("reviewer") == reviewer
            and current.get("content_sha256") == body_sha256
            and current.get("source_commit") == article["source"]["commit"]
            and current.get("notes") == normalized_notes
        )
    if current.get("status") != "pending":
        return False
    event_name = f"{review_type}_review_set_pending"
    return any(
        event.get("event") == event_name
        and event.get("actor") == reviewer
        and event.get("content_sha256") == body_sha256
        and event.get("source_commit") == article["source"]["commit"]
        and event.get("notes") == normalized_notes
        for event in reversed(article.get("review_history", []))
        if isinstance(event, dict)
    )


class EditorService:
    def __init__(self, settings: Settings, database: Database) -> None:
        self.settings = settings
        self.db = database
        # Reading and fully validating the 163-article YAML manifest on every
        # editor request is unnecessarily expensive.  Local mode therefore
        # keeps a structurally validated snapshot keyed by the manifest and
        # schema file identities.  Atomic writes replace the inode, and the
        # complete stat signature also catches in-place edits.  Callers always
        # receive a deep copy, so request code cannot mutate the cached value.
        self._manifest_cache_lock = threading.RLock()
        self._manifest_cache_signature: tuple[int, ...] | None = None
        self._manifest_cache_value: dict[str, Any] | None = None
        self.github = (
            GitHubClient(
                token=settings.github_token or "",
                repository=settings.github_repository,
                base_branch=settings.github_base_branch,
            )
            if settings.apply_mode.startswith("github")
            else None
        )

    def close(self) -> None:
        if self.github:
            self.github.close()

    @staticmethod
    def _file_signature(path: Path) -> tuple[int, int, int, int, int]:
        stat = path.stat()
        return (
            int(stat.st_dev),
            int(stat.st_ino),
            int(stat.st_size),
            int(stat.st_mtime_ns),
            int(stat.st_ctime_ns),
        )

    def _local_manifest_signature(self) -> tuple[int, ...]:
        root = self.settings.repo_root
        return self._file_signature(root / "data" / "articles.yml") + self._file_signature(
            root / "data" / "schema" / "articles.schema.json"
        )

    def _invalidate_manifest_cache(self) -> None:
        with self._manifest_cache_lock:
            self._manifest_cache_signature = None
            self._manifest_cache_value = None

    def _local_manifest(self) -> dict[str, Any]:
        """Return current local canonical metadata without serving stale state.

        Document contents are deliberately not part of this cache: a snapshot
        always reads its requested Markdown file directly.  Repository writes
        still run the full document-aware validation under ``repository_lock``.
        """

        with self._manifest_cache_lock:
            # Retry once if an external atomic write lands while the manifest is
            # being parsed.  This avoids caching data under the wrong signature.
            for _ in range(2):
                before = self._local_manifest_signature()
                if (
                    self._manifest_cache_value is not None
                    and self._manifest_cache_signature == before
                ):
                    return deepcopy(self._manifest_cache_value)
                manifest = load_manifest(
                    self.settings.repo_root,
                    validate=True,
                    validate_documents=False,
                )
                after = self._local_manifest_signature()
                if before == after:
                    self._manifest_cache_signature = after
                    self._manifest_cache_value = deepcopy(manifest)
                    return deepcopy(manifest)
            raise MetadataError("data/articles.yml changed repeatedly while it was being read")

    @staticmethod
    def normalize_path(value: str) -> str:
        value = value.replace("\\", "/")
        if value.startswith("docs/"):
            value = value[5:]
        return ensure_relative_posix(value, suffix=".md")

    def manifest_for_listing(self) -> dict[str, Any]:
        if self.github is None:
            return self._local_manifest()
        manifest_text = self.github.get_text(
            "data/articles.yml", ref=self.settings.github_base_branch
        )
        data = _normalize_scalars(yaml.safe_load(manifest_text))
        if not isinstance(data, dict):
            raise MetadataError("remote data/articles.yml is not a mapping")
        validate_manifest(self.settings.repo_root, data, validate_documents=False)
        return data

    def snapshot(self, path: str) -> ArticleSnapshot:
        relative = self.normalize_path(path)
        if self.github is None:
            manifest = self._local_manifest()
            article = article_by_path(manifest, relative)
            document = load_document(article_path(self.settings.repo_root, article))
            if document.article_id != article["id"]:
                raise MetadataError(
                    f"{relative}: front matter article_id does not match canonical metadata"
                )
            return ArticleSnapshot(manifest, article, document)
        manifest_text = self.github.get_text(
            "data/articles.yml", ref=self.settings.github_base_branch
        )
        data = _normalize_scalars(yaml.safe_load(manifest_text))
        if not isinstance(data, dict):
            raise MetadataError("remote data/articles.yml is not a mapping")
        validate_manifest(self.settings.repo_root, data, validate_documents=False)
        article = article_by_path(data, relative)
        document_text = self.github.get_text(
            f"docs/{relative}", ref=self.settings.github_base_branch
        )
        document = split_document(document_text)
        if document.article_id != article["id"]:
            raise MetadataError("remote article ID does not match canonical metadata")
        return ArticleSnapshot(data, article, document)

    def preview(self, path: str, body: str) -> RenderedMarkdown:
        body = validate_editable_body(body, max_bytes=self.settings.max_proposal_bytes)
        snapshot = self.snapshot(path)
        by_path = {item["path"]: item for item in articles(snapshot.manifest)}
        return render_markdown(body, article=snapshot.article, article_by_path=by_path)

    def submit(self, path: str, body: str, summary: str, user: User) -> int:
        body = validate_editable_body(body, max_bytes=self.settings.max_proposal_bytes)
        summary = summary.strip()[:4000]
        snapshot = self.snapshot(path)
        if body == snapshot.document.body:
            raise MetadataError("taklif joriy maqola bilan bir xil")
        if not self.db.submission_allowed(user.id, self.settings.submissions_per_hour):
            raise MetadataError("bir soatlik taklif yuborish limiti tugadi")
        return self.db.create_proposal(
            article_id=snapshot.article["id"],
            article_path=snapshot.article["path"],
            base_content_sha256=snapshot.document.body_sha256,
            old_body=snapshot.document.body,
            new_body=body,
            summary=summary,
            user=user,
        )

    def revise(self, proposal: dict[str, Any], body: str, summary: str, user: User) -> None:
        body = validate_editable_body(body, max_bytes=self.settings.max_proposal_bytes)
        if body == proposal["old_body"]:
            raise MetadataError("yangilangan taklif joriy maqola bilan bir xil")
        self.db.revise_proposal(
            int(proposal["id"]), new_body=body, summary=summary.strip()[:4000], user=user
        )

    def apply_proposal(self, proposal: dict[str, Any], moderator: User) -> ApplyResult:
        if proposal["status"] != "pending":
            raise MetadataError("only an active proposal can be approved")
        if (
            not self.settings.allow_self_approval
            and int(proposal["submitter_user_id"]) == moderator.id
        ):
            raise MetadataError("a moderator cannot approve their own proposal")
        if self.github is not None:
            return self._apply_github(proposal, moderator)
        return self._apply_local(proposal, moderator)

    def _apply_local(self, proposal: dict[str, Any], moderator: User) -> ApplyResult:
        root = self.settings.repo_root
        body = validate_editable_body(
            str(proposal["new_body"]), max_bytes=self.settings.max_proposal_bytes
        )
        new_hash = sha256_text(body)
        base_hash = str(proposal["base_content_sha256"])
        new_title = extract_h1(body)

        with repository_lock(root):
            manifest_path = root / "data" / "articles.yml"
            original_manifest = manifest_path.read_text(encoding="utf-8")
            # validate_documents=False is deliberate: it allows a safe retry after
            # a process was interrupted between the atomic Markdown and manifest
            # writes. The pair is validated again before it becomes canonical.
            manifest = load_manifest(root, validate=True, validate_documents=False)
            article = article_by_path(manifest, str(proposal["article_path"]))
            document_path = article_path(root, article)
            original_document = document_path.read_text(encoding="utf-8")
            document = split_document(original_document)
            current_hash = document.body_sha256
            if current_hash not in {base_hash, new_hash}:
                raise ProposalConflict(
                    "the canonical article changed after this proposal was submitted"
                )

            history_recorded = _proposal_change_recorded(
                article, int(proposal["id"]), new_hash
            )
            try:
                if current_hash != new_hash:
                    atomic_write_text(
                        document_path, assemble_document(article["id"], body)
                    )
                if not history_recorded:
                    record_content_change(
                        article,
                        actor=moderator.display_name,
                        old_body_sha256=base_hash,
                        new_body_sha256=new_hash,
                        new_title=new_title,
                        summary=str(proposal.get("summary") or "") or None,
                        proposal_id=int(proposal["id"]),
                    )
                if self.settings.auto_build:
                    save_manifest(root, manifest)
                    self._invalidate_manifest_cache()
                    build_repository(root)
                else:
                    persist_manifest_bundle(root, manifest)
                    self._invalidate_manifest_cache()
            except BaseException:
                atomic_write_text(document_path, original_document)
                atomic_write_text(manifest_path, original_manifest)
                self._invalidate_manifest_cache()
                if self.settings.auto_build:
                    try:
                        build_repository(root)
                    except BaseException as restoration_error:  # pragma: no cover - catastrophic path
                        raise RuntimeError(
                            "approval failed and generated outputs could not be restored"
                        ) from restoration_error
                raise
        return ApplyResult(
            status="applied", ref="local", url=None, commit_sha=new_hash
        )

    def _apply_github(self, proposal: dict[str, Any], moderator: User) -> ApplyResult:
        assert self.github is not None
        snapshot = self.snapshot(str(proposal["article_path"]))
        body = validate_editable_body(
            str(proposal["new_body"]), max_bytes=self.settings.max_proposal_bytes
        )
        new_hash = sha256_text(body)
        base_hash = str(proposal["base_content_sha256"])
        if snapshot.document.body_sha256 not in {base_hash, new_hash}:
            raise ProposalConflict(
                "the GitHub article changed after this proposal was submitted"
            )
        if not _proposal_change_recorded(
            snapshot.article, int(proposal["id"]), new_hash
        ):
            record_content_change(
                snapshot.article,
                actor=moderator.display_name,
                old_body_sha256=base_hash,
                new_body_sha256=new_hash,
                new_title=extract_h1(body),
                summary=str(proposal.get("summary") or "") or None,
                proposal_id=int(proposal["id"]),
            )
        validate_manifest(
            self.settings.repo_root, snapshot.manifest, validate_documents=False
        )
        result = self.github.commit_files(
            {
                f"docs/{snapshot.article['path']}": assemble_document(
                    snapshot.article["id"], body
                ),
                "data/articles.yml": dump_manifest(snapshot.manifest),
            },
            message=f"Apply CP.UZ article proposal #{proposal['id']}",
            mode=self.settings.apply_mode,
            branch_hint=f"proposal-{proposal['id']}-{snapshot.article['id']}",
            pull_request_title=(
                f"Article proposal #{proposal['id']}: "
                f"{snapshot.article['translation']['title']}"
            ),
            pull_request_body=(
                f"Approved in the CP.UZ moderation dashboard by {moderator.display_name}.\n\n"
                f"Proposer: @{proposal['submitter_login']}\n\n"
                f"Summary: {proposal.get('summary') or 'No summary supplied.'}\n"
            ),
            idempotency_key=f"proposal-{proposal['id']}",
        )
        status = (
            "approved_pending_merge"
            if result.pull_request_number is not None and not result.merged
            else "applied"
        )
        return ApplyResult(
            status=status,
            ref=result.ref,
            url=result.url,
            pull_request_number=result.pull_request_number,
            commit_sha=result.commit_sha,
        )

    def set_review(
        self,
        path: str,
        *,
        review_type: str,
        status: str,
        reviewer: User,
        notes: str | None,
    ) -> ApplyResult:
        if reviewer.role not in {"reviewer", "moderator"}:
            raise PermissionError("reviewer role is required")

        if self.github is not None:
            snapshot = self.snapshot(path)
            body_hash = snapshot.document.body_sha256
            if not _review_decision_recorded(
                snapshot.article,
                review_type=review_type,
                status=status,
                reviewer=reviewer.display_name,
                body_sha256=body_hash,
                notes=notes,
            ):
                set_review_status(
                    snapshot.article,
                    review_type=review_type,
                    status=status,
                    reviewer=reviewer.display_name,
                    body_sha256=body_hash,
                    notes=notes,
                )
            validate_manifest(
                self.settings.repo_root,
                snapshot.manifest,
                validate_documents=False,
            )
            manifest_text = dump_manifest(snapshot.manifest)
            decision_hash = sha256_text(manifest_text)[:16]
            result = self.github.commit_files(
                {"data/articles.yml": manifest_text},
                message=(
                    f"Set {review_type} review for "
                    f"{snapshot.article['path']} to {status}"
                ),
                mode=self.settings.apply_mode,
                branch_hint=f"review-{review_type}-{snapshot.article['id']}",
                pull_request_title=(
                    f"{review_type.title()} review: "
                    f"{snapshot.article['translation']['title']}"
                ),
                pull_request_body=(
                    f"Recorded by {reviewer.display_name} in the CP.UZ dashboard."
                ),
                idempotency_key=(
                    f"review-{snapshot.article['id']}-{review_type}-{status}-{decision_hash}"
                ),
            )
            return ApplyResult(
                status=(
                    "approved_pending_merge"
                    if result.pull_request_number is not None and not result.merged
                    else "applied"
                ),
                ref=result.ref,
                url=result.url,
                pull_request_number=result.pull_request_number,
                commit_sha=result.commit_sha,
            )

        root = self.settings.repo_root
        with repository_lock(root):
            manifest_path = root / "data" / "articles.yml"
            original = manifest_path.read_text(encoding="utf-8")
            manifest = load_manifest(root, validate=True, validate_documents=False)
            article = article_by_path(manifest, self.normalize_path(path))
            document = load_document(article_path(root, article))
            # Synchronize a deliberately edited H1 without putting mutable review
            # data back into Markdown front matter.
            article["translation"]["title"] = extract_h1(document.body)
            try:
                if not _review_decision_recorded(
                    article,
                    review_type=review_type,
                    status=status,
                    reviewer=reviewer.display_name,
                    body_sha256=document.body_sha256,
                    notes=notes,
                ):
                    set_review_status(
                        article,
                        review_type=review_type,
                        status=status,
                        reviewer=reviewer.display_name,
                        body_sha256=document.body_sha256,
                        notes=notes,
                    )
                if self.settings.auto_build:
                    save_manifest(root, manifest)
                    self._invalidate_manifest_cache()
                    build_repository(root)
                else:
                    persist_manifest_bundle(root, manifest)
                    self._invalidate_manifest_cache()
            except BaseException:
                atomic_write_text(manifest_path, original)
                self._invalidate_manifest_cache()
                if self.settings.auto_build:
                    build_repository(root)
                raise
        return ApplyResult(status="applied", ref="local", url=None)
