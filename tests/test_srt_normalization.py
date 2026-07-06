import unittest
import os
import shutil
import tempfile
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.vtt_converter import normalize_file

class TestSRTNormalization(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_srt_without_hours_normalization(self):
        # Create an SRT file with short timestamps (MM:SS,mmm)
        srt_content = """1
00:01,310 --> 00:03,420
Hello world
"""
        srt_path = os.path.join(self.test_dir, "test.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        # Run normalize_file
        normalized_path = normalize_file(srt_path)

        # Read the file back
        with open(normalized_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Assert that timestamps contain hours (00:00:01,310)
        # The current implementation fails this because it doesn't normalize SRT.
        self.assertIn("00:00:01,310", content, "SRT timestamps should be normalized to include hours")
        self.assertIn("00:00:03,420", content)

if __name__ == "__main__":
    unittest.main()
