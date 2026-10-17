"""Run with: streamlit run csv_reviewer.py"""
import csv
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import streamlit as st

from csv_store import (atomic_save, detect_delimiter, fingerprint, is_verified,
                       prepare_verified, read_csv, save_checked, serialize)
from job_applications import (APPLIED, application_status, is_job_tracker,
                              matches_queue, render_application)

ROOT = Path(__file__).resolve().parent
DEFAULT_TRACKER = Path.home() / 'Documents/JobSearch/table.csv'
st.set_page_config(page_title="CSV Reviewer · Applications", page_icon="📝", layout="wide")
st.title("CSV Reviewer")
st.caption("Your local workspace for job applications and CSV review.")


def load_session(headers, rows, output, delimiter, data):
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid4().hex[:8]
    backup = output.parent / '.csv-reviewer-backups' / f'{output.stem}-{stamp}{output.suffix}'
    st.session_state.update(headers=headers, rows=rows, output=str(output), delimiter=delimiter,
        file_digest=fingerprint(data), backup=str(backup), current=0, revision=0)


if "rows" not in st.session_state:
    opening = st.empty()
    with opening.container():
        sources = ["Job applications", "Project folder", "Local file", "Upload CSV"]
        source = st.radio("File source", sources, index=0 if DEFAULT_TRACKER.exists() else 1, horizontal=True)
        if source == "Job applications":
            st.subheader("Continue your job applications")
            tracker_path = st.text_input("Job tracker path", str(DEFAULT_TRACKER))
            st.caption("Open each employer’s application, preview your tailored résumé, copy answers, and record your progress. Changes save directly to this tracker with a backup on the first save.")
            if st.button("Open job tracker", type="primary"):
                try:
                    output = Path(tracker_path).expanduser().resolve()
                    data = output.read_bytes()
                    headers, rows = read_csv(data)
                    if not is_job_tracker(headers):
                        raise ValueError("This file does not have the job tracker columns. Open it using Local file for general CSV review.")
                    load_session(headers, rows, output, detect_delimiter(data), data)
                    opening.empty()
                    st.rerun()
                except (ValueError, UnicodeError, OSError, csv.Error) as error:
                    st.error(str(error))
            st.stop()
        st.subheader("Open a CSV or TSV")
        files = sorted([*ROOT.glob("*.csv"), *ROOT.glob("*.tsv")])
        selected = None
        uploaded = None
        if source == "Project folder":
            selected = st.selectbox("CSV file", files, format_func=lambda p: p.name)
        elif source == "Local file":
            local_path = st.text_input("Local CSV or TSV path")
            selected = Path(local_path).expanduser() if local_path.strip() else None
        else:
            uploaded = st.file_uploader("Choose a UTF-8 CSV or TSV", type=["csv", "tsv"])
        choice = st.radio("Should this CSV have a 'verified' column?", ["Yes", "No"], index=None, horizontal=True)
        st.caption("Yes adds verified if missing. An existing verified column is kept for either choice.")
        name = selected.stem if selected else Path(uploaded.name).stem if uploaded else "records"
        default_output = f"{name}_reviewed.csv"
        output_name = st.text_input("Save reviewed copy as (in project folder)", value=default_output)
        if st.button("Open for review", type="primary", disabled=choice is None or not (selected or uploaded)):
            try:
                if Path(output_name).suffix not in {".csv", ".tsv"} or Path(output_name).name != output_name:
                    raise ValueError("Enter a filename ending in .csv or .tsv, without folders.")
                output = ROOT / output_name
                if output.exists():
                    raise ValueError("That output file already exists. Choose a new name. To resume, open the existing reviewed CSV as your source.")
                data = selected.read_bytes() if selected else uploaded.getvalue()
                delimiter = detect_delimiter(data)
                headers, rows = read_csv(data, delimiter)
                prepare_verified(headers, rows, choice == "Yes")
                atomic_save(output, headers, rows, delimiter)
                load_session(headers, rows, output, delimiter, serialize(headers, rows, delimiter))
                opening.empty()
                st.rerun()
            except (ValueError, UnicodeError, OSError, csv.Error) as error:
                st.error(str(error))
        st.stop()

ss = st.session_state
# Ask older sessions to reopen once after upgrading, instead of guessing a save fingerprint.
if "file_digest" not in ss:
    st.info("CSV Reviewer was updated. Reopen your saved file to continue with the new application view.")
    if st.button("Reopen saved file"):
        ss.clear()
        st.rerun()
    st.stop()
headers, rows = ss.headers, ss.rows
has_verified = "verified" in headers
jobs = is_job_tracker(headers)


def save_row(index, edited):
    updated = list(ss.rows)
    updated[index] = edited
    if updated == ss.rows:
        return True
    try:
        digest = save_checked(ss.output, headers, updated, ss.delimiter, ss.file_digest, ss.backup)
    except (OSError, ValueError, csv.Error) as error:
        st.error(f"Could not save: {error}")
        return False
    ss.rows = updated
    ss.file_digest = digest
    return True


