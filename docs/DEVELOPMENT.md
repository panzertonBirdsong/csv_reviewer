# Developer guide

## Branches and structure

See [BRANCHES.md](BRANCHES.md) for the two independently cloned applications.
`main` at `988bca0` contains the original job workspace, which is preserved on
`codex/job-search`. This branch adapts that base to the FlowSell tracker.

- `csv_reviewer.py`: Streamlit entry point.
- `review_app.py`: open screen, table and row views, filters, create page, deletion
  confirmation, session state, and guarded persistence.
- `issue_reviews.py`: required schema, validation, defaults, immutable identity and
  creation dates, modified-date policy, and filtering. No UI dependency.
- `csv_store.py`: UTF-8 CSV/TSV parsing, string-preserving serialization, fingerprints,
  advisory locking, backup writing, and atomic replacement.
- `tests/test_reviews.py`: schema and lifecycle invariants, delimiter round trips,
  dates, filtering, backups, and stale-write refusal.
- `tests/test_review_app.py`: Streamlit AppTest workflows on synthetic files,
  including creation, validation failures, editing, filtering, empty files, deletion,
  I/O failure, and stale-write refusal for all mutation types.
- `tests/test_csv_store.py`: original parser and verification helper checks.

## Data contract

The CSV is the source of truth. Import does not coerce numbers, dates, or identifiers.
The ordered headers drive all row serialization, including unknown extra columns.
Opening validates required fields and unique IDs, then fingerprints the original
bytes without writing. No actual FlowSell findings are checked into this repository.

IDs are stable across edits. New IDs use a random 12-character suffix and are checked
against current rows. New entries receive the posting date for created and modified
dates. Changed edits preserve creation dates and refresh modified dates. No-op saves
leave all bytes unchanged. Source provenance and severity are not inferred on save.

Persistence writes before mutating session rows, the fingerprint, or navigation.
Each changed write uses a distinct backup path, including deletion. A failed write
leaves session data and form values available for retry. Backup creation may succeed
even if the final replacement fails. The retained snapshot is still valid.

Navigation uses stable IDs, never just a table position. A pending delete binds to
the displayed ID and is cancelled on navigation. Table selections map through the
current filtered index list. The creation page is routed before the empty-result
guard so an empty tracker is still usable.

The save helper uses POSIX `fcntl` advisory locking. This version targets macOS/Linux.
Writers must cooperate with the lock for full serialization; unrelated external
writers can still race inside the compare/replace window. This is a local single-user
tool, not a database or authenticated network service.

## Run checks

```sh
conda activate csv_viewer
python -m unittest discover -s tests
python -m pip check
python -m streamlit run csv_reviewer.py --server.address 127.0.0.1 --server.port 8502 --browser.gatherUsageStats false
```

UI tests use temporary directories and synthetic data. Never test create/delete on
the live master. For a browser smoke test, use a temporary copy and enter that copy's
path on the opening screen. Delete confirmation uses a callback so the next render
starts with the updated dataset, including the empty-file case.
