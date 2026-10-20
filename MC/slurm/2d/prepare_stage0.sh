#!/bin/bash
# Prepare and submit the 2D stage-0 campaign (run on the cluster login node; light). The original also prepared and submitted two
# benchmark campaigns (bench.slurm), which are not shipped.
set -euo pipefail
source /etc/profile.d/modules.sh; <LOAD_MODULES> >/dev/null 2>&1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
C2=<SCRATCH>/lri2d; cd <CODE_2D>/code; mkdir -p $C2/logs
[ -e $C2/stage0 ] || python3 prepare.py --out $C2/stage0 --dim 2 --s 1.05 1.1 1.2 1.3 1.4 1.5 1.6 1.7 --sizes 64 128 256 512 --centers ../reference/largest_pair_crossing_centers.csv --replicas 2 --measurements 100000 --warmup 10000 --beta-points 5 --beta-halfwidth 0.002 --window-exponent 0.5 --reference-length 64 --seed-base 20260920 --campaign-id stage0-2d-20260920 >/dev/null
echo "prepared: $(ls $C2/stage0/chains | wc -l) stage0 chains"
J1=$(sbatch --parsable <CODE_2D>/stage0.slurm); echo "stage0 job $J1"
sleep 15; squeue -u $USER -h -o "%i %j %T %M %P %r"
