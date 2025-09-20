import pandas as pd
import os
import gc
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
from typing import Optional, Tuple, Dict, List


def extract_record_metrics(hits_chunk: pd.DataFrame, record_times_dict: Dict, record_hit_counts_dict: Dict, record_type_counts_dict: Dict) -> None:
    """
    Modified to also extract type counts for each record_id
    """
    time_stats = hits_chunk.groupby('record_id')['time'].agg(['min', 'max', 'count'])
    for record_id, row in time_stats.iterrows():
        min_time, max_time, count = row['min'], row['max'], row['count']
        if record_id in record_hit_counts_dict:
            record_hit_counts_dict[record_id] += count
        else:
            record_hit_counts_dict[record_id] = count
        if record_id in record_times_dict:
            current_min, current_max = record_times_dict[record_id]
            record_times_dict[record_id] = [min(current_min, min_time), max(current_max, max_time)]
        else:
            record_times_dict[record_id] = [min_time, max_time]
    
    # Count types for each record_id
    if 'type' in hits_chunk.columns:
        # Filter for only the types we're interested in
        type_filter = hits_chunk['type'].isin([2, 20, 21])
        filtered_chunk = hits_chunk[type_filter]
        
        if not filtered_chunk.empty:
            type_counts = filtered_chunk.groupby(['record_id', 'type']).size().reset_index(name='count')
            
            for _, row in type_counts.iterrows():
                record_id, type_val, count = row['record_id'], row['type'], row['count']
                
                if record_id not in record_type_counts_dict:
                    record_type_counts_dict[record_id] = {}
                
                if type_val in record_type_counts_dict[record_id]:
                    record_type_counts_dict[record_id][type_val] += count
                else:
                    record_type_counts_dict[record_id][type_val] = count


def finalize_record_metrics(file_id: int, record_times_dict: Dict, record_hit_counts_dict: Dict, record_type_counts_dict: Dict, records_df: pd.DataFrame) -> pd.DataFrame:
    """
    Modified to include energy from records_df and type counts
    """
    results = []
    
    # Create a lookup dictionary for energy values
    energy_lookup = records_df.set_index('record_id')['energy'].to_dict() if 'energy' in records_df.columns else {}
    
    for record_id in record_times_dict.keys():
        min_time, max_time = record_times_dict[record_id]
        hit_count = record_hit_counts_dict[record_id]
        duration = max_time - min_time
        energy = energy_lookup.get(record_id, None)  # Get energy or None if not found
        
        # Get type counts for this record_id
        type_counts = record_type_counts_dict.get(record_id, {})
        type_count_2 = type_counts.get(2, 0)
        type_count_20 = type_counts.get(20, 0)
        type_count_21 = type_counts.get(21, 0)
        
        results.append({
            'file_id': file_id,
            'record_id': record_id,
            'duration': duration,
            'min_time': min_time,
            'max_time': max_time,
            'hit_count': hit_count,
            'energy': energy,
            'type_count_2': type_count_2,
            'type_count_20': type_count_20,
            'type_count_21': type_count_21
        })
    return pd.DataFrame(results)


def process_single_file(file_path: str, intermediate_dir: str) -> bool:
    try:
        file_id = int(Path(file_path).stem)
        record_times_dict = {}
        record_hit_counts_dict = {}
        record_type_counts_dict = {}  # New dictionary for type counts
        
        # Read records dataframe (keep this in memory as it's typically smaller)
        records_df = pd.read_hdf(file_path, key='records')
        
        with pd.HDFStore(file_path, mode='r') as store:
            hits_info = store.get_storer('hits')
            total_hits = hits_info.nrows if hits_info else 0
        if total_hits == 0:
            return False
        
        chunk_size = 1_000_000
        for start_idx in range(0, total_hits, chunk_size):
            end_idx = min(start_idx + chunk_size, total_hits)
            hits_chunk = pd.read_hdf(file_path, key='hits', start=start_idx, stop=end_idx)
            extract_record_metrics(hits_chunk, record_times_dict, record_hit_counts_dict, record_type_counts_dict)
            del hits_chunk
            gc.collect()
        
        # Pass all dictionaries to finalize_record_metrics
        final_df = finalize_record_metrics(file_id, record_times_dict, record_hit_counts_dict, record_type_counts_dict, records_df)
        intermediate_path = os.path.join(intermediate_dir, f"{file_id}.parquet")
        final_df.to_parquet(intermediate_path, index=False)
        
        del record_times_dict, record_hit_counts_dict, record_type_counts_dict, records_df, final_df
        gc.collect()
        return True
    except Exception:
        return False


