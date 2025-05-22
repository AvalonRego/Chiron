#!/bin/bash -l

#SBATCH -o ./jobs/Redistribute/OutC/%A_%a.out
#SBATCH -e ./jobs/Redistribute/ErrC/%A_%a.err
#SBATCH -D ./
#SBATCH -J Redistribute
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=32
#SBATCH --array=1-150  # Update based on total chunks
#SBATCH --time=20:00:00
#SBATCH --mem=240000

#SBATCH --cpus-per-task=2
#SBATCH --mail-type=ALL
#SBATCH --mail-user=arego@mpcdf.mpg.de

# Load required modules
module purge
module load anaconda/3/2023.03
module load gcc/13

source /viper/u/arego/Project/olympus/bin/activate

# Define paths
input_dir="/viper/ptmp/arego/CMerge4K1"
python_script="/viper/u/arego/Project/Redistribution/RedistributeC.py"
python_script1="/u/arego/Project/Redistribution/Cleanup.py"
files_per_chunk=100

# Ensure input directory exists
if [ ! -d "$input_dir" ]; then
    echo "Error: Input directory $input_dir does not exist!"
    exit 1
fi

# Fetch all .h5 files
mapfile -t files < <(find "$input_dir" -maxdepth 1 -name "*.h5")
total_files=${#files[@]}

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
    echo "No files to process in this chunk."
    exit 0
fi

# Save file names to a temporary list (optional, for debugging)
file_list="/tmp/file_list_$SLURM_ARRAY_TASK_ID.txt"
printf "%s\n" "${current_chunk[@]}" > "$file_list"

# Run the Python script with the list of files
python "$python_script" "${current_chunk[@]}"
python "$python_script1"

echo "Job completed for task ID $SLURM_ARRAY_TASK_ID"
