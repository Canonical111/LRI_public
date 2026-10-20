#!/bin/bash
#SBATCH -N 1 --exclusive
#SBATCH --mem=180G
#SBATCH -J mi72-list
# refit72 version of run_list.sbatch: workspace W from the environment (default <SCRATCH>/dconn_refit72_mi),
# per-line overrides TAG CENTRAL [CORR|-] [VARS|-] [RAWC07|-]; MI_ACC_TOPS passed through to accel.py.
# usage: sbatch -p amdq,defq -t 00:50:00 -o LOG run_list72.sbatch RUNLIST
source /etc/profile.d/modules.sh
module load anaconda3/2023.07-2
set -eo pipefail
W=${W:-<SCRATCH>/dconn_refit72_mi}
CORR0=${DCONN_CORRECTED:-$W/data/corrected.json}
VARS0=${DCONN_VARIANTS:-$W/data/variants.json}
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export MI_ACC_TOPS=${MI_ACC_TOPS:-60,72,84,88,92,100,110,118}
phys_alloc() { local a; a=$(grep -m1 Cpus_allowed_list /proc/self/status | cut -f2)
  lscpu -p=CPU,CORE | grep -v '^#' | awk -F, -v a="$a" 'BEGIN{n=split(a,r,","); for(i=1;i<=n;i++){m=split(r[i],b,"-"); lo=b[1]; hi=(m==2?b[2]:b[1]); for(c=lo;c<=hi;c++) ok[c]=1}} ($1 in ok) && !($2 in seen){seen[$2]=1; k++} END{print k+0}'; }
PA=$(phys_alloc); CAP=${SLURM_CPUS_ON_NODE:-1}; P=$(( PA < CAP ? PA : CAP ))
echo "host $(hostname) phys $PA cap $CAP P=$P tops $MI_ACC_TOPS"; date; python3 --version
sha256sum $W/data/*.json $W/code/*.py
while read -r TAG CEN CORR VARS RAWC; do
  [ -z "$TAG" ] && continue
  case "$TAG" in \#*) continue;; esac
  C=$CORR0; V=$VARS0; [ -n "$CORR" ] && [ "$CORR" != - ] && C=$CORR; [ -n "$VARS" ] && [ "$VARS" != - ] && V=$VARS
  mkdir -p $W/out/$TAG
  echo "== $TAG central=$CEN corr=$C vars=$V rawc07=${RAWC:--} $(date +%T)"
  if [ -n "$RAWC" ] && [ "$RAWC" != - ]; then RC="RAW_C07=$RAWC HT_DATA_JSON=$W/data/ht_data.json"; else RC=""; fi
  env DCONN_CENTRAL=$CEN DCONN_CORRECTED=$C DCONN_VARIANTS=$V $RC python3 $W/code/grid.py $W/out/$TAG $P > $W/out/$TAG/grid.log 2>&1
  env DCONN_CENTRAL=$CEN DCONN_CORRECTED=$C DCONN_VARIANTS=$V $RC python3 $W/code/accel.py $W/out/$TAG $P > $W/out/$TAG/accel.log 2>&1
  tail -1 $W/out/$TAG/grid.log; tail -1 $W/out/$TAG/accel.log
done < "$1"
MI_MEMBERS_CENTRAL=${MI_MEMBERS_CENTRAL:-k6:53,k7:74,k8:79}   # default here: commas cannot pass through sbatch --export
if [ -n "${MI_MEMBERS:-}" ]; then
  echo "== members $MI_MEMBERS central=${MI_MEMBERS_CENTRAL} $(date +%T)"
  mkdir -p $W/out/$MI_MEMBERS
  env DCONN_CORRECTED=$CORR0 DCONN_VARIANTS=$VARS0 python3 $W/code/members_full.py $W/out/$MI_MEMBERS/members_full.json $W/delta_code > $W/out/$MI_MEMBERS/members_full.log 2>&1
  env DCONN_CENTRAL=$MI_MEMBERS_CENTRAL DCONN_CORRECTED=$CORR0 DCONN_VARIANTS=$VARS0 python3 $W/code/members_prop.py $W/out/$MI_MEMBERS/members_full.json $W/out/$MI_MEMBERS $P > $W/out/$MI_MEMBERS/members_prop.log 2>&1
  tail -2 $W/out/$MI_MEMBERS/members_full.log; tail -1 $W/out/$MI_MEMBERS/members_prop.log
fi
date; echo DONE
