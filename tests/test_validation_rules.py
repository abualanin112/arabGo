import unittest
from core.domain import SubtitleDocument, SubtitleBlock

class TestEnhancedValidation(unittest.TestCase):
    def test_english_character_validation(self):
        # Create a dummy block
        block = SubtitleBlock(1, "00:00:01 --> 00:00:02", ["Original text"])
        doc = SubtitleDocument([block])
        
        # Test case 1: Valid Arabic text
        valid_translation = ["[1] مرحبا بالعالم"]
        errors = doc.validate_translation(valid_translation)
        self.assertEqual(len(errors), 0, "Should have no errors for Arabic text")
        
        # Test case 2: Text with English characters
        invalid_translation = ["[1] Hello world"]
        errors = doc.validate_translation(invalid_translation)
        self.assertTrue(any("English characters" in e for e in errors), "Should detect English characters")
        
        # Test case 3: Mixed text
        mixed_translation = ["[1] مرحبا Hello"]
        errors = doc.validate_translation(mixed_translation)
        self.assertTrue(any("English characters" in e for e in errors), "Should detect mixed English characters")

    def test_empty_line_validation_error(self):
        block = SubtitleBlock(1, "00:00:01 --> 00:00:02", ["Original text"])
        doc = SubtitleDocument([block])
        
        # Test case: Empty content (now ERROR, valid structure)
        empty_translation = ["[1] "]
        errors = doc.validate_translation(empty_translation)
        
        # Before it was WARNING, now it should be ERROR
        # Our implementation uses "ERROR" prefix for strict errors
        self.assertTrue(any("ERROR" in e and "empty text content" in e for e in errors), 
                        "Empty content should now be reported as an ERROR")

if __name__ == '__main__':
    unittest.main()
