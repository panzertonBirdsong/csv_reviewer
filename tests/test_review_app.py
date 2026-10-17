import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from csv_store import read_csv, serialize
from test_reviews import HEADERS, fixture_rows

ROOT = Path(__file__).resolve().parents[1]


def element(elements, label):
    return next(item for item in elements if item.label == label)


class ReviewAppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'summary.csv'
        self.rows = fixture_rows()
        self.original = serialize(HEADERS, self.rows)
        self.path.write_bytes(self.original)
        self.app = AppTest.from_file(str(ROOT / 'csv_reviewer.py'), default_timeout=15).run()
        self.assertFalse(self.app.exception)
        element(self.app.text_input, 'Review CSV path').set_value(str(self.path))
        element(self.app.button, 'Open review CSV').click().run()
        self.assertFalse(self.app.exception)

    def saved(self):
        return read_csv(self.path.read_bytes())[1]

    def test_open_is_readonly_and_edits_keep_imported_fields(self):
        app = self.app
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertTrue(element(app.text_input, 'Issue id').disabled)
        self.assertTrue(element(app.text_input, 'Created date').disabled)
        element(app.text_input, 'Title').set_value('Edited title')
        element(app.selectbox, 'Priority').set_value('High')
        with patch('issue_reviews.review_today', return_value='2030-02-03'):
            element(app.button, 'Save & Next').click().run()
        self.assertFalse(app.exception)
        saved = self.saved()
        self.assertEqual(saved[0]['title'], 'Edited title')
        self.assertEqual(saved[0]['priority'], 'High')
        self.assertEqual(saved[0]['created_date'], '2020-01-01')
        self.assertEqual(saved[0]['last_modified_date'], '2030-02-03')
        self.assertEqual(saved[0]['conversation_reference'], '001')
        self.assertEqual(saved[1:], self.rows[1:])
        self.assertIn('CR-002', app.subheader[0].value)
        self.assertEqual(list((self.root / '.csv-reviewer-backups').glob('*.csv'))[0].read_bytes(), self.original)

    def test_post_page_filters_and_all_columns(self):
        app = self.app
        element(app.multiselect, 'Filter type').set_value(['todo']).run()
        self.assertIn('N1', app.subheader[0].value)
        element(app.text_input, 'Search all fields').set_value('no-match').run()
        self.assertTrue(app.info)
        element(app.button, 'Post new row').click().run()
        self.assertEqual(app.subheader[0].value, 'Post a new row')
        element(app.button, 'Post row').click().run()
        self.assertTrue(any('Title is required' in e.value for e in app.error))
        self.assertEqual(self.path.read_bytes(), self.original)
        element(app.text_input, 'Title').set_value('New task')
        element(app.selectbox, 'Type').set_value('todo')
        element(app.text_area, 'Description').set_value('New description, "quote"\n中文')
        element(app.button, 'Post row').click().run()
        self.assertFalse(app.exception)
        saved = self.saved()
        self.assertEqual(len(saved), 4)
        self.assertEqual(saved[:3], self.rows)
        self.assertEqual(saved[-1]['title'], 'New task')
        self.assertEqual(saved[-1]['type'], 'todo')
        self.assertEqual(saved[-1]['record_type'], 'Todo')
        self.assertEqual(saved[-1]['created_date'], saved[-1]['last_modified_date'])
        self.assertEqual(read_csv(self.path.read_bytes())[0], HEADERS)
        self.assertIn('New task', app.subheader[0].value)
        element(app.sidebar.radio, 'View').set_value('Table viewer').run()
        self.assertEqual(len(app.dataframe[0].value), 4)
        element(app.checkbox, 'Show all columns').check().run()
        self.assertEqual(list(app.dataframe[0].value.columns), HEADERS)

    def test_delete_confirmation_target_and_last_row(self):
        app = self.app
        element(app.selectbox, 'Go to row').set_value('CR-002').run()
        element(app.button, 'Delete row').click().run()
        self.assertTrue(any('CR-002' in warning.value for warning in app.warning))
        self.assertEqual(self.path.read_bytes(), self.original)
        element(app.button, 'Cancel delete').click().run()
        self.assertEqual(self.path.read_bytes(), self.original)
        element(app.button, 'Delete row').click().run()
        element(app.button, 'Confirm delete').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(self.saved(), [self.rows[0], self.rows[2]])
        for _ in range(2):
            element(app.button, 'Delete row').click().run()
            element(app.button, 'Confirm delete').click().run()
            self.assertFalse(app.exception)
        self.assertEqual(self.saved(), [])
        self.assertTrue(app.info)
        self.assertEqual(len(list((self.root / '.csv-reviewer-backups').glob('*.csv'))), 3)
        element(app.button, 'Post new row').click().run()
        element(app.text_input, 'Title').set_value('Back from empty')
        element(app.button, 'Post row').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(self.saved()), 1)

    def test_external_conflict_edit_create_and_delete(self):
        app = self.app
        external = self.original + b'\n'
        self.path.write_bytes(external)
        element(app.text_input, 'Title').set_value('Stale edit')
        element(app.button, 'Save row').click().run()
        self.assertTrue(any('changed outside' in e.value for e in app.error))
        self.assertEqual(self.path.read_bytes(), external)
        self.assertEqual(app.session_state['rows'], self.rows)
        element(app.button, 'Delete row').click().run()
        element(app.button, 'Confirm delete').click().run()
        self.assertTrue(any('changed outside' in e.value for e in app.error))
        self.assertEqual(self.path.read_bytes(), external)
        element(app.button, 'Post new row').click().run()
        element(app.text_input, 'Title').set_value('Stale new task')
        element(app.button, 'Post row').click().run()
        self.assertTrue(any('changed outside' in e.value for e in app.error))
        self.assertEqual(self.path.read_bytes(), external)
        self.assertEqual(app.session_state['rows'], self.rows)
        element(app.button, 'Reload saved file').click().run()
        self.assertFalse(app.exception)

    def test_io_failure_preserves_rows_and_draft(self):
        app = self.app
        element(app.text_input, 'Title').set_value('Retry this edit')
        with patch('csv_store.atomic_save', side_effect=OSError('Read-only volume')):
            element(app.button, 'Save row').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Read-only volume' in e.value for e in app.error))
        self.assertEqual(app.session_state['rows'], self.rows)
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertEqual(element(app.text_input, 'Title').value, 'Retry this edit')
        element(app.button, 'Save row').click().run()
        self.assertEqual(self.saved()[0]['title'], 'Retry this edit')

    def test_delete_cannot_follow_navigation_to_a_different_row(self):
        app = self.app
        element(app.button, 'Delete row').click().run()
        element(app.selectbox, 'Go to row').set_value('N1').run()
        self.assertFalse(any(b.label == 'Confirm delete' for b in app.button))
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_header_only_and_custom_status_open(self):
        self.path.write_bytes(serialize(HEADERS, []))
        element(self.app.button, 'Reload saved file').click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.info)
        element(self.app.button, 'Post new row').click().run()
        self.assertEqual(self.app.subheader[0].value, 'Post a new row')
        self.path.write_bytes(serialize(HEADERS, [dict(self.rows[0], status='Custom imported status')]))
        element(self.app.button, 'Reload saved file').click().run()
        self.assertEqual(element(self.app.selectbox, 'Status').value, 'Custom imported status')


if __name__ == '__main__':
    unittest.main()
