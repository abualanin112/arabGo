import re
import os
from .domain import SubtitleDocument

def vtt_to_srt_content(vtt_text: str) -> str:
    """
    Normalization Logic:
    - Removes WEBVTT header and any following metadata.
    - Removes VTT tags <v>, <c>, etc.
    - Converts timestamps HH:MM:SS.mmm -> HH:MM:SS,mmm.
    - Adds numeric block indices.
    """
    if not vtt_text.strip().startswith("WEBVTT"):
        raise ValueError("Invalid WebVTT: Missing WEBVTT header.")

    # Strip header and metadata up to the first blank line
    content = re.sub(r'^WEBVTT.*?\n\s*\n', '', vtt_text, flags=re.DOTALL).strip()
    
    # Strip tags
    content = re.sub(r'<[^>]+>', '', content)
    
    blocks = re.split(r'\n\s*\n', content)
    srt_output = []
    
    current_index = 1
    for block in blocks:
        lines = block.strip().split('\n')
        if not lines:
            continue
            
        timestamp_line = ""
        text_lines = []
        
        for line in lines:
            if " --> " in line:
                timestamp_line = line
            elif timestamp_line:
                text_lines.append(line)
        
        if not timestamp_line:
            continue
            
        # Timestamp conversion: .mmm -> ,mmm
        srt_timestamp = timestamp_line.replace('.', ',')
        
        srt_block = f"{current_index}\n{srt_timestamp}\n" + "\n".join(text_lines)
        srt_output.append(srt_block)
        current_index += 1
        
    return "\n\n".join(srt_output) + "\n\n"

def validate_srt_file(path: str):
    """
    Strict validation of a generated SRT file.
    Must exist, be non-empty, and parseable into at least one block.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"SRT file not found: {path}")
    
    if os.path.getsize(path) == 0:
        raise ValueError(f"SRT file is empty: {path}")
        
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    doc = SubtitleDocument.from_srt(content)
    if not doc.blocks:
        raise ValueError(f"SRT file contains no valid subtitle blocks: {path}")

def normalize_file(file_path: str) -> str:
    """
    If .vtt, converts to .srt, validates the result, and DELETES the original .vtt.
    Returns path to the final .srt.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".srt":
        return file_path
    
    if ext == ".vtt":
        with open(file_path, 'r', encoding='utf-8') as f:
            vtt_content = f.read()
        
        srt_content = vtt_to_srt_content(vtt_content)
        srt_path = os.path.splitext(file_path)[0] + ".srt"
        
        # 1. Write the new file
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)
            
        # 2. Validate the new file
        try:
            validate_srt_file(srt_path)
        except Exception as e:
            # If validation fails, we DON'T delete VTT. 
            # We might even want to remove the broken SRT to be clean.
            if os.path.exists(srt_path):
                os.remove(srt_path)
            raise ValueError(f"Normalization validation failed: {e}")

        # 3. Success! Delete the original VTT
        os.remove(file_path)
        return srt_path
    
    raise ValueError(f"Unsupported format: {ext}")
