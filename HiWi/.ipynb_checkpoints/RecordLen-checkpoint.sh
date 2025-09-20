#!/bin/bash -l
#
# Python MPI4PY example job script for MPCDF Raven.
# May use more than one node.
#
#SBATCH -o /u/arego/project/HiWi/job/%j.out
#SBATCH -e /u/arego/project/HiWi/job/%j.err
#SBATCH -J DataGen
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1

#SBATCH --time=24:00:00       # Adjust as needed

#SBATCH --mem=100G
#SBATCH --cpus-per-task=8
#SBATCH --mail-type=all
#SBATCH --mail-user=arego@mpcdf.mpg.de

module purge
module load anaconda/3/2023.03
module load gcc/11

source /raven/u/arego/olympus/bin/activate

echo "Array Job ID: $SLURM_ARRAY_JOB_ID"
echo "Array Task ID: $SLURM_ARRAY_TASK_ID" 
echo "Node: $SLURM_NODELIST"
echo "Start time: $(date)"

DATA_DIR="/raven/ptmp/arego/LargeTracks/"
OUTPUT_FILE="/ptmp/arego/Record_Len_Track/out.parquet"

python /u/arego/project/HiWi/RecordLen.py \
    $DATA_DIR \
    $OUTPUT_FILE \
    --cores $SLURM_CPUS_PER_TASK \
    --batch_size 100 \
    --batch_dir /ptmp/arego/temp




