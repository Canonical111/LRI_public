#!/bin/bash
# Stage 0 of the Δσ scan (SCAN_PLAN.md §2): bracket-finding pilots for all grid points, one campaign per point under
# $CAMP/scan/ds<Δσ>/stage0, plus a per-point registry. Prepares only; prints the submit commands. Run on Expanse.
set -euo pipefail
source /etc/profile.d/modules.sh; module purge; module load cpu/0.15.4 gcc/10.2.0 anaconda3 slurm/expanse/23.02.7
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
CAMP=/expanse/lustre/scratch/zzheng8/temp_project/lri_mc; SCAN=$CAMP/scan; mkdir -p $SCAN
cd ~/lri_cluster
# Δσ, s, β_c start, half-width (±0.010 where the start is an extrapolation, ±0.004 otherwise)
python3 - <<'EOF' > $SCAN/grid.csv
rows=[(0.0125,0.975,0.59676,0.010),(0.025,0.95,0.55915,0.004),(0.0375,0.925,0.52716,0.004),(0.05,0.9,0.49948,0.004),
      (0.0625,0.875,0.47485,0.004),(0.075,0.85,0.45215,0.004),(0.0875,0.825,0.43098,0.004),(0.1,0.8,0.41111,0.004),
      (0.1125,0.775,0.39232,0.004),(0.125,0.75,0.37449,0.004),(0.1375,0.725,0.35750,0.004),(0.15,0.7,0.34123,0.004),
      (0.1625,0.675,0.32558,0.004),(0.1727335,0.654533,0.31319,0.004),(0.175,0.65,0.31050,0.004),(0.1875,0.625,0.29591,0.004),
      (0.2,0.6,0.28178,0.004),(0.2125,0.575,0.26805,0.010),(0.225,0.55,0.25466,0.010),(0.2375,0.525,0.24155,0.010)]
print("ds,s,beta,halfwidth")
for ds,s,b,h in rows: print(f"{ds},{s},{b},{h}")
EOF
i=0
while IFS=, read -r ds s b h; do
  [ "$ds" = "ds" ] && continue; i=$((i+1))
  D=$SCAN/ds$ds; mkdir -p $D
  [ -d $D/stage0 ] && { echo "skip $D/stage0 (exists)"; continue; }
  printf 's,N,beta\n%s,,%s\n' "$s" "$b" > $D/centers_stage0.csv
  python3 prepare.py --out $D/stage0 --s $s --sizes 1024 2048 4096 8192 16384 \
    --replicas 4 --measurements 200000 --warmup 20000 --beta-points 9 --beta-halfwidth $h --window-exponent 0 \
    --centers $D/centers_stage0.csv --seed-base $((2026091600+i)) > $D/stage0_prepare.log
  python3 - "$D" "$s" "$ds" <<'EOF'
import json,sys
D,s,ds=sys.argv[1],float(sys.argv[2]),sys.argv[3]
reg={"root":D,"measurements":200000,"replicas":4,"beta_points":9,"stageA_max_N":16384,
     "expected_pairs":[f"{s}:{n}" for n in (1024,2048,4096,8192,16384)],
     "campaigns":[{"name":"stage0","dir":"stage0","stage":"0","seed_base":None,"s":[s],"sizes":[1024,2048,4096,8192,16384],"status":"prepared","job_ids":[]}],
     "active":{f"{s}:{n}":"stage0" for n in (1024,2048,4096,8192,16384)}}
json.dump(reg,open(f"{D}/campaigns_stage0.json","w"),indent=1)
EOF
  echo "prepared ds=$ds s=$s: $(python3 -c "import json;print(json.load(open('$D/stage0/plan.json'))['tasks'])") tasks"
done < $SCAN/grid.csv
echo "Submit (one array per point, shared partition, 180 tasks each):"
echo '  export LRI_MODULES="cpu/0.15.4 gcc/10.2.0 anaconda3 slurm/expanse/23.02.7"'
echo '  for D in '"$SCAN"'/ds*/; do python3 submit.py $D/stage0 --concurrency 180 --tasks-per-slot 1 --time 02:00:00 --mem 2G --account yun124 --partition shared; done'
