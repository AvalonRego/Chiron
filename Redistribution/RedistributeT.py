import sys
import os
import multiprocessing
import logging
from tqdm import tqdm
from ananke.models.collection import Collection
from ananke.configurations.collection import MergeConfiguration
from ananke.configurations.events import EventRedistributionMode
import time


def redistribute(file, save_location):
    """Handles merging and redistribution of HDF5 files."""
    try:
        name = os.path.basename(file)
        output_path=f'{save_location}/{name}'
        if os.path.exists(output_path):
            os.remove(output_path)
            

        configuration = MergeConfiguration.parse_obj(
            {
                'in_collections': [{'type': 'hdf5', 'data_path': f'{file}'}],
                'out_collection': {
                    'type': 'hdf5',
                    'data_path': output_path,
                    'read_only': False
                },
                'redistribution': {
                    'interval': {'start': 0, 'end': 10000},
                    'mode': EventRedistributionMode.CONTAINS_EVENT
                }
            })
            
            # Attempt to merge
        c = Collection.from_merge(configuration)
        with c:
            records=c.storage.get_records().df
            hits=c.storage.get_hits().df
            if records['record_id'].shape[0]!=hits['record_id'].unique().shape[0]:
                os.remove(output_path)
                logging.info(f"Failed to process {file}")
                return False
        del hits, records,c
        logging.info(f"Successfully processed {file}")
        return True  # Success

    except Exception as e:
        if os.path.isfile(output_path):
            os.remove(output_path)
        logging.error(f"Error processing {file}: {e}")
        return False  # Failure

def update_progress_bar(total_files, progress_queue):
    """Updates the progress bar based on completed tasks."""
    with tqdm(total=total_files, desc="Merging Files") as pbar:
        for _ in range(total_files):
            try:
                progress_queue.get(timeout=10)  # Timeout to prevent deadlock
                pbar.update(1)
            except Exception:
                logging.warning("Progress update timeout. Skipping...")

def process_files(files, save_path, num_workers=None):
    """Processes files in parallel using multiprocessing.Pool."""
    if num_workers is None:
        num_workers = min(16, multiprocessing.cpu_count())  # Limit workers to avoid HDF5 locking issues

    progress_queue = multiprocessing.Queue()
    total_files = len(files)

    # Start progress bar in a separate process
    progress_process = multiprocessing.Process(target=update_progress_bar, args=(total_files, progress_queue))
    progress_process.start()

    def update_progress(success):
        """Callback function to update progress bar after each merge operation."""
        if success:
            progress_queue.put(1)
        else:
            logging.error("Failed process did not update progress bar.")

    with multiprocessing.Pool(processes=num_workers) as pool:
        for file in files:
            pool.apply_async(redistribute, args=(file, save_path), callback=update_progress)

        pool.close()
        pool.join()

    progress_process.join()
    print("Merging complete!")

def remove_if_old(file_path):
    """Removes the file if it was last accessed over 10 minutes ago."""
    if not os.path.exists(file_path):
        print("File does not exist.")
        return
    
    last_access_time = os.path.getatime(file_path)  # Get last access time
    current_time = time.time()  # Get current time

    if current_time - last_access_time > 600:  # 600 seconds = 10 minutes
        os.remove(file_path)
        print(f"Removed: {file_path}")
    else:
        print(f"File is recent: {file_path}")


if __name__ == "__main__":
    print('Merge Start')

    if len(sys.argv) < 2:
        print("No file paths provided.")
        sys.exit(1)

    # Get file paths from command-line arguments
    files = sys.argv[1:]
    print(f"Processing {len(files)} files...")
    for file in files:
        print(file)

    # Run parallel processing with updated fixes
    process_files(files, save_path="/viper/ptmp/arego/R1T4K_1",num_workers=32)

    path='/viper/u/arego/Project/olympus/lib/python3.10/site-packages/'
    files=os.listdir(path)
    files=[file for file in files if file.endswith('.h5')]
    for file in files:
        remove_if_old(f"{path}{file}")