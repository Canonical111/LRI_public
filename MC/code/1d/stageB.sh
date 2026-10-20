set -o pipefail
source /etc/profile.d/modules.sh; module purge >/dev/null 2>&1
module load cpu/0.15.4 gcc/10.2.0 anaconda3 slurm/expanse/23.02.7 >/dev/null 2>&1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export LRI_MODULES='cpu/0.15.4 gcc/10.2.0 anaconda3 slurm/expanse/23.02.7'
CAMP=/expanse/lustre/scratch/zzheng8/temp_project/lri_mc; CSV=$CAMP/fits/centers_prodB_20260914_224841b.csv
cd ~/lri_cluster
[ -d $CAMP/prodB ] && { echo "prodB exists; abort"; exit 1; }
echo "== prepare stage B from $CSV"
python3 prepare.py --out $CAMP/prodB --s 0.8 0.875 --sizes 131072 262144 524288 \
  --replicas 8 --measurements 2000000 --warmup 50000 \
  --beta-points 5 --beta-halfwidth 0.005 --window-exponent 0.35 \
  --centers $CSV --seed-base 2026091502 || exit 1
python3 - <<'PY'
import json,collections
CAMP='/expanse/lustre/scratch/zzheng8/temp_project/lri_mc'
m=json.load(open(f'{CAMP}/prodB/manifest.json')); g=collections.defaultdict(set)
for t in m['tasks']: g[(t['s'],t['N'])].add(t['beta'])
for k in sorted(g): print(f"  s={k[0]} N={k[1]:6d} beta in [{min(g[k]):.6f}, {max(g[k]):.6f}] points={len(g[k])}")
import sys as _sys, os as _os; _sys.path.insert(0,_os.path.expanduser('~/lri_cluster')); import registry; from pathlib import Path   # IR19-002
p=f'{CAMP}/campaigns.json'
def apply(r):   # IR19-002 / IR20-003: every change is made on the registry loaded under the lock
    if any(c['name']=='prodB' for c in r['campaigns']): raise SystemExit('prodB already registered')
    r['campaigns'].append({"name":"prodB","dir":"prodB","stage":"B","seed_base":2026091502,"s":[0.8,0.875],"sizes":[131072,262144,524288],"status":"prepared","job_ids":[],"centres_from":"fits/centers_prodB_20260914_224841b.csv"})
    for s in (0.8,0.875):
        for n in (131072,262144,524288):   # REV-004: append to the active list, never replace an active union (§4.7)
            cur=r['active'].get(f"{s}:{n}",[]); cur=[cur] if isinstance(cur,str) else list(cur)
            if "prodB" not in cur: cur.append("prodB")
            r['active'][f"{s}:{n}"]=cur
    r['campaigns'][0]['status']='complete'
registry.locked_update(Path(p),apply,validate=False); print("  registry: prodB added (under the registry lock)")
PY
python3 registry.py $CAMP/campaigns.json --require all --estimate 2>&1 | tail -3
echo "== dry run"; python3 submit.py $CAMP/prodB --concurrency 240 --tasks-per-slot 1 --time 40:00:00 --mem 2G --account yun124 --partition shared --dry-run | head -2
echo "== resources"; echo "   shared idle cores: $(sinfo -p shared -h -o '%C' | awk -F/ '{s+=$2} END{print s}')"; echo "   yun124 load: $(squeue -A yun124 -h -o '%u %T' | sort | uniq -c | tr '\n' ';')"; expanse-client user -r expanse 2>/dev/null | grep zzheng8
echo "== live submit"
python3 submit.py $CAMP/prodB --concurrency 240 --tasks-per-slot 1 --time 40:00:00 --mem 2G --account yun124 --partition shared 2>&1 | tee $CAMP/prodB/submit_1.log | head -1
JID=$(grep -oE 'Submitted batch job [0-9]+' $CAMP/prodB/submit_1.log | grep -oE '[0-9]+$'); echo "== job id: $JID"
[ -n "$JID" ] && python3 registry.py $CAMP/campaigns.json --no-validate --record-job prodB $JID
sleep 45; echo "== queue: $(squeue -j $JID -h -o %T | sort | uniq -c | tr '\n' ' ')"
f=$(ls -t $CAMP/prodB/logs/*.out 2>/dev/null | head -1); [ -n "$f" ] && { echo "== $f"; head -6 $f; }
cat $CAMP/prodB/logs/*.err 2>/dev/null | grep -v libuuid | head -3
