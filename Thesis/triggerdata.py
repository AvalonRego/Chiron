import sys
import os
import gc
import pyarrow as pa
import pyarrow.parquet as pq
import argparse
from filelock import FileLock
sys.path.append('/u/arego/Project/Experimenting')
import Trigger_Improve as ti
import pandas as pd
import numpy as np
from itertools import combinations
from joblib import Parallel, delayed
from tqdm import tqdm
import math

COMPRESSION = "snappy"  # Parquet compression type

def get_file_size_gb(file_path):
    return os.path.getsize(file_path) / (1024**3)

def determine_worker_count(files, thresholds, worker_counts, max_workers=8):
    if not files:
        return 1

    avg_size = sum(get_file_size_gb(f) for f in files) / len(files)
    max_size = max(get_file_size_gb(f) for f in files)

    print(f"Batch file stats - Count: {len(files)}, Avg size: {avg_size:.3f}GB, Max size: {max_size:.3f}GB")

    # Find appropriate worker count based on average file size
    workers = worker_counts[-1]  # Default to last (largest files) worker count
    for i, threshold in enumerate(thresholds):
        if avg_size < threshold:
            workers = worker_counts[i]
            break
    
    # Apply max_workers limit
    workers = min(max_workers, workers)

    print(f"Using {workers} workers for this batch")
    return workers

def split_files_into_batches(file_paths, total_jobs):
    if total_jobs <= 0:
        return [file_paths]
    sorted_files = sorted(file_paths, key=get_file_size_gb)
    batch_size = math.ceil(len(sorted_files) / total_jobs)
    return [sorted_files[i:i + batch_size] for i in range(0, len(sorted_files), batch_size) if sorted_files[i:i + batch_size]]

def process_file(i, file_path, OUTPUT_DIR):
    print(f"[{i}] Starting processing: {os.path.basename(file_path)} ({get_file_size_gb(file_path):.3f}GB)")
    try:
        hits_data, timer_bins, _ = ti.initialize_and_load_data(file_path)
        del _
        key = 'records'
        with pd.HDFStore(file_path, mode='r') as store:
            if 'event_no' in store[key].columns:
                records = pd.read_hdf(file_path, key=key, columns=['record_id', 'energy', 'event_no'])
            else:
                records = pd.read_hdf(file_path, key=key, columns=['record_id', 'energy'])
        records = records.drop_duplicates(subset=['record_id', 'energy'])
        print(f"[{i}] Data loaded successfully. Hits: {len(hits_data)}, Records: {len(records)}")
    except Exception as e:
        print(f"[{i}] ERROR loading data from {file_path}: {e}")
        return False

    try:
        types = [t for t in hits_data['type'].unique() if int(t) != 0]
        all_subsets = [tuple(sorted(subset)) for r in range(1, len(types) + 1) for subset in combinations(types, r)]
        number = int(os.path.basename(file_path).split('.')[0])
        print(f"[{i}] Found {len(types)} types, creating {len(all_subsets)} subsets")
    except Exception as e:
        print(f"[{i}] ERROR preparing subsets: {e}")
        return False

    subset_data = {}
    successful_subsets, failed_subsets = 0, 0

    for subset_idx, subset in enumerate(all_subsets):
        try:
            print(f"[{i}] Processing subset {subset_idx + 1}/{len(all_subsets)}: {subset}")
            subset_df = hits_data[hits_data["type"].isin(subset)]
            if subset_df.empty:
                print(f"[{i}]   WARNING: Empty subset {subset}, skipping")
                failed_subsets += 1
                continue

            aggregated_data = ti.process_hits(subset_df, timer_bins)
            del subset_df
            trigger_data = ti.create_trigger_data(aggregated_data)
            del aggregated_data
            plot_df = ti.aggregate_for_plotting(trigger_data)
            del trigger_data

            cols = [col for col in plot_df.columns if 'Mod' in col]
            plot_df = plot_df[['record_id'] + cols].applymap(np.sum)
            plot_df = plot_df.merge(records, on='record_id')
            plot_df['record_id'] += number * 10**6

            subset_data[subset] = plot_df
            successful_subsets += 1
            print(f"[{i}]   Subset processed successfully. Result size: {len(plot_df)}")
        except Exception as e:
            print(f"[{i}]   ERROR processing subset {subset}: {e}")
            failed_subsets += 1

    print(f"[{i}] Subset processing complete. Success: {successful_subsets}, Failed: {failed_subsets}")
    if successful_subsets == 0:
        return False

    try:
        if not subset_data:
            print(f"[{i}] ERROR: No subset data to process")
            return False
        all_record_ids = set.intersection(*(set(df['record_id']) for df in subset_data.values()))
        if not all_record_ids:
            print(f"[{i}] WARNING: No common record IDs across subsets!")
            return False
        filtered_subset_data = {subset: df[df['record_id'].isin(all_record_ids)] for subset, df in subset_data.items()}
    except Exception as e:
        print(f"[{i}] ERROR during record ID intersection: {e}")
        return False

    try:
        saved_files = 0
        for subset, plot_df in filtered_subset_data.items():
            subset_name = "_".join(map(str, subset))
            subset_dir = os.path.join(OUTPUT_DIR, subset_name)
            os.makedirs(subset_dir, exist_ok=True)
            output_path = os.path.join(subset_dir, 'merged.parquet')

            lock_path = output_path + ".lock"
            with FileLock(lock_path, timeout=120):
                table = pa.Table.from_pandas(plot_df)
                if os.path.exists(output_path):
                    existing_table = pq.read_table(output_path)
                    combined_table = pa.concat_tables([existing_table, table])
                    pq.write_table(combined_table, output_path, compression=COMPRESSION)
                else:
                    pq.write_table(table, output_path, compression=COMPRESSION)
                saved_files += 1
        print(f"[{i}] Successfully saved {saved_files} subset files")
    except Exception as e:
        print(f"[{i}] ERROR saving data for {file_path}: {e}")
        return False

    del subset_data, filtered_subset_data
    gc.collect()
    print(f"[{i}] File processing completed successfully: {os.path.basename(file_path)}")
    return True

