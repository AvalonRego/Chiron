#!/bin/bash -l
#
# Python MPI4PY example job script for MPCDF Raven.
# May use more than one node.
#
#SBATCH -o ./jobs/DataGen/Out/C_%A_%a.out
#SBATCH -e ./jobs/DataGen/Err/C_%A_%a.err
#SBATCH -D ./
#SBATCH -J DataGen
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1

#SBATCH --array=1-200        # Job array for 10 tasks
#SBATCH --time=15:00:00       # Adjust as needed

#SBATCH --mem=20G
#SBATCH --cpus-per-task=1
#SBATCH --mail-type=all
#SBATCH --mail-user=arego@mpcdf.mpg.de

module purge
module load anaconda/3/2023.03
module load cuda/12.1
module load jax/0.4.13 
module load cudnn/8.9.0
module load gcc/11

source /raven/u/arego/olympus/bin/activate


# Calculate staggered delay
DELAY=$(((SLURM_ARRAY_TASK_ID * 5) % 60))

# Run the shell script in the background after a delay
(
  sleep $DELAY
  bash /u/arego/project/Bashfiles/Cascade.sh $SLURM_ARRAY_TASK_ID
) &

# Wait for all background jobs to finish
wait


echo "All jobs ran"