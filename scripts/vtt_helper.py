import re
import os

def vtt_to_srt(vtt_content):
    """
    Converts VTT content to SRT format.
    - Validates WEBVTT header.
    - Removes WEBVTT header and metadata.
    - Converts timestamps HH:MM:SS.mmm -> HH:MM:SS,mmm.
    - Injects numeric indexes.
    - Removes VTT-specific tags.
    """
    if not vtt_content.strip().startswith("WEBVTT"):
        raise ValueError("Invalid VTT: Missing WEBVTT header.")

    # Remove header and metadata (up to first blank line)
    content = re.sub(r'^WEBVTT.*?\n\s*\n', '', vtt_content, flags=re.DOTALL).strip()
    
    # Remove VTT tags like <v ...> or <c>
    content = re.sub(r'<[^>]+>', '', content)

    blocks = re.split(r'\n\s*\n', content)
    srt_blocks = []
    
    for i, block in enumerate(blocks):
        lines = block.strip().split('\n')
        if not lines:
            continue
        
        # Determine if first line is a timestamp or a label
        # In simple VTT, first line is timestamp. In some, it might have a label above it.
        # But for our workflow, we assume standard blocks.
        timestamp_line = ""
        text_lines = []
        
        for line in lines:
            if " --> " in line:
                timestamp_line = line
            elif timestamp_line:
                text_lines.append(line)
        
        if not timestamp_line:
            continue # Skip malformed blocks
            
        # Convert timestamp: 00:00:00.000 --> 00:00:04.000 => 00:00:00,000 --> 00:00:04,000
        srt_timestamp = timestamp_line.replace('.', ',')
        
        srt_block = f"{i + 1}\n{srt_timestamp}\n" + "\n".join(text_lines)
        srt_blocks.append(srt_block)
        
    return "\n\n".join(srt_blocks) + "\n\n"

def srt_to_vtt(srt_content):
    """
    Converts SRT content to VTT format.
    - Adds WEBVTT header.
    - Converts timestamps HH:MM:SS,mmm -> HH:MM:SS.mmm.
    - Removes numeric indexes.
    """
    blocks = re.split(r'\n\s*\n', srt_content.strip())
    vtt_blocks = ["WEBVTT\n"]
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
            
        # Skip numbering (line 0)
        timestamp_line = lines[1]
        text_lines = lines[2:]
        
        if " --> " not in timestamp_line:
            continue
            
        vtt_timestamp = timestamp_line.replace(',', '.')
        vtt_block = f"{vtt_timestamp}\n" + "\n".join(text_lines)
        vtt_blocks.append(vtt_block)
        
    return "\n\n".join(vtt_blocks) + "\n\n"

def convert_file_vtt_to_srt(vtt_path):
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    srt_content = vtt_to_srt(content)
    srt_path = os.path.splitext(vtt_path)[0] + ".srt"
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)
    return srt_path

def convert_file_srt_to_vtt(srt_path, vtt_path=None):
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    vtt_content = srt_to_vtt(content)
    if not vtt_path:
        vtt_path = os.path.splitext(srt_path)[0] + ".vtt"
    with open(vtt_path, 'w', encoding='utf-8') as f:
        f.write(vtt_content)
    return vtt_path
