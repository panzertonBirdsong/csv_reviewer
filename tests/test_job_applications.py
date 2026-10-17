import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest
from csv_store import atomic_save, detect_delimiter, fingerprint, read_csv, save_checked, serialize
from job_applications import application_status, answer_sections, job_url, packet_folder, update_status

ROOT = Path(__file__).resolve().parents[1]
HEADERS = ['Company','Role','location','ddl','added by GPT or manually','resume&story ready','export folder path','submitted','job link']


def element(elements, label):
    return next(item for item in elements if item.label == label)


class JobDataTests(unittest.TestCase):
    def test_tab_roundtrip_and_backup(self):
        rows = [dict(zip(HEADERS, ['001, Inc.', 'ML engineer', 'NY\tNJ', '', 'GPT', 'Drafts ready', '/tmp/a', 'No\nChecked yesterday', 'https://example.com/apply']))]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'table.csv'
            before = serialize(HEADERS,rows,'\t')
            path.write_bytes(before)
            self.assertEqual(detect_delimiter(before),'\t')
            self.assertEqual(read_csv(before),(HEADERS,rows))
            updated = [dict(rows[0], submitted='Yes - submitted 2026-10-02')]
            backup = Path(directory)/'backups'/'original.csv'
            saved = save_checked(path,HEADERS,updated,'\t',fingerprint(before),backup)
            self.assertEqual(saved,fingerprint(path.read_bytes()))
            self.assertEqual(backup.read_bytes(),before)
            self.assertEqual(read_csv(path.read_bytes()),(HEADERS,updated))
            self.assertEqual(len(read_csv(path.read_bytes())[0]),9)
            external = path.read_bytes()+b'\n'
            path.write_bytes(external)
            with self.assertRaisesRegex(ValueError,'changed outside'):
                save_checked(path,HEADERS,rows,'\t',saved,backup)
            self.assertEqual(path.read_bytes(),external)
            self.assertEqual(backup.read_bytes(),before)

    def test_status_history_and_safe_links(self):
        unknown='Unknown - POSSIBLE DUPLICATE (email checked 2026-10-01)'
        self.assertEqual(application_status(unknown),'Possible duplicate')
        self.assertEqual(application_status('No matching confirmation found'),'To apply')
        self.assertEqual(application_status('Yes - email confirmed; rejected 2026-08-18'),'Rejected')
        changed=update_status(unknown,'Submitted',date(2026,10,2))
        self.assertIn(unknown,changed)
        self.assertEqual(application_status(changed),'Submitted')
        rejected=update_status(changed,'Rejected',date(2026,10,3))
        self.assertEqual(application_status(rejected),'Rejected')
        self.assertEqual(update_status(unknown,'Keep current',date.today()),unknown)
        self.assertIsNone(job_url('javascript:alert(1)'))
        self.assertEqual(job_url('https://example.com/jobs?id=1'),'https://example.com/jobs?id=1')
        self.assertEqual(packet_folder('applications/one','/tmp/table.csv'),Path('/tmp/applications/one'))
        self.assertIsNone(packet_folder('','/tmp/table.csv'))
        self.assertEqual(answer_sections('# Title\n\n## Actual prompt\n\nMy answer.\n\n## Anticipated prompt\nSecond answer.'),[('Actual prompt','My answer.'),('Anticipated prompt','Second answer.')])


class JobAppTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.app_path=self.root/'app.py'
        shutil.copy2(ROOT/'csv_reviewer.py',self.app_path)
        packet=self.root/'materials'
        packet.mkdir()
        (packet/'answers.md').write_text('# Drafts\n\n## Actual: Why this role?\nI built relevant software.\n\n## Anticipated: project\nMy supported project answer.')
        (packet/'job_notes.md').write_text('# Role evidence\nCheck degree eligibility.')
        statuses=['No matching confirmation found','Unknown - POSSIBLE DUPLICATE','Yes - email confirmed; rejected 2026-08-18','']
        self.rows=[dict(zip(HEADERS,[f'Company {i}',f'Role {i}','New York, NY','Not stated','GPT','Drafts ready',str(packet),status,f'https://example.com/{i}'])) for i,status in enumerate(statuses)]
        self.path=self.root/'table.csv'
        atomic_save(self.path,HEADERS,self.rows,'\t')
        self.original=self.path.read_bytes()
        self.app=AppTest.from_file(str(self.app_path),default_timeout=20).run()
        element(self.app.radio,'File source').set_value('Job applications').run()
        element(self.app.text_input,'Job tracker path').set_value(str(self.path))
        element(self.app.button,'Open job tracker').click().run()
        self.assertFalse(self.app.exception)

    def test_application_workflow(self):
        app=self.app
        self.assertEqual(self.path.read_bytes(),self.original)
        self.assertEqual(app.subheader[0].value,'Company 0')
        self.assertEqual(len(app.tabs),4)
        self.assertTrue(any(code.value=='I built relevant software.' for code in app.code))
        element(app.button,'Mark submitted & next').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.subheader[0].value,'Company 3')
        headers,saved=read_csv(self.path.read_bytes())
        self.assertEqual(headers,HEADERS)
        self.assertEqual(application_status(saved[0]['submitted']),'Submitted')
        self.assertIn(self.rows[0]['submitted'],saved[0]['submitted'])
        self.assertEqual(saved[1:],self.rows[1:])
        backups=list((self.root/'.csv-reviewer-backups').glob('*.csv'))
        self.assertEqual(len(backups),1)
        self.assertEqual(backups[0].read_bytes(),self.original)
        element(app.selectbox,'Application queue').set_value('Possible duplicate').run()
        self.assertEqual(app.subheader[0].value,'Company 1')
        self.assertTrue(app.warning)
        element(app.selectbox,'Update status').set_value('On hold')
        element(app.text_area,'History and notes').set_value(self.rows[1]['submitted']+'\nChecking the role ID.')
        element(app.button,'Save status').click().run()
        self.assertFalse(app.exception)
        saved=read_csv(self.path.read_bytes())[1]
        self.assertEqual(application_status(saved[1]['submitted']),'On hold')
        self.assertIn('Checking the role ID.',saved[1]['submitted'])
        element(app.selectbox,'Application queue').set_value('All jobs').run()
        app.sidebar.radio[0].set_value('Table viewer').run()
        self.assertEqual(len(app.dataframe),1)
        self.assertEqual(len(app.dataframe[0].value),4)
        app.sidebar.radio[0].set_value('Record editor').run()
        self.assertFalse(app.exception)
        self.assertTrue(any(field.label=='job link' for field in app.text_input))
        element(app.button,'Reload saved file').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['rows'],saved)

    def test_not_going_to_submit_preserves_history_and_filters(self):
        app=self.app
        element(app.selectbox,'Application queue').set_value('Possible duplicate').run()
        element(app.selectbox,'Update status').set_value('Not going to submit')
        element(app.button,'Save status').click().run()
        self.assertFalse(app.exception)
        headers,saved=read_csv(self.path.read_bytes())
        self.assertEqual(headers,HEADERS)
        self.assertTrue(saved[1]['submitted'].startswith('Not going to submit '))
        self.assertIn(self.rows[1]['submitted'],saved[1]['submitted'])
        self.assertEqual(saved[:1]+saved[2:],self.rows[:1]+self.rows[2:])
        element(app.selectbox,'Application queue').set_value('To apply').run()
        self.assertEqual(app.subheader[0].value,'Company 0')
        self.assertFalse(any('Company 1' in option for option in element(app.selectbox,'Go to job').options))
        element(app.button,'Reload saved file').click().run()
        element(app.selectbox,'Application queue').set_value('Not going to submit').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.subheader[0].value,'Company 1')
        self.assertTrue(any('Not going to submit' in info.value for info in app.info))
        element(app.selectbox,'Application queue').set_value('Applied / outcomes').run()
        self.assertEqual(app.subheader[0].value,'Company 2')

    def test_not_submitting_button_saves_and_advances(self):
        app=self.app
        # The explicit action overrides a different selection in the status dropdown.
        element(app.selectbox,'Update status').set_value('Submitted')
        element(app.button,'Not going to submit & next').click().run()
        self.assertFalse(app.exception)
        saved=read_csv(self.path.read_bytes())[1]
        self.assertEqual(application_status(saved[0]['submitted']),'Not going to submit')
        self.assertIn(self.rows[0]['submitted'],saved[0]['submitted'])
        self.assertEqual(saved[1:],self.rows[1:])
        self.assertEqual(app.subheader[0].value,'Company 3')
        # Complete the AppTest rerun so the prior form controls are removed.
        app.run()
        # The action also works on the last remaining job in the queue.
        element(app.button,'Not going to submit & next').click().run()
        self.assertFalse(app.exception)
        saved=read_csv(self.path.read_bytes())[1]
        self.assertEqual(application_status(saved[3]['submitted']),'Not going to submit')
        self.assertTrue(any('No matching records' in info.value for info in app.info))

    def test_external_change_is_not_overwritten(self):
        external=self.path.read_bytes()+b'\n'
        self.path.write_bytes(external)
        element(self.app.button,'Mark submitted & next').click().run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any('changed outside' in error.value for error in self.app.error))
        self.assertEqual(self.path.read_bytes(),external)
        self.assertEqual(self.app.session_state['rows'],self.rows)

    def test_missing_materials_are_reported(self):
        element(self.app.sidebar.radio,'View').set_value('Record editor').run()
        element(self.app.text_input,'export folder path').set_value('/no/such/application/folder')
        element(self.app.button,'Save').click().run()
        element(self.app.sidebar.radio,'View').set_value('Applications').run()
        self.assertFalse(self.app.exception)
        self.assertTrue(element(self.app.button,'Open materials folder').disabled)
        self.assertTrue(any('No résumé PDF' in info.value for info in self.app.info))


if __name__=='__main__':
    unittest.main()
