import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from csv_store import fingerprint, read_csv, save_checked, serialize
from issue_reviews import blank_row, filter_rows, prepare_row, review_today, validate_dataset

HEADERS = ['issue_id', 'type', 'title', 'category', 'severity', 'priority', 'status',
           'created_date', 'last_modified_date', 'record_type', 'description',
           'source_reports', 'source_references', 'source_severities', 'severity_basis',
           'evidence_status', 'conditions', 'code_references', 'recommended_action',
           'comments', 'conversation_reference', 'report_date', 'reviewed_commit',
           'consolidated_on', 'owner', 'resolution', 'imported_from']


def fixture_rows():
    common = dict.fromkeys(HEADERS, '')
    common.update(type='issue', category='Security', severity='High',
                  priority='Not separately assigned', status='Open (reported)',
                  created_date='2020-01-01', last_modified_date='2020-01-02',
                  owner='Unassigned', description='Comma, quote " and\nUnicode 中文',
                  source_references='CODE_REVIEW_A.md:10', conversation_reference='001')
    return [dict(common, issue_id='CR-001', title='First issue'),
            dict(common, issue_id='CR-002', title='Second issue', severity='Medium'),
            dict(common, issue_id='N1', title='Recovery task', type='todo',
                 severity='Not applicable', status='Investigation pending')]


class ReviewDataTests(unittest.TestCase):
    def test_schema_and_ids(self):
        validate_dataset(HEADERS, fixture_rows())
        validate_dataset(HEADERS, [])
        with self.assertRaisesRegex(ValueError, 'Missing review columns'):
            validate_dataset(['id', 'title'], [])
        rows = fixture_rows()
        for bad in ['', rows[0]['issue_id']]:
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, 'unique issue_id'):
                validate_dataset(HEADERS, [rows[0], dict(rows[1], issue_id=bad)])

    def test_new_row_defaults_and_validation(self):
        draft = blank_row(HEADERS, fixture_rows(), today='2026-10-16')
        self.assertRegex(draft['issue_id'], r'^CR-[0-9a-f]{12}$')
        self.assertEqual(list(draft), HEADERS)
        self.assertEqual(draft['created_date'], '2026-10-16')
        self.assertEqual(draft['source_reports'], '')
        with self.assertRaisesRegex(ValueError, 'Title is required'):
            prepare_row(HEADERS, draft, draft, creating=True)
        added = prepare_row(HEADERS, draft, dict(draft, title='New todo', type='todo'),
                            creating=True, today='2026-10-17')
        self.assertEqual(added['created_date'], '2026-10-17')
        self.assertEqual(added['last_modified_date'], '2026-10-17')
        self.assertEqual(added['record_type'], 'Todo')
        self.assertEqual(added['issue_id'], draft['issue_id'])
        with self.assertRaisesRegex(ValueError, 'Type must'):
            prepare_row(HEADERS, draft, dict(draft, title='X', type='bug'), creating=True)

    def test_edit_metadata_and_noop(self):
        original = fixture_rows()[0]
        self.assertEqual(prepare_row(HEADERS, original, original, today='2030-02-03'), original)
        edited = dict(original, title='Changed', issue_id='wrong', created_date='wrong', last_modified_date='wrong')
        actual = prepare_row(HEADERS, original, edited, today='2030-02-03')
        self.assertEqual(actual['issue_id'], original['issue_id'])
        self.assertEqual(actual['created_date'], original['created_date'])
        self.assertEqual(actual['last_modified_date'], '2030-02-03')
        self.assertEqual(actual['title'], 'Changed')
        for column in HEADERS:
            if column not in {'title', 'last_modified_date'}:
                self.assertEqual(actual[column], original[column])

    def test_filters_combine_and_find_hidden_fields(self):
        rows = fixture_rows()
        self.assertEqual(filter_rows(rows, filters={'type': ['todo']}), [2])
        self.assertEqual(filter_rows(rows, 'SECOND', {'severity': ['High']}), [])
        self.assertEqual(filter_rows(rows, 'code_review_a', {'type': ['issue']}), [0, 1])

    def test_timezone_is_explicit(self):
        with patch.dict('os.environ', {'CSV_REVIEWER_TIMEZONE': 'Not/A_Zone'}):
            with self.assertRaisesRegex(ValueError, 'Unknown review timezone'):
                review_today()

    def test_create_edit_delete_and_conflict_preserve_file(self):
        for delimiter in [',', '\t']:
            with self.subTest(delimiter=delimiter), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'summary.csv'
                original = fixture_rows()
                before = serialize(HEADERS, original, delimiter)
                path.write_bytes(before)
                new = blank_row(HEADERS, original)
                new['title'] = 'New, quoted "todo"\n中文'
                new['type'] = 'todo'
                added = [*original, new]
                backup1 = Path(directory) / 'backups' / 'before-create.csv'
                digest = save_checked(path, HEADERS, added, delimiter, fingerprint(before), backup1)
                self.assertEqual(read_csv(path.read_bytes()), (HEADERS, added))
                self.assertEqual(backup1.read_bytes(), before)
                before_delete = path.read_bytes()
                deleted = [row for row in added if row['issue_id'] != 'CR-002']
                backup2 = Path(directory) / 'backups' / 'before-delete.csv'
                digest = save_checked(path, HEADERS, deleted, delimiter, digest, backup2)
                self.assertEqual(backup2.read_bytes(), before_delete)
                self.assertEqual(read_csv(path.read_bytes()), (HEADERS, deleted))
                external = path.read_bytes() + b'\n'
                path.write_bytes(external)
                with self.assertRaisesRegex(ValueError, 'changed outside'):
                    save_checked(path, HEADERS, [], delimiter, digest, Path(directory) / 'unused.csv')
                self.assertEqual(path.read_bytes(), external)


if __name__ == '__main__':
    unittest.main()
