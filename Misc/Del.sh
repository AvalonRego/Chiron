#!/bin/bash -l

#SBATCH -o ./jobs/Out/Track_%j.out  # Standard output file
#SBATCH -e ./jobs/Err/Track_%j.err   # Error output file
#SBATCH -D ./
#SBATCH -J PythonJob                 # Job name
#SBATCH --nodes=1                    # Request 1 node
#SBATCH --ntasks=1                   # Single task
#SBATCH --cpus-per-task=1          # Request 32 CPUs
#SBATCH --time=00:10:00              # Maximum runtime (hh:mm:ss)
#SBATCH --mem=1G                   # Memory allocation (adjust as needed)
#SBATCH --mail-type=ALL              # Notifications (BEGIN, END, FAIL, etc.)
#SBATCH --mail-user=arego@mpcdf.mpg.de  # Your email for notifications

module purge
module load anaconda/3/2023.03
module load gcc/13

source /viper/u/arego/Project/olympus/bin/activate

# Define the Python script and arguments
python_script="/u/arego/Project/Misc/Deletion.py"


python "$python_script" 

echo "Job completed successfully."
