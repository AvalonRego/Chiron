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

# Set logging level to INFO
logging.getLogger().setLevel(logging.INFO)

def initialize_collection(data_path: str):
    """Initialize and return the Collection object."""
    logging.info('Initializing Collections')
    config = HDF5StorageConfiguration(data_path=data_path, read_only=False)
    collection = Collection(config)
    return collection

def load_data(collection, trigger_interval: int = 10):
    """Load hit and source data from the collection."""
    logging.info('Loading Data')
    start=time.time()
    collection.open()
    hits_data = collection.storage.get_hits()  # Fetch hits from the collection
    collection.close()

    upper_limit = hits_data.get_statistics().max
    lower_limit = hits_data.get_statistics().min
    timer_bins = np.arange(lower_limit, upper_limit + trigger_interval, trigger_interval)
    time_intervals = (timer_bins[1:] + timer_bins[:-1]) / 2
    end=time.time()-start
    logging.info(f'it took {end}s to load data')
    return hits_data, timer_bins, time_intervals

def concatenate_arrays(array_list):
    """Concatenate a list of numpy arrays into a single numpy array."""
    concatenated_array = np.concatenate(array_list.values)
    concatenated_array.sort()
    return concatenated_array

def sum_arrays(array_list):
    """Sum a list of numpy arrays element-wise."""
    return np.sum(array_list.values, axis=0)

def process_hits(hits_data, timer_bins):
    """Process hits data and return aggregated results."""
    logging.info("Started Processing Hits")
    #Grouping by multiple fields
    if isinstance(hits_data, pd.DataFrame):
        grouped_data = hits_data.groupby(['record_id', 'string_id', 'module_id', 'pmt_id'])['time'] \
            .apply(lambda times: np.sort(np.array(times))) \
            .reset_index()

    else:
        grouped_data = hits_data.df.groupby(['record_id', 'string_id', 'module_id', 'pmt_id'])['time'] \
            .apply(lambda times: np.sort(np.array(times))) \
            .reset_index()

    # grouped_data = hits_data.df.groupby(['record_id', 'string_id', 'module_id', 'pmt_id']) \
    # .apply(lambda group: pd.Series({
    #     'time': np.sort(group['time'].to_numpy()),
    #     'type': group.iloc[group['time'].argsort()]['type'].to_numpy()
    # })) \
    # .reset_index()




    # Initialize arrays for counting and activation
    count_array = np.zeros((grouped_data.shape[0], len(timer_bins) - 1)).astype(int)
    pmt_activation_array = np.zeros((grouped_data.shape[0], len(timer_bins) - 1)).astype(int)

    # Timing the histogram creation
    start_time = time.time()
    for i in range(grouped_data.shape[0]):
        count_array[i] = np.histogram(grouped_data['time'][i], bins=timer_bins)[0].astype(int)
        pmt_activation_array[i] = np.where(count_array[i] > 0, 1, 0)
    logging.info(f'Histogram creation time: {time.time() - start_time:.2f}s')

    # Assign counts and activations to the DataFrame
    grouped_data['counts'] = [count_array[i] for i in range(count_array.shape[0])]
    grouped_data['pmt_activation'] = [pmt_activation_array[i] for i in range(pmt_activation_array.shape[0])]

    # Perform the grouping and aggregation without 'pmt_id'
    aggregated_data = (
        grouped_data.groupby(['record_id', 'string_id', 'module_id'])
        .agg({
            'time': concatenate_arrays,  # Concatenate time arrays
            'counts': sum_arrays,         # Sum the counts arrays
            'pmt_activation': sum_arrays   # Sum the pmt_activation arrays
        })
        .reset_index()
    )
    logging.info("Finished Processing Hits")
    return aggregated_data

def create_trigger_data(aggregated_data):
    start=time.time()
    """Create results DataFrame with necessary calculations.
    TS: time series"""
    logging.info("Creating Results df")
    trigger_data = aggregated_data[['record_id', 'string_id', 'module_id']].copy()
    for threshold in range(16):
        trigger_data[f'Mod Count CL: {threshold}'] = aggregated_data['pmt_activation'].apply(lambda x: np.where(x > threshold, 1, 0))
        trigger_data[f'Mod Hit Count CL: {threshold}'] = trigger_data[f'Mod Count CL: {threshold}'] * aggregated_data['counts']
        trigger_data[f'TS CL: {threshold}'] = aggregated_data[trigger_data[f'Mod Count CL: {threshold}'].apply(np.sum) > 0]['time']
        trigger_data[f'TS CL: {threshold}'] = trigger_data[f'TS CL: {threshold}'].apply(lambda times: np.where(np.isnan(times), np.array([0]), times))
    logging.info(f'Created Results df and took {time.time()-start}s')
    return trigger_data

def aggregate_for_plotting(trigger_data):
    """Prepare the data for plotting by aggregating necessary columns."""
    logging.info('Generating plotable results')
    start=time.time()
    aggregation_dict_a = {col: sum_arrays for col in trigger_data.columns if col.startswith('Mod') or col.startswith('TS')}
    aggregation_dict_b = {col: concatenate_arrays for col in trigger_data.columns if col.startswith('TS')}
    combined_aggregation_dict = {**aggregation_dict_a, **aggregation_dict_b}
    
    plotable_trigger_data = (
        trigger_data.groupby(['record_id'])
        .agg(combined_aggregation_dict)
        .reset_index()
    )
    logging.info(f'Generated plotable data and took {time.time()-start} s')
    return plotable_trigger_data

def plot_results(plotable_trigger_data, time_intervals, CL, num_plots=None):
    """Plot the results for each record."""
    for idx,record_id in enumerate(plotable_trigger_data['record_id']):
        logging.info(f'Plotting results for record: {record_id}')
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
    logging.info(f'saving {path}')
    table = pa.Table.from_pandas(df)
    if format == "parquet":
        pq.write_table(table, path)
    elif format == "feather":
        pa.feather.write_feather(df, path)
    elif format=='arrow':
        table = pa.Table.from_pandas(df)
        # Save to Arrow IPC file
        with ipc.new_file("data.arrow", schema=table.schema) as writer:
            writer.write(table)
    else:
        raise ValueError("Unsupported format. Choose 'parquet' or 'feather'.")
    logging.info(f'saved {path} in {time.time()-start} s')

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
         save: bool =False, return_value: bool=True,
         format:str ="arrow"):
    """Main function to execute the data loading, processing, and plotting."""
    start_time=time.time()
    logging.info('Running main')
    data_path=os.path.abspath(data_path)
    split=os.path.split(data_path)
    path=split[0]
    file=split[1]
    collection = initialize_collection(data_path)
    hits_data, timer_bins, time_intervals = load_data(collection, trigger_interval)
    aggregated_data = process_hits(hits_data, timer_bins)
    trigger_data = create_trigger_data(aggregated_data)
    plotable_trigger_data = aggregate_for_plotting(trigger_data)
    if plot:
        plot_results(plotable_trigger_data, time_intervals,CL)

    if save:
        #print(path+'/trigger/'+file)
        try:
            save_dataframe(trigger_data.copy(),path+'/trigger/'+file,format)
            save_dataframe(plotable_trigger_data.copy(),path+'/plot/'+file,format)
        except:
            print('Error saving')
    logging.info(f"main ran in {time.time()-start_time} s")
    if return_value:
        return trigger_data, plotable_trigger_data, time_intervals
