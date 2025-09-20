# file: find_error_occurrences.py

import os
import sys

ERROR_STRING = "Unable to open/create file"

def search_in_file(filepath: str):
    """Search for ERROR_STRING in a single file, print occurrences."""
    try:
        with open(filepath, "r", errors="ignore") as f:
            for line in f:
                if ERROR_STRING in line:
                    print(f"{filepath}: {line.strip()}")
    except (PermissionError, OSError):
        return


def search_in_directory(root_dir: str):
    """Recursively search through all files in the directory."""
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            fullpath = os.path.join(dirpath, fname)
            search_in_file(fullpath)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python find_error_occurrences.py <directory_path>")
        sys.exit(1)

    directory = sys.argv[1]
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        sys.exit(1)

    search_in_directory(directory)
