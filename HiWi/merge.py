import pandas as pd
import os
from pathlib import Path

def merge_parquet_files_by_subdir(root_dir):
    """
    Merges parquet files from numbered directories into root/merged/ structure.
    Preserves subdirectory names and creates merged.parquet in each.
    
    Args:
        root_dir: Path to root directory containing numbered subdirs
    """
    
    root_path = Path(root_dir)
    merged_path = root_path / "merged"
    
    # Create merged directory if it doesn't exist
    merged_path.mkdir(exist_ok=True)
    
    # Find all unique subdirectory names across all numbered directories
    subdirs = set()
    for numbered_dir in root_path.iterdir():
        if numbered_dir.is_dir() and numbered_dir.name.isdigit():
            for subdir in numbered_dir.iterdir():
                if subdir.is_dir():
                    subdirs.add(subdir.name)
    
    print(f"Found subdirectories: {sorted(subdirs)}")
    
    # For each subdirectory type, merge all parquet files
    for subdir_name in sorted(subdirs):
        parquet_files = []
        
        # Collect all merged.parquet files for this subdirectory type
        for numbered_dir in root_path.iterdir():
            if numbered_dir.is_dir() and numbered_dir.name.isdigit():
                parquet_path = numbered_dir / subdir_name / "merged.parquet"
                if parquet_path.exists():
                    parquet_files.append(str(parquet_path))
        
        if parquet_files:
            print(f"Merging {len(parquet_files)} files for {subdir_name}")
            
            # Read and concatenate all parquet files
            dfs = [pd.read_parquet(file) for file in parquet_files]
            merged_df = pd.concat(dfs, ignore_index=True)
            
            # Create subdirectory in merged folder
            output_subdir = merged_path / subdir_name
            output_subdir.mkdir(exist_ok=True)
            
            # Save merged file with same name
            output_file = output_subdir / "merged.parquet"
            merged_df.to_parquet(output_file, index=False)
            
            print(f"Saved {len(merged_df)} rows to {output_file}")
        else:
            print(f"No parquet files found for {subdir_name}")

# Usage
root_directory = "/u/arego/Project/HiWi/Trigger_process/Track"  # Update this path
merge_parquet_files_by_subdir(root_directory)