import unittest
import os
import sys
import shutil

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.vtt_converter import vtt_to_srt_content, srt_to_vtt_content

class TestVTTEdgeCases(unittest.TestCase):
    def test_vtt_with_metadata_and_cues(self):
        vtt = """WEBVTT
Kind: captions
Language: ar

cue-1
00:00:01.000 --> 00:00:04.000
<v Speaker>مرحبا بكم</v>

cue-2
00:00:05.500 --> 00:00:08.750
هذا <i>نص</i> تجريبي

00:00:10.000 --> 00:00:12.000
نص بدون cue identifier
"""
        srt = vtt_to_srt_content(vtt)
        
        # Check consecutive indexing
        self.assertTrue(srt.startswith("1\n"))
        self.assertIn("2\n00:00:05,500 --> 00:00:08,750", srt)
        self.assertIn("3\n00:00:10,000 --> 00:00:12,000", srt)
        
        # Check tag removal
        self.assertIn("مرحبا بكم", srt)
        self.assertNotIn("<v", srt)
        self.assertIn("نص تجريبي", srt)
        self.assertNotIn("<i>", srt)
        
        # Check timestamps
        self.assertIn("00:00:01,000", srt)
        self.assertIn("00:00:05,500", srt)

    def test_vtt_with_empty_blocks(self):
        vtt = """WEBVTT

1
00:00:01.000 --> 00:00:02.000
Valid Text

00:00:03.000 --> 00:00:04.000

2
00:00:05.000 --> 00:00:06.000
Another Block
"""
        srt = vtt_to_srt_content(vtt)
        # Should skip the empty block and re-index
        self.assertIn("1\n00:00:01,000", srt)
        self.assertIn("2\n00:00:05,000", srt)
        self.assertNotIn("00:00:03,000", srt)

    def test_srt_to_vtt_back_and_forth(self):
        srt = """1
00:00:01,000 --> 00:00:04,000
Hello World

2
00:00:05,000 --> 00:00:08,000
Testing VTT
"""
        vtt = srt_to_vtt_content(srt)
        self.assertTrue(vtt.startswith("WEBVTT\n"))
        self.assertIn("00:00:01.000 --> 00:00:04.000", vtt)
        self.assertIn("Hello World", vtt)
        
        # Back to SRT
        srt_back = vtt_to_srt_content(vtt)
        self.assertIn("1\n00:00:01,000 --> 00:00:04,000", srt_back)
        self.assertIn("Hello World", srt_back)


    def test_vtt_with_short_timestamps(self):
        """Test VTT files with MM:SS.mmm format (without hours)"""
        vtt = """WEBVTT
X-TIMESTAMP-MAP=LOCAL:00:00:00.000,MPEGTS:0

00:05.189 --> 00:11.860
Relative pronouns are THAT, WHICH, WHO, WHOM

00:11.860 --> 00:18.930
They are used to introduce more information

01:05.250 --> 01:08.890
This has minutes over 60 seconds (edge case)
"""
        srt = vtt_to_srt_content(vtt)
        
        # Check that output is not empty
        self.assertTrue(srt.strip(), "SRT output should not be empty")
        
        # Check proper conversion to full format with hours
        self.assertIn("1\n00:00:05,189 --> 00:00:11,860", srt)
        self.assertIn("2\n00:00:11,860 --> 00:00:18,930", srt)
        self.assertIn("3\n00:01:05,250 --> 00:01:08,890", srt)
        
        # Check text preservation
        self.assertIn("Relative pronouns", srt)
        self.assertIn("introduce more information", srt)

    def test_vtt_mixed_timestamp_formats(self):
        """Test VTT with both short (MM:SS.mmm) and long (HH:MM:SS.mmm) formats"""
        vtt = """WEBVTT

00:05.100 --> 00:10.200
Short format subtitle

01:00:15.300 --> 01:00:20.400
Long format subtitle with hours
"""
        srt = vtt_to_srt_content(vtt)
        
        # Both should be properly converted
        self.assertIn("00:00:05,100 --> 00:00:10,200", srt)
        self.assertIn("01:00:15,300 --> 01:00:20,400", srt)

    def test_vtt_edge_case_timestamps(self):
        """Test edge cases: exactly 1 hour, 59:59, etc."""
        vtt = """WEBVTT

59:59.999 --> 01:00:00.000
Just before one hour to exactly one hour
"""
        srt = vtt_to_srt_content(vtt)
        
        # 59:59.999 should become 00:59:59,999
        # 01:00:00.000 should become 01:00:00,000
        self.assertIn("00:59:59,999 --> 01:00:00,000", srt)

if __name__ == "__main__":
    unittest.main()
