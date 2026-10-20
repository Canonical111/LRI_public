#!/bin/bash
# Run engine cfgs listed in a file (one name per line, relative to RUNDIR), lines [FIRST, LAST], sequentially,
# each with all physical cores of this allocation (OpenMP).  Usage: run_list.sh RUNDIR LISTFILE FIRST LAST
# Restart safety (v2): the engine writes <cfg>.json via <cfg>.json.tmp.<pid> + rename and ends it with
# "complete": true; a cfg is skipped only if its .json carries that marker, stale .tmp files are removed,
# and the script exits non-zero if any cfg failed (so sacct marks the task FAILED).
set -uo pipefail
RUNDIR=$(cd "$1" && pwd) || exit 66
LIST=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")   # absolute: the loop runs inside RUNDIR
FIRST=${3:-1}; LAST=${4:-1000000}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
ENGINE=${LRI_ENGINE:-$ROOT/bin/lri_engine}
phys_alloc() {   # distinct physical cores in this process's allowed CPU set (hpc-clusters rule 7)
  local a; a=$(grep -m1 Cpus_allowed_list /proc/self/status | cut -f2)
  lscpu -p=CPU,CORE | grep -v '^#' | awk -F, -v a="$a" '
    BEGIN{n=split(a,r,","); for(i=1;i<=n;i++){m=split(r[i],b,"-"); lo=b[1]; hi=(m==2?b[2]:b[1]); for(c=lo;c<=hi;c++) ok[c]=1}}
    ($1 in ok) && !($2 in seen){seen[$2]=1; k++} END{print k+0}'
}
PA=$(phys_alloc); CAP=${SLURM_CPUS_ON_NODE:-$PA}
P=$(( PA < CAP ? PA : CAP ))
(( P >= 1 )) || { echo "refusing: no physical cores visible" >&2; exit 64; }
export OMP_NUM_THREADS=$P OMP_PROC_BIND=spread OMP_PLACES=cores
echo "host $(hostname) threads $P engine $ENGINE ($(md5sum "$ENGINE" | cut -c1-12)) start $(date -Is)"
cd "$RUNDIR" || exit 66
nfail=0
while read -r cfg; do
  [ -z "$cfg" ] && continue
  if [ -s "$cfg.json" ] && tail -c 64 "$cfg.json" | grep -q '"complete": true'; then echo "skip $cfg (done)"; continue; fi
  rm -f "$cfg.json".tmp.*
  t0=$(date +%s)
  echo "=== $(date -Is) $(hostname) threads $P" >> "$cfg.log"
  "$ENGINE" "$cfg" >> "$cfg.log" 2>&1
  rc=$?
  [ $rc -ne 0 ] && nfail=$((nfail+1))
  echo "$cfg rc=$rc $(( $(date +%s) - t0 ))s $(date -Is)"
done < <(sed -n "${FIRST},${LAST}p" "$LIST")
echo "end $(date -Is) failures $nfail"
[ $nfail -eq 0 ] || exit 1