def get_h5_files(input_dir: str, file_range: Optional[Tuple[int, int]] = None) -> List[str]:
    input_path = Path(input_dir)
    all_files = []
    for file_path in input_path.glob("*.h5"):
        try:
            file_id = int(file_path.stem)
            all_files.append((file_id, str(file_path)))
        except ValueError:
            pass
    all_files.sort(key=lambda x: x[0])
    if file_range:
        start_id, end_id = file_range
        all_files = [(fid, fpath) for fid, fpath in all_files if start_id <= fid <= end_id]
    return [fpath for _, fpath in all_files]


def clean_intermediate_directory(intermediate_dir: str) -> None:
    """Remove all parquet files from intermediate directory"""
    intermediate_path = Path(intermediate_dir)
    if intermediate_path.exists():
        for parquet_file in intermediate_path.glob("*.parquet"):
            try:
                parquet_file.unlink()
                print(f"🧹 Cleaned old intermediate file: {parquet_file.name}")
            except Exception as e:
                print(f"Could not remove {parquet_file.name}: {e}")


def merge_intermediate_files(intermediate_dir: str, output_path: str, expected_files: List[str]) -> bool:
    """
    Merge intermediate files, ensuring we only use files from the current run
    """
    try:
        intermediate_path = Path(intermediate_dir)
        
        # Only consider files that correspond to the current run
        expected_file_ids = {int(Path(f).stem) for f in expected_files}
        current_run_files = []
        
        for parquet_file in intermediate_path.glob("*.parquet"):
            try:
                file_id = int(parquet_file.stem)
                if file_id in expected_file_ids:
                    current_run_files.append(parquet_file)
            except ValueError:
                # Skip files that don't have integer names
                continue
        
        if not current_run_files:
            print("No intermediate files from current run found")
            return False
        
        print(f"📊 Merging {len(current_run_files)} intermediate files from current run")
        
        dfs = []
        for file_path in tqdm(current_run_files, desc="Merging results"):
            df = pd.read_parquet(file_path)
            dfs.append(df)
        
        final_df = pd.concat(dfs, ignore_index=True)
        final_df = final_df.sort_values(['file_id', 'record_id']).reset_index(drop=True)
        
        # Remove existing output file if it exists
        output_path_obj = Path(output_path)
        if output_path_obj.exists():
            output_path_obj.unlink()
            print(f"🧹 Removed existing output file: {output_path}")
        
        final_df.to_parquet(output_path, index=False)

        # cleanup parquet files from current run
        for file_path in current_run_files:
            file_path.unlink()

        return True
    except Exception as e:
        print(f"Merge failed with error: {e}")
        return False



def main_processor(input_dir: str, intermediate_dir: str, output_path: str, file_range: Optional[Tuple[int, int]] = None, n_cores: Optional[int] = None) -> bool:
    os.makedirs(intermediate_dir, exist_ok=True)
    os.makedirs(Path(output_path).parent, exist_ok=True)
    
    # Clean intermediate directory before starting
    clean_intermediate_directory(intermediate_dir)
    
    files_to_process = get_h5_files(input_dir, file_range)
    if not files_to_process:
        print("No HDF5 files found to process")
        return False
    
    print(f"Starting processing of {len(files_to_process)} files")
    
    successful_files = 0
    with ProcessPoolExecutor(max_workers=n_cores) as executor:
        futures = [executor.submit(process_single_file, file_path, intermediate_dir) for file_path in files_to_process]
        for f in tqdm(futures, desc="Processing files"):
            if f.result():
                successful_files += 1
    
    print(f"Successfully processed {successful_files}/{len(files_to_process)} files")
    
    if successful_files == 0:
        print("No files were successfully processed")
        return False
    
    # Pass the list of files that were supposed to be processed for validation
    success = merge_intermediate_files(intermediate_dir, output_path, files_to_process)
    if success:
        print("Processing completed successfully!")
        print(f"Final output saved to: {output_path}")
    else:
        print("Merging failed!")
    return success


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Process HDF5 physics data files to extract record metrics")
    parser.add_argument("input_dir", help="Directory containing HDF5 files ({int}.h5 format)")
    parser.add_argument("intermediate_dir", help="Directory to save intermediate parquet files")
    parser.add_argument("output_path", help="Path for final merged parquet file")
    parser.add_argument("--file-range", nargs=2, type=int, metavar=('START', 'END'), help="Process only files in range [START, END]")
    parser.add_argument("--cores", "-c", type=int, help="Number of CPU cores to use")
    args = parser.parse_args()
    file_range = (args.file_range[0], args.file_range[1]) if args.file_range else None
    main_processor(args.input_dir, args.intermediate_dir, args.output_path, file_range, args.cores)


if __name__ == "__main__":
    main()