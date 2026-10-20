#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --no-requeue
# Validation of a code snapshot on one node (PLAN.md sec. 2 and 6). In order, each step must pass:
#   C5T_SLOW=1 pytest validate/test_*.py        (A6a-c incl. the slow mirror tests, rs term list, orders 2-4 regression)
#   validate/v1_exact.py                        (A1, A2)
#   validate/v3_brute.py --cut4max 128          (A3)
#   validate/v7_closed.py --Lmax 2000           (Delta R4 / Delta R5 closed forms)
#   Lmax = 80 and 160 runs on this node (node.slurm, both sockets) with assembly (assemble.slurm): A6e at both,
#   A4, A5 and A6d (80 vs 160) at 160.
# C5_EXPECT_SHA is the snapshot sha; C5_VAL_WPS / C5_VAL_BLOCK (default 2 / 8 = run5.py's --block default) set the
# workers per socket and the block of the two runs. The tests and validators run bound to socket 0 (numactl
# --cpunodebind; threads = physical cores of socket 0). Step outputs: $C5_DATA/validation/<sha>/{pytest,v1,v3,v7}.txt;
# gate records $C5_DATA/results/<sha12>/gates_L{80,160}.txt.
# After the tests, v1 and v3 pass it writes (atomically) $C5_DATA/validation/<sha>/PRELIM (A1-A3, A6a-c: the
# prerequisite of benchmarks); only if everything passes it writes (atomically) $C5_DATA/validation/<sha>/PASS.
# Refuses to start if PASS exists.  A resubmitted validation reuses a completed L80/L160 rung of this snapshot (gate
# record bound to the result on disk, no FAIL, and for L160 the A6d line bound to the current L80 result); any other
# leftover result/gate pair of the rung is moved together to results/<sha12>/stale/ before the rung is redone (its task
# checkpoints are reused).
set -euo pipefail
: "${C5_ROOT:?}" "${C5_DATA:?}" "${C5_EXPECT_SHA:?}"
source "$C5_ROOT/slurm/env.sh"
cd "$C5_ROOT"
got=$(python run5.py sha --kind snapshot)
[[ $got == "$C5_EXPECT_SHA" ]] || { echo "snapshot sha $got != expected $C5_EXPECT_SHA" >&2; exit 64; }
V=$C5_DATA/validation/$C5_EXPECT_SHA; R=$C5_DATA/results/${C5_EXPECT_SHA:0:12}
[[ ! -e $V/PASS ]] || { echo "$V/PASS exists; remove it by hand to re-validate this snapshot" >&2; exit 64; }
export C5_NNODES=1 C5_WPS=${C5_VAL_WPS:-2} C5_BLOCK=${C5_VAL_BLOCK:-8}
[[ $C5_WPS =~ ^[1-9][0-9]*$ && $C5_BLOCK =~ ^[1-9][0-9]*$ ]] || { echo "bad C5_VAL_WPS/C5_VAL_BLOCK" >&2; exit 64; }
mkdir -p "$V" "$R"
rm -f "$V/gates.txt"
sha() { sha256sum "$1" | cut -c1-64; }
rung_ok() {  # rung_ok L: a completed rung of this snapshot (gate record bound to the result on disk, no FAIL)
  local G=$R/gates_L$1.txt O=$R/c5_1d_L$1.npz rs
  [[ -f $G && -f $O ]] || return 1
  grep -qx "snapshot_sha $C5_EXPECT_SHA" "$G" || return 1
  ! grep -q '^FAIL' "$G" || return 1
  rs=$(sed -n 's/^result .* sha256 \([0-9a-f]\{64\}\)$/\1/p' "$G")
  [[ $rs == "$(sha "$O")" ]]
}
archive_rung() {  # archive_rung L: move a stale/orphan result and/or gate record of the rung aside (kept together)
  local d
  if [[ -e $R/c5_1d_L$1.npz || -e $R/gates_L$1.txt ]]; then
    d=$R/stale/L$1_$(date +%Y%m%dT%H%M%S)_${SLURM_JOB_ID:-$$}; mkdir -p "$d"
    [[ ! -e $R/c5_1d_L$1.npz ]] || mv "$R/c5_1d_L$1.npz" "$d/"
    [[ ! -e $R/gates_L$1.txt ]] || mv "$R/gates_L$1.txt" "$d/"
    echo "[val] stale rung L$1 moved to $d"
  fi
}
echo "[val] job ${SLURM_JOB_ID:-} host $(hostname) partition ${SLURM_JOB_PARTITION:-} $(date '+%Y-%m-%dT%H:%M:%S%z') snapshot $C5_EXPECT_SHA"
lscpu | grep -E 'Model name|Socket|Core|NUMA node[0-9]' || true
numa0=$(c5_numa 0); T0=$(c5_cores 0)
[[ -n $numa0 && $T0 =~ ^[1-9][0-9]*$ ]] || { echo "cannot determine socket 0 (numa '$numa0', cores '$T0')" >&2; exit 64; }
export OMP_NUM_THREADS=$T0 MKL_NUM_THREADS=$T0 NUMBA_NUM_THREADS=$T0 NUMBA_CACHE_DIR="$C5_DATA/numba_cache/$(hostname)_val"
on0() { numactl --cpunodebind="$numa0" "$@"; }
on0 python - <<'PY'
import os, time, numpy as np
for n in (2000, 4000):
    a = np.random.rand(n, n); b = np.random.rand(n, n); a @ b
    t = time.time(); a @ b; dt = time.time() - t
    print(f"[val] dgemm n={n} {2 * n ** 3 / dt / 1e9:.0f} GFLOP/s ({os.environ['OMP_NUM_THREADS']} threads, socket 0)")
