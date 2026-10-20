#!/bin/bash
#SBATCH --job-name=c2e2eC
#SBATCH --ntasks=1 --cpus-per-task=14
#SBATCH --mem=14G
#SBATCH --time=03:00:00
#SBATCH --chdir=<DATA>/<USER>/c2rev_e2e
#SBATCH --output=<DATA>/<USER>/c2rev_e2e/logs/%x-%j.out
TAG=C; ETA=0.07; KAPV=0.2; NS=300000000; SB=9000
mkdir -p run_$TAG
export LMIN=-16 ERRTOL=1e-2 KAP=$KAPV NBATCH=20
AF=run_$TAG/alpha.txt
NADAPT=500000 ALPHAOUT=$AF ./c2mc3 $ETA 100 1 > /dev/null 2>&1
NW=14; echo "host $(hostname) workers $NW tag $TAG eta $ETA kap $KAPV ns $NS"; date
for i in $(seq 1 $NW); do
  ALPHAFILE=$AF ./c2mc3 $ETA $NS $((SB+i)) > run_$TAG/out_$i.txt 2> run_$TAG/err_$i.txt &
done
wait
date
python3 summ.py run_$TAG/out_*.txt | head -24
