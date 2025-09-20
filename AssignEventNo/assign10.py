import os
import sys
import time
import logging
import multiprocessing
import pandas as pd
import numpy as np
from tqdm import tqdm
import shutil

# Set up logging
logging.basicConfig(
    filename="/u/arego/Project/AssignEventNo/hdf5_processing_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def balance_event_types(hits: pd.DataFrame, records: pd.DataFrame) -> (pd.DataFrame, pd.DataFrame):
    # Count the number of 0s and 1s
    count_1s = (records['type'] == 1).sum()
    count_0s = (records['type'] == 0).sum()

    # Calculate desired limits for 1s
    upper_limit = int(count_0s * 1.1)  # 10% above the count of 0s
    lower_limit = int(count_0s * 0.9)  # 10% below the count of 0s

    # Check if the number of 1s is out of bounds
    if count_1s > upper_limit:
        # Calculate the exact number of 1s to discard to meet the upper limit
        excess = np.random.randint(count_1s - upper_limit,count_1s - lower_limit)
        discard_event_nos = np.random.choice(records.loc[records['type'] == 1, 'event_no'], excess, replace=False)
        
        # Update records and hits by discarding the selected event_nos
        records = records[~records['event_no'].isin(discard_event_nos)]
        hits = hits[~hits['event_no'].isin(discard_event_nos)]
    
    elif count_1s < upper_limit:
        raise ValueError("Number of 1s is below the acceptable range.")

    return hits.reset_index(drop=True), records.reset_index(drop=True)

def process_and_save_hdf5(original_file_path,time_interval):
    """Processes and modifies an HDF5 file in-place."""
    try:
        start_time = time.time()
        logging.info(f"Processing {original_file_path}")

        output_dir = os.path.dirname(original_file_path)
        temp_dir = f'{output_dir}_{time_interval}' # Start with the original output_dir
        i = 1
        name=os.path.basename(original_file_path)
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
        #logging.info(f"Copied {original_file_path} to {modified_file_path}")

        num,_=name.split('.')
        with pd.HDFStore(modified_file_path, mode='a') as store:  # 'a' mode allows modifying the file
            if 'hits' not in store or 'records' not in store:
                logging.error(f"Skipping {modified_file_path}: Missing 'hits' or 'records' dataset.")
                return f"Skipped {modified_file_path}: Missing required datasets."

            #logging.info('Successfull loading')
            # Read datasets
            hits = store['hits']
            records = store['records']

            if 'event_no' in hits.columns:
                hits = hits.drop(columns=['event_no'])
            if 'event_no' in records.columns:
                records = records.drop(columns=['event_no'])

            # Compute event bins per record_id (Optimized)
            hits["min_time"] = hits.groupby("record_id")["time"].transform('min')
            hits["event_no"] = np.floor((hits["time"] - hits["min_time"]) // time_interval + 1).astype(np.int64)
            hits["event_no"] += ( hits["record_id"].astype(np.int64) * 10**6  # Ensures uniqueness within a dataset
                                    + np.int64(num) * 10**12 ) # Adds uniqueness across datasets)

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
            hits,records=balance_event_types(hits,merged_df)
            #logging.info('hit the save part of the function')
            # Overwrite modified datasets inside the same HDF5 file
            store.put('hits', hits, format='table', data_columns=True, complib='zlib', complevel=5)
            #store.put('records', merged_df, format='table', data_columns=True)
            store.put('records', records, format='table', data_columns=True, complib='zlib', complevel=5)

        
        store.close()
        del store
        duration = time.time() - start_time
        logging.info(f"Completed {modified_file_path} in {duration:.2f} seconds")
        return f"Processed {modified_file_path} in {duration:.2f} seconds"

    except Exception as e:
        logging.error(f"Error processing {modified_file_path}: {str(e)}")
        return f"Error processing {modified_file_path}: {str(e)}"

def update_progress_bar(total_files, progress_queue):
    """Updates the progress bar based on completed tasks."""
    with tqdm(total=total_files, desc="Processing HDF5 Files") as pbar:
        for _ in range(total_files):
            progress_queue.get()  # Wait for an update
            pbar.update(1)

def process_files_parallel(files,time_interval, num_workers=8):
    """Processes multiple HDF5 files in parallel using multiprocessing."""
    manager = multiprocessing.Manager()
    progress_queue = manager.Queue()
    total_files = len(files)

    # Start progress bar in a separate process
    progress_process = multiprocessing.Process(target=update_progress_bar, args=(total_files, progress_queue))
    progress_process.start()

    def update_progress(_):
        """Callback function to update progress bar after each process."""
        progress_queue.put(1)

    with multiprocessing.Pool(processes=num_workers) as pool:
        for file_path in files:
            pool.apply_async(process_and_save_hdf5, args=(file_path,time_interval), callback=update_progress)

        pool.close()
        pool.join()

    progress_process.join()
    print("Processing complete!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("No file paths provided.")
        sys.exit(1)

    # Collect valid HDF5 file paths from command-line arguments
    files = sorted(
    [file for file in sys.argv[1:] if file.endswith('.h5')],
    key=os.path.getsize
)

    if not files:
        print("No valid HDF5 files found.")
        sys.exit(1)

    print(f"Processing {len(files)} HDF5 files in parallel...")
    print(files)


    # Run parallel processing
    process_files_parallel(files, time_interval=10,num_workers=32)  # Adjust num_workers based on system capacity
