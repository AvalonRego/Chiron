#!/bin/bash
#SBATCH --job-name=merge_parquet
#SBATCH --output=/u/arego/Project/Parquet_merge/merge_parquet1.out
#SBATCH --error=/u/arego/Project/Parquet_merge/merge_parquet1.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16   # Use 8 CPU cores
#SBATCH --mem=128G            # Adjust memory based on dataset size
#SBATCH --time=20:00:00      # Set max job duration
module purge
module load anaconda/3/2023.03
module load gcc/13

source /viper/u/arego/Project/olympus/bin/activate

# Run the merging script
python /viper/u/arego/Project/Parquet_merge/Pyarraow_merge.py
