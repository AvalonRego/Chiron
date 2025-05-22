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

COMPRESSION = "snappy"  # Parquet compression type

def process_file(i, file_path, OUTPUT_DIR):
    """Processes a single HDF5 file and saves results as Parquet files only after all subsets are processed."""

    # --- Load Data ---
    try:
        hits_data, timer_bins, _ = ti.initialize_and_load_data(file_path)
        del _
        key='records'
        with pd.HDFStore(file_path, mode='r') as store:
            if 'event_no' in store[key].columns:
                records = pd.read_hdf(file_path, key=key, columns=['record_id', 'energy', 'event_no'])
            else:
                return
                records = pd.read_hdf(file_path, key=key, columns=['record_id', 'energy'])

        records = records.drop_duplicates(subset=['record_id', 'energy'])
    except Exception as e:
        print(f"ERROR loading data from {file_path}: {e}")
        return  # Skip this file

    # --- Prepare Subsets ---
    types = hits_data['type'].unique()
    types = [t for t in types if int(t) != 0]
    all_subsets = [tuple(sorted(subset)) for r in range(1, len(types) + 1) for subset in combinations(types, r)]

    try:
        number = int(os.path.basename(file_path).split('.')[0])
    except ValueError:
        print(f"ERROR extracting file number from {file_path}")
        return  # Skip this file

    subset_data = {}
    num_rows = None  # Track expected row count

    # --- Process Each Subset ---
    for subset in all_subsets:
        try:
            subset_df = hits_data[hits_data["type"].isin(subset)]
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

            # # --- Check for Row Consistency ---
            # if num_rows is None:
            #     num_rows = len(plot_df)
            # elif len(plot_df) != num_rows:
            #     print(f"WARNING: Row count mismatch in {file_path}. Expected {num_rows}, but got {len(plot_df)} for subset {subset}. Skipping file.")
            #     return  # Skip saving if inconsistency is detected

            subset_data[subset] = plot_df  # Store in dictionary

        except Exception as e:
            print(f"ERROR processing subset {subset} in {file_path}: {e}")
            return  # Skip this subset but continue with others

    # --- Save Data ---

    # Assuming subset_data is a dictionary where each key is a subset identifier and each value is a DataFrame
    # Example: subset_data = {'subset1': df1, 'subset2': df2, ...}

    # Step 1: Get the intersection of all record_ids
    all_record_ids = set.intersection(*(set(plot_df['record_id']) for plot_df in subset_data.values()))

    # Step 2: Filter each DataFrame in subset_data to keep only the common record_ids
    filtered_subset_data = {subset: plot_df[plot_df['record_id'].isin(all_record_ids)] for subset, plot_df in subset_data.items()}

    # Now proceed with the merging and writing to parquet files
    try:
        for subset, plot_df in filtered_subset_data.items():
            subset_name = "_".join(map(str, subset))
            subset_dir = os.path.join(OUTPUT_DIR, subset_name)
            os.makedirs(subset_dir, exist_ok=True)
            output_path = os.path.join(subset_dir, 'merged.parquet')

            lock_path = output_path + ".lock"
            with FileLock(lock_path, timeout=60):
                table = pa.Table.from_pandas(plot_df)
                if os.path.exists(output_path):
                    existing_table = pq.read_table(output_path)
                    combined_table = pa.concat_tables([existing_table, table])
                    pq.write_table(combined_table, output_path, compression=COMPRESSION)
                else:
                    pq.write_table(table, output_path, compression=COMPRESSION)


    except Exception as e:
        print(f"ERROR saving data for {file_path}: {e}")
        return  # Skip saving if an error occurs

    del subset_data
    gc.collect()


def process_files_in_parallel(file_paths, OUTPUT_DIR, num_workers=4):
    """Processes multiple HDF5 files in parallel using Joblib and tqdm."""
    Parallel(n_jobs=num_workers)(
        delayed(process_file)(i, file, OUTPUT_DIR) for i, file in tqdm(enumerate(file_paths), total=len(file_paths), desc="Processing Files", unit="file")
    )

if __name__ == '__main__':
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Process HDF5 files and save results as Parquet files.")
    parser.add_argument('input_dir', type=str, help='Input directory containing HDF5 files.')
    parser.add_argument('output_dir', type=str, help='Output directory for saving Parquet files.')
    args = parser.parse_args()

    path = args.input_dir
    print(f"Input Directory: {path}")
    
    file_paths = [os.path.join(path, file) for file in os.listdir(path) if file.endswith('.h5')]

    # Filter files by size < 1GB
    file_paths = [file for file in file_paths if os.path.getsize(file) < 10**9][:1400]
    # Sort files by size (small to big)
    file_paths = sorted(file_paths, key=os.path.getsize)
    
    OUTPUT_DIR = args.output_dir  # Set output directory from arguments

    print(f"Output Directory: {OUTPUT_DIR}")
    process_files_in_parallel(file_paths, OUTPUT_DIR, num_workers=8)  # Adjust workers as needed
