#!/bin/bash
#SBATCH -N 1 --exclusive
#SBATCH -t 04:00:00
#SBATCH -J fd_val50
#SBATCH -o <SCRATCH>/c5_gend/foundation/fd_val50_%j.out
source /etc/profile.d/modules.sh; module load python/3.11
cd <SCRATCH>/c5_gend/foundation
phys_alloc() { local a; a=$(grep -m1 Cpus_allowed_list /proc/self/status | cut -f2)
  lscpu -p=CPU,CORE | grep -v '^#' | awk -F, -v a="$a" 'BEGIN{n=split(a,r,","); for(i=1;i<=n;i++){m=split(r[i],b,"-"); lo=b[1]; hi=(m==2?b[2]:b[1]); for(c=lo;c<=hi;c++) ok[c]=1}} ($1 in ok) && !($2 in seen){seen[$2]=1; k++} END{print k+0}'; }
export SLURM_CPUS_PER_TASK=$(phys_alloc)
echo "host $(hostname) workers $SLURM_CPUS_PER_TASK start $(date)"
export CIRCLE_DS=1,2,3,1.5,2.5,0.8,1.25,2.75 MCIRC=96
~/c5d2/venv/bin/python run_validation.py val50.json 50 refs center offdiag spectral circles
echo "end $(date)"
