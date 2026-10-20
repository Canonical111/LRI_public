#!/bin/bash
#SBATCH --partition=defq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --mem=180G
#SBATCH --time=24:00:00
#SBATCH --no-requeue
#SBATCH --output=<SCRATCH>/lri_s10/logs/%x_%A_%a.out
# One cutoff per array task, Dconn degree 8, one single-threaded process per exclusive node (memory-bound).
# S10_CUTOFFS is the comma-separated list indexed by SLURM_ARRAY_TASK_ID. Submit with slurm/submit.sh production.
set -euo pipefail
: "${S10_ROOT:?}" "${S10_DATA:?}" "${S10_CUTOFFS:?}" "${S10_MAX_STATES:?}"
source "$S10_ROOT/slurm/symmetry_env.sh"
[[ $- == *e* ]] || { echo "errexit lost" >&2; exit 70; }
# Run only the solver the submission was checked against (immutable snapshot; hash verified on this node).
: "${S10_EXPECT_SHA:?}"
got=$(sha256sum "$S10_ROOT/code/ragged_quotient.py" | cut -c1-64)
[[ $got == "$S10_EXPECT_SHA" ]] || { echo "solver sha $got != expected $S10_EXPECT_SHA" >&2; exit 64; }
IFS=, read -r -a cut <<<"$S10_CUTOFFS"
L=${cut[$SLURM_ARRAY_TASK_ID]:?no cutoff for task $SLURM_ARRAY_TASK_ID}
# Exact allowed strings (no arithmetic: long decimals would wrap in 64-bit bash arithmetic).
case $L in 46|48|50|52|54|56|58|60|62|64|66|68|70|72) ;; *) echo "cutoff '$L' is not one of the supported even cutoffs 46..72" >&2; exit 64 ;; esac
[[ $S10_MAX_STATES =~ ^[1-9][0-9]{0,9}$ ]] || { echo "bad max_states '$S10_MAX_STATES' (1..10 digits)" >&2; exit 64; }
OUT=$S10_DATA/production; mkdir -p "$OUT"
echo "[prod] job $SLURM_JOB_ID task $SLURM_ARRAY_TASK_ID L=$L on $(hostname) $(date '+%Y-%m-%dT%H:%M:%S%z'); max_states $S10_MAX_STATES"
python "$S10_ROOT/code/ragged_quotient.py" --cutoffs "$L" --degree 8 --scheme dconn --batch 1 \
  --max-states "$S10_MAX_STATES" --out "$OUT"
echo "[prod] done L=$L $(date '+%Y-%m-%dT%H:%M:%S%z')"
