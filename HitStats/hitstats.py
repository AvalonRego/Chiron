import os
import pandas as pd
import multiprocessing as mp
import numpy as np
from tqdm import tqdm
import argparse

def check_hdf5(file_path):
    try:
        key_1 = int(os.path.basename(file_path).split('.')[0])
        with pd.HDFStore(file_path, 'r') as store:
            records = store['hits']['record_id']
            counts = pd.Series(records).value_counts()  # ensure Series if NumPy array

            adjusted_indices = counts.index.to_numpy() + (10**12 * key_1)
            result_array = np.column_stack((adjusted_indices, counts.values))

            np.save(f"/ptmp/arego/stat_saves/{key_1}.npy", result_array)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def process_dir(dir_path):
    files = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.endswith('.h5')]
    with mp.Pool(8) as pool:
        list(tqdm(pool.imap_unordered(check_hdf5, files), total=len(files)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dir_path", help="Directory containing .h5 files")
    args = parser.parse_args()

    process_dir(args.dir_path)
