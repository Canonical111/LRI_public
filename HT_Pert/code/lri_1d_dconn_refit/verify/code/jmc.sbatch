#!/bin/bash
#SBATCH -p sharedq
#SBATCH -c 8
#SBATCH --mem=12G
#SBATCH -t 02:00:00
#SBATCH -J r72-verify-jmc
#SBATCH -o <SCRATCH>/dconn_refit72_verify/logs/%x_%j.out
# verifier (hi72): joint-lens C8 grid on baselines, own-continuation members and synthetic noise realizations
set -eo pipefail
W=<SCRATCH>/dconn_refit72_verify
PY=<HOME>/kgen_vbjet/venv/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
phys_alloc() { local a; a=$(grep -m1 Cpus_allowed_list /proc/self/status | cut -f2)
  lscpu -p=CPU,CORE | grep -v '^#' | awk -F, -v a="$a" 'BEGIN{n=split(a,r,","); for(i=1;i<=n;i++){m=split(r[i],b,"-"); lo=b[1]; hi=(m==2?b[2]:b[1]); for(c=lo;c<=hi;c++) ok[c]=1}} ($1 in ok) && !($2 in seen){seen[$2]=1; k++} END{print k+0}'; }
PA=$(phys_alloc); CAP=${SLURM_CPUS_ON_NODE:-1}; P=$(( PA < CAP ? PA : CAP ))
(( P >= 1 )) || { echo "no cores" >&2; exit 64; }
export P
echo "host $(hostname) phys $PA cap $CAP -> P=$P"; date
sha256sum $W/code/*.py $W/out/tabs.npz $W/out/mycont_dC678.json
cd $W/code
$PY jmc.py ${1:-all} $W/out/jmc_${2:-all}.pkl
date; echo DONE
