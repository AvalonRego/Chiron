#!/bin/bash -l

#SBATCH -o ./stats_me/%j.out  # Standard output file
#SBATCH -e ./stats_me/%j.err   # Error output file
#SBATCH -D ./
#SBATCH -J Stats                 # Job name
#SBATCH --nodes=1                    # Request 1 node
#SBATCH --ntasks=1                   # Single task
#SBATCH --cpus-per-task=8          # Request 32 CPUs
#SBATCH --time=04:00:00              # Maximum runtime (hh:mm:ss)
#SBATCH --mem=240000                   # Memory allocation (adjust as needed)
#SBATCH --mail-type=ALL              # Notifications (BEGIN, END, FAIL, etc.)
#SBATCH --mail-user=arego@mpcdf.mpg.de  # Your email for notifications
#SBATCH --priority=TOP


module purge
module load anaconda/3/2023.03
module load gcc/13

source /viper/u/arego/Project/olympus/bin/activate

# Define the Python script and arguments
python_script="/u/arego/Project/HitStats/stat_mergr.py"


python "$python_script" /ptmp/arego/stat_saves/ /ptmp/arego/stat_merge_bio/merge.npy

echo "Job completed successfully."