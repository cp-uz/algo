from __future__ import annotations

import hashlib
import hmac
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from cpuz.metadata import MetadataError, articles, effective_review_status, workflow_stage
from cpuz.rendering import render_markdown

from .config import ConfigurationError, Settings
from .db import Database, ProposalStateError, User
from .diffing import diff_stats, side_by_side
from .service import EditorService, ProposalConflict

ROLE_LEVEL = {"contributor": 1, "reviewer": 2, "moderator": 3}
STATUS_LABELS = {
    "pending": "Moderatsiya kutilmoqda",
    "changes_requested": "O‘zgartirish so‘ralgan",
    "rejected": "Rad etilgan",
    "applied": "Qabul qilingan",
    "approved_pending_merge": "Pull request birlashtirilishi kutilmoqda",
    "conflict": "Maqola o‘zgargan — qayta ko‘rib chiqish kerak",
}
REVIEW_LABELS = {
    "pending": "Kutilmoqda",
    "approved": "Tasdiqlangan",
    "changes_requested": "O‘zgartirish so‘ralgan",
    "stale": "Eskirgan",
}


def _safe_next(value: str | None, default: str = "/") -> str:
    if not value or not value.startswith("/") or value.startswith("//"):
        return default
    return value


def _safe_github_result_url(value: str | None, *, repository: str) -> str | None:
    """Accept only result links inside the configured GitHub repository."""

    if not value:
        return None
    parts = urlsplit(value)
    expected_prefix = f"/{repository.strip('/')}/".casefold()
    if (
        parts.scheme == "https"
        and parts.netloc.casefold() == "github.com"
        and parts.path.casefold().startswith(expected_prefix)
        and not parts.username
        and not parts.password
    ):
        return value
    return None


