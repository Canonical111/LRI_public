#!/bin/bash
# Submit S10 extension jobs to symmetry defq from the login node (light work only).
#   slurm/submit.sh validate
#   slurm/submit.sh production L1,L2,...  [max_states]   (default max_states 120000000)
# Run it from an immutable, read-only code snapshot (see SYMMETRY_EXTENSION.md); jobs re-verify the solver sha256 on
# the node. Under a cross-node mutex (atomic mkdir on BeeGFS) it refuses while a job of the same name is queued,
# running or suspended. Production needs a validation of this exact solver and stack whose comparison the gate
# recomputes (code/check_validation.py), accepts only canonical even decimal cutoffs 46..72, and skips cutoffs whose
# output exists.
set -euo pipefail
S10_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P); S10_DATA=${S10_DATA:-<SCRATCH>/lri_s10}
export S10_ROOT S10_DATA
source "$S10_ROOT/slurm/symmetry_env.sh"
[[ $- == *e* ]] || { echo "submit: errexit lost" >&2; exit 2; }
for __v in $(compgen -e); do [[ $__v == SBATCH_* || $__v == SQUEUE_* ]] && unset "$__v"; done; unset __v
die() { echo "submit: $*" >&2; exit 2; }
if [[ ${S10_LOCAL_TEST:-0} != 1 ]]; then
  w=$(find "$S10_ROOT" -type f -perm -u+w -print -quit); [[ -z $w ]] || die "code snapshot is writable ($w); deploy a read-only snapshot"
fi
export S10_EXPECT_SHA=$(sha256sum "$S10_ROOT/code/ragged_quotient.py" | cut -c1-64)
lock=
release_lock() { if [[ -n $lock ]]; then rm -rf "$lock"; fi; }
take_lock() {  # cross-node mutex held through the queue query and sbatch (mkdir is atomic on BeeGFS)
  mkdir "$1" 2>/dev/null || die "another submission holds $1 (remove it only if no submit.sh is running)"
  lock=$1; trap release_lock EXIT; echo "$(hostname) $$ $(date '+%Y-%m-%dT%H:%M:%S%z')" > "$lock/owner"
}
live() {  # non-terminal jobs of this user with exactly this name; a failed query aborts
  local out; out=$(squeue -h -u "$USER" --states=all -n "$1" -o '%F %j %T') || return 1
  awk '$3 !~ /^(COMPLETED|CANCELLED|FAILED|TIMEOUT|NODE_FAIL|OUT_OF_MEMORY|BOOT_FAIL|DEADLINE|PREEMPTED|REVOKED)/' <<<"$out"
}
mkdir -p "$S10_DATA/logs"
take_lock "$S10_DATA/.submit.lock"
case ${1:-} in
  validate)
    busy=$(live s10-validate) || die "squeue failed"; [[ -z $busy ]] || die "validation already live: $busy"
    jid=$(sbatch --parsable --job-name=s10-validate --nodes=1 --ntasks=1 --exclusive --mem=180G --no-requeue \
      --output="$S10_DATA/logs/%x_%j.out" --export=ALL "$S10_ROOT/slurm/validate.slurm") || die "sbatch failed"
    echo "submitted ${jid%%;*}; log $S10_DATA/logs/s10-validate_${jid%%;*}.out" ;;
  production)
    [[ -n ${2:-} ]] || die "usage: production L1,L2,... [max_states]"
    val=$(python "$S10_ROOT/code/check_validation.py" --data "$S10_DATA" --solver-sha "$S10_EXPECT_SHA") || die "no passing validation for this solver and stack (run validate and wait for PASS)"
    echo "validated by $val" >&2
    export S10_MAX_STATES=${3:-120000000}
    [[ $S10_MAX_STATES =~ ^[1-9][0-9]{0,9}$ ]] || die "bad max_states (1..10 digits)"
    todo=()
    IFS=, read -r -a req <<<"$2"
    for L in "${req[@]}"; do
      # Exact allowed strings (no arithmetic: long decimals would wrap in 64-bit bash arithmetic).
      case $L in 46|48|50|52|54|56|58|60|62|64|66|68|70|72) ;; *) die "cutoff '$L' is not one of the supported even cutoffs 46..72" ;; esac
      if [[ -f $S10_DATA/production/dconn_L${L}_d8.json ]]; then echo "skip L=$L (done)" >&2; else todo+=("$L"); fi
    done
    (( ${#todo[@]} > 0 )) || { echo "nothing to submit" >&2; exit 0; }
    busy=$(live s10-prod) || die "squeue failed"; [[ -z $busy ]] || die "production jobs already live: $busy"
    export S10_CUTOFFS=$(IFS=,; echo "${todo[*]}")
    jid=$(sbatch --parsable --job-name=s10-prod --array="0-$(( ${#todo[@]} - 1 ))" --nodes=1 --ntasks=1 --exclusive \
      --mem=180G --no-requeue --output="$S10_DATA/logs/%x_%A_%a.out" --export=ALL "$S10_ROOT/slurm/production.slurm") \
      || die "sbatch failed"
    echo "submitted ${jid%%;*} for L=$S10_CUTOFFS (max_states $S10_MAX_STATES); logs $S10_DATA/logs/s10-prod_${jid%%;*}_<task>.out" ;;
  *) die "usage: $0 validate | production L1,L2,... [max_states]" ;;
esac
