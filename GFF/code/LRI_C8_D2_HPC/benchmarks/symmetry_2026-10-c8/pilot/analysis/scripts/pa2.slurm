#!/bin/bash
#SBATCH -p sharedq -N 1 -n 1 -c 4 --mem=8G -t 00:30:00 --no-requeue
#SBATCH -o /mnt/beegfs/zzheng1/c8d2/logs/%x_%j.out
# Post-pilot analysis, part 2: heavy-tail context (pa_tails.py) on the pilot, the report's tails.csv of job 570669 and
# the eight bundles it froze. Reads only; writes this job's evidence folder. No seed, no plan, nothing submitted.
# Usage (from the login node): sbatch -J c8d2-pa2 --export=ALL pa2.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
PKG=/mnt/beegfs/zzheng1/c8d2/pkg/ba68f401e46e
RUN=/mnt/beegfs/zzheng1/c8-d2/pilot1-20261006-ba68f401e46e
DES=/mnt/beegfs/zzheng1/c8-d2/designs
WK=/mnt/beegfs/zzheng1/c8d2/work/pilot-analysis-ba68f401e46e
PA=/mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/pa.570669.0
E=/mnt/beegfs/zzheng1/c8d2/evidence/ba68f401e46e/pa2.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
mkdir "$E" || exit 64
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); evidence $E"
cd "$PKG" || exit 64
sha256sum "$RUN/manifest.json" "$PA/tails.csv" tools/design.py "$WK"/pa_tails.py "$WK"/pa2.slurm | tee "$E/inputs.sha256"
python3 -B "$WK/pa_tails.py" --package "$PKG" --run "$RUN" --tails "$PA/tails.csv" --bundles "$DES"/pilot1-20261006-{exact,ddmp256}-{1e-3,5e-4,2.5e-4,1.35e-4} \
  --out "$E/pa_tails.json" > "$E/pa_tails.stdout" 2>&1; s=$?
cat "$E/pa_tails.stdout"; echo "done at $(date -Is), exit $s"; exit $s
