import numpy as np

# define path here
path = "/ptmp/arego/stat_merge_electrical/merge.npy"

def print_npy(file_path):
    arr = np.load(file_path, allow_pickle=True)
    print(arr.shape)

if __name__ == "__main__":
    print_npy(path)
