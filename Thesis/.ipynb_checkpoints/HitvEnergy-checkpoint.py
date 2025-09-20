import os
import pandas as pd
import numpy as np
import multiprocessing

def process_file(file_path):
    """Processes a single HDF5 file using HDFStore and returns an array of (energy, count) pairs."""
    try:
        with pd.HDFStore(file_path, mode='r') as store:
            hits = store["hits"]
            records = store["records"]

            record_counts = hits["record_id"].value_counts().reset_index()
            record_counts.columns = ["record_id", "count"]

            merged_df = records[["record_id", "energy"]].merge(record_counts, on="record_id", how="inner")

            return merged_df[["energy", "count"]].to_numpy()
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return np.empty((0, 2))  # Return empty array on failure

def process_directory(directory, num_workers=8):
    """Processes all .h5 files in a directory using multiprocessing and returns a merged numpy array."""
    h5_files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".h5")]
    h5_files=h5_files[:100]
    with multiprocessing.Pool(processes=min(num_workers, len(h5_files))) as pool:
        results = pool.map(process_file, h5_files)

    return np.vstack(results) if results else np.empty((0, 2))

if __name__="__main__":
# Example usage
    directory = "/viper/ptmp1/arego/LargeTracks/"
    merged_array = process_directory(directory, num_workers=16)
    
    np.save("EvH_LT.npz",merged_array)
    

    print("Final Merged Shape:", merged_array.shape)  # Should be (N, 2), where N is the total rows across files
