#!/bin/bash
#SBATCH --partition=defq
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --no-requeue
#SBATCH --mem=180G
#SBATCH --time=04:00:00
#SBATCH --output=<SCRATCH>/lri_c8/logs/%x_%j.out
# Compute-node validation of the current source on the production stack. Writes the
# receipt that make_campaign.py requires and then warms the persistent Numba cache.
# Submit with: slurm/submit_defq.sh validate
set -euo pipefail
: "${C8_ROOT:?}" "${C8_DATA:?}"
export C8_CACHE_ROLE=node
source "$C8_ROOT/slurm/symmetry_env.sh"
[[ $- == *e* ]] || { echo "[validate] errexit lost" >&2; exit 70; }
VAL=$C8_DATA/validation/${C8_SRC16}_${SLURM_JOB_ID}
mkdir -p "$VAL" "$NUMBA_CACHE_DIR"
PHYS=$(c8_phys_cpus); NPHYS=$(c8_count "$PHYS")
echo "[validate] job $SLURM_JOB_ID on $(hostname) $(date '+%Y-%m-%dT%H:%M:%S%z'); $NPHYS physical cores; output $VAL"
{ echo "== lscpu"; lscpu; echo "== numactl -H"; numactl -H; echo "== free -g"; free -g; echo "== uname -r"; uname -r
  echo "== cgroup"; cat /sys/fs/cgroup/memory.max 2>/dev/null || cat /sys/fs/cgroup/memory/slurm/uid_$(id -u)/job_${SLURM_JOB_ID}/memory.limit_in_bytes 2>/dev/null || true
} > "$VAL/node.txt" 2>&1
BIND=(numactl --physcpubind="$PHYS" --interleave=all)
export NUMBA_NUM_THREADS=$NPHYS   # the --full steps call numba.set_num_threads($NPHYS)
if ! "${BIND[@]}" python "$C8_ROOT/scripts/validate_release.py" --full --threads "$NPHYS" \
     --output "$VAL/receipt.json" --work-dir "$VAL/steps" --fs-probe-dir "$C8_DATA/fs_probe"; then
  echo "[validate] FAIL: see $VAL/receipt.json and $VAL/steps/*.log" >&2; exit 1
fi
# Only a passing validation warms the cache that production jobs load.
if ! "${BIND[@]}" python -m lri_c8 warmup --threads "$NPHYS"; then
  echo "[validate] FAIL: warmup" >&2; exit 1
fi
cp "$VAL/receipt.json" "$C8_DATA/validation/receipt_${C8_SRC16}.json" || { echo "[validate] FAIL: copy receipt" >&2; exit 1; }
echo "[validate] PASS $(date '+%Y-%m-%dT%H:%M:%S%z'); receipt $C8_DATA/validation/receipt_${C8_SRC16}.json"
