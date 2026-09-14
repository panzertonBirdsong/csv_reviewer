import tempfile
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest
from csv_store import read_csv

ROOT = Path(__file__).resolve().parents[1]


class AppTests(unittest.TestCase):
    def test_open_choices_and_edit(self):
        for choice in ("Yes", "No"):
            for exists in (True, False):
                with self.subTest(choice=choice, exists=exists), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    app_path = root / "app.py"
                    app_path.write_text((ROOT / "csv_reviewer.py").read_text())
                    source = "id,Description" + (",verified" if exists else "") + "\n001,First" + (",yes" if exists else "") + "\n002,Second" + (",false" if exists else "") + "\n"
                    (root / "sample.csv").write_text(source)
                    app = AppTest.from_file(str(app_path), default_timeout=15).run()
                    self.assertFalse(app.exception)
                    app.radio[1].set_value(choice).run()
                    app.button[0].click().run()
                    self.assertFalse(app.exception)
                    output = root / "sample_reviewed.csv"
                    headers, rows = read_csv(output.read_bytes())
                    self.assertEqual("verified" in headers, exists or choice == "Yes")
                    if exists:
                        self.assertEqual(rows[0]["verified"], "yes")
                    next(field for field in app.text_input if field.label == "Description").set_value('Edited, "quoted"\nline')
                    next(button for button in app.button if button.label == "Save & Next").click().run()
                    self.assertFalse(app.exception)
                    self.assertEqual(app.subheader[0].value, "Record 2 of 2")
                    self.assertEqual(read_csv(output.read_bytes())[1][0]["Description"], 'Edited, "quoted"\nline')
                    self.assertEqual((root / "sample.csv").read_text(), source)
                    if exists or choice == "Yes":
                        next(button for button in app.button if button.label == "Verify & Next").click().run()
                        self.assertEqual(read_csv(output.read_bytes())[1][1]["verified"], "true")
                        self.assertFalse(app.exception)
                    app.sidebar.radio[0].set_value("Table viewer").run()
                    self.assertFalse(app.exception)
                    self.assertEqual(len(app.dataframe), 1)
                    self.assertEqual(app.dataframe[0].value.iloc[0]["id"], "001")
                    app.sidebar.radio[0].set_value("Record editor").run()
                    next(field for field in app.selectbox if field.label == "Go to record").set_value(0).run()
                    self.assertFalse(app.exception)
                    self.assertEqual(app.subheader[0].value, "Record 1 of 2")
                    next(field for field in app.checkbox if field.label == "Use multiline editors for all fields").check().run()
                    self.assertTrue(any(field.label == "id" for field in app.text_area))
