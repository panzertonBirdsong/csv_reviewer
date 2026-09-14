"""Lossless string-based CSV loading and atomic saving."""
import csv
import io
import os
import tempfile
from pathlib import Path


def read_csv(data: bytes):
    text = data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
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


def serialize(headers, rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def atomic_save(path: Path, headers, rows):
    data = serialize(headers, rows)
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
