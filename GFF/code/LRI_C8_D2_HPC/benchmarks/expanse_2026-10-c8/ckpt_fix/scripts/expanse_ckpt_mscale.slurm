#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=16 --mem=48G -t 03:00:00 --no-requeue
#SBATCH -J c8d2-ckfix-mscale
#SBATCH -o <SCRATCH>/temp_project/c8d2/logs/%x_%j.out
# Merge scale for the checkpoint-review fixes (T-01/O02, O01) on Expanse (site deviation U1):
#  1. tests/merge_scale.py --rows 1000000 --jobs 16 --run-jobs 16 --shards 16 (as J-VAL-3's A-ORC-6 part, job 54643361),
#     now also with its memory-scaling section (4 -> 32 points, 1 and 4 shards; peak RSS of `merge --jobs 1`);
#  2. the scaling regression at 8x more rows per shard and a larger base (32 -> 256 points: 0.16 -> 1.25 * 10^6 rows of
#     a_free_L7, 1 and 4 shards, fixed checkpoint size 256 and fan-in 16), peak RSS and the traced Python heap;
#  3. the same as 2 with 601b102's tools/production.py ($C8_OLD_PRODUCTION) in an otherwise identical copy of the
#     export: expected to FAIL the bound (phase 1 kept every row of a shard), which shows the regression bites on Linux.
# Usage: C8_PACKAGE=$C8_DATA/pkg/<sha12> C8_OLD_PRODUCTION=<601b102 tools/production.py> sbatch --export=ALL --dependency=afterok:<build job> ...
set -uo pipefail
source "$HOME/c8d2/env_expanse.sh"
: "${C8_PACKAGE:?}" "${C8_OLD_PRODUCTION:?}"
TAG=$(basename "$C8_PACKAGE"); RUN=ckmscale.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$C8_DATA/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E"
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; evidence $E"
lscpu | grep -E 'Model name'
sha256sum "$HOME/c8d2/env_expanse.sh" | tee "$E/env_expanse.sha256"
L=/scratch/$USER/job_$SLURM_JOB_ID; if [ -d "$L" ]; then export TMPDIR=$L/tmp; else export TMPDIR=$C8_DATA/work/$RUN; fi
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1; mkdir -p "$TMPDIR"; echo "TMPDIR $TMPDIR"
status=0
cd "$C8_PACKAGE"
python3 -B tests/merge_scale.py --rows 1000000 --jobs 16 --run-jobs 16 --shards 16 --output "$E/merge_scale.json" > "$E/merge_scale.stdout" 2>&1 || status=$?
tail -40 "$E/merge_scale.stdout"
python3 -B tests/merge_scale.py --rows 20000 --run-jobs 16 --skip-many-shards --scaling-points 32,256 --output "$E/mscale_new_32_256.json" > "$E/mscale_new_32_256.stdout" 2>&1 || status=$?
tail -60 "$E/mscale_new_32_256.stdout"
HYB=$TMPDIR/pkg_hybrid601; mkdir -p "$HYB"; cp -a "$C8_PACKAGE"/. "$HYB"/; cp "$C8_OLD_PRODUCTION" "$HYB/tools/production.py"; sha256sum "$HYB/tools/production.py" | tee "$E/old_production.sha256"
cd "$HYB"; old=0
python3 -B tests/merge_scale.py --rows 20000 --run-jobs 16 --skip-many-shards --scaling-points 32,256 --output "$E/mscale_old601_32_256.json" > "$E/mscale_old601_32_256.stdout" 2>&1 || old=$?
tail -60 "$E/mscale_old601_32_256.stdout"; echo "601b102 production.py: merge_scale exit $old (expected nonzero: the memory bound fails)"
cd "$C8_PACKAGE"; rm -rf "$TMPDIR"
echo "finished $(date -Is), status $status"
exit $status
