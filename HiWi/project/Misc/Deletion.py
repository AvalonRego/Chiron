import os

INPUT_LOG = "/u/arego/project/Misc/jobs/Out/Track_21611515.out"  # replace with your actual log file path



def extract_path(line: str) -> str | None:
    if "Failed to process" in line or line.startswith("Remove"):
        parts = line.split()
        for part in parts:
            if part.startswith("/") and part.endswith(".h5"):
                return part
    return None


def cleanup_files(log_path: str):
    with open(log_path, "r") as f:
        for line in f:
            file_path = extract_path(line)
            if file_path is None:
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
    cleanup_files(INPUT_LOG)
