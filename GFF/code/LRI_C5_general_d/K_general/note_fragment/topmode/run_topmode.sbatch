#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1 --exclusive
#SBATCH -t 01:30:00
#SBATCH --mem=64G
#SBATCH -J c63d-topmode
#SBATCH -o <SCRATCH>/c63d_topmode/logs/%x_%j.out
# topmode checks (session C63d): 10 per-spin runs + 11 Horn-block mode checks + 3 three-node K_d jets (3 x 14 workers) = 63 processes
source ~/c7d3_prod/env.sh
export PYTHONDONTWRITEBYTECODE=1
cd ~/c63d_topmode
OUT=<SCRATCH>/c63d_topmode
echo "start $(date) on $(hostname); cores $(nproc)"; md5sum rblocks.py
for c in R1 R2 R3 R4 R5 G1 G2 C1 C2 C3; do
  python3 perspin_topmode.py $c 200 40 $OUT/perspin_$c.json > $OUT/logs/perspin_$c.log 2>&1 &
done
while read d t; do
  python3 mode_check_rblocks.py $d $t 40 $OUT/modes_d${d}_t${t}.json > $OUT/logs/modes_d${d}_t${t}.log 2>&1 &
done <<PTS
1.7 0.55+0.3j
0.5 0.9+0.2j
3.3 1.1-0.4j
3.7 0.95+0.15j
3.9 1.2+0.3j
0.3 1.0+0.1j
2.2 -0.12+0.05j
1.25 0+0.08j
2.6 2.0+0.5j
3.3 1.6-0.4j
1.25 0.7
PTS
for spec in "0.8 0.04" "1.25 0.08" "2.75 0.08"; do
  set -- $spec
  NWORKERS=14 python3 kjet3_prod.py $1 $2 48 30 400 72 $OUT/kjet3_B_d$1.json > $OUT/logs/kjet3_B_d$1.log 2>&1 &
done
wait
echo "end $(date)"
