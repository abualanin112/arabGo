import os
import threading
import tempfile
import shutil
from queue import Queue

def scan_directory_threaded(root_path: str, result_queue: Queue):
    """
    Recursively scans for .srt and .vtt files.
    Runs in a background thread.
    """
    def worker():
        try:
            detected_files = []
            for root, dirs, files in os.walk(root_path):
                for file in files:
                    if file.lower().endswith(('.srt', '.vtt')):
                        full_path = os.path.join(root, file)
                        detected_files.append(full_path)
            result_queue.put({"type": "success", "files": detected_files})
        except Exception as e:
            result_queue.put({"type": "error", "message": f"Scan failed: {str(e)}"})

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

def atomic_save(file_path: str, content: str):
    """
    Saves content into file_path using a temporary file.
    Ensures that an incomplete write doesn't corrupt the original.
    """
    dir_name = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    
    with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tmp:
        try:
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_name = tmp.name
        except Exception as e:
            # Cleanup temp file on failure
            tmp.close()
            if os.path.exists(tmp.name):
                os.remove(tmp.name)
            raise e

    # Atomic swap
    try:
        # Move updated content to original location
        # shutil.move is safer across potential filesystem boundaries than os.replace
        shutil.move(tmp_name, file_path)
    except Exception as e:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise e
