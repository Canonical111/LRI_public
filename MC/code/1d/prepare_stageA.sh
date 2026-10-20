#!/bin/bash
# Stage A of the Δσ scan: one campaign per point under $CAMP/scan/ds<Δσ>/stageA with per-size centres.
# Usage on Expanse: prepare_stageA.sh centres_perN.csv   (columns s,N,beta; one row per (s,N), N in 1024..65536)
set -euo pipefail
source /etc/profile.d/modules.sh; module purge; module load cpu/0.15.4 gcc/10.2.0 anaconda3 slurm/expanse/23.02.7
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
CSV=${1:?centres csv}; CAMP=/expanse/lustre/scratch/zzheng8/temp_project/lri_mc; SCAN=$CAMP/scan
cd ~/lri_cluster
i=0
for s in $(tail -n +2 "$CSV" | cut -d, -f1 | sort -u); do
  i=$((i+1)); dsn=$(python3 -c "x=(1-$s)/2; print(('%.7f'%x).rstrip('0').rstrip('.'))"); D=$SCAN/ds$dsn; mkdir -p $D
  [ -d $D/stageA ] && { echo "skip $D/stageA (exists)"; continue; }
  { echo "s,N,beta"; grep "^$s," "$CSV"; } > $D/centers_stageA.csv
  python3 prepare.py --out $D/stageA --s $s --sizes 1024 2048 4096 8192 16384 32768 65536 \
    --replicas 8 --measurements 2000000 --warmup 50000 --beta-points 5 --beta-halfwidth 0.005 --window-exponent 0.35 \
    --centers $D/centers_stageA.csv --seed-base $((2026091700+i)) > $D/stageA_prepare.log
  python3 - "$D" "$s" <<'PY'
import json,sys
D,s=sys.argv[1],float(sys.argv[2]); sizes=[2**k for k in range(10,20)]
reg={"root":D,"measurements":2000000,"replicas":8,"beta_points":5,"stageA_max_N":65536,
     "expected_pairs":[f"{s}:{n}" for n in sizes],
     "campaigns":[{"name":"stageA","dir":"stageA","stage":"A","seed_base":None,"s":[s],"sizes":sizes[:7],"status":"prepared","job_ids":[]}],
     "active":{f"{s}:{n}":"stageA" for n in sizes[:7]}}
json.dump(reg,open(f"{D}/campaigns.json","w"),indent=1)
PY
  echo "prepared ds=$dsn s=$s: $(python3 -c "import json;print(json.load(open('$D/stageA/plan.json'))['tasks'])") tasks; centres $(tail -n +2 $D/centers_stageA.csv | cut -d, -f3 | tr '\n' ' ')"
done
