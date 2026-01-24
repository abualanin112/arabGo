import os
import sys
import re

def get_chunk_part_number(filename):
    match = re.search(r'_part_(\d+)', filename)
    if match:
        return int(match.group(1))
    return -1

def merge_lesson(lesson_name, chunks_dir, go_done_dir, final_dir):
    lesson_chunk_path = os.path.join(chunks_dir, lesson_name)
    if not os.path.exists(lesson_chunk_path):
        return False

    # 1. Identify all expected chunks
    all_chunks = sorted([f for f in os.listdir(lesson_chunk_path) if f.lower().endswith('.srt')],
                        key=get_chunk_part_number)
    
    if not all_chunks:
        print(f"No .srt chunks found for lesson: {lesson_name}")
        return False

    # 2. Check if all corresponding go_done files exist
    done_paths = []
    missing_chunks = []
    
    for chunk_file in all_chunks:
        expected_done = chunk_file.replace('.srt', '.go.srt')
        done_path = os.path.join(go_done_dir, expected_done)
        
        if not os.path.exists(done_path):
            missing_chunks.append(expected_done)
        else:
            done_paths.append(done_path)

    if missing_chunks:
        print(f"Error: Missing {len(missing_chunks)} chunks for {lesson_name}:")
        for m in missing_chunks:
            print(f"  - {m}")
        print(f"Merge FAILED for {lesson_name}.")
        return False

    # 3. Merge files
    os.makedirs(final_dir, exist_ok=True)
    final_output = os.path.join(final_dir, f"{lesson_name}.ar.final.srt")
    
    total_block_count = 0
    with open(final_output, 'w', encoding='utf-8') as out_f:
        for done_path in done_paths:
            with open(done_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    continue
                
                blocks = re.split(r'\n\s*\n', content)
                for block in blocks:
                    lines = block.strip().split('\n')
                    if not lines:
                        continue
                    
                    total_block_count += 1
                    # Global continuous numbering for SRT
                    lines[0] = str(total_block_count)
                    out_f.write('\n'.join(lines) + '\n\n')

    print(f"Success: Merged {len(done_paths)} chunks into {final_output} ({total_block_count} blocks).")
    return True

def main():
    chunks_dir = "chunks"
    go_done_dir = "go_done"
    final_dir = "final"
    
    if not os.path.exists(chunks_dir):
        print(f"Error: {chunks_dir} not found.")
        sys.exit(1)

    all_success = True
    lessons = [d for d in os.listdir(chunks_dir) if os.path.isdir(os.path.join(chunks_dir, d))]
    
    if not lessons:
        print("No lessons found in chunks/.")
        return

    for lesson in lessons:
        if not merge_lesson(lesson, chunks_dir, go_done_dir, final_dir):
            all_success = False

    if not all_success:
        sys.exit(1)

if __name__ == "__main__":
    main()
