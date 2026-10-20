#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --no-requeue
# Assemble a finished C5 run (all task checkpoints in $C5_DATA/cache_L<Lmax>_<numerics sha12>) and run the gates that
# need its result. With R = $C5_DATA/results/<snapshot sha12> the result is assembled to a pending file, every gate runs
# on that file, and only then are the result $R/c5_1d_L<Lmax>.npz and the gate record $R/gates_L<Lmax>.txt published
# (each by an atomic rename, result first). A crash before the end leaves neither; a crash between the two renames
# leaves an orphan result, which `slurm/submit.sh assemble L` moves aside after checking its provenance. A result with
# any FAIL gate is never published under the canonical name: the pair goes to $R/failed/L<Lmax>_<job>/. The record:
#   snapshot_sha <full snapshot sha>
#   result <path> sha256 <sha256 of the result>
#   PASS|FAIL A4  or SKIP A4 (...)    validate/v4_ht.py RESULT                     (run when Lmax >= 118)
#   PASS|FAIL A5  or SKIP A5 (...)    validate/v5_windows.py RESULT                (run when Lmax >= 152)
#   PASS A6d_<prev>_vs_<Lmax> prev_sha256=<..> cur_sha256=<..>   (validate/v6_overlap.py PREV RESULT; only when
#        C5_PREV is set; requires the previous result to be the one named by its own gate record, and both sha256 to
#        appear in the validator's output)
#   PASS A6e c4ref_sha256=<..> cur_sha256=<..>   (validate/v6_overlap.py --c4ref RESULT --c4npz $C5_C4REF; C2..C4 vs
#        the C4P production result, whose sha256 must equal the pinned C5_C4REF_SHA256 of env.sh; both sha256 must
#        appear in the validator's output)
# A failing gate writes "FAIL <gate> [(reason)]". Validator output: $R/gatelogs_L<Lmax>/<gate>.txt (and this job's log).
# All Python runs are bound to socket 0 (numactl --cpunodebind; threads = physical cores of socket 0).
# Exit status 0 iff the record has no FAIL line. Submitted by slurm/submit.sh prod; called by validate.slurm.
set -euo pipefail
: "${C5_ROOT:?}" "${C5_DATA:?}" "${C5_LMAX:?}" "${C5_EXPECT_SHA:?}"
source "$C5_ROOT/slurm/env.sh"
L=$C5_LMAX; PREV=${C5_PREV:-}
[[ $L =~ ^[1-9][0-9]*$ ]] || { echo "C5_LMAX='$L' is not a positive integer" >&2; exit 64; }
[[ -z $PREV ]] || { [[ $PREV =~ ^[1-9][0-9]*$ ]] && (( PREV < L )); } || { echo "C5_PREV='$PREV' must be < C5_LMAX" >&2; exit 64; }
cd "$C5_ROOT"
got=$(python run5.py sha --kind snapshot)
[[ $got == "$C5_EXPECT_SHA" ]] || { echo "snapshot sha $got != expected $C5_EXPECT_SHA" >&2; exit 64; }
NUM=$(python run5.py sha --kind numerics)
[[ $NUM =~ ^[0-9a-f]{64}$ ]] || { echo "numerics sha '$NUM' is not a sha256" >&2; exit 64; }
numa0=$(c5_numa 0); T0=$(c5_cores 0)
[[ -n $numa0 && $T0 =~ ^[1-9][0-9]*$ ]] || { echo "cannot determine socket 0 (numa '$numa0', cores '$T0')" >&2; exit 64; }
export OMP_NUM_THREADS=$T0 MKL_NUM_THREADS=$T0 NUMBA_NUM_THREADS=$T0 NUMBA_CACHE_DIR="$C5_DATA/numba_cache/$(hostname)_asm"
on0() { numactl --cpunodebind="$numa0" "$@"; }
sha() { sha256sum "$1" | cut -c1-64; }
R=$C5_DATA/results/${C5_EXPECT_SHA:0:12}; mkdir -p "$R"
OUT=$R/c5_1d_L$L.npz; G=$R/gates_L$L.txt; LG=$R/gatelogs_L$L
CACHE=$C5_DATA/cache_L${L}_${NUM:0:12}
[[ ! -e $G ]] || { echo "gate record $G exists" >&2; exit 64; }
[[ ! -e $OUT ]] || { echo "result $OUT exists without a gate record (orphan): use slurm/submit.sh assemble $L" >&2; exit 64; }
[[ -d $CACHE ]] || { echo "cache $CACHE missing (node jobs not run for this numerics sha?)" >&2; exit 64; }
echo "[asm] job ${SLURM_JOB_ID:-} host $(hostname) partition ${SLURM_JOB_PARTITION:-} $(date '+%Y-%m-%dT%H:%M:%S%z')" \
  "Lmax=$L prev=${PREV:-none} snapshot $C5_EXPECT_SHA numerics ${NUM:0:12} socket0 numa=$numa0 threads=$T0"