with st.sidebar:
    view = st.radio("View", (["Applications"] if jobs else []) + ["Record editor", "Table viewer"], key="workspace_view")
    st.subheader("Application progress" if jobs else "Review progress")
    st.write(f"{len(rows)} {'jobs' if jobs else 'records'}")
    queue = "All jobs"
    if jobs:
        count = sum(application_status(row['submitted']) in APPLIED for row in rows)
        duplicates = sum(application_status(row['submitted']) == 'Possible duplicate' for row in rows)
        st.progress(count / len(rows) if rows else 0, text=f"{count} / {len(rows)} applied")
        st.caption(f"{duplicates} possible duplicates to review")
        queue = st.selectbox("Application queue", ["To apply", "Possible duplicate", "Applied / outcomes", "On hold", "Skipped", "Not going to submit", "All jobs"])
    if has_verified:
        count = sum(is_verified(row["verified"]) for row in rows)
        st.progress(count / len(rows) if rows else 0, text=f"{count} / {len(rows)} verified")
    pending = st.checkbox("Only unverified", disabled=not has_verified) if not jobs or has_verified else False
    search = st.text_input("Search all fields", placeholder="Company, role, location…" if jobs else None)
    jump_slot = st.empty()
    multiline = st.checkbox("Use multiline editors for all fields") if view == 'Record editor' else False
    st.caption("Save edits before changing views, filters, records, or opening another file.")
    with st.expander("Help"):
        st.markdown("In **Applications**, open the employer’s form, use your résumé and answers, then mark your progress here. **Record editor** edits any tracker field. **Table viewer** shows the saved records. The application button opens a website; it does not submit a form.")
    st.divider()
    st.caption(f"Saving to: {ss.output}")
    st.download_button("Download saved CSV", serialize(headers, rows, ss.delimiter), Path(ss.output).name, "text/tab-separated-values" if ss.delimiter == '\t' else "text/csv", on_click="ignore")
    if st.button("Reload saved file"):
        try:
            output = Path(ss.output)
            data = output.read_bytes()
            new_headers, new_rows = read_csv(data)
            ss.clear()
            load_session(new_headers, new_rows, output, detect_delimiter(data), data)
            st.rerun()
        except (ValueError, UnicodeError, OSError, csv.Error) as error:
            st.error(str(error))
    if st.button("Open another CSV"):
        ss.clear()
        st.rerun()

visible = [i for i, row in enumerate(rows)
    if (not pending or not is_verified(row.get("verified", "")))
    and (not jobs or matches_queue(row, queue))
    and (not search or any(search.casefold() in value.casefold() for value in row.values()))]
if "notice" in ss:
    st.success(ss.pop("notice"))
if not visible:
    st.info("No matching records. Change the filters or open another CSV.")
    st.stop()
if ss.current not in visible:
    ss.current = visible[0]
if view == "Table viewer":
    st.subheader(f"Table · {len(visible)} of {len(rows)} records")
    st.caption("Saved values only. Choose a row to open it. Row numbers refer to the original record order.")
    import pandas as pd
    table = pd.DataFrame([rows[i] for i in visible], columns=headers, dtype=str)
    table.index = [i + 1 for i in visible]
    selection = st.dataframe(table, width="stretch", on_select='rerun', selection_mode='single-row', key=f'table_{ss.revision}')
    if selection.selection.rows:
        ss.current = visible[selection.selection.rows[0]]
        def open_selection():
            ss.workspace_view = 'Applications' if jobs else 'Record editor'
            ss.revision += 1
        st.button("Open selected job" if jobs else "Edit selected record", on_click=open_selection, type="primary")
    st.stop()
with jump_slot.container():
    label = (lambda i: f"{rows[i]['Company']} — {rows[i]['Role']} (#{i+1})") if jobs else (lambda i: f"Record {i+1}")
    target = st.selectbox("Go to job" if jobs else "Go to record", visible, index=visible.index(ss.current), format_func=label, key=f"jump_{ss.current}_{ss.revision}")
    if target != ss.current:
        ss.current = target
        ss.revision += 1
        st.rerun()
index = ss.current
position = visible.index(index)
if jobs and view == 'Applications':
    render_application(rows, index, visible, save_row)
    st.stop()
st.subheader(f"Record {index + 1} of {len(rows)}")
st.caption(f"Match {position + 1} of {len(visible)} · All fields are editable. Navigation buttons save your edits.")

with st.form(f"record_{index}_{ss.revision}"):
    edited = {}
    for column_index, column in enumerate(headers):
        value = rows[index][column]
        field_key = f"field_{index}_{ss.revision}_{column_index}"
        if column == "verified":
            checked = st.checkbox("Verified", value=is_verified(value), key=field_key)
            edited[column] = value if checked == is_verified(value) else str(checked).lower()
        elif multiline or len(value) > 100 or "\n" in value or "\r" in value:
            edited[column] = st.text_area(column, value=value, height=130, key=field_key)
        else:
            edited[column] = st.text_input(column, value=value, key=field_key)
    a, b, c, d = st.columns(4)
    previous = a.form_submit_button("Save & Previous", disabled=position == 0)
    save = b.form_submit_button("Save", type="primary")
    next_record = c.form_submit_button("Save & Next", disabled=position == len(visible) - 1)
    verify = d.form_submit_button("Verify & Next", disabled=not has_verified)

if previous or save or next_record or verify:
    if verify:
        edited["verified"] = "true"
    if save_row(index, edited):
        if previous:
            ss.current = visible[position - 1]
        elif next_record or verify:
            ss.current = visible[min(position + 1, len(visible) - 1)]
        ss.revision += 1
        ss.notice = f"Record {index + 1} saved."
        st.rerun()
