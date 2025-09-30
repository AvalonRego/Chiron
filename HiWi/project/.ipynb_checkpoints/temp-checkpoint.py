import os
import pandas as pd
import time
from joblib import Parallel, delayed
from tqdm import tqdm

def check_file(file):
    with pd.HDFStore(file, 'r') as store:
        column_names = store['hits'].columns
        if 'event_no' not in column_names:
            return file
        
        column_names = store['records'].columns
        if 'event_no' not in column_names:
            return file
    
    return None

def find_problematic_file(path):
    files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.h5')]
    
    # Using joblib for parallel processing with 8 cores
    result = Parallel(n_jobs=8)(
        delayed(check_file)(file) for file in tqdm(files, desc="Processing files")
    )
    
    
    # Return all problematic files
    return result

# Example usage
t = time.time()
path = '/viper/ptmp1/arego/R1T4K_1_EN_100/'
problematic_files = find_problematic_file(path)
print(f"Time taken: {time.time() - t:.4f} seconds")
