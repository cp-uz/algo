# Migration from the legacy review package

The repository has already been migrated to metadata schema version 2. The migration performed these operations:

- preserved all Uzbek article prose;
- replaced mutable front-matter mirrors with stable `article_id` only;
- moved review/publication/upstream state into `data/articles.yml`;
- removed the machine-generated “Tarjima holati” header and attribution footer from Markdown because they are rendered by the page template;
- generated JSON/CSV/site/checksums from canonical inputs;
- initialized structured pending review records and retained existing translators/source metadata.

The migration script is `scripts/migrate_metadata_v2.py`. It creates external safety copies before changing files and refuses to re-migrate schema version 2.

## One-time Git cleanup

Generated files are now ignored. In an existing clone where they were previously tracked, run once:

```bash
git rm -r --cached site
git rm --cached data/articles.json data/review_queue.csv MANIFEST.sha256
git add .gitignore
git commit -m "Stop tracking generated CP.UZ site artifacts"
```

Do not delete local generated output when preparing a release ZIP; `make build` recreates it.

## Verification

```bash
make check
```

The validator rejects legacy mutable front-matter keys, missing articles, schema violations, stale generated representations, invalid review transitions, broken links/assets, unsafe renderer output, and checksum differences.
