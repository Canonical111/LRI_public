#!/bin/bash
#SBATCH -N 1 --exclusive --mem=180G
#SBATCH -o /mnt/beegfs/zzheng1/lri_c6_1d/logs/%x_%A_%a.out
# One c6sum invocation per array task: sectors [a, b), a = SLURM_ARRAY_TASK_ID * CHUNK. Resumes a partial output.
set -eo pipefail
source "$C6_CODE/cluster/env.sh"
c6_require_approval   # a queued task runs only against the approved binaries and inputs
: "${L:?}" "${N:?}" "${MODE:?}" "${STRATUM:?}" "${KIND:?}" "${PERTURB:?}" "${MOD:?}" "${CHUNK:?}" "${STEM:?}"
BIN=$C6_CODE/bin/c6sum; [[ $KIND == ld ]] && BIN=$C6_CODE/bin/c6sum_ld
NSECT=$(( L == 6 ? 360 : 60 ))
a=$(( ${SLURM_ARRAY_TASK_ID:-0} * CHUNK )); b=$(( a + CHUNK )); (( b > NSECT )) && b=$NSECT
mkdir -p "$C6_RUNS/$STEM"
out=$C6_RUNS/$STEM/part_$(printf %03d $a)_$(printf %03d $b).jsonl
T=$(phys_alloc)
echo "$(date) $STEM sectors [$a,$b) threads=$T host=$(hostname) bin=$BIN"
"$BIN" $L $N $T "$C6_DATA" $MODE --out "$out" --first $a --stop $b --mod $MOD --stratum $STRATUM --perturb $PERTURB
echo "$(date) done"
