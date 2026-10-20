#!/bin/bash
#SBATCH -J lri3d_pack
#SBATCH -A <ACCOUNT>
#SBATCH -p <PARTITION_SHARED>
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8 --mem=48G
#SBATCH -t 08:00:00
#SBATCH -o <SCRATCH>/lri3d/logs/prod_pack_%j.out
# FIT_MODEL_3D §4.1/§5.2 (FIT3D-014): pack every chain of prod3d at b = 2000 (primary), 1000 and 4000 (reblocking) into SNAPSHOT-scoped immutable
# directories hist_b<b>_<SNAP>. SNAP (default: this job id) names one raw snapshot: analysis and evaluation of the same snapshot use the same SNAP.
# Gate: all 2400 chains DONE and every chain at its required measurement total (1e6, or the registered per-point total in extensions.json).
set -uo pipefail
source /etc/profile.d/modules.sh; module purge >/dev/null 2>&1; <LOAD_MODULES> || exit 1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd <CODE_2D>/code || exit 1
CAMP=<SCRATCH>/lri3d/prod3d; LOGS=<SCRATCH>/lri3d/logs; SNAP=${SNAP:-$SLURM_JOB_ID}
mkdir -p $CAMP/snapshots; SREC=$CAMP/snapshots/$SNAP.json
[ -e $SREC ] && { echo "snapshot $SNAP already recorded ($SREC); refusing to repack; exit 63"; exit 63; }
python3 - "$CAMP" "$SNAP" <<'PY' || { echo "gate: chain set incomplete or not at the required totals; nothing packed; exit 64"; exit 64; }
import json,os,sys,hashlib,time
C,SNAP=sys.argv[1],sys.argv[2]; m=json.load(open(C+'/manifest.json')); ext={}
if os.path.exists(C+'/extensions.json'):
    ext={round(float(k),10):int(v) for k,v in json.load(open(C+'/extensions.json')).items()}
missing=[]; short=[]
for t in m['tasks']:
    f=os.path.join(C,t['directory'],'DONE.json')
    if not os.path.exists(f): missing.append(t['id']); continue
    d=json.load(open(f)); need=ext.get(round(t['s'],10),1000000)
    if d.get('measurements_done')!=need: short.append((t['id'],d.get('measurements_done'),need))
print(f"chains {len(m['tasks'])}: missing DONE {len(missing)}, not at required total {len(short)} {short[:3]}; extensions {ext or 'none'}")
ok=not missing and not short
if ok:
    # FIT3D-019: freeze the extension ledger with the snapshot (immutable copy + hash); evaluation of this snapshot uses only the frozen copy
    frozen=None; fsha=None
    if os.path.exists(C+'/extensions.json'):
        frozen=f'{C}/snapshots/{SNAP}.extensions.json'
        with open(C+'/extensions.json','rb') as src, open(frozen,'xb') as dst: data=src.read(); dst.write(data)
        fsha=hashlib.sha256(data).hexdigest()
    rec=dict(snapshot=SNAP,time=time.strftime('%F_%T'),campaign_id=m['campaign_id'],manifest_sha256=hashlib.sha256(open(C+'/manifest.json','rb').read()).hexdigest(),
             extensions=ext,extensions_frozen=frozen,extensions_sha256=fsha,chains=len(m['tasks']),hist_dirs={b:f'hist_b{b}_{SNAP}' for b in (2000,1000,4000)})
    json.dump(rec,open(f'{C}/snapshots/{SNAP}.json','x'),indent=1)
sys.exit(0 if ok else 1)
PY
for b in 2000 1000 4000; do
  OUT=$CAMP/hist_b${b}_$SNAP
  python3 pack_histograms.py $CAMP --block $b --out $OUT > $LOGS/prod_pack_${SNAP}_b$b.log 2>&1; echo "pack b=$b exit $? ($(date))"
  [ -s $OUT/index.json ] || { echo "missing $OUT/index.json; exit 65"; exit 65; }
  python3 -c "import json,sys;i=json.load(open('$OUT/index.json'));sys.exit(0 if not i.get('skipped') and len(i['tasks'])==i['manifest_tasks'] else 1)" || { echo "packed index b=$b incomplete (skipped chains); exit 65"; exit 65; }
done
echo "$(date) PACK DONE snapshot $SNAP"; cat $SREC
