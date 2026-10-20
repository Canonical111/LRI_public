#!/bin/bash
#SBATCH -p sharedq
#SBATCH -c 8
#SBATCH --mem=15G
#SBATCH -J r72-joint
#SBATCH -o <SCRATCH>/dconn_refit72_joint/logs/%x_%j.out
# refit72 joint lens: scan on symmetry sharedq (amdq/defq full on 2026-10-09). usage: sbatch -t 03:00:00 run_scan_shared.sbatch TAG [KINDS]
set -eo pipefail
W=<SCRATCH>/dconn_refit72_joint
TAG=${1:-r72}; KINDS=${2:-"o8 o7"}
PY=<HOME>/kgen_vbjet/venv/bin/python
export DCONN_CORRECTED=$W/data/delta_v1_hi72_corrected.json
export DCONN_VARIANTS_FULL=$W/data/variants_full_hi72.json
export DCONN_OLD_CORRECTED=$W/data/old/delta_v1_corrected.json
export DCONN_OLD_VARIANTS_FULL=$W/data/old/variants_full.json
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
phys_alloc() { local a; a=$(grep -m1 Cpus_allowed_list /proc/self/status | cut -f2)
  lscpu -p=CPU,CORE | grep -v '^#' | awk -F, -v a="$a" 'BEGIN{n=split(a,r,","); for(i=1;i<=n;i++){m=split(r[i],b,"-"); lo=b[1]; hi=(m==2?b[2]:b[1]); for(c=lo;c<=hi;c++) ok[c]=1}} ($1 in ok) && !($2 in seen){seen[$2]=1; k++} END{print k+0}'; }
PA=$(phys_alloc); CAP=${SLURM_CPUS_ON_NODE:-1}; P=$(( PA < CAP ? PA : CAP ))
(( P >= 1 )) || { echo "no cores" >&2; exit 64; }
echo "host $(hostname) allowed $(grep -m1 Cpus_allowed_list /proc/self/status | cut -f2) phys $PA cap $CAP -> P=$P; tag $TAG kinds $KINDS"; date
sha256sum "$DCONN_CORRECTED" "$DCONN_VARIANTS_FULL" "$DCONN_OLD_CORRECTED" "$DCONN_OLD_VARIANTS_FULL" $W/code/*.py
mkdir -p $W/out/$TAG
for K in $KINDS; do
  $PY $W/code/scan.py $K --workers $P --out $W/out/$TAG/scan_${K}${OUTSUF:-}.jsonl.gz
done
date; echo DONE
