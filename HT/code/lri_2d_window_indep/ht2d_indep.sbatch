#!/bin/bash
#SBATCH -J ht2d-indep
#SBATCH -p amdq
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 64
#SBATCH --mem=240G
#SBATCH -t 24:00:00
#SBATCH -o <SCRATCH>/ht2d_indep/logs/%x_%j.out
set -euo pipefail
ROOT=<SCRATCH>/ht2d_indep
PY=<HOME>/lri2d_coeff/venv/bin/python
cd $ROOT/code
phys_alloc() { local a; a=$(grep -m1 Cpus_allowed_list /proc/self/status | cut -f2)
  lscpu -p=CPU,CORE | grep -v '^#' | awk -F, -v a="$a" 'BEGIN{n=split(a,r,","); for(i=1;i<=n;i++){m=split(r[i],b,"-"); lo=b[1]; hi=(m==2?b[2]:b[1]); for(c=lo;c<=hi;c++) ok[c]=1}} ($1 in ok) && !($2 in seen){seen[$2]=1; k++} END{print k+0}'; }
NW=${NWORKERS:-56}; PA=$(phys_alloc); echo "host $(hostname) physical cores $PA workers $NW"
(( NW <= PA )) || { echo "refusing: $NW workers > $PA cores" >&2; exit 64; }
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
$PY -c "import sys,numpy,scipy;print(sys.version.split()[0],numpy.__version__,scipy.__version__)"
sha256sum indep_ht2d.py run_check.py test_indep.py
$PY test_indep.py
$PY run_check.py $ROOT/prod_records $ROOT/out $NW
