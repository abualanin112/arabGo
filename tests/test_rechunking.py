import unittest
import copy
from core.domain import SubtitleDocument, SubtitleBlock
from core.session import TranslationSession

class TestDynamicRechunking(unittest.TestCase):
    def setUp(self):
        # Create a document with 100 blocks
        blocks = []
        for i in range(1, 101):
            blocks.append(SubtitleBlock(i, f"00:00:{i:02d} --> 00:00:{i+1:02d}", [f"Line {i}"]))
        self.doc = SubtitleDocument(blocks)
        
    def test_rechunk_exact_preservation(self):
        """Test resizing where boundaries align perfectly (10 -> 20)"""
        session = TranslationSession(self.doc, max_blocks=10) # 10 chunks of 10
        
        # Complete chunks 1 and 2 (Blocks 1-20)
        # Note: blocks are 1-based, but our mocked validation/injection doesn't strictly matter for rechunking
        # We just need to simulate "completed chunks" in the dictionary
        
        # Simulate completion of Chunk 1 (Blocks 1-10)
        session.completed_chunks[1] = [f"[1] Trans {i}" for i in range(1, 11)]
        # Simulate completion of Chunk 2 (Blocks 11-20)
        session.completed_chunks[2] = [f"[1] Trans {i}" for i in range(11, 21)]
        
        # Resize to 20
        stats = session.rechunk_session(20)
        
        # Expect: 100 blocks / 20 = 5 total chunks
        self.assertEqual(len(session.chunks), 5)
        self.assertEqual(stats['total'], 5)
        
        # Blocks 1-20 are now Chunk 1. It should be complete.
        self.assertTrue(session.is_chunk_complete(1))
        self.assertEqual(len(session.completed_chunks), 1)
        self.assertEqual(stats['migrated'], 1)
        
    def test_rechunk_partial_migration(self):
        """Test resizing where boundaries split a completed chunk"""
        session = TranslationSession(self.doc, max_blocks=50) # 2 chunks (1-50, 51-100)
        
        # Complete Chunk 1 (Blocks 1-50)
        session.completed_chunks[1] = [f"[{i}] Trans" for i in range(1, 51)]
        
        # Resize to 40
        # New Chunks:
        # 1: 1-40 (Covered by old Chunk 1) -> Should be DONE
        # 2: 41-80 (41-50 covered, 51-80 missing) -> Should be PENDING
        # 3: 81-100 -> PENDING
        
        stats = session.rechunk_session(40)
        
        self.assertTrue(session.is_chunk_complete(1))
        self.assertFalse(session.is_chunk_complete(2)) # Partial
        
        self.assertEqual(stats['migrated'], 1)
        
    def test_rollback_on_failure(self):
        """Test that state is restored if rechunking fails"""
        session = TranslationSession(self.doc, max_blocks=10)
        session.completed_chunks[1] = ["dummy"]
        
        # Inject a fault? We can't easily inject inside the method without mock patches.
        # But we can verify that the method catches exceptions if we pass invalid args?
        # split_document raises ValueError for size <= 0
        
        with self.assertRaises(RuntimeError):
            session.rechunk_session(0) # Invalid size
            
        # Verify rollback: size should still be 10, completed_chunks preserved
        self.assertEqual(session.max_blocks, 10)
        self.assertEqual(len(session.completed_chunks), 1)

if __name__ == '__main__':
    unittest.main()
