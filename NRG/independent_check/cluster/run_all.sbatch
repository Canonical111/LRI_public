#!/bin/bash
#SBATCH -J indep_nrg
#SBATCH -p amdq
#SBATCH --exclude=cn112
#SBATCH -N1
#SBATCH --exclusive
#SBATCH --mem=64G
#SBATCH -t 12:00:00
#SBATCH --no-requeue
#SBATCH -o indep_nrg-%j.out
#
# Independent bosonic-NRG check: the 8 configurations of SPEC.md section 7, run in parallel on one
# symmetry amdq node, one single-threaded Python process each.
#
# WORK must point to the cluster copy of the independent_check/ directory (the one containing
# indep_nrg.py, run_config.py, selftest.py).  Submit, e.g.:
#     export WORK=/path/to/independent_check
#     sbatch --chdir="$WORK" "$WORK/cluster/run_all.sbatch"
# (--export=ALL is the sbatch default, so WORK reaches the job.)  The Slurm log indep_nrg-<jobid>.out
# lands in the --chdir directory; per-configuration logs go to $WORK/logs/<id>.log and results to
# $WORK/out/<id>.json.  Expected wall time: well under 1 h (c5 and c6 are the longest).

if [ -z "${WORK:-}" ]; then
    echo "ERROR: WORK is not set (must point to the independent_check directory)" >&2
    exit 1
fi

source /etc/profile.d/modules.sh
module load python/3.13-mamba

# one BLAS/LAPACK thread per process (8 processes share the node)
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

cd "$WORK" || exit 1
mkdir -p out logs

echo "host $(hostname)  job ${SLURM_JOB_ID:-none}  start $(date -Is)  WORK=$WORK"
python -c 'import sys, numpy, scipy, mpmath; print(sys.version); print("numpy", numpy.__version__, "scipy", scipy.__version__, "mpmath", mpmath.__version__)'

# fast self-test first (seconds); abort if the environment is broken
if ! python -u "$WORK/selftest.py" > "$WORK/logs/selftest.log" 2>&1; then
    echo "selftest FAILED, see $WORK/logs/selftest.log"
    exit 1
fi
tail -n 1 "$WORK/logs/selftest.log"

CONFIGS=(c1 c2 c3 c4 c5 c6 c7 c8)
PIDS=()
for id in "${CONFIGS[@]}"; do
    python -u "$WORK/run_config.py" "$id" --outdir "$WORK/out" > "$WORK/logs/$id.log" 2>&1 &
    PIDS+=($!)
    echo "launched $id (pid $!)"
done

rc=0
for i in "${!CONFIGS[@]}"; do
    id=${CONFIGS[$i]}
    if wait "${PIDS[$i]}"; then
        echo "$id finished ok  $(date -Is)"
    else
        st=$?
        echo "$id FAILED with exit status $st  $(date -Is)  (see logs/$id.log)"
        rc=1
    fi
done
echo "end $(date -Is)  rc=$rc"
exit $rc
