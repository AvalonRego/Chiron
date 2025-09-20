import os
import sys
import time
import logging
import multiprocessing
import pandas as pd
import numpy as np
from tqdm import tqdm
import shutil
from datetime import datetime

# Generate filename with timestamp
log_filename = f"/u/arego/Project/AssignEventNo/log/hdf5_processing_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

# Configure logging
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def load_skip_records_csv(csv_path):
    """
    Load CSV file and create lookup structures for skipping records.
    Returns:
        - skip_files: set of file_ids that should be skipped entirely (have 20 records)
        - skip_records: dict mapping file_id to set of record_ids to skip
    """
    try:
        df = pd.read_csv(csv_path)
        
        # Validate required columns
        if 'file_id' not in df.columns or 'record_id' not in df.columns:
            raise ValueError("CSV must contain 'file_id' and 'record_id' columns")
        
        # Group by file_id and count unique record_ids
        file_record_counts = df.groupby('file_id')['record_id'].nunique()
        
        # Files with 20 records should be skipped entirely
        skip_files = set(file_record_counts[file_record_counts == 20].index)
        
        # For files with < 20 records, create record skip lookup
        skip_records = {}
        for file_id, group in df.groupby('file_id'):
            if file_id not in skip_files:  # Only process files that aren't completely skipped
                skip_records[file_id] = set(group['record_id'].unique())
        
        logging.info(f"Loaded skip configuration: {len(skip_files)} files to skip entirely, "
                    f"{len(skip_records)} files with partial record skips")
        
        return skip_files, skip_records
        
    except Exception as e:
        logging.error(f"Error loading CSV file {csv_path}: {str(e)}")
        raise

def balance_event_types(hits: pd.DataFrame, records: pd.DataFrame) -> (pd.DataFrame, pd.DataFrame):
    # Count the number of 0s and 1s
    count_1s = (records['type'] == 1).sum()
    count_0s = (records['type'] == 0).sum()

    # Calculate desired limits for 1s
    upper_limit = int(count_0s * 1.1)  # 10% above the count of 0s
    lower_limit = int(count_0s * 1)  # 10% below the count of 0s

    # Check if the number of 1s is out of bounds
    if count_1s > upper_limit:
        # Calculate the exact number of 1s to discard to meet the upper limit
        excess = np.random.randint(count_1s - upper_limit, count_1s - lower_limit)
        discard_event_nos = np.random.choice(records.loc[records['type'] == 1, 'event_no'], excess, replace=False)
        
        # Update records and hits by discarding the selected event_nos
        records = records[~records['event_no'].isin(discard_event_nos)]
        hits = hits[~hits['event_no'].isin(discard_event_nos)]

    return hits.reset_index(drop=True), records.reset_index(drop=True)

