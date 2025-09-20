#!/usr/bin/env python3
"""
Simple script to modify paths in text files.
Usage: python simple_modify_paths.py filename.txt
"""

import sys
import os

def modify_paths_in_file(filename, suffix="_EN_100"):
    """Modify paths in a text file, safe to run repeatedly."""
    
    if not os.path.exists(filename):
        print(f"File {filename} not found!")
        return
    
    # Read the file
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    modified_lines = []
    changes = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            modified_lines.append(line)
            continue
        
        # Check if already modified (contains the suffix)
        if suffix in line:
            modified_lines.append(line)
            continue
        
        # Find the last directory separator and modify
        parts = line.split('/')
        if len(parts) >= 2:
            # Modify the second-to-last part (directory name)
            parts[-2] = parts[-2] + suffix
            modified_line = '/'.join(parts)
            modified_lines.append(modified_line)
            changes += 1
        else:
            modified_lines.append(line)
    
    # Write back to file
    with open(filename, 'w') as f:
        for line in modified_lines:
            f.write(line + '\n')
    
    print(f"Modified {changes} paths in {filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python simple_modify_paths.py <filename.txt> [suffix]")
        print("Example: python simple_modify_paths.py job38_files.txt")
        print("Example: python simple_modify_paths.py job38_files.txt _EN_200")
        sys.exit(1)
    
    filename = sys.argv[1]
    suffix = sys.argv[2] if len(sys.argv) > 2 else "_EN_100"
    
    modify_paths_in_file(filename, suffix)