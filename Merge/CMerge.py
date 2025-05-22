import os
import sys
import multiprocessing
import logging
from tqdm import tqdm
from ananke.models.collection import Collection
from ananke.configurations.collection import MergeConfiguration
from ananke.schemas.event import RecordType

# Set up logging
logging.basicConfig(
    filename="merge_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def merger(file, base_path):
    """Merges data from HDF5 files."""
    #print('entered merge')
    try:
        name = os.path.basename(file)
        logging.info(f"Starting processing for {name}")

        # Define paths
        data_path = f"{file}"
        en_path = f"{base_path}LargeElectrical/4000s/{name}"
        bn_path = f"{base_path}LargeBio/4000s/{name}"
        save_path = f"{base_path}CMerge4K1/{name}"
        print( data_path,en_path,bn_path,save_path)

        if not os.path.exists(en_path) :
            print(f'{en_path}file dont exist')
            return None

        if not os.path.exists(bn_path) :
            print(f'{bn_path}file dont exist')
            return None
        
        #return None
        #print('try')
        # Skip if file already exists
        if os.path.isfile(save_path):
            print('skip')
            logging.info(f"Skipped {name}: Already exists.")
            return f"Skipped {name}: Already exists."

        # Create merge configuration
        configuration = MergeConfiguration.parse_obj(
            {
                "in_collections": [
                    {"type": "hdf5", "data_path": data_path,"read_only": "False"},
                    {"type": "hdf5", "data_path": en_path,"read_only": "False"},
                    {"type": "hdf5", "data_path": bn_path,"read_only": "False"},
                ],
                "out_collection": {"type": "hdf5", "data_path": save_path, "read_only": "False"},
                "content": [
                    {
                        "primary_type": RecordType.CASCADE.value,
                        "secondary_types": [RecordType.ELECTRICAL.value, RecordType.BIOLUMINESCENCE],
                        "number_of_records": 20,
                        "interval": {"start": 0, "end": 1000000},
                    },
                ],
            }
        )

        # Perform the merge operation
        Collection.from_merge(configuration)

        logging.info(f"Completed {name}")
        return f"Processed {name}"

    except Exception as e:
        logging.error(f"Error processing {file}: {str(e)}")
        return f"Error processing {file}: {str(e)}"
    


        
        


def update_progress_bar(total_files, progress_queue):
    """Updates the progress bar based on completed tasks."""
    with tqdm(total=total_files, desc="Merging Files") as pbar:
        for _ in range(total_files):
            progress_queue.get()  # Wait for an update
            pbar.update(1)

def process_files(files, base_path, num_workers=32):
    """Processes files in parallel using multiprocessing.Pool."""
    manager = multiprocessing.Manager()
    progress_queue = manager.Queue()
    total_files = len(files)
    print('good till here')
    # Start progress bar in a separate process
    progress_process = multiprocessing.Process(target=update_progress_bar, args=(total_files, progress_queue))
    progress_process.start()

    def update_progress(_):
        """Callback function to update progress bar after each merge operation."""
        progress_queue.put(1)

    with multiprocessing.Pool(processes=num_workers) as pool:
        for file in files:
            pool.apply_async(merger, args=(file, base_path), callback=update_progress)

        pool.close()
        pool.join()

    progress_process.join()
    print("Merging complete!")

if __name__ == "__main__":
    print('Merge Start')
    
    if len(sys.argv) < 2:
        print("No file paths provided.")

    # Iterate through the provided file paths and print them
    files=sys.argv[1:]
    print(f"Processing {len(files)} files...")

    # Run parallel processing
    process_files(files, base_path="/viper/ptmp/arego/", num_workers=32)

    path='/viper/u/arego/Project/olympus/lib/python3.10/site-packages/'
    files=os.listdir(path)
    files=[file for file in files if file.endswith('.h5') or file.endswith('.tmp')]
    for file in files:
        os.remove(os.path.join(path, file))
