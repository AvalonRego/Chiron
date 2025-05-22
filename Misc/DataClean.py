import os
import multiprocessing
from tqdm import tqdm
import pandas as pd

def check_and_delete_file(file_path, failed_files, progress_queue, total_files):
    """Check if record count is divisible by 10; if not, delete the file."""
    flag=False
    try:
        with pd.HDFStore(file_path, mode='a') as store:  # 'a' mode allows modifying the file
        # Read existing datasets
            hits = store['hits']
            flag =True
        

        
        rec_no = hits['record_id'].nunique()  # Unique record count

        if rec_no % 10 != 0:
            os.remove(file_path)
            result = f"Deleted {file_path} (record count: {rec_no})"
        else:
            result = f"Kept {file_path} (record count: {rec_no})"
        

    except Exception as e:
        failed_files.append(file_path)
        if flag:
            os.remove(file_path)
        result = f"Failed to process {file_path}: {e}"
    


    # Update progress queue
    progress_queue.put(1)
    return result

def update_progress_bar(progress_queue, total_files):
    """Process function to update the tqdm progress bar."""
    with tqdm(total=total_files, desc="Processing Files") as pbar:
        for _ in range(total_files):
            progress_queue.get()  # Wait for an update
            pbar.update(1)

def process_files(path, num_workers=32):
    """Process all files in the given path using multiple cores with progress tracking."""
    files = [os.path.join(path, file) for file in os.listdir(path)]
    files = [file for file in files if '.h5' in file]
    #files = files[:10]
    manager = multiprocessing.Manager()
    failed_files = manager.list()  # Shared list for failed files
    progress_queue = manager.Queue()  # Queue for progress updates
    total_files = len(files)
    #return files

    # Start a separate process for progress tracking
    progress_process = multiprocessing.Process(target=update_progress_bar, args=(progress_queue, total_files))
    progress_process.start()

    with multiprocessing.Pool(num_workers) as pool:
        results = pool.starmap(check_and_delete_file, [(file, failed_files, progress_queue, total_files) for file in files])

    # Wait for progress bar process to finish
    progress_process.join()

    print("\nProcessing complete!")

    # Print results
    for res in results:
        print(res)

    # Save failed file paths
    if failed_files:
        with open("failed_files.txt", "w") as f:
            f.write("\n".join(failed_files))
        print(f"Failed files saved to failed_files.txt")

process_files('/u/arego/Project/LargeBio')