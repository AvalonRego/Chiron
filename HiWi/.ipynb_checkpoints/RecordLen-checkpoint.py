import pandas as pd
import os
import gc
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
import logging
from typing import Optional, Tuple, Dict, List
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_record_metrics(hits_chunk: pd.DataFrame, record_times_dict: Dict, 
                         record_hit_counts_dict: Dict, progress: bool = True) -> None:
    """
    Extract and accumulate metrics for record_ids from a hits chunk.
    
    Args:
        hits_chunk: Chunk of hits data with record_id and time columns
        record_times_dict: Dict to accumulate {record_id: [min_time, max_time]}
        record_hit_counts_dict: Dict to accumulate {record_id: hit_count}
        progress: Whether to show progress information
    """
    if progress:
        logger.debug(f"Processing chunk with {len(hits_chunk)} hits")
    
    # Group by record_id and get time statistics
    time_stats = hits_chunk.groupby('record_id')['time'].agg(['min', 'max', 'count'])
    
    # Update accumulation dictionaries
    for record_id, row in time_stats.iterrows():
        min_time, max_time, count = row['min'], row['max'], row['count']
        
        # Update hit counts
        if record_id in record_hit_counts_dict:
            record_hit_counts_dict[record_id] += count
        else:
            record_hit_counts_dict[record_id] = count
            
        # Update time ranges
        if record_id in record_times_dict:
            current_min, current_max = record_times_dict[record_id]
            record_times_dict[record_id] = [
                min(current_min, min_time),
                max(current_max, max_time)
            ]
        else:
            record_times_dict[record_id] = [min_time, max_time]

def finalize_record_metrics(file_id: int, record_times_dict: Dict, 
                          record_hit_counts_dict: Dict, progress: bool = True) -> pd.DataFrame:
    """
    Convert accumulated metrics into final DataFrame.
    
    Args:
        file_id: The file identifier
        record_times_dict: Accumulated time data per record_id
        record_hit_counts_dict: Accumulated hit counts per record_id
        progress: Whether to show progress information
        
    Returns:
        DataFrame with final metrics per record_id
    """
    if progress:
        logger.debug(f"Finalizing metrics for {len(record_times_dict)} record_ids")
    
    results = []
    for record_id in record_times_dict.keys():
        min_time, max_time = record_times_dict[record_id]
        hit_count = record_hit_counts_dict[record_id]
        duration = max_time - min_time
        
        results.append({
            'file_id': file_id,
            'record_id': record_id,
            'duration': duration,
            'min_time': min_time,
            'max_time': max_time,
            'hit_count': hit_count
        })
    
    return pd.DataFrame(results)

def process_single_file(file_path: str, intermediate_dir: str, progress: bool = True) -> bool:
    """
    Process a single HDF5 file and save intermediate results.
    
    Args:
        file_path: Path to the HDF5 file
        intermediate_dir: Directory to save intermediate parquet files
        progress: Whether to show progress information
        
    Returns:
        Boolean indicating success
    """
    try:
        file_id = int(Path(file_path).stem)
        if progress:
            logger.info(f"Processing file {file_id}: {file_path}")
        
        # Initialize accumulation dictionaries
        record_times_dict = {}
        record_hit_counts_dict = {}
        
        # Load records (small dataset, no chunking needed)
        if progress:
            logger.debug(f"Loading records dataset for file {file_id}")
        records_df = pd.read_hdf(file_path, key='records')
        
        # Get total hits count for chunking
        with pd.HDFStore(file_path, mode='r') as store:
            hits_info = store.get_storer('hits')
            total_hits = hits_info.nrows if hits_info else 0
        
        if total_hits == 0:
            logger.warning(f"No hits data found in file {file_id}")
            return False
            
        chunk_size = 1_000_000
        
        if progress:
            logger.debug(f"Processing {total_hits} hits in chunks of {chunk_size}")
        
        # Process hits in chunks using pandas
        for start_idx in range(0, total_hits, chunk_size):
            end_idx = min(start_idx + chunk_size, total_hits)
            
            if progress:
                logger.debug(f"Processing hits chunk {start_idx:,} to {end_idx:,}")
            
            # Load chunk using pandas
            hits_chunk = pd.read_hdf(file_path, key='hits', start=start_idx, stop=end_idx)
            
            # Extract metrics from this chunk
            extract_record_metrics(hits_chunk, record_times_dict, 
                                 record_hit_counts_dict, progress)
            
            # Clear chunk from memory
            del hits_chunk
            gc.collect()
        
        # Finalize metrics for this file
        final_df = finalize_record_metrics(file_id, record_times_dict, 
                                         record_hit_counts_dict, progress)
        
        # Save intermediate result
        intermediate_path = os.path.join(intermediate_dir, f"{file_id}.parquet")
        final_df.to_parquet(intermediate_path, index=False)
        
        if progress:
            logger.info(f"Completed file {file_id}: {len(final_df)} records saved to {intermediate_path}")
        
        # Clear memory
        del record_times_dict, record_hit_counts_dict, records_df, final_df
        gc.collect()
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        return False

