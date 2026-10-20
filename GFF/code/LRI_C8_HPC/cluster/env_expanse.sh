# C8 production environment on Expanse (sourced by jobs before set -u)
module purge
module load cpu/0.21.2a gcc/13.3.0 boost/1.86.0
module load slurm/expanse/23.02.7 2>/dev/null || true
export CPATH="$BOOST_ROOT/include${CPATH:+:$CPATH}"
source /expanse/lustre/scratch/zzheng8/temp_project/c7_hpc/venv/bin/activate
export C8_PYTHON=/expanse/lustre/scratch/zzheng8/temp_project/c7_hpc/venv/bin/python3
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
