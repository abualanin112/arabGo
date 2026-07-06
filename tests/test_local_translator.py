import unittest
from integrations import local_translator

class TestLocalTranslator(unittest.TestCase):
    def setUp(self):
        local_translator._is_initialized = True
        
    def test_auto_correct_english(self):
        # Original text containing English
        text = "[1] Hello world and python movie.objects.get"
        
        corrected = local_translator.auto_correct_english(text)
        
        # Verify english phrases were transliterated phonetically
        # Hello -> هيللو, world -> وورلد, python -> بيثون, movie -> موفيي, objects -> وبجيكتس
        self.assertIn("هيللو", corrected)
        self.assertIn("وورلد", corrected)
        self.assertIn("بيثون", corrected)
        self.assertIn("موفيي", corrected)
        self.assertIn("وبجيكتس", corrected)
        self.assertIn("جيت", corrected)
        
        # Ensure no english characters remain
        self.assertNotIn("python", corrected)
        self.assertNotIn("movie", corrected)
        self.assertNotIn("objects", corrected)
        self.assertNotIn("get", corrected)
        
    def test_auto_correct_uninitialized(self):
        local_translator._is_initialized = False
        text = "Hello world"
        corrected = local_translator.auto_correct_english(text)
        
        # Should return original if not initialized
        self.assertEqual(corrected, text)
        
if __name__ == '__main__':
    unittest.main()
