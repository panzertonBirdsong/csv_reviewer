"""Run with: streamlit run csv_reviewer.py"""
import csv
from pathlib import Path

import streamlit as st

from csv_store import atomic_save, is_verified, prepare_verified, read_csv, serialize

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="CSV Reviewer", page_icon="📝", layout="wide")
st.title("CSV Reviewer")
st.caption("Browse and edit CSV files with any column layout. Files and edits stay on this Mac.")

if "rows" not in st.session_state:
    opening = st.empty()
    with opening.container():
        st.subheader("Open a CSV")
        files = sorted(ROOT.glob("*.csv"))
        source = st.radio("File source", ["Project folder", "Upload CSV"], horizontal=True)
        selected = None
        uploaded = None
        if source == "Project folder":
            selected = st.selectbox("CSV file", files, format_func=lambda p: p.name)
        else:
            uploaded = st.file_uploader("Choose a UTF-8 CSV", type="csv")
        choice = st.radio("Should this CSV have a 'verified' column?", ["Yes", "No"], index=None, horizontal=True)
        st.caption("Yes adds verified if missing. An existing verified column is kept for either choice.")
        name = selected.stem if selected else Path(uploaded.name).stem if uploaded else "records"
        default_output = f"{name}_reviewed.csv"
        output_name = st.text_input("Save reviewed copy as (in project folder)", value=default_output)
        if st.button("Open for review", type="primary", disabled=choice is None or not (selected or uploaded)):
            try:
                if not output_name.endswith(".csv") or Path(output_name).name != output_name:
                    raise ValueError("Enter a filename ending in .csv, without folders.")
                output = ROOT / output_name
                if output.exists():
                    raise ValueError("That output file already exists. Choose a new name. To resume, open the existing reviewed CSV as your source.")
                headers, rows = read_csv(selected.read_bytes() if selected else uploaded.getvalue())
                prepare_verified(headers, rows, choice == "Yes")
                atomic_save(output, headers, rows)
                st.session_state.update(headers=headers, rows=rows, output=str(output), current=0, revision=0)
                opening.empty()
                st.rerun()
            except (ValueError, UnicodeError, OSError, csv.Error) as error:
                st.error(str(error))
        st.stop()

ss = st.session_state
headers, rows = ss.headers, ss.rows
has_verified = "verified" in headers
with st.sidebar:
    view = st.radio("View", ["Record editor", "Table viewer"])
    st.subheader("Review progress")
    st.write(f"{len(rows)} records")
    if has_verified:
        count = sum(is_verified(row["verified"]) for row in rows)
        st.progress(count / len(rows) if rows else 0, text=f"{count} / {len(rows)} verified")
    pending = st.checkbox("Only unverified", disabled=not has_verified)
    search = st.text_input("Search all fields")
    multiline = st.checkbox("Use multiline editors for all fields")
    st.caption("Save edits before changing views, filters, records, or opening another file.")
    with st.expander("Help"):
        st.markdown("Open any CSV with a header row. Use **Table viewer** to browse saved records or **Record editor** to edit them. Save buttons write a separate copy. See **docs/USER_GUIDE.md** for the full guide.")
    st.divider()
    st.caption(f"Saving to: {Path(ss.output).name}")
    st.download_button("Download saved CSV", serialize(headers, rows), Path(ss.output).name, "text/csv")
    if st.button("Open another CSV"):
        ss.clear()
        st.rerun()

visible = [i for i, row in enumerate(rows) if (not pending or not is_verified(row.get("verified", ""))) and (not search or any(search.casefold() in value.casefold() for value in row.values()))]
if "notice" in ss:
    st.success(ss.pop("notice"))
if not visible:
    st.info("No matching records. Change the filters or open another CSV.")
    st.stop()
if ss.current not in visible:
    ss.current = visible[0]
if view == "Table viewer":
    st.subheader(f"Table · {len(visible)} of {len(rows)} records")
    st.caption("Saved values only. Switch to Record editor to make changes. Row numbers refer to the original record order.")
    # Build explicit string columns so identifiers, blanks, and numbers stay text.
    import pandas as pd
    table = pd.DataFrame([rows[i] for i in visible], columns=headers, dtype=str)
    table.index = [i + 1 for i in visible]
    st.dataframe(table, width="stretch")
    st.stop()
with st.sidebar:
    target = st.selectbox("Go to record", visible, index=visible.index(ss.current), format_func=lambda i: f"Record {i + 1}", key=f"jump_{ss.current}_{ss.revision}")
    if target != ss.current:
        ss.current = target
        ss.revision += 1
        st.rerun()
index = ss.current
position = visible.index(index)
st.subheader(f"Record {index + 1} of {len(rows)}")
st.caption(f"Match {position + 1} of {len(visible)} · All fields are editable. Navigation buttons save your edits.")

with st.form(f"record_{index}_{ss.revision}"):
    edited = {}
    for column_index, column in enumerate(headers):
        value = rows[index][column]
        field_key = f"field_{index}_{ss.revision}_{column_index}"
        if column == "verified":
            # Keep unusual existing values untouched unless the checkbox changes.
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
    updated = list(rows)
    updated[index] = edited
    try:
        atomic_save(Path(ss.output), headers, updated)
    except OSError as error:
        st.error(f"Could not save: {error}. Your edits are still in the form; retry saving.")
    else:
        ss.rows = updated
        if previous:
            ss.current = visible[position - 1]
        elif next_record or verify:
            ss.current = visible[min(position + 1, len(visible) - 1)]
        ss.revision += 1
        ss.notice = f"Record {index + 1} saved."
        st.rerun()
