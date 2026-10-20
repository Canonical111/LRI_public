#!/bin/bash
#SBATCH -A <ACCOUNT> -p compute -N 1 --ntasks=1 --cpus-per-task=128 --exclusive --mem=240G -t 02:00:00 --no-requeue
#SBATCH -J c8d2-s3-val2
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# The J-VAL-2 part of Stage 3 on Expanse (site deviation U1; one whole compute node, 2 x EPYC 7742): tests/validate.py
# --full (A-KER-1/2/3/5, G-REF/G-C7/G-JET = A-RPL-1/2/3 on the L=2 graph and all 3,773 L3-L7 kernels with both
# backends, the chunk and layout part of A-RPL-6, class B, the diagnostic builds) and tests/check_points.py (450-digit
# point checks L3-L8). Executables from the build job (expanse_s3_build.slurm) in the same export.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL --dependency=afterok:<build job> ...
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=s3val2.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name|NUMA node\(s\)'
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$C8_PACKAGE"
sha256sum bin/c8d2_decimal bin/c8d2_gmp bin/ref/c7d2_decimal bin/ref/c7d2_gmp | tee "$E/binaries.sha256"
status=0
run() { local name=$1; shift; echo "== $name $(date -Is)"; "$@" > "$E/$name.stdout" 2>&1 || { echo "== $name: FAILED"; tail -30 "$E/$name.stdout"; status=1; }; grep -E 'passed in|FAILED|Error' "$E/$name.stdout" | head -20; }
run validate_full python3 -B tests/validate.py --full --jobs 32 --threads 4 --output "$E/validate_full.json"
run point_checks python3 -B tests/check_points.py --output "$E/point_checks.json"
echo "finished $(date -Is), status $status"
exit $status