def get_h5_files(input_dir: str, file_range: Optional[Tuple[int, int]] = None) -> List[str]:
    """
    Get list of HDF5 files to process.
    
    Args:
        input_dir: Directory containing HDF5 files
        file_range: Optional tuple (start, end) to limit file range for debugging
        
    Returns:
        List of file paths to process
    """
    input_path = Path(input_dir)
    all_files = []
    
    for file_path in input_path.glob("*.h5"):
        try:
            file_id = int(file_path.stem)
            all_files.append((file_id, str(file_path)))
        except ValueError:
            logger.warning(f"Skipping file with non-integer name: {file_path}")
    
    # Sort by file_id
    all_files.sort(key=lambda x: x[0])
    
    # Apply file range filter if specified
    if file_range:
        start_id, end_id = file_range
        all_files = [(fid, fpath) for fid, fpath in all_files 
                     if start_id <= fid <= end_id]
        logger.info(f"Filtered to file range {start_id}-{end_id}: {len(all_files)} files")
    
    return [fpath for _, fpath in all_files]

def merge_intermediate_files(intermediate_dir: str, output_path: str, progress: bool = True) -> bool:
    """
    Merge all intermediate parquet files into final output.
    
    Args:
        intermediate_dir: Directory containing intermediate parquet files
        output_path: Path for final merged parquet file
        progress: Whether to show progress information
        
    Returns:
        Boolean indicating success
    """
    try:
        if progress:
            logger.info("Starting merge of intermediate files")
        
        intermediate_path = Path(intermediate_dir)
        parquet_files = list(intermediate_path.glob("*.parquet"))
        
        if not parquet_files:
            logger.error("No intermediate parquet files found")
            return False
        
        if progress:
            logger.info(f"Found {len(parquet_files)} intermediate files to merge")
        
        # Read and concatenate all intermediate files
        dfs = []
        for file_path in tqdm(parquet_files, desc="Loading intermediate files", disable=not progress):
            df = pd.read_parquet(file_path)
            dfs.append(df)
        
        # Concatenate all dataframes
        if progress:
            logger.info("Concatenating all dataframes")
        final_df = pd.concat(dfs, ignore_index=True)
        
        # Sort by file_id and record_id for consistent output
        final_df = final_df.sort_values(['file_id', 'record_id']).reset_index(drop=True)
        
        # Save final result
        final_df.to_parquet(output_path, index=False)
        
        if progress:
            logger.info(f"Final merged file saved: {output_path}")
            logger.info(f"Total records processed: {len(final_df):,}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error merging intermediate files: {str(e)}")
        return False

