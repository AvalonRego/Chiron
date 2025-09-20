import os
import argparse
import numpy as np
from tqdm import tqdm
from multiprocessing import Pool

def init_worker(_shared_array_, _shape_, _dtype_):
    global shared_array, shape, dtype
    shared_array = _shared_array_
    shape = _shape_
    dtype = _dtype_

def write_chunk(args):
    idx, fpath = args
    arr = np.load(fpath, mmap_mode="r")
    shared_array[idx] = arr

def main():
    parser = argparse.ArgumentParser(description="Merge .npy files into one .npy using minimal RAM.")
    parser.add_argument("input_dir", help="Directory with .npy files")
    parser.add_argument("output_file", help="Path for merged output .npy file")
    parser.add_argument("--cores", type=int, default=8, help="Number of worker processes")
    args = parser.parse_args()

    files = [os.path.join(args.input_dir, f) for f in os.listdir(args.input_dir) if f.endswith(".npy")]
    files.sort()

    sample = np.load(files[0], mmap_mode="r")
    shape = (len(files),) + sample.shape
    dtype = sample.dtype

    tmp_file = args.output_file + ".memmap"
    out = np.memmap(tmp_file, dtype=dtype, mode="w+", shape=shape)

    with Pool(processes=args.cores, initializer=init_worker, 
              initargs=(out, shape, dtype)) as pool:
        list(tqdm(pool.imap_unordered(write_chunk, enumerate(files)), total=len(files)))

    out.flush()

    # write proper npy file
    np.save(args.output_file, np.asarray(out))

    # reload merged file and show summary
    merged = np.load(args.output_file, mmap_mode="r")
    print("Final shape:", merged.shape)
    print("First few rows:\n", merged[:5])

if __name__ == "__main__":
    main()
