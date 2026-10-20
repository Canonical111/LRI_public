#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --no-requeue
# Assemble a finished production run and run the validators that need it (A4, A5, A6d). Writes
# $C4_DATA/results/c4_1d_L$C4_LMAX.npz and $C4_DATA/results/gates_L$C4_LMAX.txt (PASS/FAIL per gate).
set -euo pipefail
: "${C4_ROOT:?}" "${C4_DATA:?}" "${C4_LMAX:?}" "${C4_EXPECT_SHA:?}"
source "$C4_ROOT/slurm/env.sh"
cd "$C4_ROOT"
got=$(python c4_run1d.py sha --kind snapshot)
[[ $got == "$C4_EXPECT_SHA" ]] || { echo "snapshot sha $got != expected $C4_EXPECT_SHA" >&2; exit 64; }
NUM=$(python c4_run1d.py sha --kind numerics)
export OMP_NUM_THREADS=20 MKL_NUM_THREADS=20 NUMBA_NUM_THREADS=20 NUMBA_CACHE_DIR="$C4_DATA/numba_cache/$(hostname)_asm"
R=$C4_DATA/results/${C4_EXPECT_SHA:0:12}; mkdir -p "$R"; OUT=$R/c4_1d_L$C4_LMAX.npz; G=$R/gates_L$C4_LMAX.txt
[[ ! -e $G ]] || { echo "gate record $G exists" >&2; exit 64; }
echo "[asm] job $SLURM_JOB_ID host $(hostname) $(date '+%Y-%m-%dT%H:%M:%S%z') Lmax=$C4_LMAX snapshot $C4_EXPECT_SHA"
/usr/bin/time -v python c4_run1d.py assemble --Lmax "$C4_LMAX" --cache "$C4_DATA/cache_L${C4_LMAX}_${NUM:0:12}" --out "$OUT"
GT=$G.tmp$$
{ echo "snapshot_sha $C4_EXPECT_SHA"; echo "result $OUT sha256 $(sha256sum "$OUT" | cut -c1-64)"; } > "$GT"
gate() { local name=$1; shift; if "$@"; then echo "PASS $name" >> "$GT"; else echo "FAIL $name" >> "$GT"; fi; }
(( C4_LMAX >= 118 )) && gate A4 python validate/v4_ht.py "$OUT"
(( C4_LMAX >= 152 )) && gate A5 python validate/v5_windows.py "$OUT" --g2D-Lmax "$(( C4_LMAX < 400 ? C4_LMAX : 400 ))"
if [[ -n ${C4_PREV:-} ]]; then
  P=$R/c4_1d_L$C4_PREV.npz
  if python validate/v6_overlap.py "$P" "$OUT"; then
    echo "PASS A6d_${C4_PREV}_vs_${C4_LMAX} prev_sha256=$(sha256sum "$P" | cut -c1-64) cur_sha256=$(sha256sum "$OUT" | cut -c1-64)" >> "$GT"
  else
    echo "FAIL A6d_${C4_PREV}_vs_${C4_LMAX}" >> "$GT"
  fi
fi
mv "$GT" "$G"                                   # the gate record appears atomically, complete
cat "$G"
! grep -q '^FAIL' "$G"
