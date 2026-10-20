#!/bin/bash
# Amendment A3 (docs/EXTENSION_A3.md), symmetry login node: sanitized submission of the A3 jobs. Every inherited C8X_*
# and SBATCH_* variable is removed and C8X_A3 is set to this script's own directory (the deployed revision), which the
# jobs check by comparing their own script with the copy there. Usage:
#   submit_sym.sh close              the closing job (a3_close.slurm, defq, job name c8x-finalize)
#   submit_sym.sh check LABEL...     the optional early validation of staged copies (a3_check.slurm, sharedq, 8 cores)
set -eo pipefail
export PATH=/cm/shared/apps/slurm/current/bin:$PATH
W=/mnt/beegfs/zzheng1/c8_hpc;HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
[[ "$HERE" == $W/code/*/cluster/a3 ]] || { echo "not a deployed cluster/a3: $HERE" >&2; exit 64; }
[[ -z "${SLURM_JOB_ID:-}" ]] || { echo "run from the login node" >&2; exit 64; }
for v in $(compgen -e | grep -E '^(C8X_|SBATCH_)' || true); do unset "$v"; done
export C8X_A3=$HERE
[[ "$(env | grep '^C8X_' | sort | tr '\n' '|')" == "C8X_A3=$HERE|" ]] || { echo "C8X_* environment not as pinned" >&2; exit 64; }
cd $W
case "${1:-}" in
close) j=$(sbatch --parsable -p defq --job-name=c8x-finalize --export=ALL $HERE/a3_close.slurm);;
check) shift;[[ $# -ge 1 ]] || { echo "give labels" >&2; exit 64; }
       j=$(sbatch --parsable -p sharedq -N 1 -c 8 --mem=16000M -t 04:00:00 --job-name=c8x-a3check -o $W/logs/%x_%j.out --export=ALL $HERE/a3_check.slurm "$@");;
*) echo "usage: submit_sym.sh close | check LABEL..." >&2; exit 64;;
esac
[[ "$j" =~ ^[0-9]+$ ]] || { echo "sbatch failed: $j" >&2; exit 66; }
echo "$j $1 $(date -Is) $HERE" >> $W/runs/ext1/a3_sym_jobs.txt;echo "$j"
