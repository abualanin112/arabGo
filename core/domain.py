import re
from dataclasses import dataclass
from typing import List

@dataclass
class SubtitleBlock:
    index: int
    timestamp_line: str
    text_lines: List[str]

    def to_srt(self) -> str:
        return f"{self.index}\n{self.timestamp_line}\n" + "\n".join(self.text_lines)

class SubtitleDocument:
    def __init__(self, blocks: List[SubtitleBlock]):
        self.blocks = blocks

    @classmethod
    def from_srt(cls, content: str) -> 'SubtitleDocument':
        blocks = []
        # Use regex to find potential blocks split by double newlines or single if it follows indices
        raw_blocks = re.split(r'\n\s*\n', content.strip())
        for raw_block in raw_blocks:
            lines = raw_block.strip().split('\n')
            if len(lines) < 2:
                continue
            
            try:
                # Basic SRT format: Line 1 is index, Line 2 is timestamp
                # More robust parsing would check for timestamp pattern on lines[1]
                index = int(lines[0])
                timestamp_line = lines[1]
                text_lines = lines[2:]
                blocks.append(SubtitleBlock(index, timestamp_line, text_lines))
            except (ValueError, IndexError):
                continue # Skip malformed or non-subtitle blocks
        return cls(blocks)

    def extract_text(self) -> List[str]:
        """Returns a list of text strings, one per block, prefixed with [ID]."""
        text_view = []
        for block in self.blocks:
            joined_text = " ".join(block.text_lines)
            text_view.append(f"[{block.index}] {joined_text}")
        return text_view

    def validate_translation(self, translated_lines: List[str]) -> List[str]:
        """
        Validates a list of translated lines (from UI) against the original document.
        Returns a list of error/warning strings.
        """
        results = []
        
        # 1. Structural Validation
        if len(translated_lines) != len(self.blocks):
            results.append(f"CRITICAL ERROR: Block count mismatch. Original has {len(self.blocks)}, Translation has {len(translated_lines)}.")
            return results # Stop here for structural errors

        # 2. Identity and Content Validation
        for i, (block, trans_text) in enumerate(zip(self.blocks, translated_lines)):
            line_num = i + 1
            
            # Extract ID from [ID] text
            match = re.match(r'^\[(\d+)\]', trans_text.strip())
            if not match:
                results.append(f"ERROR (Line {line_num}): Missing or malformed ID marker [ID].")
                continue
            
            trans_id = int(match.group(1))
            if trans_id != block.index:
                results.append(f"ERROR (Line {line_num}): ID mismatch. Expected [{block.index}], found [{trans_id}].")
                
            content = trans_text[match.end():].strip()
            if not content:
                results.append(f"WARNING (Line {line_num}): Block [{block.index}] has empty text content.")

        return results

    def inject_translation(self, translated_lines: List[str]) -> str:
        """
        Recombines translated text with original structure.
        Requires validation to have passed (structural match).
        """
        new_blocks = []
        for i, block in enumerate(self.blocks):
            # Strip the ID marker
            clean_text = re.sub(r'^\[\d+\]\s*', '', translated_lines[i]).strip()
            # We treat the entire clean_text as a single line or preserve lines if needed
            # For this simple implementation, we'll keep it as a single-line block
            new_block = SubtitleBlock(
                index=block.index,
                timestamp_line=block.timestamp_line,
                text_lines=[clean_text]
            )
            new_blocks.append(new_block.to_srt())
            
        return "\n\n".join(new_blocks) + "\n\n"
