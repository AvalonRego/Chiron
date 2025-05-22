import os
import pandas as pd
import numpy as np
import multiprocessing
from tqdm import tqdm

def process_file(file_path, output_dir):
    """Processes a single HDF5 file and saves the output as a .npy file."""
    try:
        with pd.HDFStore(file_path, mode='r') as store:
            # Read data from HDF5 file
            hits = store["hits"]['record_id']
            records = store["records"][['record_id', 'energy']]
            
            # Count occurrences of each record_id
            record_counts = hits.value_counts().reset_index()
            record_counts.columns = ["record_id", "count"]
            
            # Merge energy values with count data
            merged_df = records.merge(record_counts, on="record_id", how="inner")
            result_array = merged_df[["energy", "count"]].to_numpy()
            
            # Save as .npy file
            output_file = os.path.join(output_dir, os.path.basename(file_path).replace(".h5", ".npy"))
            np.save(output_file, result_array)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def process_wrapper(args):
    """Wrapper function for multiprocessing."""
    file_path, output_dir = args
    process_file(file_path, output_dir)

def merge_and_cleanup(output_dir, batch_size=1000):
    """Merges every batch_size .npy files and deletes originals after merging."""
    npy_files = sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".npy") and 'merged' not in f])
    
    while len(npy_files) >= batch_size:
        # Select a batch of files to merge
        batch = npy_files[:batch_size]
        
        # Load and concatenate data
        merged_data = np.vstack([np.load(f) for f in batch])
        merge_count=len([f for f in os.listdir(output_dir) if 'merged' in f])
        # Save merged batch
        batch_output_file = os.path.join(output_dir, f"merged_{merge_count}.npy")
        np.save(batch_output_file, merged_data)

        # Delete original files after merging
        for f in batch:
            os.remove(f)
        
        # Update file list after deletion
        npy_files = npy_files[batch_size:]

def process_directory(input_dir, output_dir, num_workers=8, batch_size=1000):
    """Processes all .h5 files and merges every batch_size .npy files."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all .h5 files and sort them by size (smallest first for efficiency)
    h5_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith(".h5")]
    h5_files.sort(key=lambda f: os.path.getsize(f))
    temp=h5_files
    h5_files=h5_files[:-100]
    with multiprocessing.Pool(processes=min(num_workers, len(h5_files))) as pool:
        with tqdm(total=len(h5_files), desc="Processing Files") as pbar:
            for i, _ in enumerate(pool.imap_unordered(process_wrapper, [(f, output_dir) for f in h5_files])):
                pbar.update(1)
                
                # Merge and clean up every batch_size files
                if (i + 1) % batch_size == 0:
                    merge_and_cleanup(output_dir, batch_size)
    
    h5_files=temp[-100:]
    with multiprocessing.Pool(processes=min(num_workers//4, len(h5_files))) as pool:
        with tqdm(total=len(h5_files), desc="Processing Files") as pbar:
            for i, _ in enumerate(pool.imap_unordered(process_wrapper, [(f, output_dir) for f in h5_files])):
                pbar.update(1)
                
                # Merge and clean up every batch_size files
                if (i + 1) % batch_size == 0:
                    merge_and_cleanup(output_dir, batch_size)
    
    # Final merge after all files are processed
    merge_and_cleanup(output_dir, batch_size)

def merge_results(output_dir, merged_file):
    """Loads remaining .npy files and merges them into a final file."""
    npy_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith(".npy") and 'merged' in f]
    
    # Load and merge all remaining .npy files
    results = [np.load(f) for f in npy_files]
    merged_array = np.vstack(results) if results else np.empty((0, 2))
    
    # Save final merged file
    np.save(merged_file, merged_array)
    print("Final Merged Shape:", merged_array.shape)

if __name__ == "__main__":
    # Define input and output directories
    # input_dir = "/viper/ptmp/arego/R1T4K/"
    # output_dir = "/u/arego/Project/Thesis/plot/R1T4K_HvE"
    # merged_file = "EvHRT.npy"
    #input_dir = "/viper/ptmp/arego/RC4K1/"
    #output_dir = "/u/arego/Project/Thesis/plot/RC4K1_HvE"
    #merged_file = "EvHRC.npy"
    input_dir = "/viper/ptmp/arego/TMerge/"
    output_dir = "/u/arego/Project/Thesis/plot/TM100K_HvE"
    merged_file = "EvHTM.npy"
    print(input)
    # Process .h5 files, merge in batches, and create final merged file
    process_directory(input_dir, output_dir, num_workers=16, batch_size=1000)
    merge_results(output_dir, merged_file)
