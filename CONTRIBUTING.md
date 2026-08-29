# Contributing to CP.UZ Algoritmlar

## Browser contributors

1. Open an article and choose **Tahrirlashni taklif qilish**.
2. Sign in with GitHub.
3. Edit only the Markdown body. Metadata and front matter are managed by the system.
4. Check the sanitized preview and add a concise change summary.
5. Submit the proposal and follow its status under **Takliflarim**.
6. A moderator may approve, reject, or request a revision. Nothing is published immediately.

Do not change fenced code, formulas, link targets, anchors, tables, or asset paths unless that is the intended correction and it has been checked against the pinned upstream source.

## Repository contributors

Canonical article prose is under `docs/`. Canonical mutable metadata is only in `data/articles.yml`. Never hand-edit `data/articles.json`, `data/review_queue.csv`, `site/`, or `MANIFEST.sha256`.

```bash
# edit prose
code docs/algebra/binary-exp.md

# record a review decision
python scripts/review.py approve algebra/binary-exp.md \
  --type technical --reviewer "Your Name"

# regenerate and verify
make check
```

A full translation must preserve the upstream article’s technical meaning, preconditions, complexity, code, formulas, links, and attribution. Use `data/glossary.yml` consistently. A synopsis must not be relabeled as a full translation without translating and reviewing the complete source.

Technical review must precede language review. A changed article or changed upstream source invalidates current approvals but preserves their audit history.

All article adaptations are contributed under CC BY-SA 4.0. Tooling contributions are under the repository’s MIT code license.
