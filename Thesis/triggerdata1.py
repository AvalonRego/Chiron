import sys
import os
import gc
import pyarrow as pa
import pyarrow.parquet as pq
sys.path.append('/u/arego/Project/Experimenting')
import Trigger_Improve as ti
import pandas as pd
import numpy as np
from itertools import combinations
from joblib import Parallel, delayed
from tqdm import tqdm

COMPRESSION = "snappy"  # Parquet compression type

def process_file(i, file_path, OUTPUT_DIR):
    """Processes a single HDF5 file and saves results as Parquet files in structured directories."""
    hits_data, timer_bins, _ = ti.initialize_and_load_data(file_path)
    del _
    records = pd.read_hdf(file_path, key='records', columns=['record_id', 'energy'])

    types = hits_data['type'].unique()
    # Create sorted tuples for all subsets
    all_subsets = [tuple(sorted(subset)) for r in range(1, len(types) + 1) for subset in combinations(types, r)]

    for subset in all_subsets:
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

        # Define output directory based on sorted subset key
        subset_name = "_".join(map(str, subset))  # Convert tuple to string
        subset_dir = os.path.join(OUTPUT_DIR, subset_name)
        os.makedirs(subset_dir, exist_ok=True)  # Create directory if not exists

        # Define output file path
        file_name = os.path.basename(file_path).replace(".h5", ".parquet")
        output_path = os.path.join(subset_dir, file_name)

        # Append to the Parquet file without reading the existing file
        table = pa.Table.from_pandas(plot_df)

        if os.path.exists(output_path):
            # Append data to existing Parquet file
            with pq.ParquetWriter(output_path, table.schema, compression=COMPRESSION, append=True) as writer:
                writer.write_table(table)
        else:
            # Create a new Parquet file
            pq.write_table(table, output_path, compression=COMPRESSION)

        del plot_df
        gc.collect()

def process_files_in_parallel(file_paths, num_workers=4):
    """Processes multiple HDF5 files in parallel using Joblib and tqdm."""
    Parallel(n_jobs=num_workers)(
        delayed(process_file)(i, file) for i, file in tqdm(enumerate(file_paths), total=len(file_paths), desc="Processing Files", unit="file")
    )

if __name__ == '__main__':
    path = '/viper/ptmp/arego/R1T4K/'
    #path = '/viper/ptmp/arego/TMerge/'
    #path = '/viper/ptmp/arego/RC4K1/'
    #path = '/viper/ptmp/arego/R1T4K/'
    print(path)
    file_paths = [os.path.join(path, file) for file in os.listdir(path) if file.endswith('.h5')]

    # Filter files by size < 1GB
    file_paths = [file for file in file_paths if os.path.getsize(file) < 10**9]

    # Sort files by size (small to big)
    file_paths = [file for file, size in sorted(file_paths, key=lambda x: x[1])]
    
    OUTPUT_DIR = "/u/arego/Project/Thesis/plot/TD4K"  # Base directory for storing results

    process_files_in_parallel(file_paths, num_workers=8)  # Adjust workers as needed