def process_and_save_hdf5(original_file_path, time_interval, skip_files, skip_records):
    """Processes and modifies an HDF5 file in-place."""
    try:
        start_time = time.time()
        
        # Extract file_id from filename
        name = os.path.basename(original_file_path)
        file_id_str, _ = name.split('.')
        file_id = int(file_id_str)
        
        # Check if this file should be skipped entirely
        if file_id in skip_files:
            logging.info(f"Skipping file {original_file_path} entirely (has 20 records in skip list)")
            return f"Skipped {original_file_path} entirely (all 20 records marked for skipping)"
        
        logging.info(f"Processing {original_file_path}")

        output_dir = os.path.dirname(original_file_path)
        temp_dir = f'{output_dir}_EN_{time_interval}' # Start with the original output_dir
        i = 1
        
        # Check if output_dir already exists
        while os.path.isdir(temp_dir) and os.path.isfile(f'{temp_dir}/{name}'):
            # Create a new temp_dir with an incremented suffix
            temp_dir = f'{output_dir}_{i}'
            i += 1

        # Final output_dir is the new unique directory
        output_dir = temp_dir

        os.makedirs(output_dir, exist_ok=True)

        modified_file_path = os.path.join(output_dir, name)
        
        # Copy the original file to the output directory
        shutil.copy2(original_file_path, modified_file_path)

        with pd.HDFStore(modified_file_path, mode='a') as store:  # 'a' mode allows modifying the file
            if 'hits' not in store or 'records' not in store:
                logging.error(f"Skipping {modified_file_path}: Missing 'hits' or 'records' dataset.")
                return f"Skipped {modified_file_path}: Missing required datasets."

            # Read datasets
            hits = store['hits']
            records = store['records']
            
            # Apply record filtering if this file has records to skip
            if file_id in skip_records:
                records_to_skip = skip_records[file_id]
                initial_hit_count = len(hits)
                initial_record_count = len(records)
                
                # Filter out the records to skip
                hits = hits[~hits['record_id'].isin(records_to_skip)]
                records = records[~records['record_id'].isin(records_to_skip)]
                
                filtered_hit_count = len(hits)
                filtered_record_count = len(records)
                
                logging.info(f"File {file_id}: Filtered {initial_hit_count - filtered_hit_count} hits "
                           f"and {initial_record_count - filtered_record_count} records")
                
                # Check if we filtered out all data
                if len(hits) == 0 or len(records) == 0:
                    logging.info(f"File {file_id}: No data remaining after filtering, skipping")
                    store.close()
                    os.remove(modified_file_path)
                    return f"Skipped {modified_file_path}: No data remaining after filtering"

            if 'event_no' in hits.columns:
                hits = hits.drop(columns=['event_no'])
            if 'event_no' in records.columns:
                records = records.drop(columns=['event_no'])

            # Compute event bins per record_id (Optimized)
            hits["min_time"] = hits.groupby("record_id")["time"].transform('min')
            hits["event_no"] = np.floor((hits["time"] - hits["min_time"]) // time_interval + 1).astype(np.int64)
            hits["event_no"] += ( hits["record_id"].astype(np.int64) * 10**6  # Ensures uniqueness within a dataset
                                    + np.int64(file_id) * 10**12 ) # Adds uniqueness across datasets)

            hits.drop(columns=["min_time"], inplace=True)

            # Generate event truth mapping (Corrected Aggregation)
            
            # Step 1: Remove unwanted types (already optimized)
            valid_hits = hits.loc[hits["type"] > 5]  

            # Step 2: Compute event counts (already optimized)
            group_keys = ["record_id", "event_no"]
            event_counts = valid_hits.groupby(group_keys, sort=False).size()

            # Step 3: Compute std and median (already optimized)
            record_grouped = event_counts.groupby(level=0, sort=False)
            std_values = record_grouped.std(ddof=0).fillna(0)  
            median_values = record_grouped.median()
            thresholds = (5 * std_values) + median_values 

            # Step 3.5: Get total count (already optimized)
            total_count = hits.groupby(group_keys, sort=False).size()

            # Step 4: Identify excess events (Optimized)
            aligned_thresholds = thresholds.reindex(total_count.index, level=0)
            excess_events = total_count.index[ (total_count > aligned_thresholds)]
            # Convert to dictionary (O(1) lookups instead of `isin()`)
            excess_events_dict = {key: True for key in excess_events}

            # Step 5: Optimized Filtering (Fast Dictionary Lookup!)
            record_event_tuples = list(zip(hits["record_id"], hits["event_no"]))  # This was actually FASTER
            mask_to_keep = np.array([key not in excess_events_dict for key in record_event_tuples], dtype=bool)

            # Apply the mask
            hits = hits.loc[mask_to_keep].reset_index(drop=True)

            event_truth = hits[['record_id', 'event_no', 'type']].drop_duplicates()
            event_truth = event_truth.groupby('event_no', as_index=False).agg({'record_id': 'min', 'type': 'min'})
            event_truth['type'] = (event_truth['type'] // 19).astype(int)

            # Drop 'type' column before merging
            records.drop(columns=['type'], errors='ignore', inplace=True)
            hits.drop(columns=['type'], errors='ignore', inplace=True)

            # Merge on event_no (Corrected)
            merged_df = records.merge(event_truth, on='record_id', how='left', sort=False)
            hits, records = balance_event_types(hits, merged_df)
            
            if 'event_no' not in hits.columns or 'event_no' not in records.columns:
                logging.info(f"{modified_file_path} has an event no mismatch")
                
            # Overwrite modified datasets inside the same HDF5 file
            store.put('hits', hits, format='table', data_columns=True, complib='zlib', complevel=5)
            store.put('records', records, format='table', data_columns=True, complib='zlib', complevel=5)

        store.close()
        del store
        duration = time.time() - start_time
        logging.info(f"Completed {modified_file_path} in {duration:.2f} seconds")
        return f"Processed {modified_file_path} in {duration:.2f} seconds"

    except Exception as e:
        logging.error(f"Error processing {original_file_path}: {str(e)}")
        if 'modified_file_path' in locals() and os.path.exists(modified_file_path):
            os.remove(modified_file_path)
        return f"Error processing {original_file_path}: {str(e)}"

def update_progress_bar(total_files, progress_queue):
    """Updates the progress bar based on completed tasks."""
    with tqdm(total=total_files, desc="Processing HDF5 Files") as pbar:
        for _ in range(total_files):
            progress_queue.get()  # Wait for an update
            pbar.update(1)

def process_files_parallel(files, time_interval, skip_files, skip_records, num_workers=8):
    """Processes multiple HDF5 files in parallel using multiprocessing."""
    manager = multiprocessing.Manager()
    progress_queue = manager.Queue()
    
    # Filter out files that should be skipped entirely
    files_to_process = []
    skipped_count = 0
    
    for file_path in files:
        name = os.path.basename(file_path)
        file_id_str, _ = name.split('.')
        file_id = int(file_id_str)
        
        if file_id in skip_files:
            skipped_count += 1
            logging.info(f"Pre-filtering: Skipping {file_path} (all 20 records marked for skipping)")
        else:
            files_to_process.append(file_path)
    
    total_files = len(files_to_process)
    print(f"Pre-filtered {skipped_count} files that would be skipped entirely. Processing {total_files} remaining files.")

    if total_files == 0:
        print("No files to process after filtering!")
        return

    # Start progress bar in a separate process
    progress_process = multiprocessing.Process(target=update_progress_bar, args=(total_files, progress_queue))
    progress_process.start()

    def update_progress(_):
        """Callback function to update progress bar after each process."""
        progress_queue.put(1)

    with multiprocessing.Pool(processes=num_workers) as pool:
        for file_path in files_to_process:
            pool.apply_async(process_and_save_hdf5, args=(file_path, time_interval, skip_files, skip_records), 
                           callback=update_progress)

        pool.close()
        pool.join()

    progress_process.join()
    print("Processing complete!")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script.py <csv_file> <h5_files...>")
        print("CSV file should contain 'file_id' and 'record_id' columns")
        sys.exit(1)

    # First argument is the CSV file path
    csv_file_path = sys.argv[1]
    
    # Load skip configuration from CSV
    try:
        skip_files, skip_records = load_skip_records_csv(csv_file_path)
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        sys.exit(1)

    # Collect valid HDF5 file paths from remaining command-line arguments
    files = sorted(
        [file for file in sys.argv[2:] if file.endswith('.h5')],
        key=os.path.getsize
    )

    if not files:
        print("No valid HDF5 files found.")
        sys.exit(1)

    print(f"Found {len(files)} HDF5 files to potentially process...")
    print(f"Skip configuration loaded: {len(skip_files)} files to skip entirely, "
          f"{len(skip_records)} files with partial record skips")

    # Run parallel processing
    process_files_parallel(files, time_interval=100, skip_files=skip_files, skip_records=skip_records, num_workers=8)