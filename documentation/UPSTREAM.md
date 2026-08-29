# Upstream synchronization

The cp-algorithms source version is recorded per article and the shared baseline is in `UPSTREAM_PIN`. The `source.file` value such as `src/algebra/binary-exp.md` is the path inside the upstream cp-algorithms repository; it is not a local CP.UZ `src/` directory.

## Fetch pinned snapshots

```bash
make fetch
```

This downloads exact English Markdown into `upstream/src/`. It never writes `docs/`.

## Compare a newer upstream commit

```bash
make upstream-check TO_COMMIT=<full-40-character-sha>
```

Dry run output is written to `reports/upstream-sync-<old>-<new>.json` and `.md`. No canonical file changes.

After inspecting the report:

```bash
make upstream-check TO_COMMIT=<full-40-character-sha> APPLY=1
```

Changed articles are marked `upstream_changed`/`needs_retranslation`; missing paths are marked `upstream_missing`. Existing Uzbek Markdown is preserved byte-for-byte. Current publication/review status becomes stale/draft through metadata rather than by replacing prose.

For deterministic offline tests, provide GitHub compare JSON and a directory containing target `src/` files:

```bash
python scripts/sync_upstream.py \
  --to-commit <sha> \
  --compare-json fixtures/compare.json \
  --source-dir fixtures/target-src
```

A network failure aborts synchronization. Only an actual HTTP 404 or missing offline source is treated as a missing upstream article.

## Incorporating an upstream change

1. Review the old and new English sources.
2. Manually update the existing Uzbek file under `docs/`; never regenerate it wholesale over human edits.
3. Update the accepted source version through the maintained synchronization/migration process.
4. Obtain new technical and language reviews.
5. Build and validate.

Review history from the previous version remains in `review_history`.
