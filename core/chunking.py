from dataclasses import dataclass, field
from typing import List
from .domain import SubtitleBlock, SubtitleDocument
import hashlib
import re

@dataclass
class TranslationChunk:
    """
    Represents a READ-ONLY view of a portion of a SubtitleDocument.
    Used for managing large files in digestible segments.
    
    Includes a deterministic signature for concurrent chunk identification.
    """
    chunk_id: int
    start_index: int  # Original block index (NOT zero-based chunk position)
    end_index: int    # Original block index (inclusive)
    blocks: List[SubtitleBlock]
    signature: str = field(default="")  # SHA-256 hash of block IDs

    def extract_text(self) -> List[str]:
        """Extract text with [ID] markers for this chunk only."""
        text_view = []
        for block in self.blocks:
            joined_text = " ".join(block.text_lines)
            text_view.append(f"[{block.index}] {joined_text}")
        return text_view
    
    def extract_text_with_signature(self) -> str:
        """
        Extract text with embedded signature header for AI processing.
        The signature is machine-readable and should be preserved during translation.
        """
        lines = self.extract_text()
        signature_header = f"@@CHUNK_SIGNATURE={self.signature}@@"
        return signature_header + "\n" + "\n".join(lines)
    
    @staticmethod
    def extract_signature_from_text(text: str) -> tuple[str, str]:
        """
        Extracts and removes the signature header from translated text.
        Handles cases where the signature might be on its own line or prefixed.
        
        Returns:
            (signature, cleaned_text) tuple
        """
        signature_pattern = r'@@CHUNK_SIGNATURE=([a-f0-9]+)@@'
        match = re.search(signature_pattern, text)
        
        if match:
            signature = match.group(1)
            # Remove the signature header from the text
            cleaned_text = re.sub(signature_pattern, '', text).strip()
            return signature, cleaned_text
        
        return "", text.strip()

def _generate_chunk_signature(blocks: List[SubtitleBlock]) -> str:
    """
    Generates a deterministic SHA-256 signature for a chunk based on block IDs.
    This allows for concurrent chunk identification without relying on order.
    """
    block_ids = "-".join(str(block.index) for block in blocks)
    return hashlib.sha256(block_ids.encode('utf-8')).hexdigest()[:16]

def split_document(document: SubtitleDocument, max_blocks: int = 80) -> List[TranslationChunk]:
    """
    Splits a SubtitleDocument into TranslationChunks.
    
    IMPORTANT:
    - Does NOT modify the original document
    - Creates READ-ONLY views
    - Preserves original block indices
    - No renumbering occurs
    - Generates deterministic signatures for concurrent chunk matching
    
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
        
        signature = _generate_chunk_signature(chunk_blocks)
        
        chunk = TranslationChunk(
            chunk_id=chunk_id,
            start_index=chunk_blocks[0].index,
            end_index=chunk_blocks[-1].index,
            blocks=chunk_blocks,
            signature=signature
        )
        chunks.append(chunk)
        chunk_id += 1
    
    return chunks
