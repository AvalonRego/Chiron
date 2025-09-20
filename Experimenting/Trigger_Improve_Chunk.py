import logging
import os
import numpy as np
import time
import matplotlib.pyplot as plt
from ananke.models.collection import Collection
from ananke.configurations.collection import HDF5StorageConfiguration
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.ipc as ipc
import pandas as pd
from typing import Iterator, Tuple, List, Dict, Any

# Set logging level to INFO
logging.getLogger().setLevel(logging.INFO)


def initialize_and_load_data(data_path: str, trigger_interval: int = 10):
    """
    Initialize the Collection object and load hit data.
    
    Args:
        data_path (str): Path to the HDF5 storage file.
        trigger_interval (int): Interval for binning time data.
    
    Returns:
        Tuple: (hits_data, timer_bins, time_intervals)
    """
    logging.debug('Initializing Collections and Loading Data')
    start = time.time()
    
    # Initialize Collection
    config = HDF5StorageConfiguration(data_path=data_path)
    collection = Collection(config)

    with collection:
        # Load only required columns
        hits_data = collection.storage.get_hits().df

    # Optimize time normalization using map()
    min_time_per_record = hits_data.groupby("record_id")["time"].min().to_dict()
    hits_data["time"] -= hits_data["record_id"].map(min_time_per_record)

    # Optimized min/max calculation
    time_values = hits_data["time"].values
    lower_limit = np.min(time_values)
    upper_limit = np.max(time_values)

    # Efficient bin calculation
    num_bins = int((upper_limit - lower_limit) / trigger_interval) + 1
    timer_bins = np.linspace(lower_limit, upper_limit, num_bins)
    time_intervals = (timer_bins[:-1] + timer_bins[1:]) * 0.5

    end = time.time() - start
    logging.info(f'Initialization and data loading took {end:.2f}s')

    if 'event_no' in hits_data.columns:
        hits_data.drop(columns=['event_no'])

    return hits_data, timer_bins, time_intervals

def initialize_collection(data_path: str):
    """Initialize and return the Collection object."""
    logging.debug('Initializing Collections')
    config = HDF5StorageConfiguration(data_path=data_path, read_only=False)
    collection = Collection(config)
    return collection

def load_data(collection, trigger_interval: int = 10):
    """Load hit and source data from the collection."""
    logging.debug('Loading Data')
    start=time.time()
    collection.open()
    hits_data = collection.storage.get_hits()  # Fetch hits from the collection
    collection.close()

    upper_limit = hits_data.get_statistics().max
    lower_limit = hits_data.get_statistics().min
    timer_bins = np.arange(lower_limit, upper_limit + trigger_interval, trigger_interval)
    time_intervals = (timer_bins[1:] + timer_bins[:-1]) / 2
    end=time.time()-start
    logging.debug(f'it took {end}s to load data')
    return hits_data, timer_bins, time_intervals

def get_data_chunks(hits_data, chunk_size: int = 10000) -> Iterator[pd.DataFrame]:
    """
    Generator that yields chunks of hits data.
    
    Args:
        hits_data: DataFrame or data object with df attribute
        chunk_size: Number of rows per chunk
        
    Yields:
        pd.DataFrame: Chunk of hits data
    """
    if isinstance(hits_data, pd.DataFrame):
        df = hits_data
    else:
        df = hits_data.df
    
    total_rows = len(df)
    logging.info(f'Processing {total_rows} rows in chunks of {chunk_size}')
    
    for start_idx in range(0, total_rows, chunk_size):
        end_idx = min(start_idx + chunk_size, total_rows)
        chunk = df.iloc[start_idx:end_idx].copy()
        logging.debug(f'Processing chunk {start_idx//chunk_size + 1}/{(total_rows-1)//chunk_size + 1}')
        yield chunk

def concatenate_arrays(array_list):
    """Concatenate a list of numpy arrays into a single numpy array."""
    concatenated_array = np.concatenate(array_list.values)
    concatenated_array.sort()
    return concatenated_array

def sum_arrays(array_list):
    """Sum a list of numpy arrays element-wise."""
    return np.sum(array_list.values, axis=0)

