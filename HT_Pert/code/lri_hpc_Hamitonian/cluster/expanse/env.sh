# Expanse environment for lri_hpc jobs (source before `set -u`; the site bashrc is not nounset-safe).
module purge
module load cpu/0.21.2a gcc/13.3.0 python/3.11.9
module load slurm/expanse/23.02.7 2>/dev/null || true
export LRIHT_HOME=<SCRATCH>/temp_project/lri_ht
source "$LRIHT_HOME/venv/bin/activate"
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1
# Node-local JIT cache (one compile per node; Lustre is not used for cache files).
export NUMBA_CACHE_DIR=/scratch/$USER/job_${SLURM_JOB_ID:-login}/numba_cache
mkdir -p "$NUMBA_CACHE_DIR" 2>/dev/null || export NUMBA_CACHE_DIR=${TMPDIR:-/tmp}/lriht_numba_$USER
mkdir -p "$NUMBA_CACHE_DIR"
