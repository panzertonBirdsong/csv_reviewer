# FlowSell review: user guide

## Open the master tracker

Start the FlowSell checkout using the command in the [README](../README.md).
Use port 8502 if the job-search version is also running on 8501.

1. Check **Review CSV path**. It defaults to `~/Projects/FlowSell/code_review/summary.csv`.
2. Click **Open review CSV**. Opening reads the file without modifying it or adding columns.
3. Confirm the **Saving to** path in the sidebar before editing.

This branch edits the selected file directly. It does not create a separate reviewed
copy. To experiment, first copy the CSV and open the copy. The dated original reports
and `issue_summary.csv` are separate artifacts and are not changed by editing the master.

The app accepts UTF-8 CSV or TSV, with or without a BOM. Headers must be unique and
nonempty, and all rows must have the header's width. Required fields are `issue_id`,
`type`, `title`, `description`, `severity`, `priority`, `status`, `created_date`, and
`last_modified_date`. IDs must be unique and nonempty, and type must be `issue` or
`todo`. Extra columns remain present and editable. Header-only files are supported.

## Find and review records

Search scans every saved field, including source references and comments. Each
filter can contain several values. Values within a filter are alternatives;
different filters are combined. Empty filter selections mean all values.

**Go to row** displays both the stable ID and title. **Table viewer** shows the main
tracking fields and a wide description column with taller rows by default; select
**Show all columns** to see the full imported record. Select a table row and click
**Review selected row** to read or edit the complete description.

Severity describes the reported impact. Priority describes scheduling urgency and
is edited separately. Opening the tracker does not infer or change either field.
Existing custom severity, priority, or status values remain selectable and are not
silently normalized to one of the suggested options.

The master backlog's initial priorities use this triage policy:

- **Critical:** verify and address the known signing-key exposure immediately.
- **High:** address serious access, accounting, data-loss, deployment, and blocked
  core-workflow risks; verify conditional risks before deciding the remedy.
- **Medium:** schedule other functional, validation, reliability, and supporting
  refactoring work.
- **Low:** handle minor edge cases, lower-impact optimizations, and routine cleanup.

Reported severity is the starting point. Importance can raise priority: for example,
silent payment loss, incorrect billing quantities, stock-deletion races, and actions
on the wrong preview deserve High priority even where a report rated severity lower.
An elevated priority does not turn a tentative finding into a confirmed defect.
The six investigations retain their source-recommended High or Medium priorities.
This is a one-time triage of the master; opening or saving a row does not auto-assign
priorities, and new rows still require your assessment.

## Edit a row

The main form starts with a full-width, 320-pixel-tall description editor, followed by
classification, ownership, status, recommended action, and comments. CSV files do not
store display widths; the app supplies this reading layout. The master has no
`resolution` column. **Comments** is reserved for your manually entered review notes.
Expand **Evidence, source details, and additional fields** for the remaining columns,
including imported source ratings.

- **Save row** writes changes and stays on the row.
- **Save & Previous** or **Save & Next** writes changes and advances in the current filtered list.
- A save that changes a filtered field may remove the row from the current view.

The title is required. The ID and creation date are read-only. Changed saves set
`last_modified_date` to today's date in the configured timezone. A no-op save does
not write the CSV, create a backup, or change dates. Original report dates and source
severity fields do not change automatically.

Save before changing a view, filter, selected row, or file. Form edits are not saved
while typing. Downloads contain saved records only. Reloading or closing the browser
can discard unsaved edits.

## Post an issue or todo

1. Click **Post new row** in the sidebar or choose **New row** in View. It works even
   when the file is empty or the current filters match nothing.
2. Choose `issue` or `todo`, enter a title, and fill the relevant description, category,
   priority, status, owner, and other fields.
3. Click **Post row**. Both dates use the actual posting day. A new `CR-` ID with a
   random 12-character suffix avoids collisions with imported and deleted record IDs.
4. The saved row opens for review and filters clear so that it is visible.

New rows default to Unrated severity, no assigned priority, Open (reported) status,
and Unassigned owner. Change these as appropriate for a todo. Source and evidence
fields start blank. If `record_type` is left blank, posting fills Reported issue or
Todo according to `type`. Every extra column in the file is preserved.

**Cancel new row** discards the draft without changing the file.

## Delete a row

Open the exact row, click **Delete row**, then inspect the ID and title in the
confirmation message. **Confirm delete** removes only that saved row. **Cancel delete**
leaves the file unchanged. Unsaved edits in the deleted row are discarded.

Deletion saves a complete copy of the immediately previous CSV in
`.csv-reviewer-backups` next to the tracker. Other records and their audit dates remain
unchanged. Deleting the last row leaves a valid header-only file, and new rows can
still be posted. Navigating to another row cancels an outstanding delete confirmation.

## Outside changes and recovery

Each changed save, post, or delete takes a per-path advisory lock, checks the file's
SHA-256 fingerprint, backs up its previous contents, and atomically replaces it. If
another app or process changed the CSV, the save is refused and the session data is
not advanced. Copy any unsaved text you need, then click **Reload saved file** and
reapply the intended change. There is no automatic merge.

Backups live beside the selected CSV, for example:
`~/Projects/FlowSell/code_review/.csv-reviewer-backups/summary-<timestamp>-<suffix>.csv`.
The latest backup path appears in the sidebar. To restore a deletion or earlier save,
stop editing, inspect the appropriate backup, keep a separate copy of the current
CSV, replace the master with the chosen backup, then reopen or reload the app.
Backups can contain the same sensitive information as the master, so keep them local.

Use one active editor when possible. External tools that ignore the advisory lock
can still race between the comparison and replacement. All rows remain in memory,
and each write serializes the entire dataset. CSV quoting and line endings may be
normalized; cell values and column order are preserved.

## Configuration

```sh
export FLOWSELL_REVIEW_CSV="$HOME/Projects/FlowSell/code_review/summary.csv"
export CSV_REVIEWER_TIMEZONE="America/New_York"
```

The path can also be entered in the opening screen. Timezone values use IANA names,
such as `America/New_York` or `Asia/Shanghai`. They control new and modified dates,
not historical report dates. An invalid timezone is reported before a changed row
is saved. Local backup filenames use the operating system clock and a unique suffix.

Keep the Streamlit server bound to `127.0.0.1`; this is a local file editor without
multi-user authentication.
