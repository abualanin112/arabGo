import os
import sys

def get_pending_chunks(chunks_dir, go_done_dir):
    pending = []
    
    if not os.path.exists(chunks_dir):
        print(f"Error: {chunks_dir} directory not found.")
        sys.exit(1)
        
    if not os.path.exists(go_done_dir):
        os.makedirs(go_done_dir, exist_ok=True)

    # chunks/ contains subfolders for each lesson
    for lesson in os.listdir(chunks_dir):
        lesson_path = os.path.join(chunks_dir, lesson)
        if not os.path.isdir(lesson_path):
            continue
            
        for chunk_file in os.listdir(lesson_path):
            if not chunk_file.lower().endswith('.srt'):
                continue
                
            # expected output name: lesson_part_NN.go.srt
            expected_done = chunk_file.replace('.srt', '.go.srt')
            if not os.path.exists(os.path.join(go_done_dir, expected_done)):
                pending.append(f"{lesson}/{chunk_file}")
                
    return pending

def main():
    chunks_dir = "chunks"
    go_done_dir = "go_done"
    qc_dir = "qc"
    pending_file = os.path.join(qc_dir, "pending.txt")
    
    os.makedirs(qc_dir, exist_ok=True)
    
    pending = get_pending_chunks(chunks_dir, go_done_dir)
    
    with open(pending_file, 'w', encoding='utf-8') as f:
        for item in sorted(pending):
            f.write(item + '\n')
            
    if pending:
        print(f"Status: {len(pending)} chunks pending. See {pending_file}")
    else:
        print("Status: All chunks processed!")

if __name__ == "__main__":
    main()
