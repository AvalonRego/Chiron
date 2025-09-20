#!/bin/bash -l
#
# Python MPI4PY example job script for MPCDF Raven.
# May use more than one node.
#
#SBATCH -o /u/arego/Project/HiWi/job/%j.out
#SBATCH -e /u/arego/Project/HiWi/job/%j.err
#SBATCH -J DataGen
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1

#SBATCH --time=24:00:00       # Adjust as needed

#SBATCH --mem=240000
#SBATCH --cpus-per-task=64
#SBATCH --mail-type=all
#SBATCH --mail-user=arego@mpcdf.mpg.de

module purge
module load anaconda/3/2023.03
module load gcc/13

source /viper/u/arego/Project/olympus/bin/activate

echo "Array Job ID: $SLURM_ARRAY_JOB_ID"
echo "Array Task ID: $SLURM_ARRAY_TASK_ID" 
echo "Node: $SLURM_NODELIST"
echo "Start time: $(date)"

INPUT_DIR="/viper/ptmp/arego/Red_T_7K_1/"
INTERMEDIATE_DIR="/ptmp/arego/tempT/"
OUTPUT_FILE="/viper/ptmp/arego/Record_Len_RedT"


python /u/arego/Project/HiWi/RecordLenNew.py \
    "$INPUT_DIR" \
    "$INTERMEDIATE_DIR" \
    "$OUTPUT_FILE" \
    --cores $SLURM_CPUS_PER_TASK

