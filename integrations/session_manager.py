# integrations/session_manager.py
import uuid
import threading
from enum import Enum
from typing import Optional, Dict
from datetime import datetime

class ChunkState(Enum):
    """Chunk processing states for concurrency control."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class SessionManager:
    """
    Manages application session lifetime and chunk processing states.
    Ensures thread-safe concurrent translation handling.
    """
    
    def __init__(self):
        self.session_id: str = str(uuid.uuid4())
        self.created_at: datetime = datetime.now()
        self.chunk_states: Dict[str, ChunkState] = {}  # signature -> state
        self.chunk_locks: Dict[str, threading.Lock] = {}  # signature -> lock
        self.final_save_attempted: bool = False
        self._global_lock = threading.Lock()
    
    def get_session_info(self) -> dict:
        """Returns current session information."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "active": True
        }
    
    def initialize_chunk(self, signature: str):
        """Registers a new chunk with PENDING state."""
        with self._global_lock:
            if signature not in self.chunk_states:
                self.chunk_states[signature] = ChunkState.PENDING
                self.chunk_locks[signature] = threading.Lock()
    
    def acquire_chunk(self, signature: str) -> bool:
        """
        Attempts to acquire a chunk for processing.
        Returns True if successful (chunk is PENDING), False otherwise.
        """
        with self._global_lock:
            if signature not in self.chunk_states:
                return False
            
            current_state = self.chunk_states[signature]
            
            # Only PENDING and FAILED chunks can be processed
            if current_state in (ChunkState.PENDING, ChunkState.FAILED):
                self.chunk_states[signature] = ChunkState.PROCESSING
                return True
            
            return False
    
    def mark_chunk_completed(self, signature: str):
        """Marks a chunk as successfully completed."""
        with self._global_lock:
            if signature in self.chunk_states:
                self.chunk_states[signature] = ChunkState.COMPLETED
    
    def mark_chunk_failed(self, signature: str):
        """Marks a chunk as failed (can be retried)."""
        with self._global_lock:
            if signature in self.chunk_states:
                self.chunk_states[signature] = ChunkState.FAILED
    
    def reset_chunk(self, signature: str):
        """Resets a chunk to PENDING state (for manual retry)."""
        with self._global_lock:
            if signature in self.chunk_states:
                self.chunk_states[signature] = ChunkState.PENDING
    
    def get_chunk_state(self, signature: str) -> Optional[ChunkState]:
        """Returns the current state of a chunk."""
        with self._global_lock:
            return self.chunk_states.get(signature)
    
    def get_chunk_lock(self, signature: str) -> Optional[threading.Lock]:
        """Returns the lock for a specific chunk."""
        with self._global_lock:
            return self.chunk_locks.get(signature)

    def can_initiate_final_save(self) -> bool:
        """
        Checks if a final save can be initiated.
        Returns True ONLY if all chunks are COMPLETED and final save hasn't been tried.
        Sets final_save_attempted to True if returning True.
        """
        with self._global_lock:
            if self.final_save_attempted:
                return False
            
            all_done = all(state == ChunkState.COMPLETED for state in self.chunk_states.values())
            if all_done and self.chunk_states: # Ensure there are chunks
                self.final_save_attempted = True
                return True
                
            return False

# Global session manager instance
_session_manager: Optional[SessionManager] = None

def get_session_manager() -> Optional[SessionManager]:
    """Returns the current session manager or None if not initialized."""
    return _session_manager

def initialize_session() -> SessionManager:
    """Initializes a new session manager."""
    global _session_manager
    _session_manager = SessionManager()
    return _session_manager

def terminate_session():
    """Terminates the current session."""
    global _session_manager
    _session_manager = None
