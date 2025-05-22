#!/bin/bash -l
#
# Python multiprocessing example job script for MPCDF Raven.
#
#SBATCH -o ./Logs/out.%j
#SBATCH -e ./Logs/err.%j
#SBATCH -D ./
#SBATCH -J Plot
#SBATCH --nodes=1             # request a full node
#SBATCH --ntasks-per-node=1   # only start 1 task via srun because Python multiprocessing starts more tasks internally
#SBATCH --cpus-per-task=16    # assign all the cores to that first task to make room for Python's multiprocessing tasks
#SBATCH --time=20:10:00
#SBATCH --mem=240000
#SBATCH --mail-type=all
#SBATCH --mail-user=arego@mpcdf.mpg.de

module purge
module load anaconda/3/2023.03

# Important:
# Set the number of OMP threads *per process* to avoid overloading of the node!
export OMP_NUM_THREADS=1

# Use the environment variable SLURM_CPUS_PER_TASK to have multiprocessing
# spawn exactly as many processes as you have CPUs available.
srun python3 /u/arego/Project/Thesis/HitvEnergy.py