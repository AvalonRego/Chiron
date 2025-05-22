#!/bin/bash -l
#
# Python MPI4PY example job script for MPCDF Raven.
# May use more than one node.
#
#SBATCH -o ./jobs/DataGen/OutE1/E.%A_%a.out
#SBATCH -e ./jobs/DataGen/ErrE1/E.%A_%a.err
#SBATCH -D ./
#SBATCH -J DataGen
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1

#SBATCH --array=1     # Job array for 10 tasks
#SBATCH --time=1:00:00       # Adjust as needed

#SBATCH --mem=20G
#SBATCH --cpus-per-task=1
#SBATCH --mail-type=all
#SBATCH --mail-user=arego@mpcdf.mpg.de

module purge
module load anaconda/3/2023.03
module load gcc/13

source /viper/u/arego/Project/olympus/bin/activate


# Calculate staggered delay
DELAY=$(((SLURM_ARRAY_TASK_ID *5) ))

# Run the shell script in the background after a delay
(
  sleep $DELAY
  #bash /u/arego/Project/BashNGen/Electrical.sh $SLURM_ARRAY_TASK_ID
) &

# Wait for all background jobs to finish
wait


echo "All jobs ran"