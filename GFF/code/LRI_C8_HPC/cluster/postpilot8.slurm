#!/bin/bash
#SBATCH --job-name=c8-postpilot
#SBATCH --account=yun124
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=%x-%j.out
# After the exact stage and the pilot: merge, affine map (K from exact L2-L4 at degree 24, loop-5 sequence), frozen
# zero-pole controls (trained on the pilot coarse campaigns), pilot preview, and the frozen production design bundle.
# Required: C8_ENV_SETUP, C8_ROOT (frozen code), C8_RUNS (runs directory), C8_ANALYSIS (output directory),
# C8_BUDGETS (space-separated candidate production budgets in core-hours, all batches), C8_BATCHES, C8_PILOT_JOB,
# C8_DESIGN_PREFIX (new design bundles C8_DESIGN_PREFIX_<budget>). Spent core-hours = all c8* jobs of this user today.
set -eo pipefail
source "${C8_ENV_SETUP:?}"
set -u
: "${C8_ROOT:?}" "${C8_RUNS:?}" "${C8_ANALYSIS:?}" "${C8_BUDGETS:?}" "${C8_BATCHES:?}" "${C8_PILOT_JOB:?}" "${C8_DESIGN_PREFIX:?}"
PY="${C8_PYTHON:-python3}";T="$C8_ROOT/tools";mkdir -p "$C8_ANALYSIS"
scratch_args=();if [[ -n "${SLURM_TMPDIR:-}" ]]; then scratch_args=(--scratch "$SLURM_TMPDIR"); fi
L5="$C8_RUNS/exact8_L5/exact_L5"
for c in "$C8_RUNS/exact8/exact_L2" "$C8_RUNS/exact8/exact_L3" "$C8_RUNS/exact8/exact_L4" "$L5"; do # deterministic inputs merged (or re-verified) first
  if [[ -f "$c/merged/audit.json" ]]; then "$PY" "$T/campaign.py" verify "$c"; else "$PY" "$T/campaign.py" merge "$c" ${scratch_args[@]+"${scratch_args[@]}"}; fi
done
"$PY" "$T/production8.py" merge "$C8_RUNS/pilot8" ${scratch_args[@]+"${scratch_args[@]}"}
[[ -f "$C8_ANALYSIS/affine8.json" ]] || "$PY" "$T/affine8.py" --exact "$C8_RUNS/exact8/exact_L2" "$C8_RUNS/exact8/exact_L3" "$C8_RUNS/exact8/exact_L4" "$L5" --degree 2=24 3=24 4=24 --out "$C8_ANALYSIS/affine8.json"
train=();for L in 6 7 8; do for t in A B; do train+=("$L=$C8_RUNS/pilot8/power_coarse${t}_L$L"); done; done
[[ -f "$C8_ANALYSIS/full_affine8.json" ]] || "$PY" "$T/controls8.py" --affine "$C8_ANALYSIS/affine8.json" --train "${train[@]}" --out "$C8_ANALYSIS/full_affine8.json"
top=$(ls "$L5/merged" | sed -n 's/^N\([0-9]*\)\.json$/\1/p' | sort -n | tail -2 | tr '\n' ' ')
read -r prev hi <<<"$top"
[[ -f "$C8_ANALYSIS/pilot_preview/C8_preview.json" ]] || "$PY" "$T/preview8.py" "$C8_RUNS/pilot8" --affine "$C8_ANALYSIS/full_affine8.json" --exact5 "$L5/merged/N$hi.json" "$L5/merged/N$prev.json" --output "$C8_ANALYSIS/pilot_preview" > "$C8_ANALYSIS/pilot_preview.txt"
cat "$C8_ANALYSIS/pilot_preview.txt"
spent=$(sacct -u "$USER" -S "${C8_SINCE:-2026-10-02T00:00}" -X -n -P -o JobName,ElapsedRaw,AllocCPUS | awk -F'|' '$1 ~ /^c8/ {s+=$2*$3} END{printf "%.1f", s/3600}')
echo "C8: core-hours spent so far by c8* jobs: $spent"
for B in $C8_BUDGETS; do
  "$PY" "$T/design8.py" --pilot "$C8_RUNS/pilot8" --affine "$C8_ANALYSIS/full_affine8.json" --budget-core-hours "$B" --batches "$C8_BATCHES" --pilot-job $C8_PILOT_JOB --spent-core-hours "$spent" --out "${C8_DESIGN_PREFIX}_$B" > "${C8_DESIGN_PREFIX}_$B.txt"
  cat "${C8_DESIGN_PREFIX}_$B.txt"
done
