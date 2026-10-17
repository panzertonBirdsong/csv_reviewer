# FlowSell CSV Reviewer

A local workspace for the FlowSell code-review backlog. This is the
`codex/flowsell-review` branch. The original job application workflow is preserved
on `codex/job-search`; see [Branches and local workspaces](docs/BRANCHES.md).

## Start

```sh
cd ~/Projects/tools/csv-reviewer-flowsell
conda activate csv_viewer
python -m streamlit run csv_reviewer.py --server.address 127.0.0.1 --server.port 8502 --browser.gatherUsageStats false
```

Open <http://localhost:8502>, then **Open review CSV**. The path defaults to
`~/Projects/FlowSell/code_review/summary.csv` and can be changed before opening.
For a new environment, create it with `conda create --name csv_viewer python=3.12 pip -y`
and install with `python -m pip install -r requirements.txt` after activating it.

- **Review row:** browse by ID and title, edit fields, and save or save-and-advance.
- **Table viewer:** inspect matching records, select one to review, or show every column.
- **Post new row:** opens a page to add an issue or todo, with an automatic unique ID and dates.
- **Delete row:** available on a row view, with explicit confirmation and a backup of the previous CSV.
- Filter by type, severity, priority, status, category, or owner. Search includes every field.

Opening never writes. Saves update the selected master CSV directly, preserving all
columns, string values, and the comma or tab delimiter. Each changed save backs up
the previous contents and checks for outside changes before replacing the file.

IDs and creation dates are fixed during editing. Changed saves update
`last_modified_date`; no-op saves leave the file and dates alone. Dates use
`America/New_York`, configurable through `CSV_REVIEWER_TIMEZONE`.
`FLOWSELL_REVIEW_CSV` overrides the default path.

See [User guide](docs/USER_GUIDE.md) for creation, deletion, and recovery, and
[Developer guide](docs/DEVELOPMENT.md) for tests and data contracts.

```sh
python -m unittest discover -s tests
```

Tests use synthetic temporary CSVs. The application repository does not include the
FlowSell review data or job application materials.
