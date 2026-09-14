# CSV viewer and editor: user guide

## What the app does

The app reads column headers from your file and creates a table and editing form for those columns. It works with inventories, contact lists, exports, review datasets, or other tabular text. There are no required business fields. The optional, exact lowercase column name `verified` has special review controls.

## Start the app

From the project directory, after completing the setup in the README:

```sh
conda activate csv_viewer
python -m streamlit run csv_reviewer.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

Open the localhost URL printed in the terminal. Keep the terminal process running while using the app. Press Control+C in that terminal to stop it.

## Open a file

1. Choose **Project folder** to select a CSV beside the app, or **Upload CSV** to choose a file from elsewhere on your Mac. Upload sends the file to this local app process.
2. Answer the `verified` question. Yes adds the column with `false` values only if it is missing. No leaves the columns unchanged. Both answers preserve an existing `verified` column and its values.
3. Choose a new output filename ending in `.csv`. Output is saved in the project directory. Existing output files cannot be selected for replacement.
4. Click **Open for review**. A separate output copy is created immediately, even if you only intend to browse.

The app supports comma-separated UTF-8 text, with or without a UTF-8 byte-order mark. Each column needs a nonempty, unique header. Every record must contain the same number of fields as the header. Quoted commas, double quotes, and multiline values are supported. Blank physical records are skipped. Header-only CSV files can be opened but have no records to display.

Semicolon/tab-separated files and other text encodings should be converted to comma-separated UTF-8 CSV first. Spreadsheet workbooks such as `.xlsx` must be exported as CSV.

## Browse and find records

Select **Table viewer** in the sidebar to see saved records in a scrollable table. The table is read-only; switch to **Record editor** to edit. Table row numbers represent the record's position in the source, starting at 1, rather than physical file line numbers. Multiline CSV records can span several physical lines.

**Search all fields** finds case-insensitive text in any column. **Only unverified** restricts results when the `verified` column exists. Both filters apply to the table and editor. **Go to record** jumps to any record matching those filters. Editing does not add or delete records or rearrange columns.

## Edit and save

The editor displays all columns in their original order. Short values use single-line inputs. Values longer than 100 characters or containing line breaks use text areas. Enable **Use multiline editors for all fields** before editing if you want to insert line breaks into a short field. Editor selection depends on content, not column names.

| Button | Action |
| --- | --- |
| Save | Write the current record to the output copy |
| Save & Previous | Save, then move to the previous matching record |
| Save & Next | Save, then move to the next matching record |
| Verify & Next | Set `verified` to `true`, save, then move forward when possible |

Save before changing the view, filters, record selector, or editor layout, or opening another file. Form edits are not automatically saved while typing. Closing or refreshing the browser can lose unsaved edits. Download contains saved records only.

Each save writes the full dataset to a temporary file and replaces the output copy atomically. Your input file stays unchanged. Use one editing session per output file; concurrent editing or external changes to the output are not merged.

## Verification

If present, `verified` is displayed as a checkbox. Values `true`, `yes`, `1`, `y`, and `verified` count as verified regardless of case or surrounding whitespace. Other values count as unverified. An existing value is preserved when its checkbox state is unchanged; toggling the checkbox writes `true` or `false`. **Verify & Next** always writes `true`.

Choosing No at opening does not hide or disable an existing `verified` column. Without the column, review controls are disabled. `Verified` and `VERIFIED` are ordinary columns; the special name is case-sensitive.

## Resume and export

Your saved copy is already on disk in the project folder. **Download saved CSV** offers the same saved dataset through the browser. To resume in a later session, open that reviewed copy as the input and pick a new output filename.

All cells remain strings, preserving leading zeroes, empty strings, and text that resembles dates or numbers. The app does not evaluate formulas. Output uses UTF-8; quoting and line endings may be normalized, so preserving values does not imply byte-for-byte preservation of the original file.

## Troubleshooting and limits

- **Output already exists:** choose a new filename, or open that existing file as your source to continue its review in another copy.
- **Wrong number of fields:** check delimiters and quoting, especially commas in unquoted text.
- **Duplicate or empty headers:** give every column a unique nonempty name before opening.
- **Encoding error:** export or convert the source to UTF-8.
- **No matching records:** clear search or disable Only unverified.
- **Could not save:** check folder permissions and available disk space, then retry saving the form.

The entire CSV is held in memory and rewritten on each save. This app is intended for interactive review of modest datasets, not very large exports. It does not provide undo history, automatic conflict resolution, or a database backend. Keep the app bound to `127.0.0.1` for local use.