def main_processor(input_dir: str, intermediate_dir: str, output_path: str,
                  file_range: Optional[Tuple[int, int]] = None,
                  n_cores: Optional[int] = None,
                  progress_flags: Optional[Dict[str, bool]] = None) -> bool:
    """
    Main processing function that orchestrates the entire pipeline.
    
    Args:
        input_dir: Directory containing HDF5 files
        intermediate_dir: Directory to save intermediate parquet files
        output_path: Path for final merged parquet file
        file_range: Optional (start, end) tuple for debugging specific file range
        n_cores: Number of cores to use (None for auto-detect)
        progress_flags: Dict controlling progress display for different functions
        
    Returns:
        Boolean indicating overall success
    """
    # Set up progress flags
    if progress_flags is None:
        progress_flags = {}
    
    main_progress = progress_flags.get('main', True)
    file_progress = progress_flags.get('file_processing', True)
    merge_progress = progress_flags.get('merging', True)
    
    # Create directories
    os.makedirs(intermediate_dir, exist_ok=True)
    os.makedirs(Path(output_path).parent, exist_ok=True)
    
    # Get files to process
    files_to_process = get_h5_files(input_dir, file_range)
    
    if not files_to_process:
        logger.error("No HDF5 files found to process")
        return False
    
    if main_progress:
        logger.info(f"Found {len(files_to_process)} files to process")
        if n_cores:
            logger.info(f"Using {n_cores} cores")
    
    # Process files in parallel
    successful_files = 0
    failed_files = []
    
    with ProcessPoolExecutor(max_workers=n_cores) as executor:
        # Submit all jobs
        future_to_file = {
            executor.submit(process_single_file, file_path, intermediate_dir, file_progress): file_path
            for file_path in files_to_process
        }
        
        # Track progress
        for future in tqdm(future_to_file, desc="Processing files", disable=not main_progress):
            file_path = future_to_file[future]
            try:
                success = future.result()
                if success:
                    successful_files += 1
                else:
                    failed_files.append(file_path)
            except Exception as e:
                logger.error(f"Exception processing {file_path}: {str(e)}")
                failed_files.append(file_path)
    
    # Report processing results
    if main_progress:
        logger.info(f"File processing complete: {successful_files} successful, {len(failed_files)} failed")
        if failed_files:
            logger.warning(f"Failed files: {failed_files}")
    
    # Merge intermediate files
    if successful_files > 0:
        if main_progress:
            logger.info("Starting merge of intermediate results")
        merge_success = merge_intermediate_files(intermediate_dir, output_path, merge_progress)
        
        if merge_success and main_progress:
            logger.info("Processing pipeline completed successfully")
            
        return merge_success
    else:
        logger.error("No files were successfully processed")
        return False

def process_files_with_progress_control(input_dir: str, intermediate_dir: str, output_path: str,
                                      file_range: Optional[Tuple[int, int]] = None,
                                      n_cores: Optional[int] = None,
                                      show_main_progress: bool = True,
                                      show_file_progress: bool = True,
                                      show_merge_progress: bool = True) -> bool:
    """
    Convenience function with individual progress controls.
    
    Args:
        input_dir: Directory containing HDF5 files  
        intermediate_dir: Directory to save intermediate parquet files
        output_path: Path for final merged parquet file
        file_range: Optional (start, end) tuple for debugging specific file range
        n_cores: Number of cores to use (None for auto-detect)
        show_main_progress: Show main progress bar
        show_file_progress: Show file-level progress info
        show_merge_progress: Show merge progress
        
    Returns:
        Boolean indicating overall success
    """
    progress_flags = {
        'main': show_main_progress,
        'file_processing': show_file_progress, 
        'merging': show_merge_progress
    }
    
    return main_processor(input_dir, intermediate_dir, output_path,
                         file_range, n_cores, progress_flags)

# Example usage functions for testing individual components
def test_single_file(file_path: str, intermediate_dir: str) -> bool:
    """Test processing of a single file."""
    return process_single_file(file_path, intermediate_dir, progress=True)

def test_merge_only(intermediate_dir: str, output_path: str) -> bool:
    """Test only the merging functionality."""
    return merge_intermediate_files(intermediate_dir, output_path, progress=True)