def _claim_is_stale(claim: dict[str, Any] | None, *, timeout_minutes: int) -> bool:
    """Return whether another moderator may safely recover an approval claim.

    Claims are written by this service in UTC ISO-8601 form. An invalid timestamp
    is treated as active rather than stale so malformed data never enables an
    accidental takeover.
    """

    if not claim:
        return False
    try:
        claimed_at = datetime.fromisoformat(str(claim["claimed_at"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return False
    if claimed_at.tzinfo is None:
        claimed_at = claimed_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - claimed_at >= timedelta(minutes=timeout_minutes)


def _role_for(settings: Settings, login: str, *, organization_ok: bool) -> str | None:
    normalized = login.casefold()
    if settings.allowed_github_org and not organization_ok:
        return None
    if normalized in settings.moderator_logins:
        return "moderator"
    if normalized in settings.reviewer_logins:
        return "reviewer"
    if settings.contributor_logins and normalized not in settings.contributor_logins:
        return None
    return "contributor"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    database = Database(settings.database_path)
    database.initialize()
    service = EditorService(settings, database)
    templates = Environment(
        loader=FileSystemLoader(settings.repo_root / "web" / "templates"),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        service.close()

    app = FastAPI(title="CP.UZ Algorithms Editor", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.state.settings = settings
    app.state.database = database
    app.state.service = service

    def context(request: Request, **values: Any) -> dict[str, Any]:
        return {
            "request": request,
            "user": getattr(request.state, "user", None),
            "csrf_token": getattr(request.state, "csrf_token", ""),
            "status_labels": STATUS_LABELS,
            "review_labels": REVIEW_LABELS,
            "environment": settings.environment,
            **values,
        }

    def render(request: Request, template: str, *, status_code: int = 200, **values: Any) -> HTMLResponse:
        body = templates.get_template(template).render(context(request, **values))
        return HTMLResponse(body, status_code=status_code)

    def require_user(request: Request, role: str = "contributor") -> User:
        user = getattr(request.state, "user", None)
        if user is None:
            next_path = _safe_next(request.url.path)
            raise HTTPException(
                status_code=303,
                headers={"Location": f"/auth/github/start?{urlencode({'next': next_path})}"},
            )
        if ROLE_LEVEL[user.role] < ROLE_LEVEL[role]:
            raise HTTPException(status_code=403, detail="Bu amal uchun ruxsat yetarli emas.")
        return user

    def verify_csrf(request: Request, supplied: str | None) -> None:
        expected = getattr(request.state, "csrf_token", "")
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            raise HTTPException(status_code=403, detail="CSRF tekshiruvi muvaffaqiyatsiz tugadi.")

    def proposal_access(request: Request, proposal: dict[str, Any]) -> User:
        user = require_user(request)
        if user.role in {"reviewer", "moderator"} or int(proposal["submitter_user_id"]) == user.id:
            return user
        raise HTTPException(status_code=403, detail="Bu taklifni ko‘rish huquqi yo‘q.")

    @app.middleware("http")
    async def security_and_session(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                request_bytes = int(content_length)
            except ValueError:
                return JSONResponse({"detail": "Noto‘g‘ri Content-Length."}, status_code=400)
            # Webhook payloads and article forms have separate, explicitly
            # bounded limits. The form allowance covers URL encoding and the
            # optional summary without permitting unbounded body buffering.
            limit = (
                settings.max_webhook_bytes
                if request.url.path == "/webhooks/github"
                else settings.max_proposal_bytes + 128 * 1024
            )
            if request_bytes < 0 or request_bytes > limit:
                return JSONResponse(
                    {"detail": "So‘rov hajmi ruxsat etilgan limitdan katta."},
                    status_code=413,
                )
        elif request.method in {"POST", "PUT", "PATCH"}:
            # Bound chunked requests that omit Content-Length. Starlette will
            # reuse this cached body in the route handler.
            limit = (
                settings.max_webhook_bytes
                if request.url.path == "/webhooks/github"
                else settings.max_proposal_bytes + 128 * 1024
            )
            chunks: list[bytes] = []
            total = 0
            async for chunk in request.stream():
                total += len(chunk)
                if total > limit:
                    return JSONResponse(
                        {"detail": "So‘rov hajmi ruxsat etilgan limitdan katta."},
                        status_code=413,
                    )
                chunks.append(chunk)
            request._body = b"".join(chunks)  # Starlette request-body cache
        session = database.session(request.cookies.get("cpuz_session"))
        if session:
            request.state.user, request.state.csrf_token = session
        else:
            request.state.user, request.state.csrf_token = None, ""
        try:
            response = await call_next(request)
        except HTTPException as exc:
            if exc.status_code == 303 and exc.headers and exc.headers.get("Location"):
                response = RedirectResponse(exc.headers["Location"], status_code=303)
            else:
                response = render(request, "error.html", status_code=exc.status_code, message=str(exc.detail))
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
            "form-action 'self'; img-src 'self' data: https://avatars.githubusercontent.com; "
            "style-src 'self' 'unsafe-inline'; script-src 'self' https://cdn.jsdelivr.net; connect-src 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.exception_handler(MetadataError)
    async def metadata_error(request: Request, exc: MetadataError):
        return render(request, "error.html", status_code=400, message=str(exc))

    @app.exception_handler(ProposalStateError)
    async def proposal_state_error(request: Request, exc: ProposalStateError):
        return render(request, "error.html", status_code=409, message=str(exc))

    @app.exception_handler(ConfigurationError)
    async def configuration_error(request: Request, exc: ConfigurationError):
        return render(request, "error.html", status_code=500, message=str(exc))

    @app.get("/healthz")
    async def healthz() -> JSONResponse:
        return JSONResponse({"ok": True, "mode": settings.apply_mode})

    @app.post("/webhooks/github")
    async def github_webhook(request: Request) -> JSONResponse:
        secret = settings.github_webhook_secret
        if not secret:
            raise HTTPException(status_code=404, detail="Topilmadi")
        body = await request.body()
        if len(body) > settings.max_webhook_bytes:
            raise HTTPException(
                status_code=413,
                detail="Webhook hajmi ruxsat etilgan limitdan katta.",
            )
        supplied_signature = request.headers.get("X-Hub-Signature-256", "")
        expected_signature = "sha256=" + hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise HTTPException(status_code=401, detail="Webhook imzosi noto‘g‘ri.")

        delivery_id = request.headers.get("X-GitHub-Delivery", "").strip()
        if (
            not delivery_id
            or len(delivery_id) > 128
            or any(ord(character) < 33 or ord(character) > 126 for character in delivery_id)
        ):
            raise HTTPException(status_code=400, detail="Webhook delivery ID noto‘g‘ri.")
        event_name = request.headers.get("X-GitHub-Event", "")
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail="Webhook JSON noto‘g‘ri.") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Webhook JSON obyekti kutilgan.")
        if event_name != "pull_request" or payload.get("action") != "closed":
            return JSONResponse({"status": "ignored"})

        repository = payload.get("repository")
        pull_request = payload.get("pull_request")
        if not isinstance(repository, dict) or repository.get("full_name") != settings.github_repository:
            raise HTTPException(status_code=400, detail="Webhook repository mos emas.")
        if not isinstance(pull_request, dict):
            raise HTTPException(status_code=400, detail="Pull request ma’lumoti yo‘q.")
        base = pull_request.get("base")
        if not isinstance(base, dict) or base.get("ref") != settings.github_base_branch:
            raise HTTPException(status_code=400, detail="Pull request base branch mos emas.")
        try:
            pull_request_number = int(pull_request["number"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Pull request raqami noto‘g‘ri.") from exc
        sender = payload.get("sender")
        sender_login = (
            str(sender.get("login"))
            if isinstance(sender, dict) and sender.get("login")
            else None
        )
        merged = pull_request.get("merged") is True
        commit_sha = (
            str(pull_request.get("merge_commit_sha"))
            if merged and pull_request.get("merge_commit_sha")
            else None
        )
        result, proposal_id = database.process_pull_request_webhook(
            delivery_id=delivery_id,
            pull_request_number=pull_request_number,
            merged=merged,
            pull_request_url=str(pull_request.get("html_url") or ""),
            commit_sha=commit_sha,
            sender_login=sender_login,
        )
        return JSONResponse({"status": result, "proposal_id": proposal_id})

    @app.get("/auth/github/start")
    async def github_start(request: Request, next: str = "/"):
        if settings.development and not settings.github_client_id:
            return RedirectResponse(f"/dev/login?{urlencode({'next': _safe_next(next)})}", status_code=303)
        if not settings.github_client_id:
            raise HTTPException(status_code=503, detail="GitHub OAuth sozlanmagan.")
        redirect_path = _safe_next(next)
        state = database.create_oauth_state(redirect_path)
        callback = settings.public_url + "/auth/github/callback"
        scopes = ["read:user"]
        if settings.allowed_github_org:
            scopes.append("read:org")
        query = urlencode(
            {
                "client_id": settings.github_client_id,
                "redirect_uri": callback,
                "scope": " ".join(scopes),
                "state": state,
                "allow_signup": "true",
            }
        )
        response = RedirectResponse("https://github.com/login/oauth/authorize?" + query, status_code=303)
        response.set_cookie(
            "cpuz_oauth_state",
            state,
            max_age=600,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            path="/auth/github/callback",
        )
        return response

    @app.get("/auth/github/callback")
    async def github_callback(request: Request, code: str, state: str):
        cookie_state = request.cookies.get("cpuz_oauth_state")
        if not cookie_state or not hmac.compare_digest(cookie_state, state):
            raise HTTPException(status_code=400, detail="OAuth state noto‘g‘ri.")
        redirect_path = database.consume_oauth_state(state)
        if redirect_path is None:
            raise HTTPException(status_code=400, detail="OAuth state eskirgan yoki ishlatilgan.")
        assert settings.github_client_id and settings.github_client_secret
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                token_response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    headers={"Accept": "application/json"},
                    data={
                        "client_id": settings.github_client_id,
                        "client_secret": settings.github_client_secret,
                        "code": code,
                        "redirect_uri": settings.public_url + "/auth/github/callback",
                    },
                )
                token_response.raise_for_status()
                try:
                    token_payload = token_response.json()
                except ValueError as exc:
                    raise HTTPException(
                        status_code=502,
                        detail="GitHub OAuth noto‘g‘ri javob qaytardi.",
                    ) from exc
                if not isinstance(token_payload, dict):
                    raise HTTPException(
                        status_code=502,
                        detail="GitHub OAuth noto‘g‘ri javob qaytardi.",
                    )
                access_token = token_payload.get("access_token")
                if not isinstance(access_token, str) or not access_token:
                    raise HTTPException(
                        status_code=401,
                        detail="GitHub login muvaffaqiyatsiz tugadi.",
                    )
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
                user_response = await client.get(
                    "https://api.github.com/user", headers=headers
                )
                user_response.raise_for_status()
                try:
                    profile = user_response.json()
                except ValueError as exc:
                    raise HTTPException(
                        status_code=502,
                        detail="GitHub profil javobi noto‘g‘ri.",
                    ) from exc
                if not isinstance(profile, dict) or not profile.get("login") or not profile.get("id"):
                    raise HTTPException(
                        status_code=502,
                        detail="GitHub profil javobida zarur maydonlar yo‘q.",
                    )
                organization_ok = True
                if settings.allowed_github_org:
                    membership = await client.get(
                        f"https://api.github.com/user/memberships/orgs/{settings.allowed_github_org}",
                        headers=headers,
                    )
                    if membership.status_code >= 500:
                        membership.raise_for_status()
                    if membership.status_code == 200:
                        try:
                            membership_payload = membership.json()
                        except ValueError as exc:
                            raise HTTPException(
                                status_code=502,
                                detail="GitHub tashkilot javobi noto‘g‘ri.",
                            ) from exc
                        organization_ok = (
                            isinstance(membership_payload, dict)
                            and membership_payload.get("state") == "active"
                        )
                    else:
                        organization_ok = False
        except HTTPException:
            raise
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail="GitHub bilan autentifikatsiya vaqtincha ishlamayapti.",
            ) from exc
        login = str(profile["login"])
        role = _role_for(settings, login, organization_ok=organization_ok)
        if role is None:
            raise HTTPException(status_code=403, detail="Ushbu GitHub akkaunti hissa qo‘shishga ruxsat etilmagan.")
        user = database.upsert_user(
            github_id=str(profile["id"]),
            login=login,
            display_name=str(profile.get("name") or login),
            email=profile.get("email"),
            avatar_url=profile.get("avatar_url"),
            role=role,
        )
        token, _ = database.create_session(user.id, hours=settings.session_hours)
        response = RedirectResponse(_safe_next(redirect_path), status_code=303)
        response.delete_cookie("cpuz_oauth_state", path="/auth/github/callback")
        response.set_cookie(
            "cpuz_session",
            token,
            max_age=settings.session_hours * 3600,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            path="/",
        )
        return response

    @app.get("/dev/login")
    async def dev_login_form(request: Request, next: str = "/"):
        if not settings.development and settings.environment != "test":
            raise HTTPException(status_code=404, detail="Topilmadi")
        return render(request, "dev_login.html", next=_safe_next(next))

    @app.post("/dev/login")
    async def dev_login(request: Request):
        if not settings.development and settings.environment != "test":
            raise HTTPException(status_code=404, detail="Topilmadi")
        form = await request.form()
        role = str(form.get("role", "contributor"))
        if role not in ROLE_LEVEL:
            raise HTTPException(status_code=400, detail="Noto‘g‘ri rol")
        login = str(form.get("login", "local-user")).strip() or "local-user"
        name = str(form.get("name", login)).strip() or login
        user = database.upsert_user(
            github_id=f"dev:{login}",
            login=login,
            display_name=name,
            email=None,
            avatar_url=None,
            role=role,
        )
        token, _ = database.create_session(user.id, hours=settings.session_hours)
        response = RedirectResponse(_safe_next(str(form.get("next", "/"))), status_code=303)
        response.set_cookie(
            "cpuz_session",
            token,
            max_age=settings.session_hours * 3600,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
        )
        return response

    @app.post("/auth/logout")
    async def logout(request: Request):
        require_user(request)
        form = await request.form()
        verify_csrf(request, str(form.get("csrf_token", "")))
        database.delete_session(request.cookies.get("cpuz_session"))
        response = RedirectResponse("/", status_code=303)
        response.delete_cookie("cpuz_session", path="/")
        return response

    @app.get("/edit/{article_path:path}")
    async def edit_article(request: Request, article_path: str):
        require_user(request)
        snapshot = service.snapshot(article_path)
        rendered = render_markdown(snapshot.document.body).html
        return render(
            request,
            "edit.html",
            article=snapshot.article,
            body=snapshot.document.body,
            preview=Markup(rendered),
            submit_url=f"/edit/{snapshot.article['path']}",
        )

    @app.post("/edit/{article_path:path}")
    async def submit_article(request: Request, article_path: str):
        user = require_user(request)
        form = await request.form()
        verify_csrf(request, str(form.get("csrf_token", "")))
        proposal_id = service.submit(
            article_path,
            str(form.get("body", "")),
            str(form.get("summary", "")),
            user,
        )
        return RedirectResponse(f"/proposals/{proposal_id}", status_code=303)

    @app.post("/preview/{article_path:path}")
    async def preview_article(request: Request, article_path: str):
        require_user(request)
        verify_csrf(request, request.headers.get("X-CSRF-Token"))
        payload = await request.json()
        body = str(payload.get("body", ""))
        rendered = service.preview(article_path, body)
        return JSONResponse({"html": rendered.html, "toc": [entry.__dict__ for entry in rendered.toc]})

    @app.get("/my-proposals")
    async def my_proposals(request: Request):
        user = require_user(request)
        proposals = database.list_proposals(submitter_id=user.id)
        for proposal in proposals:
            proposal["status_label"] = STATUS_LABELS.get(proposal["status"], proposal["status"])
            proposal["added"], proposal["removed"] = diff_stats(proposal["old_body"], proposal["new_body"])
        return render(request, "my_proposals.html", proposals=proposals)

    @app.get("/proposals/{proposal_id}")
    async def proposal_status(request: Request, proposal_id: int):
        proposal = database.get_proposal(proposal_id)
        if proposal is None:
            raise HTTPException(status_code=404, detail="Taklif topilmadi.")
        user = proposal_access(request, proposal)
        proposal["status_label"] = STATUS_LABELS.get(proposal["status"], proposal["status"])
        added, removed = diff_stats(proposal["old_body"], proposal["new_body"])
        return render(
            request,
            "proposal.html",
            proposal=proposal,
            added=added,
            removed=removed,
            can_revise=(proposal["status"] == "changes_requested" and user.id == proposal["submitter_user_id"]),
        )

    @app.post("/proposals/{proposal_id}/revise")
    async def revise_proposal(request: Request, proposal_id: int):
        proposal = database.get_proposal(proposal_id)
        if proposal is None:
            raise HTTPException(status_code=404, detail="Taklif topilmadi.")
        user = proposal_access(request, proposal)
        form = await request.form()
        verify_csrf(request, str(form.get("csrf_token", "")))
        service.revise(proposal, str(form.get("body", "")), str(form.get("summary", "")), user)
        return RedirectResponse(f"/proposals/{proposal_id}", status_code=303)

    @app.get("/moderation/")
    async def moderation_dashboard(request: Request, status: str = "pending"):
        require_user(request, "reviewer")
        selected = status if status in STATUS_LABELS else None
        proposals = database.list_proposals(status=selected)
        for proposal in proposals:
            proposal["status_label"] = STATUS_LABELS.get(proposal["status"], proposal["status"])
            proposal["added"], proposal["removed"] = diff_stats(proposal["old_body"], proposal["new_body"])
        manifest = service.manifest_for_listing()
        article_rows = []
        for item in articles(manifest):
            article_rows.append(
                {
                    "path": item["path"],
                    "title": item["translation"]["title"],
                    "technical": item["reviews"]["technical"]["status"],
                    "language": item["reviews"]["language"]["status"],
                    "upstream": item["upstream"]["status"],
                }
            )
        return render(
            request,
            "moderation.html",
            proposals=proposals,
            selected_status=selected or "all",
            article_rows=article_rows,
        )

    @app.get("/moderation/{proposal_id}")
    async def moderation_detail(request: Request, proposal_id: int):
        require_user(request, "reviewer")
        proposal = database.get_proposal(proposal_id)
        if proposal is None:
            raise HTTPException(status_code=404, detail="Taklif topilmadi.")
        snapshot = service.snapshot(proposal["article_path"])
        technical = snapshot.article["reviews"]["technical"]
        language = snapshot.article["reviews"]["language"]
        added, removed = diff_stats(proposal["old_body"], proposal["new_body"])
        current_user = getattr(request.state, "user")
        claim = proposal.get("claim")
        can_decide = current_user.role == "moderator"
        claim_owned = bool(
            claim is not None and int(claim["moderator_user_id"]) == current_user.id
        )
        claim_stale = _claim_is_stale(
            claim, timeout_minutes=settings.approval_claim_timeout_minutes
        )
        can_approve = can_decide and (claim is None or claim_owned or claim_stale)
        return render(
            request,
            "moderation_detail.html",
            proposal=proposal,
            rows=side_by_side(proposal["old_body"], proposal["new_body"]),
            added=added,
            removed=removed,
            article=snapshot.article,
            technical=technical,
            language=language,
            can_decide=can_decide,
            can_approve=can_approve,
            claim_owned=claim_owned,
            claim_stale=claim_stale,
        )

    @app.post("/moderation/{proposal_id}/decision")
    async def moderation_decision(request: Request, proposal_id: int):
        moderator = require_user(request, "moderator")
        proposal = database.get_proposal(proposal_id)
        if proposal is None:
            raise HTTPException(status_code=404, detail="Taklif topilmadi.")
        form = await request.form()
        verify_csrf(request, str(form.get("csrf_token", "")))
        action = str(form.get("action", ""))
        feedback = str(form.get("feedback", "")).strip() or None
        current_status = str(proposal["status"])
        if action == "reject":
            if current_status not in {"pending", "changes_requested"}:
                raise HTTPException(status_code=409, detail="Bu taklif endi rad etilishi mumkin emas.")
            database.moderate(
                proposal_id,
                status="rejected",
                moderator=moderator,
                feedback=feedback,
                event="rejected",
                expected_statuses=("pending", "changes_requested"),
            )
        elif action == "request_changes":
            if current_status != "pending":
                raise HTTPException(status_code=409, detail="Faqat pending taklif uchun o‘zgartirish so‘rash mumkin.")
            if not feedback:
                raise HTTPException(status_code=400, detail="O‘zgartirish so‘rash uchun izoh kiriting.")
            database.moderate(
                proposal_id,
                status="changes_requested",
                moderator=moderator,
                feedback=feedback,
                event="changes_requested",
                expected_statuses=("pending",),
            )
        elif action == "approve":
            if current_status != "pending":
                raise HTTPException(
                    status_code=409,
                    detail="Faqat pending taklif tasdiqlanishi mumkin.",
                )
            database.claim_proposal(
                proposal_id,
                moderator=moderator,
                takeover_after_minutes=settings.approval_claim_timeout_minutes,
            )
            try:
                applied = service.apply_proposal(proposal, moderator)
            except ProposalConflict as exc:
                database.finish_claim(
                    proposal_id,
                    status="conflict",
                    moderator=moderator,
                    feedback=str(exc),
                    applied_ref=None,
                    applied_url=None,
                    applied_pr_number=None,
                    applied_commit_sha=None,
                    event="conflict_detected",
                )
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            except BaseException as exc:
                database.release_claim(
                    proposal_id,
                    moderator=moderator,
                    reason=f"Approval failed before completion: {type(exc).__name__}",
                )
                raise
            database.finish_claim(
                proposal_id,
                status=applied.status,
                moderator=moderator,
                feedback=feedback,
                applied_ref=applied.ref,
                applied_url=applied.url,
                applied_pr_number=applied.pull_request_number,
                applied_commit_sha=applied.commit_sha,
                event="approved",
            )
        else:
            raise HTTPException(status_code=400, detail="Noto‘g‘ri moderatsiya amali.")
        return RedirectResponse(f"/moderation/{proposal_id}", status_code=303)

    @app.get("/moderation/article/{article_path:path}")
    async def article_review_page(
        request: Request,
        article_path: str,
        applied: str | None = None,
        result_url: str | None = None,
    ):
        require_user(request, "reviewer")
        snapshot = service.snapshot(article_path)
        body_hash = snapshot.document.body_sha256
        applied_result = (
            applied if applied in {"applied", "approved_pending_merge"} else None
        )
        return render(
            request,
            "article_review.html",
            article=snapshot.article,
            body_hash=body_hash,
            stage=workflow_stage(snapshot.article, body_hash),
            technical_effective=effective_review_status(snapshot.article, "technical", body_hash),
            language_effective=effective_review_status(snapshot.article, "language", body_hash),
            applied_result=applied_result,
            applied_url=_safe_github_result_url(
                result_url, repository=settings.github_repository
            ),
        )

    @app.post("/moderation/article/{article_path:path}/review")
    async def article_review_action(request: Request, article_path: str):
        reviewer = require_user(request, "reviewer")
        form = await request.form()
        verify_csrf(request, str(form.get("csrf_token", "")))
        review_type = str(form.get("review_type", ""))
        status = str(form.get("status", ""))
        notes = str(form.get("notes", "")).strip() or None
        result = service.set_review(
            article_path,
            review_type=review_type,
            status=status,
            reviewer=reviewer,
            notes=notes,
        )
        query = {"applied": result.status}
        if result.url:
            query["result_url"] = result.url
        return RedirectResponse(
            f"/moderation/article/{article_path}?{urlencode(query)}",
            status_code=303,
        )

    web_static = settings.repo_root / "web" / "static"
    app.mount("/editor-assets", StaticFiles(directory=web_static), name="editor-assets")
    # Mount last so application routes win. In local development this serves the
    # built public site and editor from one origin.
    app.mount("/", StaticFiles(directory=settings.repo_root / "site", html=True), name="site")
    return app


app = create_app()
