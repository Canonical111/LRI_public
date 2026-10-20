#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=32G -t 02:00:00 --no-requeue
#SBATCH -J c8d2-s3b-val4
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# J-VAL-4 on Expanse (site deviation U1), on the tagged Stage-3 export: tests/sanitize.py --selftest (A-KER-4) with the
# sanitizer executables of the build job (make sanitize: -O1 -g ASan/UBSan/_GLIBCXX_ASSERTIONS plus the required flags).
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL --dependency=afterok:<build job> ...
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=s3bval4.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name'
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd "$C8_PACKAGE"
sha256sum bin/c8d2_decimal_san bin/c8d2_gmp_san | tee "$E/binaries.sha256"
status=0
python3 -B tests/sanitize.py --selftest --output "$E/sanitize.json" > "$E/sanitize.stdout" 2>&1 || { echo "sanitize FAILED"; tail -40 "$E/sanitize.stdout"; status=1; }
tail -3 "$E/sanitize.stdout" | cut -c1-400
echo "finished $(date -Is), status $status"
exit $status
