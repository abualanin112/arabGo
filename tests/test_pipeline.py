import unittest
import logging
import os
import shutil
import tempfile
import sys
import re

# Add scripts to path so we can import them
sys.path.append(os.path.abspath('scripts'))

import split
import status
import check_consistency
import merge
from core import vtt_converter

class TestPipeline(unittest.TestCase):
    def setUp(self):
        # Silence script logging
        logging.getLogger("split").setLevel(logging.CRITICAL)
        
        self.test_dir = tempfile.mkdtemp()
        self.en_srt_dir = os.path.join(self.test_dir, 'en_srt')
        self.chunks_dir = os.path.join(self.test_dir, 'chunks')
        self.go_done_dir = os.path.join(self.test_dir, 'go_done')
        self.final_dir = os.path.join(self.test_dir, 'final')
        self.qc_dir = os.path.join(self.test_dir, 'qc')
        
        os.makedirs(self.en_srt_dir)
        os.makedirs(self.chunks_dir)
        os.makedirs(self.go_done_dir)
        os.makedirs(self.final_dir)
        os.makedirs(self.qc_dir)

        # Create a sample SRT
        self.sample_srt = os.path.join(self.en_srt_dir, 'lesson_srt.srt')
        with open(self.sample_srt, 'w', encoding='utf-8') as f:
            for i in range(1, 11): # 10 blocks
                f.write(f"{i}\n00:00:0{i-1},000 --> 00:00:0{i},000\nSubtitle block {i}\n\n")

        # Create a sample VTT
        self.sample_vtt = os.path.join(self.en_srt_dir, 'lesson_vtt.vtt')
        with open(self.sample_vtt, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for i in range(1, 4): # 3 blocks
                f.write(f"00:00:0{i-1}.000 --> 00:00:0{i}.000\nSubtitle block {i}\n\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_vtt_to_srt_conversion(self):
        with open(self.sample_vtt, 'r', encoding='utf-8') as f:
            vtt_content = f.read()
        srt_content = vtt_converter.vtt_to_srt_content(vtt_content)
        
        # Should have indexes 1, 2, 3
        self.assertTrue(srt_content.startswith("1\n"))
        self.assertIn("2\n", srt_content)
        self.assertIn("3\n", srt_content)
        # Should have comma timestamps
        self.assertIn("00:00:00,000", srt_content)
        self.assertNotIn("WEBVTT", srt_content)

    def test_srt_to_vtt_conversion(self):
        with open(self.sample_srt, 'r', encoding='utf-8') as f:
            srt_content = f.read()
        vtt_content = vtt_converter.srt_to_vtt_content(srt_content)
        
        self.assertTrue(vtt_content.startswith("WEBVTT\n"))
        # Should NOT have numeric indexes at line starts
        self.assertFalse(re.search(r'^\d+\n', vtt_content.replace("WEBVTT\n", ""), re.MULTILINE))
        # Should have dot timestamps
        self.assertIn("00:00:00.000", vtt_content)

    def test_split_rejects_vtt(self):
        # split.py should now only accept .srt
        with self.assertRaises(ValueError):
            split.split_srt(self.sample_vtt, self.chunks_dir)

    def test_pipeline_srt_only_integrity(self):
        # 1. Convert VTT to SRT manually (simulating UI behavior)
        vtt_converter.convert_file_vtt_to_srt(self.sample_vtt)
        converted_srt_path = os.path.join(self.en_srt_dir, "lesson_vtt.srt")
        self.assertTrue(os.path.exists(converted_srt_path))

        # 2. Split should work on converted SRT
        split.split_srt(converted_srt_path, self.chunks_dir, chunk_size=2)
        lesson_dir = os.path.join(self.chunks_dir, "lesson_vtt")
        self.assertTrue(os.path.exists(lesson_dir))
        self.assertEqual(len(os.listdir(lesson_dir)), 2) # 2+1

        # 3. Match go_done filenames (must be .go.srt)
        for f in os.listdir(lesson_dir):
            done_name = f.replace(".srt", ".go.srt")
            open(os.path.join(self.go_done_dir, done_name), 'w').close()

        # 4. Status should report 0 pending
        pending = status.get_pending_chunks(self.chunks_dir, self.go_done_dir)
        self.assertEqual(len(pending), 0)

if __name__ == '__main__':
    unittest.main()
