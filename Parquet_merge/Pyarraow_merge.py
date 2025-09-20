import pyarrow.parquet as pq
import pyarrow as pa
import glob
import os
from concurrent.futures import ThreadPoolExecutor

# Set chunk size
CHUNK_SIZE = 10
THREADS = 16

def read_parquet(file):
    """Reads a single Parquet file."""
    return pq.read_table(file)

def merge_and_save(parquet_files, output_path, chunk_id):
    """Merges a chunk of Parquet files and saves them."""
    if os.path.exists(output_path):
        print(f"⏭️  Skipping existing chunk {chunk_id}: {output_path}")
        return

    print(f"🔄 Merging chunk {chunk_id} with {len(parquet_files)} files...")

    # Use ThreadPoolExecutor instead of multiprocessing for I/O-bound tasks
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        tables = list(executor.map(read_parquet, parquet_files))

    # Merge tables efficiently
    merged_table = pa.concat_tables(tables, promote=True)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    pq.write_table(merged_table, output_path)

    del merged_table, tables
    print(f"✅ Saved chunk {chunk_id}: {output_path}")

def process_directory(input_dir, output_dir, prefix):
    """Processes all Parquet files in chunks of CHUNK_SIZE."""
    parquet_files = glob.glob(os.path.join(input_dir, "*.parquet"))
    
    if not parquet_files:
        print(f"No Parquet files found in {input_dir}. Skipping...")
        return

    print(f"🔍 Found {len(parquet_files)} files in {input_dir}")

    # Precompute chunks and process them
    for chunk_id, i in enumerate(range(0, len(parquet_files), CHUNK_SIZE)):
        chunk_files = parquet_files[i:i + CHUNK_SIZE]
        output_path = os.path.join(output_dir, f"{prefix}_chunk_{chunk_id}.parquet")
        merge_and_save(chunk_files, output_path, chunk_id)
        if chunk_id > 3:
            break

# Define directories
hits_input = "/viper/ptmp/arego/LBC_parquet/hits"
hits_output = "/viper/ptmp/arego/LBC_Chunk/hits"

records_input = "/viper/ptmp/arego/LBC_parquet/records"
records_output = "/viper/ptmp/arego/LBC_Chunk/records"

# Process "hits" and "records"
process_directory(hits_input, hits_output, "hits")
process_directory(records_input, records_output, "records")

print("🎉 Merging completed successfully!")
