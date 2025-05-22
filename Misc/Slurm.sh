#!/bin/bash -l

#SBATCH -o ./jobs/Out/Track_%j.out  # Standard output file
#SBATCH -e ./jobs/Err/Track_%j.err   # Error output file
#SBATCH -D ./
#SBATCH -J PythonJob                 # Job name
#SBATCH --nodes=1                    # Request 1 node
#SBATCH --ntasks=1                   # Single task
#SBATCH --cpus-per-task=32          # Request 32 CPUs
#SBATCH --time=01:00:00              # Maximum runtime (hh:mm:ss)
#SBATCH --mem=240000                   # Memory allocation (adjust as needed)
#SBATCH --mail-type=ALL              # Notifications (BEGIN, END, FAIL, etc.)
#SBATCH --mail-user=arego@mpcdf.mpg.de  # Your email for notifications

module purge
module load anaconda/3/2023.03
module load gcc/13

source /viper/u/arego/Project/olympus/bin/activate

# Define the Python script and arguments
python_script="/u/arego/Project/Misc/DataCleanT.py"


# Run the Python script with multiprocessing
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK  # Ensure Python uses all allocated CPUs
python "$python_script" 

echo "Job completed successfully."
