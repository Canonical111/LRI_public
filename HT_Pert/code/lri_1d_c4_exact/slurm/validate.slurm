#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --no-requeue
# Validation of a code snapshot on one node: unit tests incl. the slow A6a/A6b (Lmax 40), A1/A2, A3, then the
# Delta R4 closed form through L = 2000 (A5 ii), the Lmax = 200 and 400 runs (both sockets) with assembly, A4, A5 and
# the staged A6d (200 vs 400). C4_EXPECT_SHA is the snapshot sha. On success writes (atomically)
# $C4_DATA/validation/$C4_EXPECT_SHA/PASS.
set -euo pipefail
: "${C4_ROOT:?}" "${C4_DATA:?}" "${C4_EXPECT_SHA:?}"
source "$C4_ROOT/slurm/env.sh"
cd "$C4_ROOT"
got=$(python c4_run1d.py sha --kind snapshot)
[[ $got == "$C4_EXPECT_SHA" ]] || { echo "snapshot sha $got != expected $C4_EXPECT_SHA" >&2; exit 64; }
V=$C4_DATA/validation/$C4_EXPECT_SHA; mkdir -p "$V"; rm -f "$V/PASS"
rm -f "$C4_DATA/results/${C4_EXPECT_SHA:0:12}"/gates_L200.txt "$C4_DATA/results/${C4_EXPECT_SHA:0:12}"/gates_L400.txt
echo "[val] job $SLURM_JOB_ID host $(hostname) partition $SLURM_JOB_PARTITION $(date '+%Y-%m-%dT%H:%M:%S%z')"
lscpu | grep -E 'Model name|Socket|Core|NUMA node[0-9]'
export OMP_NUM_THREADS=20 MKL_NUM_THREADS=20 NUMBA_NUM_THREADS=20 NUMBA_CACHE_DIR="$C4_DATA/numba_cache/$(hostname)_val"
python - <<'PY'
import time, numpy as np
for n in (2000, 4000):
    a = np.random.rand(n, n); b = np.random.rand(n, n); a @ b
    t = time.time(); a @ b; dt = time.time() - t
    print(f"[val] dgemm n={n} {2 * n ** 3 / dt / 1e9:.0f} GFLOP/s (20 threads)")
PY
C4T_SLOW=1 C4T_LMAX=40 python -m pytest -q validate/test_kernels.py 2>&1 | tee "$V/pytest.txt"
python validate/v1_exact.py 2>&1 | tee "$V/v1.txt"
python validate/v3_brute.py --cut4max 48 2>&1 | tee "$V/v3.txt"
python validate/v7_dR4.py --Lmax 2000 2>&1 | tee "$V/v7.txt"
for L in 200 400; do
  export C4_LMAX=$L C4_NNODES=1 C4_WPS=2 C4_BLOCK=32
  SLURM_ARRAY_TASK_ID=0 bash "$C4_ROOT/slurm/node.slurm"
  C4_PREV=$([[ $L == 400 ]] && echo 200 || true) bash "$C4_ROOT/slurm/assemble.slurm"
done
R=$C4_DATA/results/${C4_EXPECT_SHA:0:12}
cat "$R/gates_L200.txt" "$R/gates_L400.txt" > "$V/gates.txt"
if grep -q '^FAIL' "$V/gates.txt"; then echo "[val] FAIL"; exit 1; fi
grep -q '^PASS A6d_200_vs_400 ' "$V/gates.txt" || { echo "[val] A6d record missing"; exit 1; }
{ echo "PASS $(date '+%Y-%m-%dT%H:%M:%S%z') job $SLURM_JOB_ID snapshot_sha $C4_EXPECT_SHA"
  echo "checks: pytest(A6a-c) v1(A1,A2) v3(A3) v7(A5 ii to 2000) L200+L400 gates(A4,A5,A6d)"; cat "$V/gates.txt"; } > "$V/PASS.tmp$$"
mv "$V/PASS.tmp$$" "$V/PASS"
echo "[val] PASS -> $V/PASS"
