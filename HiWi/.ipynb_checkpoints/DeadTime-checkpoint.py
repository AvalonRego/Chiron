#!/usr/bin/env python3
"""
HPC script to apply dead time filtering to detector simulation data.
Processes .h5 files with PMT-level dead time applied per record_id.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import argparse
import sys


def apply_deadtime_to_group(group_data, deadtime_ns):
    """
    Apply dead time filter to a single PMT within a single record_id.
    
    Parameters:
    -----------
    group_data : pd.DataFrame
        Data for one PMT in one record_id
    deadtime_ns : float
        Dead time in nanoseconds
    
    Returns:
    --------
    pd.DataFrame : Filtered data with dead time applied
    """
    if len(group_data) == 0:
        return group_data
    
    # CRITICAL: Sort by time to ensure correct ordering
    # The data may not be time-sorted in the input file
    group_data = group_data.sort_values('time').reset_index(drop=True)
    
    # Initialize mask - first hit is always accepted
    keep_mask = np.zeros(len(group_data), dtype=bool)
    keep_mask[0] = True
    
    last_accepted_time = group_data.iloc[0]['time']
    
    # Iterate through hits
    for idx in range(1, len(group_data)):
        current_time = group_data.iloc[idx]['time']
        
        # Check if enough time has passed since last accepted hit
        if current_time - last_accepted_time >= deadtime_ns:
            keep_mask[idx] = True
            last_accepted_time = current_time
    
    return group_data[keep_mask]


def process_chunk(chunk, deadtime_ns):
    """
    Process a chunk of data by applying dead time filtering.
    
    Parameters:
    -----------
    chunk : pd.DataFrame
        Chunk of hits data
    deadtime_ns : float
        Dead time in nanoseconds
    
    Returns:
    --------
    pd.DataFrame : Filtered chunk
    """
    # Group by record_id and PMT identifier
    grouped = chunk.groupby(['record_id', 'string_id', 'module_id', 'pmt_id'], 
                           group_keys=False)
    
    # Apply dead time to each group
    filtered = grouped.apply(lambda x: apply_deadtime_to_group(x, deadtime_ns))
    
    return filtered.reset_index(drop=True)


def process_single_file(args):
    """
    Process a single h5 file with dead time filtering.
    
    Parameters:
    -----------
    args : tuple
        (input_file_path, output_dir, deadtime_ns, chunk_size, debug)
    
    Returns:
    --------
    tuple : (filename, success, message)
    """
    if len(args) == 5:
        input_file, output_dir, deadtime_ns, chunk_size, debug = args
    else:
        input_file, output_dir, deadtime_ns, chunk_size = args
        debug = False
    
    try:
        input_path = Path(input_file)
        output_path = Path(output_dir) / input_path.name
        
        if debug:
            print(f"\n{'='*60}")
            print(f"DEBUG: Starting processing of {input_path.name}")
            print(f"{'='*60}")
            print(f"Input file: {input_path}")
            print(f"Output file: {output_path}")
            print(f"Dead time: {deadtime_ns} ns")
            print(f"Chunk size: {chunk_size:,}")
        
        # Get all keys from the file
        if debug:
            print(f"\nDEBUG: Opening file to read keys...")
        with pd.HDFStore(input_path, 'r') as store:
            all_keys = store.keys()
        
        if debug:
            print(f"DEBUG: Found keys in file: {all_keys}")
        
        # Get total number of rows in 'hits' for progress bar
        if debug:
            print(f"DEBUG: Getting total row count...")
        with pd.HDFStore(input_path, 'r') as store:
            if '/hits' not in all_keys:
                return (input_path.name, False, "No 'hits' key found")
            
            total_rows = store.get_storer('hits').nrows
        
        if debug:
            print(f"DEBUG: Total rows in 'hits': {total_rows:,}")
        
        # Create progress bar for this file
        pbar = tqdm(total=total_rows, 
                   desc=f"Processing {input_path.name}", 
                   position=0, 
                   leave=False,
                   disable=debug)  # Disable progress bar in debug mode
        
        # Process hits data in chunks with record_id boundary handling
        all_filtered = []
        buffer_data = None
        
        if debug:
            print(f"\nDEBUG: Starting chunked reading...")
        
        # Read in chunks using iterator
        chunk_iterator = pd.read_hdf(input_path, key='hits', chunksize=chunk_size, mode='r')
        
        chunk_num = 0
        for chunk in chunk_iterator:
            chunk_num += 1
            
            if debug:
                print(f"\nDEBUG: Processing chunk {chunk_num}")
                print(f"  - Chunk shape: {chunk.shape}")
                print(f"  - Columns: {list(chunk.columns)}")
                print(f"  - Unique record_ids in chunk: {chunk['record_id'].nunique()}")
            
            # If we have buffer data from previous iteration, prepend it
            if buffer_data is not None:
                if debug:
                    print(f"  - Adding {len(buffer_data)} rows from buffer")
                chunk = pd.concat([buffer_data, chunk], ignore_index=True)
                buffer_data = None
            
            # We need to handle record_id boundaries more carefully
            # Only buffer the LAST record_id if it might be incomplete
            # A record_id is complete if we've seen its last row
            
            # Check if this is not the last chunk by trying to peek at the iterator
            # Since we can't peek, we'll use a simpler heuristic:
            # Only buffer record_ids that appear in BOTH the beginning and end of the chunk
            # These are likely large record_ids that span the entire chunk
            
            if len(chunk) >= chunk_size:
                # Get the last record_id in the chunk - this one might be incomplete
                last_record_id = chunk.iloc[-1]['record_id']
                
                # Only buffer rows from this specific record_id
                incomplete_mask = chunk['record_id'] == last_record_id
                buffer_data = chunk[incomplete_mask].copy()
                chunk = chunk[~incomplete_mask]
                
                if debug:
                    print(f"  - Last record_id in chunk: {last_record_id}")
                    print(f"  - Moved {len(buffer_data)} rows to buffer for this record_id")
                    print(f"  - Processing {len(chunk)} rows in this iteration")
            
            # Process chunk
            if len(chunk) > 0:
                if debug:
                    print(f"  - Applying dead time filter...")
                    n_pmts = chunk.groupby(['string_id', 'module_id', 'pmt_id']).ngroups
                    n_records = chunk['record_id'].nunique()
                    print(f"  - Number of unique PMTs: {n_pmts}")
                    print(f"  - Number of unique record_ids: {n_records}")
                
                filtered_chunk = process_chunk(chunk, deadtime_ns)
                
                if debug:
                    reduction = (1 - len(filtered_chunk) / len(chunk)) * 100
                    print(f"  - Filtered: {len(chunk)} → {len(filtered_chunk)} rows ({reduction:.1f}% reduction)")
                
                all_filtered.append(filtered_chunk)
            
            pbar.update(len(chunk))
        
        # Process any remaining buffer data
        if buffer_data is not None and len(buffer_data) > 0:
            if debug:
                print(f"\nDEBUG: Processing final buffer data ({len(buffer_data)} rows)")
            filtered_chunk = process_chunk(buffer_data, deadtime_ns)
            all_filtered.append(filtered_chunk)
            pbar.update(len(buffer_data))
        
        pbar.close()
        
        if debug:
            print(f"\nDEBUG: Finished chunked processing")
            print(f"  - Total chunks processed: {chunk_num}")
            print(f"  - Total filtered chunks: {len(all_filtered)}")
        
        # Combine all filtered chunks
        if not all_filtered:
            return (input_path.name, False, "No data after filtering")
        
        if debug:
            print(f"\nDEBUG: Combining all filtered chunks...")
        final_filtered = pd.concat(all_filtered, ignore_index=True)
        
        if debug:
            print(f"DEBUG: Final combined shape: {final_filtered.shape}")
            overall_reduction = (1 - len(final_filtered) / total_rows) * 100
            print(f"DEBUG: Overall reduction: {total_rows:,} → {len(final_filtered):,} ({overall_reduction:.1f}%)")
        
        # Write output file
        if debug:
            print(f"\nDEBUG: Writing output file...")
        with pd.HDFStore(output_path, 'w', complevel=9, complib='blosc') as store_out:
            # Copy all keys except 'hits'
            if debug:
                print(f"DEBUG: Copying non-hits keys: {[k for k in all_keys if k != '/hits']}")
            with pd.HDFStore(input_path, 'r') as store_in:
                for key in all_keys:
                    if key != '/hits':
                        data = store_in[key]
                        store_out.put(key, data)
                        if debug:
                            print(f"  - Copied key: {key}")
            
            # Write filtered hits
            if debug:
                print(f"DEBUG: Writing filtered 'hits' data...")
            store_out.put('hits', final_filtered, format='table')
        
        if debug:
            print(f"DEBUG: Output file written successfully")
            print(f"{'='*60}\n")
        
        reduction = (1 - len(final_filtered) / total_rows) * 100
        return (input_path.name, True, 
               f"Filtered: {total_rows} → {len(final_filtered)} hits ({reduction:.1f}% reduction)")
        
    except Exception as e:
        import traceback
        return (input_path.name, False, f"Error: {str(e)}\n{traceback.format_exc()}")


def main():
    parser = argparse.ArgumentParser(
        description='Apply dead time filtering to detector simulation h5 files'
    )
    parser.add_argument('input_dir', type=str, 
                       help='Directory containing input .h5 files')
    parser.add_argument('output_dir', type=str,
                       help='Directory for output filtered .h5 files')
    parser.add_argument('--deadtime', type=float, default=100.0,
                       help='Dead time in nanoseconds (default: 100 ns)')
    parser.add_argument('--chunk-size', type=int, default=10_000_000,
                       help='Chunk size for processing (default: 10,000,000)')
    parser.add_argument('--n-jobs', type=int, default=None,
                       help='Number of parallel jobs (default: number of CPUs)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode with verbose output')
    
    args = parser.parse_args()
    
    # Setup paths
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        print(f"Error: Input directory {input_dir} does not exist")
        sys.exit(1)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all h5 files
    h5_files = list(input_dir.glob('*.h5'))
    
    if not h5_files:
        print(f"Error: No .h5 files found in {input_dir}")
        sys.exit(1)
    
    print(f"Found {len(h5_files)} .h5 files to process")
    print(f"Dead time: {args.deadtime} ns")
    print(f"Chunk size: {args.chunk_size:,}")
    print(f"Output directory: {output_dir}")
    print(f"Debug mode: {'ON' if args.debug else 'OFF'}")
    
    # Prepare arguments for parallel processing
    n_jobs = args.n_jobs if args.n_jobs else cpu_count()
    
    # In debug mode, use only 1 job for cleaner output
    if args.debug:
        n_jobs = 1
        print("\nDEBUG: Forcing single-threaded execution for debug mode")
    
    process_args = [(f, output_dir, args.deadtime, args.chunk_size, args.debug) 
                    for f in h5_files]
    
    # Process files in parallel
    print(f"\nProcessing with {n_jobs} parallel workers...\n")
    
    with Pool(processes=n_jobs) as pool:
        results = list(tqdm(
            pool.imap(process_single_file, process_args),
            total=len(h5_files),
            desc="Overall progress"
        ))
    
    # Print summary
    print("\n" + "="*70)
    print("PROCESSING SUMMARY")
    print("="*70)
    
    successful = 0
    failed = 0
    
    for filename, success, message in results:
        status = "✓" if success else "✗"
        print(f"{status} {filename}: {message}")
        if success:
            successful += 1
        else:
            failed += 1
    
    print("="*70)
    print(f"Total: {len(results)} files | Successful: {successful} | Failed: {failed}")
    print("="*70)


if __name__ == "__main__":
    main()