"""String-preserving CSV/TSV loading, atomic saving, and conflict detection."""
import csv
import hashlib
import io
import os
import tempfile
from pathlib import Path


def detect_delimiter(data: bytes):
    """Use the header, not commas in prose cells, to distinguish CSV and TSV."""
    text = data.decode("utf-8-sig")
    widths = {}
    for delimiter in (",", "\t"):
        try:
            widths[delimiter] = len(next(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True), []))
        except csv.Error:
            widths[delimiter] = 0
    return max(widths, key=widths.get)


def read_csv(data: bytes, delimiter=None):
    text = data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter or detect_delimiter(data), strict=True)
    headers = next(reader, None)
    if not headers or any(not name.strip() for name in headers):
        raise ValueError("The CSV must have a nonempty header for every column.")
    if len(set(headers)) != len(headers):
        raise ValueError("Duplicate column names are not supported.")
    rows = []
    for values in reader:
        if not values:
            continue
        if len(values) != len(headers):
            raise ValueError(f"CSV line {reader.line_num} has {len(values)} fields; expected {len(headers)}.")
        rows.append(dict(zip(headers, values)))
    return headers, rows


def prepare_verified(headers, rows, requested):
    if requested and "verified" not in headers:
        headers.append("verified")
        for row in rows:
            row["verified"] = "false"


def is_verified(value):
    return value.strip().lower() in {"true", "yes", "1", "y", "verified"}


def serialize(headers, rows, delimiter=","):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=headers, delimiter=delimiter)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def atomic_save(path: Path, headers, rows, delimiter=","):
    data = serialize(headers, rows, delimiter)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def fingerprint(data):
    return hashlib.sha256(data).hexdigest()


def save_checked(path, headers, rows, delimiter, expected, backup):
    """Serialize cooperating sessions; refuse to replace externally changed data."""
    import fcntl
    path, backup = Path(path), Path(backup)
    with path.with_name('.' + path.name + '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = path.read_bytes()
        if fingerprint(current) != expected:
            raise ValueError("This file changed outside this session. Reopen it to load the latest data before saving; your changes have not overwritten it.")
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            with backup.open('xb') as handle:
                handle.write(current)
        atomic_save(path, headers, rows, delimiter)
        return fingerprint(serialize(headers, rows, delimiter))
