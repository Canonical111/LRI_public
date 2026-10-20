#!/bin/bash
#SBATCH -N 1 --exclusive
#SBATCH --mem=200G
#SBATCH -J dconn-mi-mem
#SBATCH -o <SCRATCH>/dconn_fit_mi/logs/%x_%j.out
source /etc/profile.d/modules.sh
module load anaconda3/2023.07-2
set -eo pipefail
W=<SCRATCH>/dconn_fit_mi
export DCONN_CORRECTED=${DCONN_CORRECTED:-$W/data/delta_v1_corrected.json}
export DCONN_VARIANTS=${DCONN_VARIANTS:-$W/data/delta_v1_variants.json}
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
phys_alloc() { local a; a=$(grep -m1 Cpus_allowed_list /proc/self/status | cut -f2)
  lscpu -p=CPU,CORE | grep -v '^#' | awk -F, -v a="$a" 'BEGIN{n=split(a,r,","); for(i=1;i<=n;i++){m=split(r[i],b,"-"); lo=b[1]; hi=(m==2?b[2]:b[1]); for(c=lo;c<=hi;c++) ok[c]=1}} ($1 in ok) && !($2 in seen){seen[$2]=1; k++} END{print k+0}'; }
PA=$(phys_alloc); CAP=${SLURM_CPUS_ON_NODE:-1}; P=$(( PA < CAP ? PA : CAP ))
TAG=${1:-mem1}
echo "host $(hostname) P=$P"; date; sha256sum "$DCONN_CORRECTED" "$DCONN_VARIANTS"
mkdir -p $W/out/$TAG
python3 $W/code/members_full.py $W/out/$TAG/members_full.json $W/delta_code > $W/out/$TAG/members_full.log 2>&1
python3 $W/code/members_prop.py $W/out/$TAG/members_full.json $W/out/$TAG $P > $W/out/$TAG/members_prop.log 2>&1
date; echo DONE
