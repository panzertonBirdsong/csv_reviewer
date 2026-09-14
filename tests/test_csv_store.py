import tempfile
import unittest
from pathlib import Path

from csv_store import atomic_save, prepare_verified, read_csv, serialize


class CSVStoreTests(unittest.TestCase):
    def test_verified_all_four_cases(self):
        for requested in (True, False):
            for exists in (True, False):
                with self.subTest(requested=requested, exists=exists):
                    headers = ["id"] + (["verified"] if exists else [])
                    rows = [{"id": "001", **({"verified": "yes"} if exists else {})}]
                    prepare_verified(headers, rows, requested)
                    self.assertEqual("verified" in headers, requested or exists)
                    if exists:
                        self.assertEqual(rows[0]["verified"], "yes")
                        self.assertEqual(headers.count("verified"), 1)
                    elif requested:
                        self.assertEqual(rows[0]["verified"], "false")

    def test_round_trip(self):
        headers = ["id", "description", "empty"]
        rows = [{"id": "001", "description": 'Comma, quote " and\nnew line —', "empty": ""}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reviewed.csv"
            atomic_save(path, headers, rows)
            self.assertEqual(read_csv(path.read_bytes()), (headers, rows))
            self.assertEqual(read_csv(b"\xef\xbb\xbf" + serialize(headers, rows)), (headers, rows))

    def test_malformed_rows_rejected(self):
        for data in (b"a,a\n1,2", b"a,b\n1,2,3", b"a,b\n1"):
            with self.assertRaises(ValueError):
                read_csv(data)


if __name__ == "__main__":
    unittest.main()
