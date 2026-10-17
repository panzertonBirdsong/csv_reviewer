# Developer guide

## Structure

- `csv_reviewer.py`: Streamlit opening screen, table viewer, dynamic record editor, filters, navigation, and session state.
- `csv_store.py`: CSV/TSV detection, parsing, serialization, verification normalization, atomic writes, session backups, and guarded saves. This module uses only Python's standard library.
- `job_applications.py`: job schema recognition, history-based queue classification, dated status updates, document preview/download, answer blocks, and the application workspace.
- `tests/test_job_applications.py`: tab-delimited round trips, backups, stale-write refusal, duplicate history, document handling, and end-to-end application UI tests.
- `requirements.txt`: pinned installed libraries. Streamlit provides the UI; pandas supplies the table representation while all values are explicitly kept as strings.
- `tests/test_csv_store.py`: verification's four opening cases, value round trips, and malformed input rejection.
- `tests/test_app.py`: temporary-file UI tests using Streamlit AppTest, including opening choices, editing, navigation, verification, table display, and source preservation.

## Data flow

Opening reads UTF-8 CSV bytes into ordered headers and a list of dictionaries of strings. The verification choice is applied once before the output copy is written. Session state retains the dataset, output path, current row index, and form revision. Search and verification filters compute matching source indices without reordering data.

The record form submits a replacement dictionary for one row. The replacement dataset is persisted before it becomes the active session dataset. On failure, the form stays available for retry. Saving increments the form revision to refresh widgets with saved values. Field widget keys use row and column indices rather than user-controlled column labels.

Table rendering uses saved records only. It does not perform numeric or date inference. The generic editor gives `verified` checkbox semantics. Job mode recognizes the nine existing JobSearch columns without adding fields. Status changes prepend dated history to `submitted`. Classification uses the leading entry so old duplicate or rejection evidence cannot override a newly recorded status. Packet paths may be absolute or relative to the tracker. HTTP/HTTPS employer links and explicit local file-open buttons are used; nothing is submitted to an employer.

## Development commands

Run from the project root:

```sh
conda activate csv_viewer
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python -m pip check
python -m streamlit run csv_reviewer.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

Tests use temporary directories and do not change project CSV files. After intentionally changing dependencies, regenerate the pinned library list with `python -m pip freeze > requirements.txt` and rerun checks.

## Design boundaries

CSV parsing deliberately avoids type conversion. Files must have unique nonempty headers and consistent widths. Serialization preserves cell values and column order but normalizes CSV formatting. Saves are atomic replacements. A SHA-256 fingerprint from the opened bytes rejects stale saves; a per-path advisory lock serializes saves from cooperating app sessions. An external writer that ignores this lock could still race within the comparison/replacement window, so avoid simultaneous outside writes. A unique per-session backup captures the original file before its first changed save. All rows reside in memory, and each save serializes all rows.

The app discovers CSV/TSV files next to the script and accepts local paths or uploads. Job mode opens the selected tracker in place; generic review creates a separate output copy. The default tracker path is built from Path.home(). The repository's included CSV is just a selectable input, never a schema definition or required startup dependency. The app can start with no CSV files in its directory and use an upload instead.