def process_files_in_parallel(file_paths, OUTPUT_DIR, max_workers, thresholds, worker_counts):
    if not file_paths:
        print("No files to process in this batch")
        return []

    num_workers = determine_worker_count(file_paths, thresholds, worker_counts, max_workers)

    print(f"Starting parallel processing with {num_workers} workers...")
    print(f"Files to process: {len(file_paths)}")

    results = Parallel(n_jobs=num_workers)(
        delayed(process_file)(i, file, OUTPUT_DIR)
        for i, file in tqdm(enumerate(file_paths), total=len(file_paths), desc="Processing Files", unit="file")
    )

    successful = sum(1 for r in results if r)
    failed = sum(1 for r in results if not r)

    print(f"\nBatch Processing Summary:\n  Total files: {len(file_paths)}\n  Successful: {successful}\n  Failed: {failed}")
    return results

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process HDF5 files and save results as Parquet files.")
    parser.add_argument('input_dir', type=str, help='Input directory containing HDF5 files.')
    parser.add_argument('output_dir', type=str, help='Output directory for saving Parquet files.')
    parser.add_argument('--workers', type=int, default=8, help='Maximum number of parallel workers (default: 8)')
    parser.add_argument('--max-size', type=float, default=2.0, help='Maximum file size in GB (default: 2.0)')
    parser.add_argument('--job-index', type=int, default=0, help='Current job index for batch processing')
    parser.add_argument('--total-jobs', type=int, default=1, help='Total number of jobs for batch processing')
    parser.add_argument('--size-thresholds', type=float, nargs='+', default=[0.1, 0.3, 0.7, 1.2], help='Size thresholds in GB for worker allocation')
    parser.add_argument('--worker-counts', type=int, nargs='+', default=[8, 6, 4, 2, 1], help='Worker counts for each size range')

    args = parser.parse_args()

    # Validation
    if len(args.worker_counts) != len(args.size_thresholds) + 1:
        print(f"ERROR: worker-counts ({len(args.worker_counts)}) must have one more element than size-thresholds ({len(args.size_thresholds)})")
        sys.exit(1)
    
    if args.size_thresholds != sorted(args.size_thresholds):
        print("ERROR: size-thresholds must be in ascending order")
        sys.exit(1)

    path = args.input_dir
    if not os.path.exists(path):
        print(f"ERROR: Input directory does not exist: {path}")
        sys.exit(1)

    file_paths = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.h5')]
    print(f"Found {len(file_paths)} .h5 files")

    max_size_bytes = int(args.max_size * 1e9)
    file_paths = [f for f in file_paths if os.path.getsize(f) < max_size_bytes]
    print(f"After size filtering (< {args.max_size}GB): {len(file_paths)} files")

    if not file_paths:
        print("ERROR: No files to process after filtering")
        sys.exit(1)

    # Sort files by size and split into batches
    file_paths = sorted(file_paths, key=os.path.getsize)
    all_batches = split_files_into_batches(file_paths, args.total_jobs + 1)
    
    if args.job_index >= len(all_batches):
        print(f"Job index {args.job_index} is out of range. Only {len(all_batches)} batches available.")
        sys.exit(0)

    current_batch = all_batches[args.job_index]
    print(f"Processing batch {args.job_index + 1}/{len(all_batches)}")
    print(f"Batch contains {len(current_batch)} files")
    
    # Show batch file size statistics
    if current_batch:
        batch_sizes = [get_file_size_gb(f) for f in current_batch]
        print(f"Batch size range: {min(batch_sizes):.3f}GB - {max(batch_sizes):.3f}GB")

    OUTPUT_DIR = args.output_dir
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    process_files_in_parallel(current_batch, OUTPUT_DIR, args.workers, args.size_thresholds, args.worker_counts)