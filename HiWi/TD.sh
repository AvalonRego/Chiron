#!/bin/bash -l
#
# Python MPI4PY example job script for MPCDF Raven.
# May use more than one node.
#
#SBATCH -o ./jobs/TD.%A_%a.out # Standard output
#SBATCH -e ./jobs/TD.%A_%a.err # Standard error
#SBATCH -D ./ # Working directory
#SBATCH -J TriggerData # Job name
#SBATCH --nodes=1 # Number of nodes
#SBATCH --ntasks-per-node=1 # Tasks per node
#SBATCH --time=24:00:00 # Time limit
#SBATCH --mem=240000 # Memory
#SBATCH --cpus-per-task=16 # CPUs per task (increased for new script)
#SBATCH --mail-type=all # Email notifications for all events
#SBATCH --mail-user=arego@mpcdf.mpg.de # Email address
#SBATCH --array=89-99 # Job array - adjust based on number of batches needed

# Load required modules
module purge
module load anaconda/3/2023.03
module load gcc/13

# Activate the Python environment
source /viper/u/arego/Project/olympus/bin/activate

# Configuration variables - easily adjustable
MAX_WORKERS=16                      # Maximum workers per job
SIZE_THRESHOLDS="0.1 0.5 0.7 1.0 1.2"   # Size thresholds in GB
WORKER_COUNTS="16 6 4 3 2 1"         # Corresponding worker counts (one more than thresholds)

# Define input and output directories (single directories, not arrays)
INPUT_DIR="/viper/ptmp/arego/Red_T_7K"
OUTPUT_DIR="/u/arego/Project/HiWi/Trigger_process/Track"

# Get the current job index
JOB_INDEX=$SLURM_ARRAY_TASK_ID

# Run the Python script with job batching and configurable parameters
echo "Starting job $JOB_INDEX with batching system"
echo "Configuration: MAX_WORKERS=$MAX_WORKERS"
echo "Size thresholds: $SIZE_THRESHOLDS"
echo "Worker counts: $WORKER_COUNTS"

srun python3 /u/arego/Project/HiWi/trigger_data.py "$INPUT_DIR" "$OUTPUT_DIR" \
    --job-index $JOB_INDEX \
    --total-jobs $SLURM_ARRAY_TASK_MAX \
    --workers $MAX_WORKERS \
    --size-thresholds $SIZE_THRESHOLDS \
    --worker-counts $WORKER_COUNTS

echo "Job finished for index $JOB_INDEX"