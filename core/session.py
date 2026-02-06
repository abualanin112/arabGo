import copy
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
    
    def __init__(self, document: SubtitleDocument, max_blocks: int = 50):
        """
        Initialize a new translation session.
        
        Args:
            document: The SubtitleDocument being translated
            max_blocks: Maximum blocks per chunk (default 50)
        """
        self.document = document
        self.chunks = split_document(document, max_blocks)
        self.completed_chunks: Dict[int, List[str]] = {}  # chunk_id -> translated_lines
        self.max_blocks = max_blocks
        self._signature_map: Dict[str, TranslationChunk] = {}  # signature -> chunk
        
        # Build signature lookup map
        for chunk in self.chunks:
            self._signature_map[chunk.signature] = chunk
    
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

    def get_next_pending_chunk(self) -> Optional[TranslationChunk]:
        """
        Returns the first chunk that has not been marked as completed.
        Returns None if all chunks are completed.
        """
        for chunk in self.chunks:
            if not self.is_chunk_complete(chunk.chunk_id):
                return chunk
        return None
    
    def get_chunk_by_signature(self, signature: str) -> Optional[TranslationChunk]:
        """
        Returns a chunk by its deterministic signature.
        This allows for concurrent chunk identification without relying on order.
        
        Args:
            signature: The SHA-256 signature of the chunk
            
        Returns:
            TranslationChunk or None if signature not found
        """
        return self._signature_map.get(signature)
    
    def get_all_signatures(self) -> List[str]:
        """
        Returns all chunk signatures in order.
        Useful for session initialization and diagnostics.
        """
        return [chunk.signature for chunk in self.chunks]

    def rechunk_session(self, new_max_blocks: int) -> Dict[str, int]:
        """
        Transactional resize of session chunks.
        Restores state if any error occurs.
        
        Args:
            new_max_blocks: New chunk size (blocks per chunk)
            
        Returns:
            Dict with migration stats: {'migrated', 'pending', 'total'}
            
        Raises:
            RuntimeError: If rechunking fails (state is rolled back)
        """
        # 1. Snapshot for Rollback
        original_state = {
            "max_blocks": self.max_blocks,
            "chunks": self.chunks,
            # Deepcopy essential to prevent mutation of the backup
            "completed_chunks": copy.deepcopy(self.completed_chunks),
            "signature_map": self._signature_map
        }
        
        try:
            # 2. Harvest Progress (Atomic Block Level)
            # Map: absolute_block_index -> translated_line
            translated_map = {}
            for chunk_id, lines in self.completed_chunks.items():
                chunk = self.chunks[chunk_id - 1]
                for i, line in enumerate(lines):
                     # inclusive start, inclusive end logic from chunking.py
                     # Block indices are 1-based usually, but here we rely on chunk.start_index
                     # chunk.start_index is from the split_document logic
                     abs_index = chunk.start_index + i
                     translated_map[abs_index] = line
            
            # 3. Apply New Structure
            self.max_blocks = new_max_blocks
            self.chunks = split_document(self.document, new_max_blocks)
            self.completed_chunks = {}
            self._signature_map = {c.signature: c for c in self.chunks}
            
            # 4. Redistribute Progress
            migrated_count = 0
            pending_count = 0
            
            for chunk in self.chunks:
                chunk_lines = []
                all_present = True
                
                # Check coverage for this new chunk
                # split_document uses inclusive ranges [start, end]
                for idx in range(chunk.start_index, chunk.end_index + 1):
                    if idx in translated_map:
                        chunk_lines.append(translated_map[idx])
                    else:
                        all_present = False
                        # If even one line is missing, the chunk is NOT complete.
                        # We do NOT partially fill it here to keep state simple:
                        # Either it's DONE (in completed_chunks) or PENDING (not in dict).
                        break
                
                if all_present:
                    self.completed_chunks[chunk.chunk_id] = chunk_lines
                    migrated_count += 1
                else:
                    pending_count += 1
            
            return {
                "migrated": migrated_count,
                "pending": pending_count,
                "total": len(self.chunks)
            }
            
        except Exception as e:
            # 5. Rollback on Failure
            self.max_blocks = original_state["max_blocks"]
            self.chunks = original_state["chunks"]
            self.completed_chunks = original_state["completed_chunks"]
            self._signature_map = original_state["signature_map"]
            raise RuntimeError(f"Rechunk failed, state rolled back: {e}")
