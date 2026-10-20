#!/bin/bash
#SBATCH --job-name=c8x-lane
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --mem=180G
#SBATCH --time=1-00:00:00
#SBATCH --output=/mnt/beegfs/zzheng1/c8_hpc/logs/%x_%j.out
# One lane8.py worker per NUMA node of a whole Intel node (amendment A1). Required: C8X_TOOLS (code with lane8.py),
# C8X_QUEUE (queue directory), C8X_MODE (phys|ht). Partition (defq, or preq with --requeue) is given at submission.
set -eo pipefail
source /mnt/beegfs/zzheng1/c8_hpc/code/symmetry/env_symmetry.sh
set -u
: "${C8X_TOOLS:?}" "${C8X_QUEUE:?}" "${C8X_MODE:?}"
[[ "$(sha256sum "$C8_EXE" | cut -d' ' -f1)" == "$C8_EXE_SHA256" ]] || { echo "C8X: executable digest mismatch" >&2; exit 64; }
S=/local1/zzheng1_c8x_${SLURM_JOB_ID}_${SLURM_RESTART_COUNT:-0}
mkdir -p "$S" "$C8X_QUEUE/logs";trap 'rm -rf "$S"' EXIT
[[ -f "$C8X_QUEUE/order.json" ]] || { echo "C8X: no order.json in $C8X_QUEUE" >&2; exit 64; }
echo "C8X: lane job $SLURM_JOB_ID restart ${SLURM_RESTART_COUNT:-0} on $(hostname) partition ${SLURM_JOB_PARTITION:-?} at $(date -Is); mode $C8X_MODE"
mapfile -t SETS < <("$C8_PYTHON" /mnt/beegfs/zzheng1/c8_hpc/code/symmetry/cpusets.py "$C8X_MODE")
(( ${#SETS[@]} >= 1 )) || { echo "C8X: no CPU sets" >&2; exit 64; }
pids=();slot=0
for line in "${SETS[@]}"; do
  read -r node n cpus <<<"$line"
  mkdir -p "$S/slot$slot"
  echo "C8X: slot $slot node $node threads $n cpus $cpus"
  numactl --physcpubind="$cpus" --membind="$node" "$C8_PYTHON" "$C8X_TOOLS/tools/lane8.py" run --queue "$C8X_QUEUE" --slot "$slot" --threads "$n" \
     --c8-root "$C8_ROOT" --executable "$C8_EXE" --scratch "$S/slot$slot" > "$C8X_QUEUE/logs/worker_${SLURM_JOB_ID}_${SLURM_RESTART_COUNT:-0}_slot$slot.log" 2>&1 &
  pids+=($!);slot=$((slot+1))
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=1; done
echo "C8X: lane job $SLURM_JOB_ID workers finished at $(date -Is), status $fail"
exit $fail
