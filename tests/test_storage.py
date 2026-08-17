import unittest
import tempfile
from pathlib import Path
from social_listening.storage import write_jsonl, read_jsonl, dedupe_by_id


class TestStorage(unittest.TestCase):
    def test_write_and_read_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test_data.jsonl"
            data = [
                {"id": "1", "text": "เรียนต่อนิด้าดีไหม"},
                {"id": "2", "text": "ค่าเทอม NIDA MBA เท่าไหร่"},
            ]
            write_jsonl(test_file, data, append=True)

            loaded = read_jsonl(test_file)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0]["id"], "1")
            self.assertIn("sentiment", loaded[0])

            # Test Append mode deduplication
            more_data = [
                {"id": "2", "text": "ค่าเทอม NIDA MBA เท่าไหร่"},
                {"id": "3", "text": "เรียนต่อ ป.เอก นิด้า"},
            ]
            write_jsonl(test_file, more_data, append=True)

            reloaded = read_jsonl(test_file)
            self.assertEqual(len(reloaded), 3)  # ID 2 deduped successfully


if __name__ == "__main__":
    unittest.main()
