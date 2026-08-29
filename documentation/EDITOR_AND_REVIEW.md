# Editing and review workflows

## A. Translator or reviewer using VS Code

Article prose lives under `docs/<category>/<article>.md`. Edit the Markdown body and keep the single managed `article_id` front-matter key unchanged.

```bash
code docs/algebra/binary-exp.md
```

To record review status:

```bash
# approve technical review
python scripts/review.py approve algebra/binary-exp.md \
  --type technical --reviewer "Reviewer Name" --notes "Checked proof and code."

# request technical changes
python scripts/review.py request-changes algebra/binary-exp.md \
  --type technical --reviewer "Reviewer Name" --notes "Correct the overflow note."

# approve language review after technical approval
python scripts/review.py approve algebra/binary-exp.md \
  --type language --reviewer "Language Reviewer"

# deliberately reset a review
python scripts/review.py pending algebra/binary-exp.md \
  --type technical --reviewer "Reviewer Name" --notes "New implementation added."
```

Publication is explicit:

```bash
python scripts/review.py publish algebra/binary-exp.md --actor "Maintainer"
python scripts/review.py unpublish algebra/binary-exp.md --actor "Maintainer"
```

Build and validate:

```bash
make build
make validate
# or the complete CI sequence
make check
```

Preview locally:

```bash
make serve   # read-only static site
make dev     # static site plus editor/moderation service
```

Commit canonical files and ordinary project changes. Generated outputs are ignored:

```bash
git add docs/algebra/binary-exp.md data/articles.yml
git commit -m "Review Uzbek binary exponentiation article"
git push
```

## B. Website contributors

1. Open the public article.
2. Select **Tahrirlashni taklif qilish**.
3. Sign in with GitHub.
4. Edit Markdown in the left pane and inspect the sanitized live preview on the right.
5. Add an optional summary and submit.
6. The proposal is stored in SQLite with the exact base article hash; the public article remains unchanged.
7. Follow decisions under **Takliflarim**. When changes are requested, revise the same proposal and resubmit it.

## C. Reviewers and moderators

The dashboard at `/moderation/` shows pending proposals and the article review queue.

A proposal page displays old/new text side by side, added/removed line counts, proposer identity, submission time, summary, current article review state, and the full proposal event log.

- **Reviewer** role can inspect proposals and manage technical/language review records.
- **Moderator** role can additionally approve, reject, or request changes on edit proposals.
- Approval is refused when the article changed since submission or when the moderator is the submitter.
- Starting approval creates an exclusive database claim. A second moderator cannot race an in-progress approval; the original moderator can retry an interrupted operation, and stale claims can be recovered after the configured timeout.
- In `github_pr` mode, approval creates a branch and pull request and the proposal is labeled as awaiting merge.
- A verified GitHub webhook marks the proposal accepted after merge, or rejected if the pull request is closed without merge.
- In local development, approval atomically writes the Markdown and metadata, then rebuilds when `CPUZ_AUTO_BUILD=true`.

Use `/moderation/article/<article-path>` to set technical/language status. The same transition rules as the CLI are enforced. In GitHub modes the dashboard creates a dedicated metadata pull request and displays its link and pending-merge state; in local mode it confirms that the canonical metadata was applied immediately.

## D. Binary Exponentiation test scenario

`tests/test_web_workflow.py` exercises `docs/algebra/binary-exp.md` end to end: submit, verify no immediate publication, request changes, revise, approve, update canonical Markdown, approve both reviews, rebuild, verify rendered content and generated state, and reject a second proposal without changing the article.