def process_hits_chunk(chunk: pd.DataFrame, timer_bins: np.ndarray) -> pd.DataFrame:
    """
    Process a single chunk of hits data and return aggregated results.
    
    Args:
        chunk: DataFrame chunk to process
        timer_bins: Time bins for histogram creation
        
    Returns:
        pd.DataFrame: Processed chunk data
    """
    # Group by PMT level first
    grouped_data = chunk.groupby(['record_id', 'string_id', 'module_id', 'pmt_id'])['time'] \
        .apply(lambda times: np.sort(np.array(times))) \
        .reset_index()

    # Initialize arrays for counting and activation
    count_array = np.zeros((grouped_data.shape[0], len(timer_bins) - 1)).astype(int)
    pmt_activation_array = np.zeros((grouped_data.shape[0], len(timer_bins) - 1)).astype(int)

    # Create histograms for each PMT
    for i in range(grouped_data.shape[0]):
        count_array[i] = np.histogram(grouped_data['time'][i], bins=timer_bins)[0].astype(int)
        pmt_activation_array[i] = np.where(count_array[i] > 0, 1, 0)

    # Assign counts and activations to the DataFrame
    grouped_data['counts'] = [count_array[i] for i in range(count_array.shape[0])]
    grouped_data['pmt_activation'] = [pmt_activation_array[i] for i in range(pmt_activation_array.shape[0])]

    # Aggregate to module level
    aggregated_chunk = (
        grouped_data.groupby(['record_id', 'string_id', 'module_id'])
        .agg({
            'time': concatenate_arrays,  # Concatenate time arrays
            'counts': sum_arrays,         # Sum the counts arrays
            'pmt_activation': sum_arrays   # Sum the pmt_activation arrays
        })
        .reset_index()
    )
    
    return aggregated_chunk

