from typing import List, Dict, Optional
from .domain import SubtitleDocument
from .chunking import TranslationChunk, split_document

class TranslationSession:
    """
    Manages the state of a chunked translation workflow.
    
    Responsibilities:
    - Track completion status of each chunk
    - Store validated translations per chunk
    - Prevent premature final save
    - Merge translations in correct order
    
    SAFETY GUARANTEES:
    - Does NOT modify the original SubtitleDocument
    - All translations must pass validation before storage
    - Final save requires ALL chunks to be completed
    """
    
    def __init__(self, document: SubtitleDocument, max_blocks: int = 80):
        """
        Initialize a new translation session.
        
        Args:
            document: The SubtitleDocument being translated
            max_blocks: Maximum blocks per chunk
        """
        self.document = document
        self.chunks = split_document(document, max_blocks)
        self.completed_chunks: Dict[int, List[str]] = {}  # chunk_id -> translated_lines
        self.max_blocks = max_blocks
    
    def get_chunk_count(self) -> int:
        """Returns the total number of chunks."""
        return len(self.chunks)
    
    def get_chunk(self, chunk_id: int) -> Optional[TranslationChunk]:
        """
        Get a specific chunk by ID.
        
        Args:
            chunk_id: 1-based chunk identifier
            
        Returns:
            TranslationChunk or None if invalid ID
        """
        if 1 <= chunk_id <= len(self.chunks):
            return self.chunks[chunk_id - 1]
        return None
    
    def mark_chunk_complete(self, chunk_id: int, translated_lines: List[str]):
        """
        Mark a chunk as completed with its validated translation.
        
        PREREQUISITE: Translation must already be validated by caller.
        
        Args:
            chunk_id: 1-based chunk identifier
            translated_lines: Validated translation lines with [ID] markers
        """
        if not (1 <= chunk_id <= len(self.chunks)):
            raise ValueError(f"Invalid chunk_id: {chunk_id}")
        
        self.completed_chunks[chunk_id] = translated_lines
    
    def is_chunk_complete(self, chunk_id: int) -> bool:
        """Check if a specific chunk has been completed."""
        return chunk_id in self.completed_chunks
    
    def all_chunks_completed(self) -> bool:
        """Check if ALL chunks have been completed."""
        return len(self.completed_chunks) == len(self.chunks)
    
    def get_completion_status(self) -> str:
        """Get human-readable completion status."""
        completed = len(self.completed_chunks)
        total = len(self.chunks)
        return f"{completed}/{total} chunks completed"
    
    def collect_full_translation(self) -> List[str]:
        """
        Merge all chunk translations in the correct order.
        
        PREREQUISITE: all_chunks_completed() must be True.
        
        Returns:
            Full ordered list of translated lines with [ID] markers
            
        Raises:
            RuntimeError: If not all chunks are completed
        """
        if not self.all_chunks_completed():
            raise RuntimeError("Cannot collect translation: Not all chunks are completed.")
        
        full_translation = []
        for chunk in self.chunks:
            chunk_translation = self.completed_chunks.get(chunk.chunk_id)
            if chunk_translation is None:
                raise RuntimeError(f"Chunk {chunk.chunk_id} marked complete but data missing.")
            full_translation.extend(chunk_translation)
        
        return full_translation
