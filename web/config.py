from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


class ConfigurationError(RuntimeError):
    """Raised when the editor service is configured unsafely or inconsistently."""


def _split(value: str | None) -> frozenset[str]:
    if not value:
        return frozenset()
    return frozenset(part.strip().casefold() for part in value.split(",") if part.strip())


def _parse_bool(name: str, raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    normalized = raw.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be true or false")


def _bounded_int(
    name: str,
    raw: str | None,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int(raw) if raw is not None else default
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}")
    return value


def _resolve_path(raw: str | None, *, root: Path, default: Path) -> Path:
    candidate = Path(raw) if raw else default
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def _validate_public_url(value: str, *, production: bool) -> str:
    value = value.strip().rstrip("/")
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ConfigurationError("CPUZ_PUBLIC_URL must be an absolute http(s) origin")
    if parts.query or parts.fragment or parts.path not in {"", "/"}:
        raise ConfigurationError("CPUZ_PUBLIC_URL must be an origin without a path, query, or fragment")
    if production and parts.scheme != "https":
        raise ConfigurationError("CPUZ_PUBLIC_URL must use HTTPS in production")
    return value


def _validate_repository(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ConfigurationError("CPUZ_GITHUB_REPOSITORY must be owner/name")
    return value


def _validate_branch(value: str) -> str:
    value = value.strip()
    forbidden = ("..", "@{", "\\", " ", "~", "^", ":", "?", "*", "[")
    if (
        not value
        or value.startswith(("/", "."))
        or value.endswith(("/", ".", ".lock"))
        or "//" in value
        or any(token in value for token in forbidden)
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ConfigurationError("CPUZ_GITHUB_BASE_BRANCH is not a safe Git ref name")
    return value


@dataclass(frozen=True)
class Settings:
    environment: str
    repo_root: Path
    database_path: Path
    public_url: str
    cookie_secure: bool
    session_hours: int
    github_client_id: str | None
    github_client_secret: str | None
    github_token: str | None
    github_webhook_secret: str | None
    github_repository: str
    github_base_branch: str
    apply_mode: str
    moderator_logins: frozenset[str]
    reviewer_logins: frozenset[str]
    contributor_logins: frozenset[str]
    allowed_github_org: str | None
    auto_build: bool
    allow_self_approval: bool
    max_proposal_bytes: int
    max_webhook_bytes: int
    submissions_per_hour: int
    approval_claim_timeout_minutes: int

    @property
    def development(self) -> bool:
        return self.environment == "development"

    @classmethod
    def from_env(
        cls,
        *,
        repo_root: Path | None = None,
        overrides: dict[str, object] | None = None,
    ) -> "Settings":
        values = dict(os.environ)
        if overrides:
            values.update({key: str(value) for key, value in overrides.items() if value is not None})

        environment = values.get("CPUZ_ENV", "development").strip().casefold()
        if environment not in {"development", "test", "production"}:
            raise ConfigurationError("CPUZ_ENV must be development, test, or production")
        production = environment == "production"

        root_value = values.get("CPUZ_REPO_ROOT")
        root = Path(root_value or repo_root or Path(__file__).resolve().parents[1]).resolve()
        database_path = _resolve_path(
            values.get("CPUZ_DATABASE_PATH"),
            root=root,
            default=root / "var" / "proposals.sqlite3",
        )
        public_url = _validate_public_url(
            values.get("CPUZ_PUBLIC_URL", "http://127.0.0.1:8000"),
            production=production,
        )

        apply_mode = values.get("CPUZ_APPLY_MODE", "local").strip().casefold()
        if apply_mode not in {"local", "github_pr", "github_direct"}:
            raise ConfigurationError("CPUZ_APPLY_MODE must be local, github_pr, or github_direct")

        token = (values.get("CPUZ_GITHUB_TOKEN") or "").strip() or None
        client_id = (values.get("CPUZ_GITHUB_CLIENT_ID") or "").strip() or None
        client_secret = (values.get("CPUZ_GITHUB_CLIENT_SECRET") or "").strip() or None
        webhook_secret = (values.get("CPUZ_GITHUB_WEBHOOK_SECRET") or "").strip() or None
        if production and (not client_id or not client_secret):
            raise ConfigurationError("GitHub OAuth client ID and secret are required in production")
        if apply_mode.startswith("github") and not token:
            raise ConfigurationError(f"CPUZ_GITHUB_TOKEN is required for {apply_mode}")
        if production and apply_mode == "local":
            raise ConfigurationError(
                "production must use github_pr or github_direct so approved edits reach the canonical repository"
            )
        if production and apply_mode == "github_pr":
            if not webhook_secret:
                raise ConfigurationError(
                    "CPUZ_GITHUB_WEBHOOK_SECRET is required in production github_pr mode"
                )
            if len(webhook_secret.encode("utf-8")) < 32:
                raise ConfigurationError("CPUZ_GITHUB_WEBHOOK_SECRET must be at least 32 bytes")

        moderator_logins = _split(values.get("CPUZ_MODERATOR_GITHUB_LOGINS"))
        if production and not moderator_logins:
            raise ConfigurationError(
                "CPUZ_MODERATOR_GITHUB_LOGINS must contain at least one login in production"
            )

        cookie_secure = _parse_bool(
            "CPUZ_COOKIE_SECURE",
            values.get("CPUZ_COOKIE_SECURE"),
            production,
        )
        if production and not cookie_secure:
            raise ConfigurationError("secure session cookies cannot be disabled in production")

        organization = (values.get("CPUZ_ALLOWED_GITHUB_ORG") or "").strip() or None
        if organization and not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", organization):
            raise ConfigurationError("CPUZ_ALLOWED_GITHUB_ORG is not a valid GitHub organization name")

        return cls(
            environment=environment,
            repo_root=root,
            database_path=database_path,
            public_url=public_url,
            cookie_secure=cookie_secure,
            session_hours=_bounded_int(
                "CPUZ_SESSION_HOURS",
                values.get("CPUZ_SESSION_HOURS"),
                24,
                minimum=1,
                maximum=720,
            ),
            github_client_id=client_id,
            github_client_secret=client_secret,
            github_token=token,
            github_webhook_secret=webhook_secret,
            github_repository=_validate_repository(
                values.get("CPUZ_GITHUB_REPOSITORY", "cp-uz/algo")
            ),
            github_base_branch=_validate_branch(
                values.get("CPUZ_GITHUB_BASE_BRANCH", "main")
            ),
            apply_mode=apply_mode,
            moderator_logins=moderator_logins,
            reviewer_logins=_split(values.get("CPUZ_REVIEWER_GITHUB_LOGINS")),
            contributor_logins=_split(values.get("CPUZ_CONTRIBUTOR_GITHUB_LOGINS")),
            allowed_github_org=organization,
            auto_build=_parse_bool(
                "CPUZ_AUTO_BUILD", values.get("CPUZ_AUTO_BUILD"), True
            ),
            allow_self_approval=_parse_bool(
                "CPUZ_ALLOW_SELF_APPROVAL",
                values.get("CPUZ_ALLOW_SELF_APPROVAL"),
                False,
            ),
            max_proposal_bytes=_bounded_int(
                "CPUZ_MAX_PROPOSAL_BYTES",
                values.get("CPUZ_MAX_PROPOSAL_BYTES"),
                512 * 1024,
                minimum=4 * 1024,
                maximum=4 * 1024 * 1024,
            ),
            max_webhook_bytes=_bounded_int(
                "CPUZ_MAX_WEBHOOK_BYTES",
                values.get("CPUZ_MAX_WEBHOOK_BYTES"),
                2 * 1024 * 1024,
                minimum=64 * 1024,
                maximum=10 * 1024 * 1024,
            ),
            submissions_per_hour=_bounded_int(
                "CPUZ_SUBMISSIONS_PER_HOUR",
                values.get("CPUZ_SUBMISSIONS_PER_HOUR"),
                12,
                minimum=1,
                maximum=1000,
            ),
            approval_claim_timeout_minutes=_bounded_int(
                "CPUZ_APPROVAL_CLAIM_TIMEOUT_MINUTES",
                values.get("CPUZ_APPROVAL_CLAIM_TIMEOUT_MINUTES"),
                15,
                minimum=1,
                maximum=1440,
            ),
        )
