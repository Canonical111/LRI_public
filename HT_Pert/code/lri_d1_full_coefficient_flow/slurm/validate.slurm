#!/bin/bash
#SBATCH --partition=defq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --mem=180G
#SBATCH --time=06:00:00
#SBATCH --no-requeue
#SBATCH --output=<SCRATCH>/lri_s10/logs/%x_%j.out
# Reproduce the archived Dconn L=40,42,44 (degree 8) and raw L=44 with the extended code, one process per run,
# and compare with the archive (rtol 1e-10). Submit with slurm/submit.sh validate.
set -euo pipefail
: "${S10_ROOT:?}" "${S10_DATA:?}"
source "$S10_ROOT/slurm/symmetry_env.sh"
[[ $- == *e* ]] || { echo "errexit lost" >&2; exit 70; }
# Run only the solver the submission was checked against (immutable snapshot; hash verified on this node).
: "${S10_EXPECT_SHA:?}"
got=$(sha256sum "$S10_ROOT/code/ragged_quotient.py" | cut -c1-64)
[[ $got == "$S10_EXPECT_SHA" ]] || { echo "solver sha $got != expected $S10_EXPECT_SHA" >&2; exit 64; }
OUT=$S10_DATA/validation/$SLURM_JOB_ID; mkdir -p "$OUT"
echo "[validate] job $SLURM_JOB_ID on $(hostname) $(date '+%Y-%m-%dT%H:%M:%S%z') -> $OUT"
for L in 40 42 44; do
  python "$S10_ROOT/code/ragged_quotient.py" --cutoffs "$L" --degree 8 --scheme dconn --batch 1 --out "$OUT" > "$OUT/run_dconn_L$L.log" 2>&1
done
python "$S10_ROOT/code/ragged_quotient.py" --cutoffs 44 --degree 8 --scheme raw --batch 1 --out "$OUT" > "$OUT/run_raw_L44.log" 2>&1
python "$S10_ROOT/code/compare_archive.py" --new-dir "$OUT" --out "$OUT/compare.json"
echo "[validate] PASS $(date '+%Y-%m-%dT%H:%M:%S%z')"
