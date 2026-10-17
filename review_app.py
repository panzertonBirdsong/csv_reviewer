"""Streamlit UI for the FlowSell master issue and todo CSV."""
import csv
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd
import streamlit as st

from csv_store import detect_delimiter, fingerprint, read_csv, save_checked, serialize
from issue_reviews import (DETAIL_FIELDS, MANAGED_FIELDS, PRIMARY_FIELDS, PRIORITIES,
                           SEVERITIES, STATUSES, blank_row, choices, filter_rows,
                           prepare_row, validate_dataset)

DEFAULT_TRACKER = Path(os.environ.get('FLOWSELL_REVIEW_CSV',
    str(Path.home() / 'Projects/FlowSell/code_review/summary.csv'))).expanduser()
FILTER_FIELDS = ['type', 'severity', 'priority', 'status', 'category', 'owner']


def main():
    st.set_page_config(page_title='FlowSell · Code review', page_icon='📋', layout='wide')
    st.title('FlowSell code review')
    st.caption('Review issues and todos, record decisions, and maintain the project backlog.')
    ss = st.session_state

    def load(path):
        path = Path(path).expanduser().resolve()
        data = path.read_bytes()
        headers, rows = read_csv(data)
        validate_dataset(headers, rows)
        ss.clear()
        ss.update(headers=headers, rows=rows, output=str(path), delimiter=detect_delimiter(data),
                  file_digest=fingerprint(data), current_id=rows[0]['issue_id'] if rows else None,
                  revision=0, workspace_view='Review row')

    if 'rows' not in ss:
        st.subheader('Open your review tracker')
        tracker = st.text_input('Review CSV path', str(DEFAULT_TRACKER))
        st.caption('Opening does not change the file. Saves update this CSV directly and back up its previous contents.')
        if st.button('Open review CSV', type='primary'):
            try:
                load(tracker)
                st.rerun()
            except (OSError, ValueError, UnicodeError, csv.Error) as error:
                st.error(str(error))
        return

    def navigate(view, identifier=None, clear_filters=False):
        ss['_navigate'] = (view, identifier, clear_filters)

    if '_navigate' in ss:
        view, identifier, clear_filters = ss.pop('_navigate')
        ss.workspace_view = view
        if identifier is not None:
            ss.current_id = identifier
        ss.pop('pending_delete', None)
        if clear_filters:
            ss.search = ''
            for field in FILTER_FIELDS:
                ss.pop('filter_' + field, None)

    def persist(updated, message, identifier=None):
        if updated == ss.rows:
            ss.notice = 'No changes to save.'
            return True
        try:
            validate_dataset(ss.headers, updated)
            output = Path(ss.output)
            stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + uuid4().hex[:8]
            backup = output.parent / '.csv-reviewer-backups' / f'{output.stem}-{stamp}{output.suffix}'
            digest = save_checked(output, ss.headers, updated, ss.delimiter, ss.file_digest, backup)
        except (OSError, ValueError, csv.Error) as error:
            st.error(f'Could not save: {error}')
            return False
        ss.rows = updated
        ss.file_digest = digest
        ss.revision += 1
        ss.notice = message
        ss.last_backup = str(backup)
        if identifier is not None:
            ss.current_id = identifier
        return True

    with st.sidebar:
        st.radio('View', ['Review row', 'Table viewer', 'New row'], key='workspace_view',
                 on_change=lambda: ss.pop('pending_delete', None))
        st.button('Post new row', type='primary', on_click=navigate, args=('New row',))
        st.subheader('Backlog')
        issues = sum(row['type'] == 'issue' for row in ss.rows)
        st.write(f'{issues} issues · {len(ss.rows) - issues} todos')
        search = st.text_input('Search all fields', key='search', placeholder='ID, title, source, or notes')
        filters = {}
        for field in FILTER_FIELDS:
            if field not in ss.headers:
                continue
            values = sorted({row[field] for row in ss.rows}, key=str.casefold)
            key = 'filter_' + field
            if key in ss:
                ss[key] = [value for value in ss[key] if value in values]
            filters[field] = st.multiselect('Filter ' + field, values, key=key,
                                            format_func=lambda value: value or '(blank)')
        st.caption('Save form edits before changing rows, views, or filters. Filters use saved values.')
        st.divider()
        st.caption('Saving to: ' + ss.output)
        st.download_button('Download saved CSV', serialize(ss.headers, ss.rows, ss.delimiter),
                           Path(ss.output).name, 'text/csv', on_click='ignore')
        if 'last_backup' in ss:
            st.caption('Latest backup: ' + ss.last_backup)
        if st.button('Reload saved file'):
            try:
                load(ss.output)
                st.rerun()
            except (OSError, ValueError, UnicodeError, csv.Error) as error:
                st.error(str(error))
        if st.button('Open another CSV'):
            ss.clear()
            st.rerun()

    if 'notice' in ss:
        st.success(ss.pop('notice'))
    headers, rows = ss.headers, ss.rows
    view = ss.workspace_view

    def fields(row, prefix):
        edited = dict(row)

        def field(column):
            value = row[column]
            label = column.replace('_', ' ').capitalize()
            key = f'{prefix}_{column}'
            if column in MANAGED_FIELDS:
                st.text_input(label, value, key=key, disabled=True)
            elif column in {'type', 'severity', 'priority', 'status'}:
                defaults = {'type': ['issue', 'todo'], 'severity': SEVERITIES,
                            'priority': PRIORITIES, 'status': STATUSES}[column]
                options = choices(defaults, value)
                edited[column] = st.selectbox(label, options, index=options.index(value), key=key)
            elif column in DETAIL_FIELDS or len(value) > 100 or '\n' in value or '\r' in value:
                edited[column] = st.text_area(label, value, height=120, key=key)
            else:
                edited[column] = st.text_input(label, value, key=key)

        left, right = st.columns(2)
        for i, column in enumerate(c for c in PRIMARY_FIELDS if c in headers):
            with left if i % 2 == 0 else right:
                field(column)
        for column in DETAIL_FIELDS:
            if column in headers:
                field(column)
        remaining = [c for c in headers if c not in PRIMARY_FIELDS + DETAIL_FIELDS]
        if remaining:
            with st.expander('Evidence, source details, and additional fields'):
                for column in remaining:
                    field(column)
        return edited

    if view == 'New row':
        st.subheader('Post a new row')
        st.caption('Choose issue or todo and enter a title. A unique ID and both dates are assigned automatically.')
        if 'new_draft' not in ss:
            try:
                ss.new_draft = blank_row(headers, rows)
            except ValueError as error:
                st.error(str(error))
                return
        with st.form(f'new_{ss.revision}'):
            edited = fields(ss.new_draft, f'new_{ss.revision}')
            submit = st.form_submit_button('Post row', type='primary')
        if submit:
            try:
                new = prepare_row(headers, ss.new_draft, edited, creating=True)
                if persist([*rows, new], f"Posted {new['issue_id']}.", new['issue_id']):
                    ss.pop('new_draft', None)
                    navigate('Review row', new['issue_id'], True)
                    st.rerun()
            except ValueError as error:
                st.error(str(error))
        if st.button('Cancel new row'):
            ss.pop('new_draft', None)
            ss.revision += 1
            navigate('Review row')
            st.rerun()
        return

    visible = filter_rows(rows, search, filters)
    if not visible:
        st.info('No matching rows. Change the filters or use Post new row to add an issue or todo.')
        return
    if ss.current_id not in {rows[i]['issue_id'] for i in visible}:
        ss.current_id = rows[visible[0]]['issue_id']

    if view == 'Table viewer':
        st.subheader(f'Table · {len(visible)} of {len(rows)} rows')
        show_all = st.checkbox('Show all columns')
        columns = headers if show_all else [c for c in PRIMARY_FIELDS if c in headers]
        table = pd.DataFrame([rows[i] for i in visible], columns=columns, dtype=str)
        selection = st.dataframe(table, width='stretch', hide_index=True, on_select='rerun',
                                 selection_mode='single-row', key=f'table_{ss.revision}')
        if selection.selection.rows:
            selected = rows[visible[selection.selection.rows[0]]]['issue_id']
            st.button('Review selected row', type='primary', on_click=navigate,
                      args=('Review row', selected))
        return

    ids = [rows[i]['issue_id'] for i in visible]
    by_id = {row['issue_id']: row for row in rows}
    selected = st.selectbox('Go to row', ids, index=ids.index(ss.current_id),
                            format_func=lambda identifier: f"{identifier} — {by_id[identifier]['title']}",
                            key=f'jump_{ss.revision}_{ss.current_id}')
    if selected != ss.current_id:
        ss.current_id = selected
        ss.pop('pending_delete', None)
        ss.revision += 1
        st.rerun()
    index = next(i for i in visible if rows[i]['issue_id'] == ss.current_id)
    position = visible.index(index)
    row = rows[index]
    st.subheader(f"{row['issue_id']} · {row['title']}")
    st.caption(f'Match {position + 1} of {len(visible)}. ID and creation date remain fixed; changed saves update the modified date.')
    with st.form(f'record_{row["issue_id"]}_{ss.revision}'):
        edited = fields(row, f'edit_{row["issue_id"]}_{ss.revision}')
        previous, save, following = st.columns(3)
        go_previous = previous.form_submit_button('Save & Previous', disabled=position == 0)
        submit = save.form_submit_button('Save row', type='primary')
        go_next = following.form_submit_button('Save & Next', disabled=position == len(visible) - 1)
    if submit or go_previous or go_next:
        try:
            new = prepare_row(headers, row, edited)
            updated = list(rows)
            updated[index] = new
            if persist(updated, f"Saved {row['issue_id']}."):
                if go_previous or go_next:
                    ss.current_id = rows[visible[position + (-1 if go_previous else 1)]]['issue_id']
                st.rerun()
        except ValueError as error:
            st.error(str(error))

    st.divider()
    def request_delete():
        ss.pending_delete = row['issue_id']

    def confirm_delete():
        identifier = ss.get('pending_delete')
        if identifier != row['issue_id']:
            return
        updated = [r for r in ss.rows if r['issue_id'] != identifier]
        if persist(updated, f'Deleted {identifier}.'):
            ss.pop('pending_delete', None)
            ss.current_id = None

    st.button('Delete row', on_click=request_delete)
    if ss.get('pending_delete') == row['issue_id']:
        st.warning(f"Delete {row['issue_id']} — {row['title']}? The saved row will be removed. A backup keeps the CSV as it was before deletion. Unsaved edits will be discarded.")
        confirm, cancel = st.columns(2)
        confirm.button('Confirm delete', type='primary', on_click=confirm_delete)
        cancel.button('Cancel delete', on_click=lambda: ss.pop('pending_delete', None))
