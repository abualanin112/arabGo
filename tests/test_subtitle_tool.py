import unittest
import os
import shutil
import tempfile
from core.domain import SubtitleDocument, SubtitleBlock
from core.vtt_converter import vtt_to_srt_content, normalize_file
from core.chunking import split_document
from core.session import TranslationSession

class TestSubtitleTool(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_vtt_to_srt_normalization(self):
        vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nHello <i>World</i>\n\n"
        srt = vtt_to_srt_content(vtt)
        self.assertIn("1\n00:00:01,000 --> 00:00:04,000\nHello World", srt)

    def test_document_extraction_and_validation(self):
        srt = "1\n00:00:01,000 --> 00:00:02,000\nLine one\n\n2\n00:00:02,000 --> 00:00:03,000\nLine two\n\n"
        doc = SubtitleDocument.from_srt(srt)
        
        extracted = doc.extract_text()
        self.assertEqual(extracted[0], "[1] Line one")
        self.assertEqual(extracted[1], "[2] Line two")
        
        # Test valid translation (Must be Arabic)
        trans = ["[1] ترجمة واحد", "[2] ترجمة اثنان"]
        errors = doc.validate_translation(trans)
        self.assertEqual(len([e for e in errors if "ERROR" in e]), 0)
        
    def test_safe_reinjection(self):
        srt = "1\n00:00:01,000 --> 00:00:02,000\nEnglish\n\n"
        doc = SubtitleDocument.from_srt(srt)
        trans = ["[1] Arabic Text"]
        
        new_srt = doc.inject_translation(trans)
        self.assertEqual(new_srt, "1\n00:00:01,000 --> 00:00:02,000\nArabic Text\n\n")

    def test_chunk_splitting(self):
        # Create doc with 10 blocks
        blocks = [SubtitleBlock(i, "time", ["text"]) for i in range(1, 11)]
        doc = SubtitleDocument(blocks)
        
        # Split into chunks of 3
        chunks = split_document(doc, max_blocks=3)
        self.assertEqual(len(chunks), 4) # 3, 3, 3, 1
        
        self.assertEqual(chunks[0].chunk_id, 1)
        self.assertEqual(chunks[0].start_index, 1)
        self.assertEqual(chunks[0].end_index, 3)
        self.assertEqual(len(chunks[0].blocks), 3)
        
        self.assertEqual(chunks[3].chunk_id, 4)
        self.assertEqual(chunks[3].start_index, 10)
        self.assertEqual(chunks[3].end_index, 10)
        self.assertEqual(len(chunks[3].blocks), 1)

    def test_translation_session_flow(self):
        blocks = [SubtitleBlock(i, f"T{i}", [f"Orig {i}"]) for i in range(1, 6)]
        doc = SubtitleDocument(blocks)
        
        session = TranslationSession(doc, max_blocks=2) # 3 chunks: [1,2], [3,4], [5]
        self.assertEqual(session.get_chunk_count(), 3)
        
        # Work through chunks
        c1_trans = ["[1] Trans 1", "[2] Trans 2"]
        session.mark_chunk_complete(1, c1_trans)
        self.assertTrue(session.is_chunk_complete(1))
        self.assertFalse(session.all_chunks_completed())
        
        # Final save should be prevented
        with self.assertRaises(RuntimeError):
            session.collect_full_translation()

        # Finish all
        session.mark_chunk_complete(2, ["[3] Trans 3", "[4] Trans 4"])
        session.mark_chunk_complete(3, ["[5] Trans 5"])
        self.assertTrue(session.all_chunks_completed())
        
        full = session.collect_full_translation()
        self.assertEqual(len(full), 5)
        self.assertEqual(full[0], "[1] Trans 1")
        self.assertEqual(full[4], "[5] Trans 5")
        
        # Verify injection order and timestamps
        final_srt = session.document.inject_translation(full)
        self.assertIn("1\nT1\nTrans 1", final_srt)
        self.assertIn("5\nT5\nTrans 5", final_srt)

    def test_vtt_deletion_on_success(self):
        vtt_path = os.path.join(self.test_dir, "test.vtt")
        with open(vtt_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nTest\n\n")
        
        srt_path = normalize_file(vtt_path)
        self.assertTrue(os.path.exists(srt_path))
        self.assertFalse(os.path.exists(vtt_path))

if __name__ == "__main__":
    unittest.main()
