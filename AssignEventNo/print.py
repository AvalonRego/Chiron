import os
import time
import shutil
import logging
import numpy as np
import pandas as pd
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

def column_check(path):
    with pd.HDFStore(path, 'r') as store:
        column_names = store.get_storer('hits').attrs.data_columns
        if 'event_no' not in column_names:
            return path
        column_names = store.get_storer('records').attrs.data_columns
        if 'event_no' not in column_names:
            return path
    return None

def check_columns_parallel(paths, num_workers=8):
    with Pool(processes=num_workers) as pool:
        results = list(tqdm(pool.imap(column_check, paths), total=len(paths)))
    return [path for path in results if path is not None]

# Example usage
if __name__ == "__main__":
    file_paths = [os.path.join(path,f) for f in os.listdir(path) if f.endswith('.h5')]
    invalid_files = check_columns_parallel(file_paths, num_workers=8)
    print("Files missing 'event_no':", invalid_files)
