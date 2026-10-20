#!/bin/bash
# The second implementation (independent_check/): self-test, then the 8 configurations c1..c8 of SPEC.md section 7 in
# parallel on one node, one single-threaded process each. The longest took 28 min on an AMD EPYC 7543 core.
# Template made from independent_check/cluster/run_all.sbatch (the script that ran, kept unchanged).
# Replace the <...> placeholders (slurm/README.md); WORK is a copy of NRG/independent_check.
#SBATCH --job-name=nrg-indep
#SBATCH --account=<ACCOUNT>
#SBATCH --partition=<PARTITION>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --no-requeue
#SBATCH --output=nrg-indep-%j.log
set -uo pipefail
<LOAD_MODULES>                                   # Python >= 3.10 with NumPy, SciPy and mpmath
WORK=<SCRATCH>/nrg/independent_check
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
cd "$WORK" || exit 1
mkdir -p out logs
python -u selftest.py > logs/selftest.log 2>&1 || { echo "selftest FAILED (logs/selftest.log)"; exit 1; }
tail -n 1 logs/selftest.log
CONFIGS=(c1 c2 c3 c4 c5 c6 c7 c8); PIDS=()
for id in "${CONFIGS[@]}"; do python -u run_config.py "$id" --outdir out > "logs/$id.log" 2>&1 & PIDS+=($!); done
rc=0
for i in "${!CONFIGS[@]}"; do
    if wait "${PIDS[$i]}"; then echo "${CONFIGS[$i]} ok"; else echo "${CONFIGS[$i]} FAILED (logs/${CONFIGS[$i]}.log)"; rc=1; fi
done
exit $rc
