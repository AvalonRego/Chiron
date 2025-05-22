import logging
import numpy as np
import pandas as pd
import time
import matplotlib.pyplot as plt
from ananke.models.collection import Collection
from ananke.configurations.collection import HDF5StorageConfiguration
from joblib import Parallel, delayed

# Set logging level to INFO
logging.getLogger().setLevel(logging.INFO)

def setup_logging(log_file='run_log.log'):
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create a file handler to write logs to a file
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)

    # Create a console handler to print logs to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Define a log format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)

    # Apply the formatter to the handlers
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)



def initialize_collection(path: str):
    """Initialize and return the Collection object."""
    config = HDF5StorageConfiguration(data_path=path, read_only=False)
    collection = Collection(config)
    return collection

def load_data(collection, 
              trigger_interval: int = 10, 
              ignore_records: bool = False):
    """Load hit and source data from the collection."""
    collection.open()
    hits = collection.storage.get_hits()  # Fetch hits from the collection
    collection.close()

    upper_limit = hits.get_statistics().max
    lower_limit = hits.get_statistics().min
    times = np.arange(lower_limit, upper_limit + trigger_interval, trigger_interval)
    intervals = (times[1:] + times[:-1]) / 2

    records = [1] if ignore_records else hits.df['record_id'].drop_duplicates()

    return hits, records, times, intervals

def count_in_interval(lst, lower_bound, upper_bound):
    """Counts the number of elements in a list that fall within a specified interval."""
    return sum(lower_bound <= x <= upper_bound for x in lst)

def custom_agg(x):
    """Custom aggregation function to either sum lists or sum numerical values."""
    if isinstance(x.iloc[0], list):
        return sum(x, [])
    else:
        return x.sum()

def prepare_trigger_data(hits, times, trigger_threshold):
    """Processes hit data to determine the number of hits in specified time intervals."""
    hit_in_intervals = {}

    for start_time, end_time in zip(times, times[1:]):
        start_time_rounded = round(start_time, 2)
        end_time_rounded = round(end_time, 2)
        interval_name = f'hit_in_interval_{start_time_rounded}-{end_time_rounded}'
        hit_in_intervals[interval_name] = hits['time'].apply(lambda x: count_in_interval(x, start_time, end_time))

    interval_df = pd.DataFrame(hit_in_intervals)
    hits = pd.concat([hits.reset_index(drop=True), interval_df], axis=1)

    trigger_data_list = []
    for interval in interval_df.columns:
        trigger_data = hits[['string_id', 'module_id', 'pmt_id', 'time', interval]]
        trigger_data = trigger_data[trigger_data[interval] != 0]
        trigger_data = trigger_data.groupby(['string_id', 'module_id']).agg({'time': lambda x: sum(x, []), interval: list}).reset_index()
        trigger_data[f'pmts_hit_in_interval_{interval[16:]}'] = trigger_data[interval].apply(len)
        trigger_data = trigger_data[trigger_data[f'pmts_hit_in_interval_{interval[16:]}'] > trigger_threshold]
        trigger_data[interval] = trigger_data[interval].apply(sum)
        trigger_data.rename(columns={interval: f'ModuleHitCount{interval[16:]}'}, inplace=True)
        trigger_data_list.append(trigger_data)

    return pd.concat(trigger_data_list, ignore_index=True, axis=0).fillna(0)

def process_record(record, hits, ignore_records, trigger_threshold, times):
    """Process a single record to compute the number of modules triggered and hits per interval."""
    logging.info(f'Record {record} started processing.')
    start_time = time.time()

    hit = hits if ignore_records else hits.get_by_record_ids(record)
    hit = hit.df.groupby(["string_id", 'module_id', 'pmt_id'])['time'].apply(list).reset_index()

    trigger_data = prepare_trigger_data(hit, times, trigger_threshold)

    if trigger_data.shape[0] > 1:
        trigger_data = trigger_data.groupby(['string_id', 'module_id']).agg(custom_agg).reset_index()

    modules_triggered = []
    hits_per_interval = []
    for col in trigger_data.columns:
        if col.startswith("ModuleHitCount"):
            modules_triggered.append(trigger_data[trigger_data[col] > 0].shape[0])
            hits_per_interval.append(sum(trigger_data[col]))

    logging.info(f'Time taken for record {record}: {time.time() - start_time:.2f} seconds')
    return [modules_triggered, hits_per_interval, trigger_data['time']]

def process_records(hits, records, ignore_records, trigger_threshold, times, n_workers=2):
    """Processes each record in parallel to compute statistics."""
    results = Parallel(n_jobs=n_workers, verbose=15)(
        delayed(process_record)(record, hits, ignore_records, trigger_threshold, times) for record in records
    )

    # Unpack results
    modules_triggered_per_record = [result[0] for result in results]
    hits_per_interval_per_record = [result[1] for result in results]
    hit_timing = [result[2] for result in results]
    
    return modules_triggered_per_record, hits_per_interval_per_record, hit_timing

def run(path: str, ignore_records: bool = False, trigger_threshold: int = 7, n_workers: int = 8):
    """Main function to compute trigger dataset statistics without any plotting."""
    start_time = time.time()
    
    # Initialize collection and load data
    collection = initialize_collection(path)
    hits, records, times, intervals = load_data(collection=collection, ignore_records=ignore_records)

    # Process records in parallel
    modules_triggered, hits_per_interval, hit_timing = process_records(
        hits, records, ignore_records, trigger_threshold, times, n_workers
    )

    logging.info(f'Total time taken: {time.time() - start_time:.2f} seconds')
    
    # Return the results without generating plots
    return modules_triggered, np.array(hits_per_interval), np.array(hit_timing,dtype=object), np.array(intervals)

def plot(modules_triggered, hits_per_interval, hit_timing, records, intervals):
    """Plot the data from the run function."""
    for number_of_modules_triggered, hits_per_interval, hit_times, record in zip(modules_triggered, hits_per_interval, hit_timing, records):
        plt.figure().set_figwidth(15)
        
        plt.subplot(1, 3, 1)
        plt.scatter(intervals, number_of_modules_triggered)
        plt.title('Modules Triggered per Interval')
        plt.ylabel('Number of modules')
        plt.xlabel('Intervals')

        plt.subplot(1, 3, 2)
        plt.scatter(intervals, np.log10(hits_per_interval + 1))
        plt.title('Total Hits of Triggered Modules per Interval')
        plt.ylabel('log(Total Hits + 1)')
        plt.xlabel('Intervals')

        plt.subplot(1, 3, 3)
        data = np.array(hit_times.sum())
        if data.size == 1:
            plt.axhline(y=0)
            continue
        bins = np.linspace(min(data), max(data), num=100)
        counts, _ = np.histogram(data, bins)
        bin_centers = (bins[:-1] + bins[1:]) / 2
        plt.plot(bin_centers, counts)
        plt.xlabel('Time in ns')
        plt.ylabel('log(Hit Count)')
        plt.yscale('log')
        plt.title('Hits in Real Time')
        
        plt.tight_layout()
        plt.show()

# Example usage:
if __name__ == "__main__":
    #call setup at the start to vreate a log file
    setup_logging('run_log.log')
    # Run data processing
    modules_triggered, hits_per_interval, hit_timing, intervals = run("your_data_path.h5", ignore_records=False)

    # Call plot function with results from run
    plot(modules_triggered, hits_per_interval, hit_timing, records.df['record_id'], intervals)

