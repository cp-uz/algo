# Architecture

## Source-of-truth boundary

```text
docs/**/*.md                       data/articles.yml
(canonical Uzbek Markdown)         (canonical mutable metadata)
              \                    /
               \                  /
                scripts/build_static.py
                         |
        +----------------+------------------+
        |                |                  |
 data/articles.json  data/review_queue.csv  site/**/*.html/assets
        |                |                  |
        +----------------+------------------+
                         |
                  MANIFEST.sha256
```

`docs/` is never generated. Each article has minimal front matter:

```yaml
---
article_id: algebra--binary-exp
---
```

Mutable review fields are forbidden in Markdown front matter. `cpuz.build.build_repository` records hashes for every file under `docs/` before rendering, stages the site in a temporary directory, and checks the hashes again before and after atomically replacing generated output.

## Canonical metadata

`data/articles.yml` is schema version 2 and is validated by `data/schema/articles.schema.json` plus cross-field invariants in `cpuz/metadata.py`. Each article records:

- stable identity, path and generated route;
- upstream title, URL, source path, repository, commit, license and optional source hash;
- translation title/scope/fidelity/status and translator information;
- upstream comparison state;
- publication state;
- structured technical and language review records;
- append-only `review_history`.

`data/articles.json` and `data/review_queue.csv` are compatibility/reporting views generated from YAML and the current Markdown body hash.

## Review state machine

Effective stages are calculated, not manually duplicated:

```text
technical_review_pending
  ├─ technical changes requested -> technical_changes_requested
  └─ technical approved          -> language_review_pending
                                      ├─ language changes requested
                                      │    -> language_changes_requested
                                      └─ language approved
                                           -> ready_to_publish
                                           -> published (explicit action)
```

Additional states:

- `needs_re_review` — a stored approval does not match the current content hash or source commit;
- `upstream_changed` — the cp-algorithms source changed after the recorded translation version;
- `upstream_missing` — the source path is absent at the compared commit;
- `deprecated` — article intentionally retired.

Rules:

- Language approval or language changes-requested requires a current technical approval.
- Every non-pending decision records reviewer, UTC timestamp, article body SHA-256 and source commit.
- Resetting technical review invalidates language review.
- Editing article content resets both current review records, returns publication to draft, and appends invalidation/history events.
- Upstream changes preserve Uzbek Markdown, mark translation as needing retranslation, and return publication to draft.
- Previous decisions are retained in `review_history`.

## Rendering and safety

Markdown rendering uses Mistune, Pygments and Bleach. Mathematical delimiters are protected during Markdown parsing and rendered with MathJax. Generated HTML is sanitized; scripts, event handlers, unsafe URL schemes and arbitrary style attributes from article Markdown are removed. Fenced code is syntax highlighted on a light gray background and safely escapes `<`, `>`, and `&`.

The validator checks schema and state invariants, document registration, generated JSON/CSV, a deterministic rebuild of `site/`, local links and fragments, assets, code escaping/sanitization, design tokens, source fidelity where pinned snapshots exist, and the checksum manifest.

## Web service

The editor is a small FastAPI service with SQLite storage:

- GitHub OAuth identifies contributors and roles.
- Sessions are random opaque tokens; only their SHA-256 digests are stored server-side.
- Session cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` in production.
- Every state-changing authenticated form/API call uses a per-session CSRF token.
- Request sizes and per-user submission rates are bounded.
- Proposals store immutable base text/hash, proposed text, author, timestamps, summary, decision data, and append-only events.
- Approval checks the base hash again before applying, preventing stale proposals from overwriting newer article content.
- A database-backed approval claim prevents two moderators from applying the same proposal concurrently. The same moderator may retry safely; an abandoned claim can be taken over only after the configured timeout.
- GitHub operations use deterministic branch names and compare requested files with the base branch, so retries after a crash, merge, or branch deletion do not create duplicate pull requests.
- A signed GitHub pull-request webhook moves proposals from `approved_pending_merge` to their final `applied` or `rejected` state and rejects replayed delivery IDs.
- Local metadata reads use an inode/size/timestamp keyed cache. Every caller receives a copy, article Markdown is read directly, and external atomic manifest writes invalidate the cache automatically.
- Self-approval is disabled by default.

Production must use `github_pr` or `github_direct`; local filesystem application is restricted to development/test. `github_pr` is recommended because branch protection and normal pull-request review remain in force.

## Generated files in Git

Generated outputs are ignored by Git. They are included in release ZIPs and local builds, but GitHub Pages CI always regenerates them from canonical inputs. This prevents pull requests created by the editor from having to commit hundreds of HTML files and eliminates stale generated metadata from the repository history.
