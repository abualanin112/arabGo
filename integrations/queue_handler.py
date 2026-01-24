# integrations/queue_handler.py
import queue

# Global queue for incoming translations
# Format: {"chunk_id": int, "translation": str}
translation_queue = queue.Queue()

def push_translation(chunk_id: int, translation: str):
    """Pushes a received translation into the queue."""
    translation_queue.put({"chunk_id": chunk_id, "translation": translation})

def pop_translation():
    """Pops a translation from the queue if available."""
    try:
        return translation_queue.get_nowait()
    except queue.Empty:
        return None