def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Process HDF5 physics data files to extract record metrics",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    parser.add_argument(
        "input_dir",
        help="Directory containing HDF5 files ({int}.h5 format)"
    )
    parser.add_argument(
        "intermediate_dir", 
        help="Directory to save intermediate parquet files"
    )
    parser.add_argument(
        "output_path",
        help="Path for final merged parquet file"
    )
    
    # Optional arguments
    parser.add_argument(
        "--file-range",
        nargs=2,
        type=int,
        metavar=('START', 'END'),
        help="Process only files in range [START, END] (inclusive, for debugging)"
    )
    
    parser.add_argument(
        "--cores", "-c",
        type=int,
        help="Number of CPU cores to use (default: auto-detect)"
    )
    
    # Progress control flags
    progress_group = parser.add_argument_group("progress control")
    progress_group.add_argument(
        "--no-main-progress",
        action="store_true",
        help="Disable main progress bar"
    )
    progress_group.add_argument(
        "--no-file-progress", 
        action="store_true",
        help="Disable file-level progress logging"
    )
    progress_group.add_argument(
        "--no-merge-progress",
        action="store_true", 
        help="Disable merge progress bar"
    )
    progress_group.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Disable all progress output (equivalent to all --no-* flags)"
    )
    
    # Logging level
    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help="Set logging level"
    )
    
    # Test mode flags
    test_group = parser.add_argument_group("testing options")
    test_group.add_argument(
        "--test-single-file",
        help="Test processing of a single file (provide file path)"
    )
    test_group.add_argument(
        "--test-merge-only",
        action="store_true",
        help="Test only the merging step (skip file processing)"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Handle quiet mode
    if args.quiet:
        show_main_progress = False
        show_file_progress = False  
        show_merge_progress = False
    else:
        show_main_progress = not args.no_main_progress
        show_file_progress = not args.no_file_progress
        show_merge_progress = not args.no_merge_progress
    
    # Convert file range to tuple if provided
    file_range = None
    if args.file_range:
        file_range = (args.file_range[0], args.file_range[1])
        logger.info(f"File range specified: {file_range[0]} to {file_range[1]}")
    
    # Handle test modes
    if args.test_single_file:
        logger.info(f"Testing single file: {args.test_single_file}")
        success = test_single_file(args.test_single_file, args.intermediate_dir)
        if success:
            print("Single file test completed successfully!")
        else:
            print("Single file test failed!")
        return
    
    if args.test_merge_only:
        logger.info("Testing merge functionality only")
        success = test_merge_only(args.intermediate_dir, args.output_path)
        if success:
            print("Merge test completed successfully!")
        else:
            print("Merge test failed!")
        return
    
    # Validate input arguments
    if not os.path.exists(args.input_dir):
        logger.error(f"Input directory does not exist: {args.input_dir}")
        return
    
    if not os.path.isdir(args.input_dir):
        logger.error(f"Input path is not a directory: {args.input_dir}")
        return
    
    # Log configuration
    logger.info("=== HDF5 Physics Data Processor ===")
    logger.info(f"Input directory: {args.input_dir}")
    logger.info(f"Intermediate directory: {args.intermediate_dir}")
    logger.info(f"Output path: {args.output_path}")
    
    if args.cores:
        logger.info(f"Using {args.cores} CPU cores")
    else:
        logger.info("Using auto-detected CPU cores")
        
    if file_range:
        logger.info(f"Processing file range: {file_range[0]} to {file_range[1]}")
    else:
        logger.info("Processing all files in directory")
    
    # Run main processing
    success = process_files_with_progress_control(
        input_dir=args.input_dir,
        intermediate_dir=args.intermediate_dir,
        output_path=args.output_path,
        file_range=file_range,
        n_cores=args.cores,
        show_main_progress=show_main_progress,
        show_file_progress=show_file_progress,
        show_merge_progress=show_merge_progress
    )
    
    if success:
        print("\n🎉 Processing completed successfully!")
        logger.info(f"Final output saved to: {args.output_path}")
    else:
        print("\n❌ Processing failed!")
        logger.error("Check logs above for error details")

if __name__ == "__main__":
    main()