PY
on0 env C5T_SLOW=1 python -m pytest -q -p no:cacheprovider validate/test_*.py 2>&1 | tee "$V/pytest.txt"
on0 python validate/v1_exact.py 2>&1 | tee "$V/v1.txt"
on0 python validate/v3_brute.py --cut4max 128 2>&1 | tee "$V/v3.txt"
# preliminary record (PLAN sec. 2: benchmarks need A1-A3 and A6a-c of this snapshot); written atomically
{ echo "PRELIM $(date '+%Y-%m-%dT%H:%M:%S%z') job ${SLURM_JOB_ID:-} snapshot_sha $C5_EXPECT_SHA"
  echo "checks: pytest C5T_SLOW=1 validate/test_*.py (A6a-c), v1 (A1, A2), v3 --cut4max 128 (A3)"; } > "$V/PRELIM.tmp$$"
mv "$V/PRELIM.tmp$$" "$V/PRELIM"
echo "[val] PRELIM -> $V/PRELIM"
on0 python validate/v7_closed.py --Lmax 2000 2>&1 | tee "$V/v7.txt"
prev=
for L in 80 160; do
  export C5_LMAX=$L C5_PREV=$prev
  if rung_ok "$L" && { [[ -z $prev ]] || grep -q "^PASS A6d_${prev}_vs_${L} prev_sha256=$(sha "$R/c5_1d_L$prev.npz") " "$R/gates_L$L.txt"; }; then
    echo "[val] rung L$L already complete for this snapshot (gate record bound to its result): reused"
  else
    archive_rung "$L"
    SLURM_ARRAY_TASK_ID=0 bash "$C5_ROOT/slurm/node.slurm"      # checkpoints of a previous attempt are reused
    bash "$C5_ROOT/slurm/assemble.slurm"
  fi
  prev=$L
done
G80=$R/gates_L80.txt; G160=$R/gates_L160.txt; bad=0
need() { grep -q "$2" "$1" || { echo "[val] $1 lacks a line matching '$2'"; bad=1; }; }
for G in "$G80" "$G160"; do
  need "$G" "^snapshot_sha $C5_EXPECT_SHA\$"; need "$G" '^PASS A6e '
  if grep -q '^FAIL' "$G"; then echo "[val] $G has FAIL lines"; bad=1; fi
done
need "$G160" '^PASS A4$'; need "$G160" '^PASS A5$'; need "$G160" '^PASS A6d_80_vs_160 '
cat "$G80" "$G160" > "$V/gates.txt"
(( bad == 0 )) || { echo "[val] FAIL"; exit 1; }
{ echo "PASS $(date '+%Y-%m-%dT%H:%M:%S%z') job ${SLURM_JOB_ID:-} snapshot_sha $C5_EXPECT_SHA"
  echo "checks: pytest C5T_SLOW=1 validate/test_*.py (A6a-c) v1 (A1,A2) v3 --cut4max 128 (A3) v7 --Lmax 2000" \
       "(closed forms) L80+L160 gates (A4,A5,A6d_80_vs_160,A6e)"
  echo "runs: host $(hostname) partition ${SLURM_JOB_PARTITION:-} wps $C5_WPS block $C5_BLOCK"
  cat "$G80" "$G160"; } > "$V/PASS.tmp$$"
mv "$V/PASS.tmp$$" "$V/PASS"
echo "[val] PASS -> $V/PASS"
