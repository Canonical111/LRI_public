#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=48G -t 02:00:00 --no-requeue
#SBATCH -J c8d2-s3b-mscale
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# The merge-scale part of J-VAL-3 on Expanse (site deviation U1; A-ORC-6, R06): tests/merge_scale.py --rows 1000000
# (a group of about 1.25 * 10^6 rows: peak RSS per merge process <= 1 GB, phase-1/phase-2 rows per second, parallel
# merge byte-identical to the serial reference) and the 500-shard case (RLIMIT_NOFILE = 48 and --fan-in 2). The plan of
# about 3.9 * 10^6 tasks runs inside this job (the test passes SLURM_JOB_ID to its plan step); scratch on the node.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> sbatch --export=ALL --dependency=afterok:<build job> ...
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=s3bmscale.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name'
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
cd "$C8_PACKAGE"
status=0
python3 -B tests/merge_scale.py --rows 1000000 --jobs 16 --run-jobs 16 --shards 16 --output "$E/merge_scale.json" > "$E/merge_scale.stdout" 2>&1 || status=$?
tail -60 "$E/merge_scale.stdout"
rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
