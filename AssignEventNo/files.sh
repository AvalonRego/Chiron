#!/bin/bash

# Script to list the specific files that were processed by failed jobs 38 and 57

# Configuration (same as in your original job script)
input_dir="/viper/ptmp/arego/Red_T_7K_1"
files_per_chunk=300

# Function to get files for a specific job ID
get_files_for_job() {
    local job_id=$1
    echo "=== Files for Job $job_id ==="
    
    # Calculate chunk boundaries (same logic as in your SLURM script)
    chunk_start=$(( (job_id - 1) * files_per_chunk ))
    chunk_end=$(( chunk_start + files_per_chunk ))
    
    # Get all .h5 files (same as in your script)
    mapfile -t files < <(find "$input_dir" -maxdepth 1 -name "*.h5")
    total_files=${#files[@]}
    
    # Adjust chunk_end if it exceeds total files
    if [ "$chunk_end" -gt "$total_files" ]; then
        chunk_end=$total_files
    fi
    
    echo "Job $job_id processes files $((chunk_start + 1)) to $chunk_end"
    echo "Total files in this chunk: $((chunk_end - chunk_start))"
    echo
    
    # Extract the specific file chunk
    if [ $chunk_start -lt $total_files ]; then
        for ((i=chunk_start; i<chunk_end; i++)); do
            echo "${files[$i]}"
        done
    else
        echo "No files in this range (chunk starts beyond total files)"
    fi
    echo
}

# Check if input directory exists
if [ ! -d "$input_dir" ]; then
    echo "Error: Input directory $input_dir does not exist!"
    exit 1
fi

# Get total file count first
mapfile -t all_files < <(find "$input_dir" -maxdepth 1 -name "*.h5")
total_files=${#all_files[@]}
echo "Total files found in $input_dir: $total_files"
echo "Files per chunk: $files_per_chunk"
echo

# Process each failed job
for job_id in 38 57; do
    get_files_for_job $job_id
done

# Summary
echo "=== Summary ==="
echo "Job 38: files $(( (38-1) * 300 + 1 )) to $(( 38 * 300 ))"
echo "Job 57: files $(( (57-1) * 300 + 1 )) to $(( 57 * 300 ))"

# Optional: Save to files
echo
echo "=== Saving file lists to temporary files ==="
job38_start=$(( (38-1) * files_per_chunk ))
job38_end=$(( job38_start + files_per_chunk ))
if [ "$job38_end" -gt "$total_files" ]; then
    job38_end=$total_files
fi

job57_start=$(( (57-1) * files_per_chunk ))
job57_end=$(( job57_start + files_per_chunk ))
if [ "$job57_end" -gt "$total_files" ]; then
    job57_end=$total_files
fi

# Save Job 38 files
if [ $job38_start -lt $total_files ]; then
    job38_file="/u/arego/Project/AssignEventNo/assign/job38_files.txt"
    for ((i=job38_start; i<job38_end; i++)); do
        echo "${all_files[$i]}" >> "$job38_file"
    done
    echo "Job 38 files saved to: $job38_file"
    echo "Count: $(wc -l < "$job38_file") files"
fi

# Save Job 57 files
if [ $job57_start -lt $total_files ]; then
    job57_file="/u/arego/Project/AssignEventNo/assign/job57_files.txt"
    for ((i=job57_start; i<job57_end; i++)); do
        echo "${all_files[$i]}" >> "$job57_file"
    done
    echo "Job 57 files saved to: $job57_file"
    echo "Count: $(wc -l < "$job57_file") files"
fi

echo
echo "=== File existence check ==="
echo "Checking if files actually exist..."

# Quick existence check for a few files from each job
echo "Checking first 3 files from Job 38:"
for ((i=job38_start; i<job38_start+3 && i<job38_end; i++)); do
    if [ -f "${all_files[$i]}" ]; then
        echo "✓ ${all_files[$i]} exists"
    else
        echo "✗ ${all_files[$i]} NOT FOUND"
    fi
done

echo
echo "Checking first 3 files from Job 57:"
for ((i=job57_start; i<job57_start+3 && i<job57_end; i++)); do
    if [ -f "${all_files[$i]}" ]; then
        echo "✓ ${all_files[$i]} exists"
    else
        echo "✗ ${all_files[$i]} NOT FOUND"
    fi
done