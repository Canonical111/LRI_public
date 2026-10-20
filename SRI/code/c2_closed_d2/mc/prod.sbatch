#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive
#SBATCH -t 02:30:00
#SBATCH --mem=60G
#SBATCH -J c2e2e
#SBATCH -o <SCRATCH>/c2rev_e2e/logs/%x_%j.out
# usage: sbatch prod.sbatch TAG ETA KAP NSAMP SEEDBASE [ALPHAFILE]
TAG=$1; ETA=$2; KAPV=$3; NS=$4; SB=$5; AF=$6
cd <SCRATCH>/c2rev_e2e
source /etc/profile.d/modules.sh; module load gcc/11.2.0
mkdir -p run_$TAG
gcc -O2 -march=x86-64-v3 -DUSE_QUAD -o run_$TAG/c2mc3 c2mc3.c -lquadmath -lm 2>/dev/null || exit 1
export LMIN=-16 ERRTOL=1e-2 KAP=$KAPV NBATCH=20
if [ -z "$AF" ]; then
  AF=run_$TAG/alpha.txt
  NADAPT=500000 ALPHAOUT=$AF ./run_$TAG/c2mc3 $ETA 100 1 > /dev/null 2>&1
fi
cp $AF run_$TAG/alpha_used.txt
NW=$(nproc); echo "host $(hostname) nproc $NW tag $TAG eta $ETA kap $KAPV ns $NS"; date
for i in $(seq 1 $NW); do
  ALPHAFILE=run_$TAG/alpha_used.txt ./run_$TAG/c2mc3 $ETA $NS $((SB+i)) > run_$TAG/out_$i.txt 2> run_$TAG/err_$i.txt &
done
wait
date
python3 summ.py run_$TAG/out_*.txt | head -22
