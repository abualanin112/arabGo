import os
import subprocess
import sys
from datetime import datetime

# Import vtt_helper from scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
try:
    import vtt_helper
except ImportError:
    vtt_helper = None

def get_base_path():
    """Returns the base project directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def run_script(script_name, log_callback):
    """Runs a script from the scripts/ directory as a subprocess."""
    base_path = get_base_path()
    script_path = os.path.join(base_path, "scripts", script_name)
    
    if not os.path.exists(script_path):
        log_callback(f"ERROR: Script not found: {script_path}")
        return False
    
    try:
        log_callback(f"RUNNING: {script_name}...")
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=base_path
        )
        stdout, stderr = process.communicate()
        
        if stdout:
            log_callback(stdout.strip())
        if stderr:
            log_callback(f"ERROR: {stderr.strip()}")
            
        if process.returncode == 0:
            log_callback(f"SUCCESS: {script_name} finished.")
            return True
        else:
            log_callback(f"FAILED: {script_name} exited with code {process.returncode}.")
            return False
            
    except Exception as e:
        log_callback(f"CRITICAL ERROR: {str(e)}")
        return False

def check_and_convert_imports(log_callback):
    """Detects .vtt files in en_srt and converts them to .srt."""
    base_path = get_base_path()
    en_srt_dir = os.path.join(base_path, "en_srt")
    
    if not os.path.exists(en_srt_dir):
        return
        
    vtt_files = [f for f in os.listdir(en_srt_dir) if f.lower().endswith(".vtt")]
    
    for vtt_file in vtt_files:
        vtt_path = os.path.join(en_srt_dir, vtt_file)
        srt_path = os.path.splitext(vtt_path)[0] + ".srt"
        
        if os.path.exists(srt_path):
            log_callback(f"SKIP: {vtt_file} (SRT version already exists).")
            continue
            
        try:
            log_callback(f"IMPORT: Converting {vtt_file} to SRT...")
            if vtt_helper:
                vtt_helper.convert_file_vtt_to_srt(vtt_path)
                log_callback(f"SUCCESS: Created {os.path.basename(srt_path)}.")
            else:
                log_callback("ERROR: vtt_helper module not found.")
        except Exception as e:
            log_callback(f"ERROR: Could not convert {vtt_file}: {e}")

def export_to_vtt(srt_path, log_callback):
    """Exports a final SRT file to VTT."""
    if not vtt_helper:
        log_callback("ERROR: vtt_helper not found.")
        return False
        
    try:
        vtt_path = vtt_helper.convert_file_srt_to_vtt(srt_path)
        log_callback(f"EXPORT: Final VTT created at {os.path.basename(vtt_path)}.")
        return True
    except Exception as e:
        log_callback(f"ERROR: Export failed: {e}")
        return False

def get_stats():
    """Calculates project statistics for the dashboard."""
    base_path = get_base_path()
    stats = {
        "srt_count": 0,
        "chunk_count": 0,
        "done_count": 0,
        "pending_count": 0
    }
    
    en_srt_dir = os.path.join(base_path, "en_srt")
    chunks_dir = os.path.join(base_path, "chunks")
    go_done_dir = os.path.join(base_path, "go_done")
    pending_file = os.path.join(base_path, "qc", "pending.txt")
    
    if os.path.exists(en_srt_dir):
        # Only canonical SRTs count towards pipeline progress
        stats["srt_count"] = len([f for f in os.listdir(en_srt_dir) if f.lower().endswith(".srt")])
        
    if os.path.exists(chunks_dir):
        for root, dirs, files in os.walk(chunks_dir):
            stats["chunk_count"] += len([f for f in files if f.lower().endswith(".srt")])
            
    if os.path.exists(go_done_dir):
        stats["done_count"] = len([f for f in os.listdir(go_done_dir) if f.lower().endswith(".go.srt")])
        
    if os.path.exists(pending_file):
        try:
            with open(pending_file, "r", encoding="utf-8") as f:
                stats["pending_count"] = len([l for l in f.readlines() if l.strip()])
        except Exception:
            pass
            
    return stats

def get_timestamp():
    """Returns a formatted timestamp for logs."""
    return datetime.now().strftime("[%H:%M:%S]")
