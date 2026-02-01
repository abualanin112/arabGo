import re
import os
import logging
from .domain import SubtitleDocument

logger = logging.getLogger("vtt_converter")

def vtt_to_srt_content(vtt_text: str) -> str:
    """
    Normalization Logic:
    - Removes WEBVTT header and any following metadata (handling multiple lines).
    - Removes VTT-specific tags like <v>, <c>, <i>, <b>, <u> safely.
    - Converts timestamps HH:MM:SS.mmm -> HH:MM:SS,mmm using precise regex.
    - Adds numeric block indices sequentially, avoiding gaps.
    - Handles VTT Cue Identifiers.
    """
    if not vtt_text.strip().startswith("WEBVTT"):
        raise ValueError("Invalid WebVTT: Missing WEBVTT header.")

    # 1. Improved Header & Metadata removal
    lines = vtt_text.strip().split('\n')
    start_idx = 0
    for i, line in enumerate(lines):
        if " --> " in line:
            if i > 0 and lines[i-1].strip() and not lines[i-1].strip().startswith("WEBVTT"):
                start_idx = i - 1
            else:
                start_idx = i
            break
    
    content_lines = lines[start_idx:]
    raw_content = '\n'.join(content_lines)
    blocks = re.split(r'\n\s*\n', raw_content)
    
    srt_output = []
    current_index = 1
    
    for block in blocks:
        block_lines = block.strip().split('\n')
        if not block_lines:
            continue
            
        timestamp_line = ""
        text_lines = []
        found_timestamp = False
        
        for line in block_lines:
            if " --> " in line:
                timestamp_line = line
                found_timestamp = True
            elif found_timestamp:
                clean_line = re.sub(r'</?(?:v|c|i|b|u)(?:\s[^>]*)?>', '', line)
                text_lines.append(clean_line)
        
        if not timestamp_line or not text_lines:
            continue
            
        srt_timestamp = re.sub(r'(\d{2}:\d{2}:\d{2})\.(\d{3})', r'\1,\2', timestamp_line)
        srt_block = f"{current_index}\n{srt_timestamp}\n" + "\n".join(text_lines)
        srt_output.append(srt_block)
        current_index += 1
        
    return "\n\n".join(srt_output) + "\n\n"

def srt_to_vtt_content(srt_content: str) -> str:
    """
    Converts SRT content to VTT format.
    - Adds WEBVTT header.
    - Converts timestamps HH:MM:SS,mmm -> HH:MM:SS.mmm.
    - Removes numeric indices.
    """
    blocks = re.split(r'\n\s*\n', srt_content.strip())
    vtt_blocks = ["WEBVTT\n"]
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
            
        timestamp_line = lines[1]
        text_lines = lines[2:]
        
        if " --> " not in timestamp_line:
            if " --> " in lines[0]:
                timestamp_line = lines[0]
                text_lines = lines[1:]
            else:
                continue
            
        vtt_timestamp = timestamp_line.replace(',', '.')
        vtt_block = f"{vtt_timestamp}\n" + "\n".join(text_lines)
        vtt_blocks.append(vtt_block)
        
    return "\n\n".join(vtt_blocks) + "\n\n"

def validate_srt_file(path: str):
    """
    Strict validation of a generated SRT file.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"SRT file not found: {path}")
    
    if os.path.getsize(path) == 0:
        raise ValueError(f"SRT file is empty: {path}")
        
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc = SubtitleDocument.from_srt(content)
        if not doc.blocks:
            raise ValueError(f"SRT file contains no valid subtitle blocks: {path}")
    except Exception as e:
        raise ValueError(f"SRT Parse Verification Error: {e}")

def normalize_file(file_path: str) -> str:
    """
    If .vtt, converts to .srt, validates the result, and DELETES the original .vtt.
    Returns path to the final .srt.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".srt":
        return file_path
    
    if ext == ".vtt":
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                vtt_content = f.read()
            
            srt_content = vtt_to_srt_content(vtt_content)
            srt_path = os.path.splitext(file_path)[0] + ".srt"
            
            with open(srt_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
                
            try:
                validate_srt_file(srt_path)
            except Exception as e:
                if os.path.exists(srt_path):
                    os.remove(srt_path)
                raise ValueError(f"Normalization validation failed: {e}")

            os.remove(file_path)
            logger.info(f"Successfully normalized {os.path.basename(file_path)} to {os.path.basename(srt_path)}")
            return srt_path
        except Exception as e:
            logger.error(f"Failed to normalize {file_path}: {e}")
            raise
    
    raise ValueError(f"Unsupported format: {ext}")

def convert_file_srt_to_vtt(srt_path: str, vtt_path: str = None) -> str:
    """Helper to convert an SRT file to a VTT file."""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    vtt_content = srt_to_vtt_content(content)
    if not vtt_path:
        vtt_path = os.path.splitext(srt_path)[0] + ".vtt"
    with open(vtt_path, 'w', encoding='utf-8') as f:
        f.write(vtt_content)
    return vtt_path

def convert_file_vtt_to_srt(vtt_path: str) -> str:
    """Helper to convert a VTT file to an SRT file."""
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    srt_content = vtt_to_srt_content(content)
    srt_path = os.path.splitext(vtt_path)[0] + ".srt"
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)
    return srt_path
