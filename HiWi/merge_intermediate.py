import pandas as pd
import os
from pathlib import Path
from tqdm import tqdm
import argparse


def merge_parquet_files(intermediate_dir: str, output_path: str, cleanup: bool = False) -> bool:
    """
    Merge all parquet files from intermediate directory into a single output file
    
    Args:
        intermediate_dir: Directory containing intermediate parquet files
        output_path: Path for the merged output file
        cleanup: Whether to remove intermediate files after successful merge
    
    Returns:
        bool: True if merge was successful, False otherwise
    """
    try:
        intermediate_path = Path(intermediate_dir)
        
        # Find all parquet files
        parquet_files = list(intermediate_path.glob("*.parquet"))
        
        if not parquet_files:
            print(f"❌ No parquet files found in {intermediate_dir}")
            return False
        
        print(f"📁 Found {len(parquet_files)} parquet files to merge")
        
        # Sort files by numeric ID if they follow the pattern {int}.parquet
        sorted_files = []
        other_files = []
        
        for file_path in parquet_files:
            try:
                file_id = int(file_path.stem)
                sorted_files.append((file_id, file_path))
            except ValueError:
                other_files.append(file_path)
        
        # Sort by file ID and combine with other files
        sorted_files.sort(key=lambda x: x[0])
        all_files = [f[1] for f in sorted_files] + other_files
        
        print(f"📊 Merging files...")
        
        # Read and combine all dataframes
        dfs = []
        total_rows = 0
        
        for file_path in tqdm(all_files, desc="Reading files"):
            try:
                df = pd.read_parquet(file_path)
                dfs.append(df)
                total_rows += len(df)
                print(f"  ✓ {file_path.name}: {len(df):,} rows")
            except Exception as e:
                print(f"  ❌ Failed to read {file_path.name}: {e}")
                return False
        
        if not dfs:
            print("❌ No dataframes were successfully loaded")
            return False
        
        print(f"\n🔄 Concatenating {len(dfs)} dataframes ({total_rows:,} total rows)...")
        final_df = pd.concat(dfs, ignore_index=True)
        
        # Sort by file_id and record_id if these columns exist
        if 'file_id' in final_df.columns and 'record_id' in final_df.columns:
            print("📋 Sorting by file_id and record_id...")
            final_df = final_df.sort_values(['file_id', 'record_id']).reset_index(drop=True)
        
        # Ensure output directory exists
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove existing output file if it exists
        if output_path_obj.exists():
            output_path_obj.unlink()
            print(f"🧹 Removed existing output file: {output_path}")
        
        # Save merged file
        print(f"💾 Saving merged file to: {output_path}")
        final_df.to_parquet(output_path, index=False)
        
        print(f"✅ Successfully merged {len(all_files)} files into {output_path}")
        print(f"📈 Final dataset: {len(final_df):,} rows, {len(final_df.columns)} columns")
        
        # Print column info
        print("\n📊 Dataset columns:")
        for col in final_df.columns:
            print(f"  - {col}: {final_df[col].dtype}")
        
        # Cleanup intermediate files if requested
        if cleanup:
            print(f"\n🧹 Cleaning up intermediate files...")
            removed_count = 0
            for file_path in all_files:
                try:
                    file_path.unlink()
                    removed_count += 1
                except Exception as e:
                    print(f"  ❌ Could not remove {file_path.name}: {e}")
            print(f"✅ Removed {removed_count}/{len(all_files)} intermediate files")
        
        return True
        
    except Exception as e:
        print(f"❌ Merge failed with error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Merge intermediate parquet files into a single output file")
    parser.add_argument("intermediate_dir", help="Directory containing intermediate parquet files")
    parser.add_argument("output_path", help="Path for the merged output parquet file")
    parser.add_argument("--cleanup", "-c", action="store_true", help="Remove intermediate files after successful merge")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Show what would be merged without actually doing it")
    
    args = parser.parse_args()
    
    # Validate inputs
    intermediate_path = Path(args.intermediate_dir)
    if not intermediate_path.exists():
        print(f"❌ Intermediate directory does not exist: {args.intermediate_dir}")
        return
    
    if not intermediate_path.is_dir():
        print(f"❌ Path is not a directory: {args.intermediate_dir}")
        return
    
    # Dry run mode
    if args.dry_run:
        parquet_files = list(intermediate_path.glob("*.parquet"))
        if not parquet_files:
            print(f"❌ No parquet files found in {args.intermediate_dir}")
            return
        
        print(f"🔍 DRY RUN: Would merge {len(parquet_files)} files:")
        total_size = 0
        for file_path in sorted(parquet_files):
            size = file_path.stat().st_size
            total_size += size
            print(f"  - {file_path.name} ({size:,} bytes)")
        
        print(f"\n📊 Total size: {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
        print(f"📁 Output would be saved to: {args.output_path}")
        if args.cleanup:
            print("🧹 Intermediate files would be removed after merge")
        return
    
    # Perform the merge
    success = merge_parquet_files(args.intermediate_dir, args.output_path, args.cleanup)
    
    if success:
        print("\n🎉 Merge completed successfully!")
    else:
        print("\n💥 Merge failed!")
        exit(1)

    RedT=pd.read_parquet(args.output_path)
    df=RedT[(RedT.type_count_2 == 1) | (RedT.energy > 10**4.8)][['file_id','record_id']]
    df.to_csv('Track_skiplist.csv',index=False)


if __name__ == "__main__":
    main()