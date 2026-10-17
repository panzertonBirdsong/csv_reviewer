"""FlowSell review records: string-preserving validation and lifecycle metadata."""
import os
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

REQUIRED_COLUMNS = {
    'issue_id', 'type', 'title', 'description', 'severity', 'priority',
    'status', 'created_date', 'last_modified_date',
}
SEVERITIES = ['Critical', 'High', 'Medium', 'Low', 'Unrated', 'Not applicable']
PRIORITIES = ['Critical', 'High', 'Medium', 'Low', 'Not separately assigned']
STATUSES = ['Open (reported)', 'Not started', 'In progress', 'Blocked',
            'Needs verification', 'Needs deployment verification', 'Needs decision',
            'Investigation pending', 'Backlog', 'Resolved', 'Closed',
            'Duplicate', "Won't fix"]
PRIMARY_FIELDS = ['issue_id', 'type', 'title', 'category', 'severity', 'priority',
                  'status', 'owner', 'created_date', 'last_modified_date']
DETAIL_FIELDS = ['description', 'recommended_action', 'resolution', 'comments']
MANAGED_FIELDS = {'issue_id', 'created_date', 'last_modified_date'}


def review_today():
    name = os.environ.get('CSV_REVIEWER_TIMEZONE', 'America/New_York')
    try:
        return datetime.now(ZoneInfo(name)).date().isoformat()
    except ZoneInfoNotFoundError as error:
        raise ValueError(f'Unknown review timezone: {name}. Set CSV_REVIEWER_TIMEZONE to an IANA timezone.') from error


def validate_dataset(headers, rows):
    missing = sorted(REQUIRED_COLUMNS - set(headers))
    if missing:
        raise ValueError('Missing review columns: ' + ', '.join(missing))
    seen = set()
    for position, row in enumerate(rows, 1):
        identifier = row['issue_id']
        if not identifier.strip() or identifier in seen:
            raise ValueError(f'Row {position} needs a nonempty, unique issue_id.')
        seen.add(identifier)
        if row['type'] not in {'issue', 'todo'}:
            raise ValueError(f'Row {position} type must be issue or todo.')


def blank_row(headers, rows, today=None):
    row = dict.fromkeys(headers, '')
    existing = {r['issue_id'] for r in rows}
    identifier = 'CR-' + uuid4().hex[:12]
    while identifier in existing:
        identifier = 'CR-' + uuid4().hex[:12]
    defaults = {
        'issue_id': identifier, 'type': 'issue', 'severity': 'Unrated',
        'priority': 'Not separately assigned', 'status': 'Open (reported)',
        'owner': 'Unassigned', 'created_date': today or review_today(),
        'last_modified_date': today or review_today(),
    }
    row.update({key: value for key, value in defaults.items() if key in row})
    return row


def prepare_row(headers, original, edited, *, creating=False, today=None):
    """Do not alter audit metadata on no-op saves or rewrite imported values."""
    row = {key: edited.get(key, original[key]) for key in headers}
    for key in MANAGED_FIELDS:
        row[key] = original[key]
    if not row['title'].strip():
        raise ValueError('Title is required.')
    if row['type'] not in {'issue', 'todo'}:
        raise ValueError('Type must be issue or todo.')
    if creating:
        row['created_date'] = row['last_modified_date'] = today or review_today()
        if 'record_type' in row and not row['record_type']:
            row['record_type'] = 'Reported issue' if row['type'] == 'issue' else 'Todo'
    elif row != original:
        row['last_modified_date'] = today or review_today()
    return row


def filter_rows(rows, search='', filters=None):
    filters = filters or {}
    needle = search.casefold()
    return [index for index, row in enumerate(rows)
            if all(not values or row.get(field, '') in values for field, values in filters.items())
            and (not needle or any(needle in value.casefold() for value in row.values()))]


def choices(defaults, value):
    return list(dict.fromkeys([*defaults, value]))
