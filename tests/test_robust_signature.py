# tests/test_robust_signature.py
import unittest
from core.chunking import TranslationChunk

class TestRobustSignature(unittest.TestCase):
    def test_signature_no_newline(self):
        # Mimic user's log input where there is no newline after the signature
        text = "@@CHUNK_SIGNATURE=3bc6ef34edb5c0fc@@ [321] some translation text"
        signature, cleaned = TranslationChunk.extract_signature_from_text(text)
        
        self.assertEqual(signature, "3bc6ef34edb5c0fc")
        self.assertEqual(cleaned, "[321] some translation text")

    def test_signature_with_newline(self):
        # Verify it still works with newlines
        text = "@@CHUNK_SIGNATURE=3bc6ef34edb5c0fc@@\n[321] some translation text"
        signature, cleaned = TranslationChunk.extract_signature_from_text(text)
        
        self.assertEqual(signature, "3bc6ef34edb5c0fc")
        self.assertEqual(cleaned, "[321] some translation text")

    def test_no_signature(self):
        text = "[321] some translation text"
        signature, cleaned = TranslationChunk.extract_signature_from_text(text)
        
        self.assertEqual(signature, "")
        self.assertEqual(cleaned, "[321] some translation text")

if __name__ == "__main__":
    unittest.main()
