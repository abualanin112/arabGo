import os
import sys
import re

def count_blocks(filepath):
    if not os.path.exists(filepath):
        return 0
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    if not content:
        return 0
    
    if not filepath.lower().endswith('.srt'):
        print(f"Error: check_consistency.py ONLY accepts .srt files. Found {filepath}.")
        sys.exit(1)

    # Split by double newline to count subtitle blocks
    blocks = re.split(r'\n\s*\n', content)
    return len(blocks)

def main():
    go_done_dir = "go_done"
    chunks_base_dir = "chunks"
    
    if not os.path.exists(go_done_dir):
        print("go_done directory does not exist.")
        return

    errors_found = False
    
    done_files = [f for f in os.listdir(go_done_dir) if f.lower().endswith('.go.srt')]
    
    if not done_files:
        print("No completed chunks found in go_done/.")
        return

    for done_file in done_files:
        # done_file: lesson_part_01.go.srt
        # original_file: chunks/lesson/lesson_part_01.srt
        
        basename = done_file.replace('.go.srt', '')
        lesson_name = basename.rsplit('_part_', 1)[0]
        
        orig_filename = basename + ".srt"
        orig_path = os.path.join(chunks_base_dir, lesson_name, orig_filename)
        done_path = os.path.join(go_done_dir, done_file)
        
        if not os.path.exists(orig_path):
            print(f"Error: Original chunk not found for {done_file} at {orig_path}")
            errors_found = True
            continue
            
        orig_count = count_blocks(orig_path)
        done_count = count_blocks(done_path)
        
        if orig_count != done_count:
            print(f"Mismatch in {done_file}: Original={orig_count}, Translated={done_count}")
            errors_found = True
        else:
            print(f"OK: {done_file} ({done_count} blocks)")

    if errors_found:
        print("\nConsistency check FAILED.")
        sys.exit(1)
    else:
        print("\nConsistency check PASSED.")

if __name__ == "__main__":
    main()
