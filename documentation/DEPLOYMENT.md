# Deployment

The production design has two independently deployable parts:

1. **Public static site** — GitHub Pages, built from canonical repository files by `.github/workflows/pages.yml`.
2. **Editor/moderation service** — one FastAPI instance with persistent SQLite storage and GitHub OAuth/API credentials.

The public article’s edit button points to the editor origin through the `CPUZ_EDITOR_BASE_URL` GitHub Actions repository variable.

## 1. GitHub Pages

In the `cp-uz/algo` repository:

1. Enable **Settings → Pages → Source: GitHub Actions**.
2. Add the Actions variable `CPUZ_EDITOR_BASE_URL`, for example `https://algo-editor.cp.uz`.
3. Push to `main`. The Pages workflow installs dependencies, builds, tests, validates, and deploys `site/`.

Generated `site/`, JSON/CSV and checksum files are not required in Git. CI always creates a clean deploy artifact.

## 2. Create a GitHub OAuth App

Create an OAuth App owned by the CP-UZ organization/account:

- Homepage URL: the editor origin, for example `https://algo-editor.cp.uz`
- Authorization callback URL: `https://algo-editor.cp.uz/auth/github/callback`

Save the client ID and client secret only in the editor service’s secret manager.

## 3. Repository token

Create a fine-grained token or GitHub App installation token scoped only to `cp-uz/algo`.

For recommended `CPUZ_APPLY_MODE=github_pr`, grant repository contents read/write and pull requests read/write. For `github_direct`, contents read/write is required and branch protection must permit the token; direct mode is not recommended.

The token is used only by the backend. It is never included in static HTML or frontend JavaScript.

## 4. Environment variables

Copy `.env.example` and set real values in the platform secret manager. Required production values:

| Variable | Purpose |
|---|---|
| `CPUZ_ENV=production` | Disables development login and enables production checks/headers |
| `CPUZ_PUBLIC_URL` | HTTPS editor origin, no trailing slash |
| `CPUZ_DATABASE_PATH` | Persistent SQLite path, normally `/data/proposals.sqlite3` |
| `CPUZ_GITHUB_CLIENT_ID` | OAuth App client ID |
| `CPUZ_GITHUB_CLIENT_SECRET` | OAuth App secret |
| `CPUZ_GITHUB_TOKEN` | Server-side repository write token |
| `CPUZ_GITHUB_WEBHOOK_SECRET` | At least 32 random bytes; verifies GitHub pull-request webhook signatures |
| `CPUZ_GITHUB_REPOSITORY` | `cp-uz/algo` |
| `CPUZ_GITHUB_BASE_BRANCH` | Normally `main` |
| `CPUZ_APPLY_MODE` | `github_pr` recommended, or `github_direct` |
| `CPUZ_MODERATOR_GITHUB_LOGINS` | Comma-separated moderator logins; at least one is required |

Optional controls:

- `CPUZ_REVIEWER_GITHUB_LOGINS`
- `CPUZ_CONTRIBUTOR_GITHUB_LOGINS` (empty means any authenticated GitHub user may propose edits)
- `CPUZ_ALLOWED_GITHUB_ORG`
- `CPUZ_SESSION_HOURS` (default 24)
- `CPUZ_MAX_PROPOSAL_BYTES` (default 524288)
- `CPUZ_MAX_WEBHOOK_BYTES` (default 2097152)
- `CPUZ_SUBMISSIONS_PER_HOUR` (default 12)
- `CPUZ_APPROVAL_CLAIM_TIMEOUT_MINUTES` (default 15; allows recovery of abandoned approvals)
- `CPUZ_ALLOW_SELF_APPROVAL=false`
- `CPUZ_COOKIE_SECURE=true` (required in production)

## 5. Configure the GitHub webhook

In the `cp-uz/algo` repository, create a repository webhook with:

- Payload URL: `https://algo-editor.cp.uz/webhooks/github` (replace the origin with `CPUZ_PUBLIC_URL`)
- Content type: `application/json`
- Secret: exactly the value of `CPUZ_GITHUB_WEBHOOK_SECRET`
- Events: **Pull requests** only
- Active: enabled

The service accepts only signed `pull_request` `closed` events for the configured repository and base branch. Delivery IDs are stored for 30 days to prevent replay. A merged PR finalizes the proposal as accepted; a PR closed without merge finalizes it as rejected. The endpoint has its own bounded request-size limit and does not use browser sessions or CSRF because authenticity comes from the HMAC signature.

## 6. Docker deployment

```bash
cp .env.example .env
# edit .env; never commit it
docker compose up --build -d
```

The service listens on port 8000 and stores SQLite data in the named `cpuz-editor-data` volume. Deploy behind an HTTPS reverse proxy. Run exactly one application worker when using SQLite; horizontal scaling requires replacing the proposal store with a shared transactional database.

Health check:

```text
GET /healthz
```

## 7. Backups

Back up the persistent database volume regularly. The repository helper creates a consistent SQLite backup and a JSON export:

```bash
CPUZ_DATABASE_PATH=/data/proposals.sqlite3 \
python scripts/backup_proposals.py --output /secure/backups
```

Copy the resulting timestamped directory to off-host storage. Test restoration periodically by starting a disposable service against the copied SQLite file.

## 8. How approved edits reach production

In `github_pr` mode:

1. Moderator approval creates a branch and PR containing only the canonical Markdown and `data/articles.yml` changes.
2. Normal branch protection/CI reviews the PR.
3. A maintainer merges it.
4. The signed pull-request webhook marks the proposal as applied when GitHub reports the merge.
5. The push to `main` triggers Pages CI, which rebuilds all generated files and deploys the updated article.

The moderation dashboard truthfully labels the proposal **Pull request birlashtirilishi kutilmoqda** and links to the PR. The database remains the audit record for submission/moderation; GitHub is the canonical merge/deployment record.

## 9. Approval recovery

Before applying an edit, a moderator acquires an exclusive SQLite claim. A retry by that same moderator is idempotent. Another moderator sees the active owner and cannot approve, reject, or request changes until the claim is released. If the process died, the second moderator may retry after `CPUZ_APPROVAL_CLAIM_TIMEOUT_MINUTES`; deterministic GitHub branch/PR handling prevents duplicate side effects.

## 10. Operational security

- Terminate TLS before the app and preserve the original HTTPS scheme/host.
- Keep OAuth and repository tokens in a managed secret store.
- Generate the webhook secret independently from OAuth and repository credentials, and rotate it in GitHub and the service together.
- Restrict moderator and reviewer logins explicitly.
- Keep `CPUZ_ALLOW_SELF_APPROVAL=false`.
- Apply GitHub branch protection to `main` and require the validation workflow.
- Do not expose `/data`, `.env`, or the SQLite file through the reverse proxy.
- Rotate credentials after staff changes or suspected exposure.
