from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from cpuz.util import utc_now


class ProposalStateError(RuntimeError):
    """Raised when a proposal changed concurrently or is locked by another moderator."""


@dataclass(frozen=True)
class User:
    id: int
    github_id: str
    login: str
    display_name: str
    email: str | None
    avatar_url: str | None
    role: str


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    github_id TEXT NOT NULL UNIQUE,
                    login TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    display_name TEXT NOT NULL,
                    email TEXT,
                    avatar_url TEXT,
                    role TEXT NOT NULL CHECK(role IN ('contributor','reviewer','moderator')),
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    csrf_token TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS oauth_states (
                    state_hash TEXT PRIMARY KEY,
                    redirect_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS proposals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id TEXT NOT NULL,
                    article_path TEXT NOT NULL,
                    base_content_sha256 TEXT NOT NULL,
                    old_body TEXT NOT NULL,
                    new_body TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL CHECK(status IN (
                        'pending','changes_requested','rejected','applied',
                        'approved_pending_merge','conflict'
                    )),
                    submitter_user_id INTEGER NOT NULL REFERENCES users(id),
                    submitter_name TEXT NOT NULL,
                    submitter_login TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    moderator_user_id INTEGER REFERENCES users(id),
                    moderator_name TEXT,
                    moderated_at TEXT,
                    feedback TEXT,
                    applied_ref TEXT,
                    applied_url TEXT,
                    applied_pr_number INTEGER,
                    applied_commit_sha TEXT
                );
                CREATE INDEX IF NOT EXISTS proposals_status_idx ON proposals(status, created_at DESC);
                CREATE INDEX IF NOT EXISTS proposals_submitter_idx ON proposals(submitter_user_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS proposal_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
                    event TEXT NOT NULL,
                    actor_user_id INTEGER REFERENCES users(id),
                    actor_name TEXT NOT NULL,
                    at TEXT NOT NULL,
                    message TEXT,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS proposal_events_proposal_idx ON proposal_events(proposal_id, id);
                CREATE TABLE IF NOT EXISTS proposal_claims (
                    proposal_id INTEGER PRIMARY KEY REFERENCES proposals(id) ON DELETE CASCADE,
                    moderator_user_id INTEGER NOT NULL REFERENCES users(id),
                    moderator_name TEXT NOT NULL,
                    claimed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS submission_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS submission_log_user_idx ON submission_log(user_id, created_at);
                CREATE TABLE IF NOT EXISTS github_webhook_deliveries (
                    delivery_id TEXT PRIMARY KEY,
                    received_at TEXT NOT NULL
                );
                """
            )
            # Backward-compatible migration for databases created by the first
            # editor implementation. SQLite supports adding nullable columns
            # without rebuilding the table or losing proposal history.
            existing = {
                str(row["name"])
                for row in db.execute("PRAGMA table_info(proposals)").fetchall()
            }
            if "applied_pr_number" not in existing:
                db.execute("ALTER TABLE proposals ADD COLUMN applied_pr_number INTEGER")
            if "applied_commit_sha" not in existing:
                db.execute("ALTER TABLE proposals ADD COLUMN applied_commit_sha TEXT")
            db.execute(
                "CREATE INDEX IF NOT EXISTS proposals_pr_idx ON proposals(applied_pr_number)"
            )

    @staticmethod
    def token_hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _begin_immediate(db: sqlite3.Connection) -> None:
        db.execute("BEGIN IMMEDIATE")

    def upsert_user(
        self,
        *,
        github_id: str,
        login: str,
        display_name: str,
        email: str | None,
        avatar_url: str | None,
        role: str,
    ) -> User:
        now = utc_now()
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO users(github_id, login, display_name, email, avatar_url, role, created_at, last_seen_at)
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(github_id) DO UPDATE SET
                  login=excluded.login, display_name=excluded.display_name,
                  email=excluded.email, avatar_url=excluded.avatar_url,
                  role=excluded.role, last_seen_at=excluded.last_seen_at
                """,
                (github_id, login, display_name, email, avatar_url, role, now, now),
            )
            row = db.execute("SELECT * FROM users WHERE github_id=?", (github_id,)).fetchone()
        if row is None:  # pragma: no cover - defensive database invariant
            raise RuntimeError("user upsert did not return a row")
        return self._user(row)

    def create_session(self, user_id: int, *, hours: int) -> tuple[str, str]:
        token = secrets.token_urlsafe(48)
        csrf = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=hours)
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE expires_at < ?", (utc_now(),))
            db.execute(
                "INSERT INTO sessions(token_hash,user_id,csrf_token,created_at,expires_at) VALUES(?,?,?,?,?)",
                (
                    self.token_hash(token),
                    user_id,
                    csrf,
                    now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    expires.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                ),
            )
        return token, csrf

    def session(self, token: str | None) -> tuple[User, str] | None:
        if not token:
            return None
        with self.connect() as db:
            row = db.execute(
                """
                SELECT u.*, s.csrf_token FROM sessions s
                JOIN users u ON u.id=s.user_id
                WHERE s.token_hash=? AND s.expires_at>?
                """,
                (self.token_hash(token), utc_now()),
            ).fetchone()
        if row is None:
            return None
        return self._user(row), str(row["csrf_token"])

    def delete_session(self, token: str | None) -> None:
        if not token:
            return
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (self.token_hash(token),))

    def create_oauth_state(self, redirect_path: str) -> str:
        raw = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=10)
        with self.connect() as db:
            db.execute("DELETE FROM oauth_states WHERE expires_at < ?", (utc_now(),))
            db.execute(
                "INSERT INTO oauth_states VALUES(?,?,?,?)",
                (
                    self.token_hash(raw),
                    redirect_path,
                    now.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    expires.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                ),
            )
        return raw

    def consume_oauth_state(self, raw: str) -> str | None:
        digest = self.token_hash(raw)
        with self.connect() as db:
            self._begin_immediate(db)
            row = db.execute(
                "SELECT redirect_path FROM oauth_states WHERE state_hash=? AND expires_at>?",
                (digest, utc_now()),
            ).fetchone()
            db.execute("DELETE FROM oauth_states WHERE state_hash=?", (digest,))
        return str(row["redirect_path"]) if row else None

    def submission_allowed(self, user_id: int, limit: int) -> bool:
        cutoff = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        with self.connect() as db:
            self._begin_immediate(db)
            db.execute("DELETE FROM submission_log WHERE created_at<?", (cutoff,))
            count = db.execute(
                "SELECT COUNT(*) FROM submission_log WHERE user_id=? AND created_at>=?",
                (user_id, cutoff),
            ).fetchone()[0]
            if count >= limit:
                return False
            db.execute(
                "INSERT INTO submission_log(user_id,created_at) VALUES(?,?)",
                (user_id, utc_now()),
            )
        return True

    def create_proposal(
        self,
        *,
        article_id: str,
        article_path: str,
        base_content_sha256: str,
        old_body: str,
        new_body: str,
        summary: str,
        user: User,
    ) -> int:
        now = utc_now()
        with self.connect() as db:
            cursor = db.execute(
                """
                INSERT INTO proposals(
                  article_id,article_path,base_content_sha256,old_body,new_body,summary,status,
                  submitter_user_id,submitter_name,submitter_login,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,'pending',?,?,?,?,?)
                """,
                (
                    article_id,
                    article_path,
                    base_content_sha256,
                    old_body,
                    new_body,
                    summary,
                    user.id,
                    user.display_name,
                    user.login,
                    now,
                    now,
                ),
            )
            proposal_id = int(cursor.lastrowid)
            self._event_db(db, proposal_id, "submitted", user, summary or None)
        return proposal_id

    @staticmethod
    def _claim_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "proposal_id": int(row["proposal_id"]),
            "moderator_user_id": int(row["moderator_user_id"]),
            "moderator_name": str(row["moderator_name"]),
            "claimed_at": str(row["claimed_at"]),
        }

    def get_proposal(self, proposal_id: int) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["events"] = [
                dict(item)
                for item in db.execute(
                    "SELECT * FROM proposal_events WHERE proposal_id=? ORDER BY id",
                    (proposal_id,),
                )
            ]
            claim = db.execute(
                "SELECT * FROM proposal_claims WHERE proposal_id=?", (proposal_id,)
            ).fetchone()
            result["claim"] = self._claim_from_row(claim)
        return result

    def list_proposals(
        self,
        *,
        status: str | None = None,
        submitter_id: int | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("p.status=?")
            params.append(status)
        if submitter_id is not None:
            clauses.append("p.submitter_user_id=?")
            params.append(submitter_id)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        query = (
            "SELECT p.*, c.moderator_user_id AS claim_moderator_user_id, "
            "c.moderator_name AS claim_moderator_name, c.claimed_at AS claim_claimed_at "
            "FROM proposals p LEFT JOIN proposal_claims c ON c.proposal_id=p.id"
            + where
            + " ORDER BY p.created_at DESC"
        )
        with self.connect() as db:
            rows = [dict(row) for row in db.execute(query, params)]
        for row in rows:
            claim_user = row.pop("claim_moderator_user_id")
            claim_name = row.pop("claim_moderator_name")
            claim_at = row.pop("claim_claimed_at")
            row["claim"] = (
                {
                    "proposal_id": int(row["id"]),
                    "moderator_user_id": int(claim_user),
                    "moderator_name": str(claim_name),
                    "claimed_at": str(claim_at),
                }
                if claim_user is not None
                else None
            )
        return rows

    def revise_proposal(
        self,
        proposal_id: int,
        *,
        new_body: str,
        summary: str,
        user: User,
    ) -> None:
        now = utc_now()
        with self.connect() as db:
            self._begin_immediate(db)
            row = db.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
            if row is None:
                raise ProposalStateError("proposal not found")
            claim = db.execute(
                "SELECT 1 FROM proposal_claims WHERE proposal_id=?", (proposal_id,)
            ).fetchone()
            if claim:
                raise ProposalStateError("proposal approval is currently being processed")
            if row["submitter_user_id"] != user.id or row["status"] != "changes_requested":
                raise ProposalStateError("this proposal cannot be revised by the current user")
            cursor = db.execute(
                """
                UPDATE proposals SET new_body=?, summary=?, status='pending', feedback=NULL,
                  moderator_user_id=NULL, moderator_name=NULL, moderated_at=NULL, updated_at=?,
                  applied_ref=NULL, applied_url=NULL, applied_pr_number=NULL, applied_commit_sha=NULL
                WHERE id=? AND status='changes_requested'
                """,
                (new_body, summary, now, proposal_id),
            )
            if cursor.rowcount != 1:
                raise ProposalStateError("proposal status changed before the revision was saved")
            self._event_db(db, proposal_id, "revised", user, summary or None)

    def claim_proposal(
        self,
        proposal_id: int,
        *,
        moderator: User,
        takeover_after_minutes: int,
    ) -> dict[str, Any]:
        """Exclusively claim a pending proposal before applying external side effects.

        The same moderator may retry an existing claim. Another moderator may take
        over only after the configured timeout. Application itself is idempotent,
        so a retry after a process crash cannot create a second PR or duplicate a
        local content-change history event.
        """

        now = utc_now()
        with self.connect() as db:
            self._begin_immediate(db)
            proposal = db.execute(
                "SELECT status FROM proposals WHERE id=?", (proposal_id,)
            ).fetchone()
            if proposal is None:
                raise ProposalStateError("proposal not found")
            if proposal["status"] != "pending":
                raise ProposalStateError("only a pending proposal can be approved")
            claim = db.execute(
                "SELECT * FROM proposal_claims WHERE proposal_id=?", (proposal_id,)
            ).fetchone()
            if claim is None:
                db.execute(
                    "INSERT INTO proposal_claims VALUES(?,?,?,?)",
                    (proposal_id, moderator.id, moderator.display_name, now),
                )
                self._event_db(db, proposal_id, "approval_claimed", moderator, None)
            elif int(claim["moderator_user_id"]) == moderator.id:
                # Idempotent retry by the moderator who began the approval.
                return self._claim_from_row(claim) or {}
            else:
                claimed_at = datetime.fromisoformat(
                    str(claim["claimed_at"]).replace("Z", "+00:00")
                )
                age = datetime.now(timezone.utc) - claimed_at
                if age < timedelta(minutes=takeover_after_minutes):
                    raise ProposalStateError(
                        f"approval is being processed by {claim['moderator_name']} "
                        f"since {claim['claimed_at']}"
                    )
                previous_name = str(claim["moderator_name"])
                previous_user_id = int(claim["moderator_user_id"])
                db.execute(
                    """
                    UPDATE proposal_claims SET moderator_user_id=?, moderator_name=?, claimed_at=?
                    WHERE proposal_id=?
                    """,
                    (moderator.id, moderator.display_name, now, proposal_id),
                )
                self._event_db(
                    db,
                    proposal_id,
                    "approval_claim_taken_over",
                    moderator,
                    f"Recovered a stale approval claim previously held by {previous_name}.",
                    {
                        "previous_moderator_user_id": previous_user_id,
                        "previous_moderator_name": previous_name,
                        "previous_claimed_at": str(claim["claimed_at"]),
                    },
                )
            updated = db.execute(
                "SELECT * FROM proposal_claims WHERE proposal_id=?", (proposal_id,)
            ).fetchone()
        return self._claim_from_row(updated) or {}

    def release_claim(
        self,
        proposal_id: int,
        *,
        moderator: User,
        reason: str,
    ) -> None:
        with self.connect() as db:
            self._begin_immediate(db)
            cursor = db.execute(
                "DELETE FROM proposal_claims WHERE proposal_id=? AND moderator_user_id=?",
                (proposal_id, moderator.id),
            )
            if cursor.rowcount:
                self._event_db(
                    db,
                    proposal_id,
                    "approval_claim_released",
                    moderator,
                    reason[:1000] or None,
                )

    def finish_claim(
        self,
        proposal_id: int,
        *,
        status: str,
        moderator: User,
        feedback: str | None,
        applied_ref: str | None,
        applied_url: str | None,
        applied_pr_number: int | None,
        applied_commit_sha: str | None,
        event: str,
    ) -> None:
        if status not in {"applied", "approved_pending_merge", "conflict"}:
            raise ValueError("invalid approval completion status")
        now = utc_now()
        with self.connect() as db:
            self._begin_immediate(db)
            cursor = db.execute(
                """
                UPDATE proposals SET status=?, moderator_user_id=?, moderator_name=?,
                  moderated_at=?, updated_at=?, feedback=?, applied_ref=?, applied_url=?,
                  applied_pr_number=?, applied_commit_sha=?
                WHERE id=? AND status='pending' AND EXISTS (
                  SELECT 1 FROM proposal_claims c
                  WHERE c.proposal_id=proposals.id AND c.moderator_user_id=?
                )
                """,
                (
                    status,
                    moderator.id,
                    moderator.display_name,
                    now,
                    now,
                    feedback,
                    applied_ref,
                    applied_url,
                    applied_pr_number,
                    applied_commit_sha,
                    proposal_id,
                    moderator.id,
                ),
            )
            if cursor.rowcount != 1:
                raise ProposalStateError(
                    "proposal or approval claim changed before the decision was saved"
                )
            db.execute("DELETE FROM proposal_claims WHERE proposal_id=?", (proposal_id,))
            self._event_db(
                db,
                proposal_id,
                event,
                moderator,
                feedback,
                {
                    "applied_ref": applied_ref,
                    "applied_url": applied_url,
                    "applied_pr_number": applied_pr_number,
                    "applied_commit_sha": applied_commit_sha,
                },
            )

    def moderate(
        self,
        proposal_id: int,
        *,
        status: str,
        moderator: User,
        feedback: str | None,
        applied_ref: str | None = None,
        applied_url: str | None = None,
        applied_pr_number: int | None = None,
        applied_commit_sha: str | None = None,
        event: str,
        expected_statuses: tuple[str, ...] = ("pending",),
    ) -> None:
        if not expected_statuses:
            raise ValueError("expected_statuses must not be empty")
        now = utc_now()
        placeholders = ",".join("?" for _ in expected_statuses)
        with self.connect() as db:
            self._begin_immediate(db)
            cursor = db.execute(
                f"""
                UPDATE proposals SET status=?, moderator_user_id=?, moderator_name=?,
                  moderated_at=?, updated_at=?, feedback=?, applied_ref=?, applied_url=?,
                  applied_pr_number=?, applied_commit_sha=?
                WHERE id=? AND status IN ({placeholders})
                  AND NOT EXISTS (SELECT 1 FROM proposal_claims c WHERE c.proposal_id=proposals.id)
                """,
                (
                    status,
                    moderator.id,
                    moderator.display_name,
                    now,
                    now,
                    feedback,
                    applied_ref,
                    applied_url,
                    applied_pr_number,
                    applied_commit_sha,
                    proposal_id,
                    *expected_statuses,
                ),
            )
            if cursor.rowcount != 1:
                raise ProposalStateError(
                    "proposal status changed or approval is already being processed"
                )
            self._event_db(
                db,
                proposal_id,
                event,
                moderator,
                feedback,
                {
                    "applied_ref": applied_ref,
                    "applied_url": applied_url,
                    "applied_pr_number": applied_pr_number,
                    "applied_commit_sha": applied_commit_sha,
                },
            )

    def process_pull_request_webhook(
        self,
        *,
        delivery_id: str,
        pull_request_number: int,
        merged: bool,
        pull_request_url: str,
        commit_sha: str | None,
        sender_login: str | None,
    ) -> tuple[str, int | None]:
        """Idempotently record a verified GitHub pull-request close event."""

        now = utc_now()
        with self.connect() as db:
            self._begin_immediate(db)
            # Keep replay protection bounded without requiring a maintenance job.
            cutoff = (
                datetime.now(timezone.utc) - timedelta(days=30)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            db.execute(
                "DELETE FROM github_webhook_deliveries WHERE received_at<?", (cutoff,)
            )
            try:
                db.execute(
                    "INSERT INTO github_webhook_deliveries(delivery_id,received_at) VALUES(?,?)",
                    (delivery_id, now),
                )
            except sqlite3.IntegrityError:
                return "duplicate", None

            proposal = db.execute(
                "SELECT * FROM proposals WHERE applied_pr_number=?",
                (pull_request_number,),
            ).fetchone()
            if proposal is None:
                return "unmatched", None
            proposal_id = int(proposal["id"])
            if proposal["status"] != "approved_pending_merge":
                return "already_final", proposal_id

            target_status = "applied" if merged else "rejected"
            feedback = proposal["feedback"]
            if not merged:
                close_message = "GitHub pull request was closed without being merged."
                feedback = f"{feedback}\n\n{close_message}".strip() if feedback else close_message
            cursor = db.execute(
                """
                UPDATE proposals SET status=?, updated_at=?, feedback=?, applied_url=?,
                  applied_commit_sha=COALESCE(?, applied_commit_sha)
                WHERE id=? AND status='approved_pending_merge'
                """,
                (
                    target_status,
                    now,
                    feedback,
                    pull_request_url,
                    commit_sha,
                    proposal_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ProposalStateError("proposal changed while processing GitHub webhook")
            self._event_db(
                db,
                proposal_id,
                "pull_request_merged" if merged else "pull_request_closed_without_merge",
                None,
                (
                    f"Merged by @{sender_login}."
                    if merged and sender_login
                    else (
                        f"Closed without merge by @{sender_login}."
                        if sender_login
                        else None
                    )
                ),
                {
                    "pull_request_number": pull_request_number,
                    "pull_request_url": pull_request_url,
                    "commit_sha": commit_sha,
                    "delivery_id": delivery_id,
                },
                actor_name="GitHub webhook",
            )
            return ("merged" if merged else "closed"), proposal_id

    def add_event(
        self,
        proposal_id: int,
        *,
        event: str,
        actor: User,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.connect() as db:
            self._event_db(db, proposal_id, event, actor, message, metadata)

    def _event_db(
        self,
        db: sqlite3.Connection,
        proposal_id: int,
        event: str,
        actor: User | None,
        message: str | None,
        metadata: dict[str, Any] | None = None,
        *,
        actor_name: str | None = None,
    ) -> None:
        resolved_name = actor.display_name if actor is not None else (actor_name or "System")
        db.execute(
            """
            INSERT INTO proposal_events(proposal_id,event,actor_user_id,actor_name,at,message,metadata_json)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                proposal_id,
                event,
                actor.id if actor is not None else None,
                resolved_name,
                utc_now(),
                message,
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )

    @staticmethod
    def _user(row: sqlite3.Row) -> User:
        return User(
            id=int(row["id"]),
            github_id=str(row["github_id"]),
            login=str(row["login"]),
            display_name=str(row["display_name"]),
            email=row["email"],
            avatar_url=row["avatar_url"],
            role=str(row["role"]),
        )
