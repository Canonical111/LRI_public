#!/bin/bash
# Run engine cfgs of a list CONCURRENTLY inside one allocation: NPAR worker processes, each with
# T = (physical cores of the allocation) / NPAR OpenMP threads (hpc-clusters rule 7; refuses if T < 1).
# Meant for many small single-sector cfgs (strict re-checks, refinements), whose single-cfg OpenMP efficiency is
# poor (a single sector with 1-2 shifts is split into point blocks; the slowest block sets the wall time).
# Idle OpenMP threads sleep (OMP_WAIT_POLICY=passive), threads are not pinned, so the workers share the cores.
# Same restart semantics as run_list.sh: a cfg is skipped only if its .json ends with "complete": true, stale
# .tmp files are removed, the exit status is non-zero if any cfg failed.
#   usage: run_packed.sh RUNDIR LISTFILE NPAR [FIRST LAST]
set -uo pipefail
RUNDIR=$(cd "$1" && pwd) || exit 66
LIST=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
NPAR=${3:-8}; FIRST=${4:-1}; LAST=${5:-1000000}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
ENGINE=${LRI_ENGINE:-$ROOT/bin/lri_engine}
phys_alloc() {   # distinct physical cores in this process's allowed CPU set (hpc-clusters rule 7)
  local a; a=$(grep -m1 Cpus_allowed_list /proc/self/status | cut -f2)
  lscpu -p=CPU,CORE | grep -v '^#' | awk -F, -v a="$a" '
    BEGIN{n=split(a,r,","); for(i=1;i<=n;i++){m=split(r[i],b,"-"); lo=b[1]; hi=(m==2?b[2]:b[1]); for(c=lo;c<=hi;c++) ok[c]=1}}
    ($1 in ok) && !($2 in seen){seen[$2]=1; k++} END{print k+0}'
}
PA=$(phys_alloc); CAP=${SLURM_CPUS_ON_NODE:-$PA}
BUDGET=$(( PA < CAP ? PA : CAP ))
T=$(( BUDGET / NPAR ))
(( T >= 1 )) || { echo "refusing: $NPAR workers do not fit $BUDGET physical cores" >&2; exit 64; }
export OMP_NUM_THREADS=$T OMP_PROC_BIND=false OMP_WAIT_POLICY=passive ENGINE T
echo "host $(hostname) workers $NPAR x threads $T (budget $BUDGET) engine $ENGINE ($(md5sum "$ENGINE" | cut -c1-12)) start $(date -Is)"
cd "$RUNDIR" || exit 66
run_one() {
  local cfg=$1 t0 rc
  if [ -s "$cfg.json" ] && tail -c 64 "$cfg.json" | grep -q '"complete": true'; then echo "skip $cfg (done)"; return 0; fi
  rm -f "$cfg.json".tmp.*
  t0=$(date +%s)
  echo "=== $(date -Is) $(hostname) threads $T" >> "$cfg.log"
  "$ENGINE" "$cfg" >> "$cfg.log" 2>&1
  rc=$?
  echo "$cfg rc=$rc $(( $(date +%s) - t0 ))s $(date -Is)"
  return $rc
}
export -f run_one
sed -n "${FIRST},${LAST}p" "$LIST" | grep -v '^[[:space:]]*$' | xargs -P "$NPAR" -I{} bash -c 'run_one "$1"' _ {}
rc=$?
echo "end $(date -Is) xargs rc $rc"
[ $rc -eq 0 ] || exit 1
