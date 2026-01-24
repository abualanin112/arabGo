import os
import sys
import re

def split_srt(input_path, output_dir, chunk_size=600):
    if not os.path.exists(input_path):
        print(f"Error: Input file {input_path} not found.")
        sys.exit(1)

    ext = os.path.splitext(input_path)[1].lower()
    if ext != '.srt':
        print(f"Error: split.py ONLY accepts .srt files. Found {ext}.")
        sys.exit(1)

    lesson_name = os.path.splitext(os.path.basename(input_path))[0]
    lesson_chunk_dir = os.path.join(output_dir, lesson_name)
    os.makedirs(lesson_chunk_dir, exist_ok=True)

    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    # Split by double newline or similar to get blocks
    blocks = re.split(r'\n\s*\n', content)
    
    total_blocks = len(blocks)
    if total_blocks == 0:
        print(f"Warning: No blocks found in {input_path}")
        return

    chunk_count = (total_blocks + chunk_size - 1) // chunk_size

    for i in range(chunk_count):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, total_blocks)
        chunk_blocks = blocks[start:end]
        
        part_num = i + 1
        output_filename = f"{lesson_name}_part_{part_num:02d}.srt"
        output_path = os.path.join(lesson_chunk_dir, output_filename)

        with open(output_path, 'w', encoding='utf-8') as out_f:
            for j, block in enumerate(chunk_blocks):
                lines = block.strip().split('\n')
                if not lines:
                    continue
                
                # Renumber block starting from 1
                lines[0] = str(j + 1)
                out_f.write('\n'.join(lines) + '\n\n')

    print(f"Successfully split {input_path} into {chunk_count} parts in {lesson_chunk_dir}")

def main():
    en_srt_dir = "en_srt"
    chunks_base_dir = "chunks"

    if not os.path.exists(en_srt_dir):
        print(f"Error: {en_srt_dir} directory not found.")
        sys.exit(1)

    srt_files = [f for f in os.listdir(en_srt_dir) if f.lower().endswith('.srt')]
    
    if not srt_files:
        print(f"No .srt files found in {en_srt_dir}")
        return

    for srt_file in srt_files:
        input_path = os.path.join(en_srt_dir, srt_file)
        split_srt(input_path, chunks_base_dir)

if __name__ == "__main__":
    main()
