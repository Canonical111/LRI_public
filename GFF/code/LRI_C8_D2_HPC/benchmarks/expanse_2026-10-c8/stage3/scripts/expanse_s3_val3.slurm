#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 03:00:00 --no-requeue
#SBATCH -J c8d2-s3-val3
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# The J-VAL-3 native part of Stage 3 on Expanse (site deviation U1; one whole compute node): tests/forced_tiers.py
# (A-RPL-5), tests/thread_identity.py (A-RPL-6: 1, 8, 16, 64 threads and 8 lanes x 8 threads), tests/validate.py
# --bk8 (A-RPL-4) and --l2-control (A-IN-6(b), the registered seed in C8_L2_SEED), and --l8self against
# bin/baseline/ (the G-L8SELF machinery of A-RPL-7 on the Stage-3 baseline). Executables from the build job.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_L2_SEED=<seed> sbatch --export=ALL --dependency=afterok:<build job> ...
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_L2_SEED:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=s3val3.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name|NUMA node\(s\)'
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$C8_PACKAGE"
sha256sum bin/c8d2_decimal bin/c8d2_gmp bin/baseline/c8d2_decimal bin/baseline/c8d2_gmp | tee "$E/binaries.sha256"
status=0
run() { local name=$1; shift; echo "== $name $(date -Is)"; "$@" > "$E/$name.stdout" 2>&1 || { echo "== $name: FAILED"; tail -30 "$E/$name.stdout"; status=1; }; tail -3 "$E/$name.stdout" | cut -c1-300; }
run l2_control python3 -B tests/validate.py --only none --l2-control --l2-seed "$C8_L2_SEED" --threads 64 --output "$E/l2_control.json"
run thread_identity python3 -B tests/thread_identity.py --output "$E/thread_identity.json"
run bk8 python3 -B tests/validate.py --only none --bk8 --jobs 32 --threads 4 --output "$E/bk8.json"
run l8self python3 -B tests/validate.py --only none --l8self bin/baseline --jobs 32 --threads 4 --output "$E/l8self.json"
run forced_tiers python3 -B tests/forced_tiers.py --threads 128 --output "$E/forced_tiers.json"
echo "finished $(date -Is), status $status"
exit $status
