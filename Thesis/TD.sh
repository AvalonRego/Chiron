#!/bin/bash -l
#
# Python MPI4PY example job script for MPCDF Raven.
# May use more than one node.
#
#SBATCH -o ./jobs/TD.%A_%a.out       # Standard output
#SBATCH -e ./jobs/TD.%A_%a.err       # Standard error
#SBATCH -D ./                         # Working directory
#SBATCH -J TriggerData               # Job name
#SBATCH --nodes=1                    # Number of nodes
#SBATCH --ntasks-per-node=1          # Tasks per node
#SBATCH --time=24:00:00              # Time limit
#SBATCH --mem=240000                  # Memory
#SBATCH --cpus-per-task=8           # CPUs per task
#SBATCH --mail-type=all               # Email notifications for all events
#SBATCH --mail-user=arego@mpcdf.mpg.de  # Email address
#SBATCH --array=0               # Job array for 4 jobs (0 to 3)

# Load required modules
module purge
module load anaconda/3/2023.03
module load gcc/13

# Activate the Python environment
source /viper/u/arego/Project/olympus/bin/activate

# Define input and output directory arrays
INPUT_DIRS=( /viper/ptmp/arego/RC4K1_1_EN_100_with_type)  # Add your input directories here
OUTPUT_DIRS=(/u/arego/Project/Thesis/plot/C_Cut)  # Corresponding output directories

# Get the current job index
JOB_INDEX=$SLURM_ARRAY_TASK_ID

# Check if the job index is within the range of defined arrays
if [ $JOB_INDEX -ge 0 ] && [ $JOB_INDEX -lt ${#INPUT_DIRS[@]} ]; then
    # Run the Python script with the appropriate input and output directories
    srun python3 /u/arego/Project/Thesis/triggerdata.py "${INPUT_DIRS[$JOB_INDEX]}" "${OUTPUT_DIRS[$JOB_INDEX]}"
else
    echo "Error: Job index out of range."
    exit 1
fi

echo "Job finished for index $JOB_INDEX"