def combine_chunk_results(chunk_results: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Combine results from multiple chunks, aggregating data for the same modules.
    
    Args:
        chunk_results: List of processed chunk DataFrames
        
    Returns:
        pd.DataFrame: Combined and aggregated results
    """
    if not chunk_results:
        return pd.DataFrame()
    
    # Concatenate all chunk results
    combined_df = pd.concat(chunk_results, ignore_index=True)
    
    # Group by the same keys and aggregate again to combine data from different chunks
    # that might have the same record_id, string_id, module_id combination
    final_aggregated = (
        combined_df.groupby(['record_id', 'string_id', 'module_id'])
        .agg({
            'time': concatenate_arrays,  # Concatenate time arrays
            'counts': sum_arrays,         # Sum the counts arrays
            'pmt_activation': sum_arrays   # Sum the pmt_activation arrays
        })
        .reset_index()
    )
    
    return final_aggregated

def process_hits(hits_data, timer_bins, chunk_size: int = 10000):
    """
    Process hits data in chunks and return aggregated results.
    
    Args:
        hits_data: DataFrame or data object with df attribute
        timer_bins: Time bins for histogram creation
        chunk_size: Number of rows to process per chunk
        
    Returns:
        pd.DataFrame: Aggregated results from all chunks
    """
    logging.debug("Started Processing Hits in Chunks")
    start_time = time.time()
    
    chunk_results = []
    
    # Process data in chunks
    for chunk in get_data_chunks(hits_data, chunk_size):
        chunk_result = process_hits_chunk(chunk, timer_bins)
        chunk_results.append(chunk_result)
        
        # Optional: Clear memory after processing each chunk
        del chunk
    
    # Combine results from all chunks
    aggregated_data = combine_chunk_results(chunk_results)
    
    logging.debug(f"Finished Processing Hits in {time.time() - start_time:.2f}s")
    return aggregated_data

def create_trigger_data_chunk(aggregated_chunk: pd.DataFrame) -> pd.DataFrame:
    """
    Create trigger data for a chunk of aggregated data.
    
    Args:
        aggregated_chunk: Chunk of aggregated data
        
    Returns:
        pd.DataFrame: Trigger data for the chunk
    """
    trigger_chunk = aggregated_chunk[['record_id', 'string_id', 'module_id']].copy()
    
    for threshold in range(16):
        # Calculate module count and hit count for this threshold
        mod_count = aggregated_chunk['pmt_activation'].apply(lambda x: np.where(x > threshold, 1, 0))
        trigger_chunk[f'Mod Count CL: {threshold}'] = mod_count
        trigger_chunk[f'Mod Hit Count CL: {threshold}'] = mod_count * aggregated_chunk['counts']
        
        # For time series, only include times where module is triggered
        mask = trigger_chunk[f'Mod Count CL: {threshold}'].apply(np.sum) > 0
        ts_series = aggregated_chunk.loc[mask, 'time'] if mask.any() else pd.Series(dtype=object)
        trigger_chunk[f'TS CL: {threshold}'] = pd.Series([np.array([0])] * len(trigger_chunk), index=trigger_chunk.index)
        if mask.any():
            trigger_chunk.loc[mask, f'TS CL: {threshold}'] = ts_series.apply(
                lambda times: np.where(np.isnan(times), np.array([0]), times)
            )
    
    return trigger_chunk

def create_trigger_data(aggregated_data, chunk_size: int = 1000):
    """
    Create trigger data in chunks to manage memory usage.
    
    Args:
        aggregated_data: Aggregated hits data
        chunk_size: Number of modules to process per chunk
        
    Returns:
        pd.DataFrame: Complete trigger data
    """
    start = time.time()
    logging.debug("Creating Trigger Data in Chunks")
    
    trigger_chunks = []
    total_rows = len(aggregated_data)
    
    for start_idx in range(0, total_rows, chunk_size):
        end_idx = min(start_idx + chunk_size, total_rows)
        chunk = aggregated_data.iloc[start_idx:end_idx].copy()
        
        trigger_chunk = create_trigger_data_chunk(chunk)
        trigger_chunks.append(trigger_chunk)
        
        # Clear chunk from memory
        del chunk
    
    # Combine all trigger chunks
    trigger_data = pd.concat(trigger_chunks, ignore_index=True)
    
    logging.debug(f'Created Trigger Data in chunks and took {time.time()-start:.2f}s')
    return trigger_data

def aggregate_for_plotting_chunk(trigger_chunk: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate a chunk of trigger data for plotting.
    
    Args:
        trigger_chunk: Chunk of trigger data
        
    Returns:
        pd.DataFrame: Aggregated chunk for plotting
    """
    aggregation_dict_a = {col: sum_arrays for col in trigger_chunk.columns if col.startswith('Mod')}
    aggregation_dict_b = {col: concatenate_arrays for col in trigger_chunk.columns if col.startswith('TS')}
    combined_aggregation_dict = {**aggregation_dict_a, **aggregation_dict_b}
    
    plotable_chunk = (
        trigger_chunk.groupby(['record_id'])
        .agg(combined_aggregation_dict)
        .reset_index()
    )
    
    return plotable_chunk

def combine_plotable_chunks(plotable_chunks: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Combine plotable chunks, aggregating data for the same record_ids.
    
    Args:
        plotable_chunks: List of plotable chunk DataFrames
        
    Returns:
        pd.DataFrame: Combined plotable data
    """
    if not plotable_chunks:
        return pd.DataFrame()
    
    combined_df = pd.concat(plotable_chunks, ignore_index=True)
    
    # Group by record_id and aggregate again
    aggregation_dict_a = {col: sum_arrays for col in combined_df.columns if col.startswith('Mod')}
    aggregation_dict_b = {col: concatenate_arrays for col in combined_df.columns if col.startswith('TS')}
    combined_aggregation_dict = {**aggregation_dict_a, **aggregation_dict_b}
    
    final_plotable = (
        combined_df.groupby(['record_id'])
        .agg(combined_aggregation_dict)
        .reset_index()
    )
    
    return final_plotable

def aggregate_for_plotting(trigger_data, chunk_size: int = 1000):
    """
    Prepare the data for plotting by aggregating in chunks.
    
    Args:
        trigger_data: Complete trigger data
        chunk_size: Number of rows to process per chunk
        
    Returns:
        pd.DataFrame: Aggregated data ready for plotting
    """
    logging.debug('Generating plotable results in chunks')
    start = time.time()
    
    plotable_chunks = []
    total_rows = len(trigger_data)
    
    for start_idx in range(0, total_rows, chunk_size):
        end_idx = min(start_idx + chunk_size, total_rows)
        chunk = trigger_data.iloc[start_idx:end_idx].copy()
        
        plotable_chunk = aggregate_for_plotting_chunk(chunk)
        plotable_chunks.append(plotable_chunk)
        
        # Clear chunk from memory
        del chunk
    
    # Combine all plotable chunks
    plotable_trigger_data = combine_plotable_chunks(plotable_chunks)
    
    logging.debug(f'Generated plotable data in chunks and took {time.time()-start:.2f}s')
    return plotable_trigger_data

def plot_results(plotable_trigger_data, time_intervals, CL, num_plots=None):
    """Plot the results for each record."""
    for idx,record_id in enumerate(plotable_trigger_data['record_id']):
        logging.debug(f'Plotting results for record: {record_id}')
        record_data = plotable_trigger_data[plotable_trigger_data['record_id'] == record_id][[f'Mod Count CL: {CL}', f'Mod Hit Count CL: {CL}', f'TS CL: {CL}']]
        
        plt.figure().set_figwidth(15)
        plt.suptitle(f'Record: {record_id}')

        plt.subplot(1, 3, 1)
        plt.scatter(time_intervals, record_data[f'Mod Count CL: {CL}'].iloc[0])
        plt.title('Modules Triggered per Interval')
        plt.ylabel('Number of Modules')
        plt.xlabel('Intervals')

        plt.subplot(1, 3, 2)
        plt.scatter(time_intervals, np.log10(record_data[f'Mod Hit Count CL: {CL}'].iloc[0] + 1))
        plt.title('Total Hits of Triggered Modules per Interval')
        plt.ylabel('log(Total Hits + 1)')
        plt.xlabel('Intervals')

        plt.subplot(1, 3, 3)
        time_stamps = record_data[f'TS CL: {CL}'].iloc[0][record_data[f'TS CL: {CL}'].iloc[0] > 0]
        time_stamps.sort()
        
        if time_stamps.size <= 1:
            plt.axhline(y=0)
            plt.show()
            continue
        
        histogram_bins = np.linspace(min(time_stamps), max(time_stamps), num=100)
        hit_counts, _ = np.histogram(time_stamps, histogram_bins)
        bin_centers = (histogram_bins[:-1] + histogram_bins[1:]) / 2
        plt.plot(bin_centers, hit_counts)
        plt.xlabel('Time in ns')
        plt.ylabel('log(Hit Count)')
        plt.yscale('log')
        plt.title('Hits in Real Time')

        plt.tight_layout()
        plt.show()

        if num_plots is not None:
            if num_plots<=idx:
                break

def save_dataframe(df, path, format="arrow"):
    """
    Save a pandas DataFrame to the specified path in either Parquet or Feather format.
    """
    start=time.time()
    path=path.split('.')[0]
    path=f'{path}.{format}'
    logging.debug(f'saving {path}')
    table = pa.Table.from_pandas(df)
    if format == "parquet":
        pq.write_table(table, path)
    elif format == "feather":
        pa.feather.write_feather(df, path)
    elif format=='arrow':
        table = pa.Table.from_pandas(df)
        # Save to Arrow IPC file
        with ipc.new_file(path, schema=table.schema) as writer:
            writer.write(table)
    else:
        raise ValueError("Unsupported format. Choose 'parquet' or 'feather'.")
    logging.debug(f'saved {path} in {time.time()-start} s')

def load_dataframe(path, format="arrow"):
    """
    Load data from the specified file and return as a pandas DataFrame.
    """
    if format == "parquet":
        table = pq.read_table(path)
    elif format == "feather":
        return pa.feather.read_feather(path)
    elif format == 'arrow':
        with ipc.open_file(path) as reader:
            table = reader.read_all()
            # Convert back to pandas DataFrame
            df_restored = table.to_pandas()
        return df_restored
    else:
        raise ValueError("Unsupported format. Choose 'parquet' or 'feather'.")
    return table.to_pandas()


def main(data_path: str, trigger_interval: int = 10, 
         CL: int = 7, plot: bool = False, 
         save: bool = False, return_value: bool = True,
         format: str = "arrow", chunk_size: int = 1_000_000):
    """
    Main function to execute the data loading, processing, and plotting with chunked processing.
    
    Args:
        data_path: Path to the HDF5 storage file
        trigger_interval: Interval for binning time data
        CL: Confidence level for plotting
        plot: Whether to generate plots
        save: Whether to save results
        return_value: Whether to return processed data
        format: Format for saving data
        chunk_size: Number of rows to process per chunk
    """
    start_time = time.time()
    logging.info('Running main with chunked processing')
    data_path = os.path.abspath(data_path)
    split = os.path.split(data_path)
    path = split[0]
    file = split[1]
    
    collection = initialize_collection(data_path)
    hits_data, timer_bins, time_intervals = load_data(collection, trigger_interval)
    
    # Process hits in chunks
    aggregated_data = process_hits(hits_data, timer_bins, chunk_size)
    
    # Create trigger data in chunks
    trigger_data = create_trigger_data(aggregated_data, chunk_size//10)  # Use smaller chunks for trigger data
    
    # Aggregate for plotting in chunks
    plotable_trigger_data = aggregate_for_plotting(trigger_data, chunk_size//10)
    
    if plot:
        plot_results(plotable_trigger_data, time_intervals, CL)

    if save:
        try:
            save_dataframe(trigger_data.copy(), path+'/trigger/'+file, format)
            save_dataframe(plotable_trigger_data.copy(), path+'/plot/'+file, format)
        except Exception as e:
            print(f'Error saving: {e}')
    
    logging.info(f"main ran in {time.time()-start_time:.2f}s")
    
    if return_value:
        return trigger_data, plotable_trigger_data, time_intervals