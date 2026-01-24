from dataclasses import dataclass
from typing import List
from .domain import SubtitleBlock, SubtitleDocument

@dataclass
class TranslationChunk:
    """
    Represents a READ-ONLY view of a portion of a SubtitleDocument.
    Used for managing large files in digestible segments.
    """
    chunk_id: int
    start_index: int  # Original block index (NOT zero-based chunk position)
    end_index: int    # Original block index (inclusive)
    blocks: List[SubtitleBlock]

    def extract_text(self) -> List[str]:
        """Extract text with [ID] markers for this chunk only."""
        text_view = []
        for block in self.blocks:
            joined_text = " ".join(block.text_lines)
            text_view.append(f"[{block.index}] {joined_text}")
        return text_view

def split_document(document: SubtitleDocument, max_blocks: int = 80) -> List[TranslationChunk]:
    """
    Splits a SubtitleDocument into TranslationChunks.
    
    IMPORTANT:
    - Does NOT modify the original document
    - Creates READ-ONLY views
    - Preserves original block indices
    - No renumbering occurs
    
    Args:
        document: The SubtitleDocument to split
        max_blocks: Maximum blocks per chunk (default 80)
        
    Returns:
        List of TranslationChunk objects in order
    """
    if not document.blocks:
        return []
    
    chunks = []
    total_blocks = len(document.blocks)
    chunk_id = 1
    
    for i in range(0, total_blocks, max_blocks):
        end_pos = min(i + max_blocks, total_blocks)
        chunk_blocks = document.blocks[i:end_pos]
        
        chunk = TranslationChunk(
            chunk_id=chunk_id,
            start_index=chunk_blocks[0].index,
            end_index=chunk_blocks[-1].index,
            blocks=chunk_blocks
        )
        chunks.append(chunk)
        chunk_id += 1
    
    return chunks
