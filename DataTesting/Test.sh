#!/bin/bash -l

#SBATCH -o ./jobs/OutC/%A_%a.out
#SBATCH -e ./jobs/ErrC/%A_%a.err
#SBATCH -D ./
#SBATCH -J DataValidation
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --array=0 # Update based on total number of paths (zero-based index)
#SBATCH --time=1:00:00
#SBATCH --mem=240000
#SBATCH --cpus-per-task=8
#SBATCH --mail-type=ALL
#SBATCH --mail-user=arego@mpcdf.mpg.de

# Load required modules
module purge
module load anaconda/3/2023.03
module load gcc/13

# Activate Python environment
source /u/arego/graphnet-venv/bin/activate


# Path to the Python script
python_script="/u/arego/Project/DataTesting/Test.py"

# Run the Python script with the selected path
srun python "$python_script" 

echo "Job completed for path: $current_path (Task ID: $SLURM_ARRAY_TASK_ID)"
