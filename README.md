# CSV Reviewer

This is the `codex/job-search` branch. See [Branches and local workspaces](docs/BRANCHES.md)
for separate launch commands and the FlowSell review version.

A local job-application workspace and general-purpose CSV/TSV viewer and editor. Open any UTF-8 CSV with a header row, browse its table, search records, and edit one record at a time. Column names and counts come from your file; no particular dataset or schema is required.

See the [User guide](docs/USER_GUIDE.md) for workflows, supported files, and troubleshooting, and the [Developer guide](docs/DEVELOPMENT.md) for architecture and testing.

## Job applications

Launch the app and choose **Job applications → Open job tracker**. The default is `~/Documents/JobSearch/table.csv`; you can choose another tracker path. Opening does not change the file. Job mode saves progress directly to that tracker, preserves its column order and delimiter, and creates a backup before the first change in each session.

- Filter **To apply**, **Possible duplicate**, **Applied / outcomes**, **On hold**, or **Skipped**; search by company, role, or location.
- **Open application** opens the employer’s website. Preview or download the tailored résumé, open the materials folder, and copy individual answer drafts.
- Read **Job notes** for eligibility gaps and email history. Possible duplicates remain a separate queue.
- After you submit on the employer’s website, click **Mark submitted & next**. Other statuses and notes use **Save status**. New status entries retain the earlier history in the existing `submitted` column.
- **Record editor** remains available for all nine tracker fields; **Table viewer** shows the filtered records.

Click **Not going to submit & next**, between **Save & Next** and **Mark submitted & next**, to save that status and advance. This removes the job from **To apply** while preserving its history. You can also choose the status in **Update status** and save. The **Not going to submit** queue lets you revisit those jobs.

The app does not submit applications. Saves check for outside changes and refuse stale overwrites. **Reload saved file** refreshes the tracker. Backups are under `.csv-reviewer-backups` beside the tracker.

## Setup and launch

```sh
conda create --name csv_viewer python=3.12 pip -y
conda activate csv_viewer
python -m pip install -r requirements.txt
python -m streamlit run csv_reviewer.py --server.address 127.0.0.1
```

Open the localhost URL printed by Streamlit. For general CSV review, select **Project folder**, **Local file**, or **Upload CSV**. Choose **Yes** or **No** for the `verified` column before opening:

| Choice | Column exists | Result |
| --- | --- | --- |
| Yes | Yes | Preserve the existing column and values |
| Yes | No | Add `verified`, initialized to `false` |
| No | Yes | Preserve the existing column and values |
| No | No | Do not add the column |

Choose a new output filename. The app creates a separate reviewed copy immediately and never overwrites an existing file when opening. To resume later, select the reviewed CSV as the source and choose another output filename.

Edit any field and use **Save**, **Save & Previous**, **Save & Next**, or **Verify & Next**. Each action atomically saves the entire reviewed copy. The last action marks the current row verified when that column exists. Filtering and downloading operate on saved records; save the current form before changing filters or opening another file. Unsaved form edits are not persisted when the app closes.

Choose **Table viewer** in the sidebar for a searchable overview, or **Record editor** to edit. **Go to record** jumps to any matching record. Editors adapt to the value's length and line breaks; enable **Use multiline editors for all fields** to write multiline text in any column.

The app preserves strings (including leading zeroes and empty values), commas, quotes, and embedded newlines using Python's CSV parser. Existing verified values `true`, `yes`, `1`, `y`, and `verified` are recognized without regard to case. Other values count as unverified and remain unchanged unless toggled or explicitly verified. CSV quoting and line endings may be normalized on save.

Streamlit provides the interface and streamlit-pdf provides the in-app résumé preview. All installed library versions, including its dependencies, are pinned in `requirements.txt`. CSV handling uses the Python standard library.

## Checks

```sh
python -m unittest discover -s tests
```
