# CSV Reviewer

A general-purpose local CSV viewer and editor. Open any UTF-8 CSV with a header row, browse its table, search records, and edit one record at a time. Column names and counts come from your file; no particular dataset or schema is required.

See the [User guide](docs/USER_GUIDE.md) for workflows, supported files, and troubleshooting, and the [Developer guide](docs/DEVELOPMENT.md) for architecture and testing.

## Setup and launch

```sh
conda create --name csv_viewer python=3.12 pip -y
conda activate csv_viewer
python -m pip install -r requirements.txt
python -m streamlit run csv_reviewer.py --server.address 127.0.0.1
```

Open the localhost URL printed by Streamlit. Select a CSV from the project folder or upload one through the local interface. Choose **Yes** or **No** for the `verified` column before opening:

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

Streamlit is the direct third-party dependency. All installed library versions, including its dependencies, are pinned in `requirements.txt`. CSV handling uses the Python standard library.

## Checks

```sh
python -m unittest discover -s tests
```
