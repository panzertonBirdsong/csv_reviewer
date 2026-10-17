# Job search and FlowSell workspaces

This repository has two independently usable branches:

| Branch | Local checkout | Purpose | Default port |
| --- | --- | --- | --- |
| `codex/job-search` | `~/Projects/tools/csv-reviewer-jobs` | Job applications, résumé previews, answer drafts, and application history | 8501 |
| `codex/flowsell-review` | `~/Projects/tools/csv-reviewer-flowsell` | FlowSell issues and todos, including creating and deleting rows | 8502 |

Both start from `988bca0`, which preserves the existing job-search changes on `main`.
The job-search branch adds this usage documentation without changing the saved application behavior.

## Install

The existing `csv_viewer` Conda environment can run both versions. On a new computer:

```sh
conda create --name csv_viewer python=3.12 pip -y
conda activate csv_viewer
python -m pip install -r requirements.txt
```

Each branch includes its requirements. Run installation from the checkout you intend to use.

## Run job search

```sh
cd ~/Projects/tools/csv-reviewer-jobs
conda activate csv_viewer
python -m streamlit run csv_reviewer.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

Open <http://localhost:8501>. Select **Job applications**, then **Open job tracker**.
The default tracker is `~/Documents/JobSearch/table.csv`; another path can be entered.
Use the existing application queues, résumé and answer previews, status history, and general CSV editor.
See [the user guide](USER_GUIDE.md) for the workflow on this branch.

## Run FlowSell review

```sh
cd ~/Projects/tools/csv-reviewer-flowsell
conda activate csv_viewer
python -m streamlit run csv_reviewer.py --server.address 127.0.0.1 --server.port 8502 --browser.gatherUsageStats false
```

Open <http://localhost:8502>. The default CSV is
`~/Projects/FlowSell/code_review/summary.csv`. Use **Open review CSV** to load it.
Opening is read-only. Saving, posting, and deleting update the selected CSV directly with
backups and stale-write protection. **Post new row** opens the creation page;
**Delete row** on a row view asks for confirmation before removal.
The FlowSell branch's [user guide](https://github.com/panzertonBirdsong/csv_reviewer/blob/codex/flowsell-review/docs/USER_GUIDE.md)
describes fields, filters, dates, and recovery.

Both apps can run at the same time on their separate ports. Stop each terminal with Control+C.
Keep the trackers outside these checkouts. Job data and the FlowSell master CSV are not copied
into the application repository by this setup.

## Recreate the separate checkouts

```sh
mkdir -p ~/Projects/tools
git clone --single-branch --branch codex/job-search git@github.com:panzertonBirdsong/csv_reviewer.git ~/Projects/tools/csv-reviewer-jobs
git clone --single-branch --branch codex/flowsell-review git@github.com:panzertonBirdsong/csv_reviewer.git ~/Projects/tools/csv-reviewer-flowsell
```

Update a clean checkout with `git pull --ff-only` from inside its directory.
Commit local changes before updating. You do not need to switch branches in the original
`~/Projects/csv_reviewer` checkout to run either tool.
