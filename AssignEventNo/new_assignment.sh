#!/bin/bash -l
#SBATCH -o ./jobs/%A_%a.out
#SBATCH -e ./jobs/%A_%a.err
#SBATCH -D ./
#SBATCH -J Assignment
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=8
#SBATCH --array=1-80 # Update based on total chunks
#SBATCH --time=24:00:00
#SBATCH --mem=240000
#SBATCH --cpus-per-task=1
#SBATCH --mail-type=ALL
#SBATCH --mail-user=arego@mpcdf.mpg.de

# Load required modules
module purge
module load anaconda/3/2023.03
module load gcc/13
source /viper/u/arego/Project/olympus/bin/activate

# Define paths
input_dir="/viper/ptmp/arego/RC4K1"
python_script="/u/arego/Project/AssignEventNo/new_assign.py"
csv_file="/u/arego/Project/HiWi/Cascade_skiplist.csv"  # Path to your CSV file
files_per_chunk=300

# Ensure input directory exists
if [ ! -d "$input_dir" ]; then
    echo "Error: Input directory $input_dir does not exist!"
    exit 1
fi

# Ensure CSV file exists
if [ ! -f "$csv_file" ]; then
    echo "Error: CSV file $csv_file does not exist!"
    echo "Please create a CSV file with 'file_id' and 'record_id' columns"
    exit 1
fi

# Ensure Python script exists
if [ ! -f "$python_script" ]; then
    echo "Error: Python script $python_script does not exist!"
    exit 1
fi

# Fetch all .h5 files
mapfile -t files < <(find "$input_dir" -maxdepth 1 -name "*.h5")
total_files=${#files[@]}

echo "Found $total_files HDF5 files in $input_dir"

# Define chunking logic
chunk_start=$(( (SLURM_ARRAY_TASK_ID - 1) * files_per_chunk ))
chunk_end=$(( chunk_start + files_per_chunk ))

if [ "$chunk_end" -gt "$total_files" ]; then
    chunk_end=$total_files
fi

# Select file chunk
current_chunk=("${files[@]:$chunk_start:$((chunk_end - chunk_start))}")

# Ensure we have files to process
if [ ${#current_chunk[@]} -eq 0 ]; then
    echo "No files to process in this chunk (Task ID: $SLURM_ARRAY_TASK_ID)."
    exit 0
fi

echo "Processing chunk $SLURM_ARRAY_TASK_ID: files $((chunk_start + 1)) to $chunk_end (${#current_chunk[@]} files)"

# Save file names to a temporary list (optional, for debugging)
file_list="/tmp/file_list_$SLURM_ARRAY_TASK_ID.txt"
printf "%s\n" "${current_chunk[@]}" > "$file_list"

echo "File list saved to: $file_list"
echo "Using CSV filter file: $csv_file"

# Run the Python script with CSV file as first argument, followed by the list of HDF5 files
python "$python_script" "$csv_file" "${current_chunk[@]}"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "Job completed successfully for task ID $SLURM_ARRAY_TASK_ID"
else
    echo "Job failed with exit code $exit_code for task ID $SLURM_ARRAY_TASK_ID"
    exit $exit_code
fi

# Optional: Clean up temporary file list
rm -f "$file_list"