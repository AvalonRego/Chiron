import os

INPUT_LOG = "/u/arego/Project/Misc/jobs/Out/Track_3156148.out"  # replace with your actual log file path


import string

def extract_path(line: str) -> str | None:
    if "Failed to process" in line or line.startswith("Remove"):
        parts = line.split()
        for part in parts:
            cleaned = part.rstrip(string.punctuation)
            if cleaned.startswith("/") and cleaned.endswith(".h5"):
                return cleaned
    return None



def cleanup_files(log_path: str):
    with open(log_path, "r") as f:
        for line in f:
            file_path = extract_path(line)
            if file_path is None:
                #print(file_path)
                continue
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Removed: {file_path}")
                except Exception as e:
                    print(f"Error removing {file_path}: {e}")
            else:
                print(f'file at {file_path} does not exist')


if __name__ == "__main__":
    print('start')
    cleanup_files(INPUT_LOG)
    print('end')