TMP=$R/.tmp$$_c5_1d_L$L.npz; GT=$G.tmp$$
trap 'rm -f "$TMP" "$GT"' EXIT
rm -f "$TMP"
on0 /usr/bin/time -v python run5.py assemble --Lmax "$L" --cache "$CACHE" --out "$TMP"
[[ -s $TMP ]] || { echo "assembly wrote no $TMP" >&2; exit 65; }
CS=$(sha "$TMP")                                 # gates run on the pending file; it is published under $OUT at the end
rm -rf "$LG"; mkdir -p "$LG"
{ echo "snapshot_sha $C5_EXPECT_SHA"; echo "result $OUT sha256 $CS"; } > "$GT"
rec() { echo "$*" >> "$GT"; echo "[asm] $*"; }
run_gate() {  # run_gate NAME CMD...: validator output to $LG/NAME.txt and the log; status = the validator's
  local name=$1; shift
  echo "[asm] gate $name: $*"
  "$@" 2>&1 | tee "$LG/$name.txt"
}
if (( L >= 118 )); then
  if run_gate A4 on0 python validate/v4_ht.py "$TMP"; then rec "PASS A4"; else rec "FAIL A4"; fi
else
  rec "SKIP A4 (Lmax $L < 118, the end of the HT data)"
fi
if (( L >= 152 )); then
  if run_gate A5 on0 python validate/v5_windows.py "$TMP"; then rec "PASS A5"; else rec "FAIL A5"; fi
else
  rec "SKIP A5 (Lmax $L < 152)"
fi
if [[ -n $PREV ]]; then
  name=A6d_${PREV}_vs_${L}; P=$R/c5_1d_L$PREV.npz; PG=$R/gates_L$PREV.txt
  if [[ ! -f $P || ! -f $PG ]]; then
    rec "FAIL $name (missing $P or $PG)"
  else
    PS=$(sha "$P")
    if [[ $(sed -n 's/^result .* sha256 \([0-9a-f]\{64\}\)$/\1/p' "$PG") != "$PS" ]]; then
      rec "FAIL $name (L$PREV result differs from the one named in $PG)"
    elif ! run_gate "$name" on0 python validate/v6_overlap.py "$P" "$TMP"; then
      rec "FAIL $name"
    elif ! grep -q "$PS" "$LG/$name.txt" || ! grep -q "$CS" "$LG/$name.txt"; then
      rec "FAIL $name (validator output lacks the sha256 of both files)"
    else
      rec "PASS $name prev_sha256=$PS cur_sha256=$CS"
    fi
  fi
fi
if [[ ! -f $C5_C4REF ]]; then
  rec "FAIL A6e (C4 reference $C5_C4REF missing)"
elif [[ $(sha "$C5_C4REF") != "$C5_C4REF_SHA256" ]]; then
  rec "FAIL A6e (sha256 of $C5_C4REF is not the pinned $C5_C4REF_SHA256)"
elif ! run_gate A6e on0 python validate/v6_overlap.py --c4ref "$TMP" --c4npz "$C5_C4REF"; then
  rec "FAIL A6e"
elif ! grep -q "$CS" "$LG/A6e.txt" || ! grep -q "$C5_C4REF_SHA256" "$LG/A6e.txt"; then
  rec "FAIL A6e (validator output lacks the sha256 of both files)"
else
  rec "PASS A6e c4ref_sha256=$C5_C4REF_SHA256 cur_sha256=$CS"
fi
[[ $(sha "$TMP") == "$CS" ]] || { echo "pending result changed during the gates" >&2; exit 65; }
if grep -q '^FAIL' "$GT"; then
  # a failed rung never becomes canonical: keep the pair under diagnostic names, publish nothing
  FD=$R/failed/L${L}_${SLURM_JOB_ID:-$$}; mkdir -p "$FD"
  mv "$TMP" "$FD/c5_1d_L$L.npz"; mv "$GT" "$FD/gates_L$L.txt"
  cat "$FD/gates_L$L.txt"
  echo "[asm] FAIL: nothing published; result and gate record kept in $FD" >&2
  exit 1
fi
mv "$TMP" "$OUT"                                # publish the result (atomic) ...
mv "$GT" "$G"                                   # ... then the gate record (atomic, complete)
cat "$G"
echo "[asm] all gates passed -> $G"
