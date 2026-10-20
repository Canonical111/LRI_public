#!/bin/bash
# Prepare and submit the 3D production campaign (FIT_MODEL_3D §5.2). Login node (prepare is light). SUBMIT=1 to sbatch (default: dry run).
# Guards: the preflight GATE.json must exist with passed=true (FIT3D-005); an atomic submission lock (mkdir) is claimed before any plan or sbatch
# (FIT3D-006); array A is throttled so that A + B + my other running normal-QOS jobs stay <= 22 (FIT3D-008); continuations use continue_3d.slurm
# (FIT3D-002). Env: TBIG (array-A wall limit, default from GATE.json), THROTTLE_A (default computed), SEEDBASE.
set -euo pipefail
source /etc/profile.d/modules.sh; <LOAD_MODULES> >/dev/null 2>&1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
C3=<SCRATCH>/lri3d; ROOT=<CODE_2D>/code; cd $ROOT; mkdir -p $C3/logs
DATE=${DATE:-$(date +%Y%m%d)}; CAMP=$C3/prod3d; ID=prod3d-$DATE; SEEDBASE=${SEEDBASE:-$DATE}
SLOTBIG=32; MASK=0-127:4; NSMALL=${NSMALL:-4}; TSMALL=${TSMALL:-12:00:00}
GATE=${GATE:?path of the passed preflight gate record (GATE_<jobid>.json) required}; CENTERS=<CODE_3D>/production_centers_3d.csv
[ -f $GATE ] || { echo "REFUSED: no preflight gate record $GATE"; exit 1; }
# FIT3D-011: the gate must have passed AND be bound to this design: its recorded preflight manifest/index/results hashes must still match the files,
# its centres hash must equal the centres file used here, and its D3 constants and packing (mask, slot size) must equal the production constants
python3 - "$GATE" "$C3/preflight" "$CENTERS" "$MASK" "$SLOTBIG" <<'PY' || { echo "REFUSED: gate record invalid or not bound to this design"; exit 1; }
import json,sys,hashlib,os
g=json.load(open(sys.argv[1])); P=sys.argv[2]; sha=lambda f: hashlib.sha256(open(f,'rb').read()).hexdigest(); bad=[]
if not g.get('passed'): bad.append('gate not passed: %s'%g.get('reasons'))
if g.get('manifest_sha256')!=sha(P+'/manifest.json'): bad.append('preflight manifest changed since the gate')
idx=g.get('index_path'); 
if not idx or not os.path.exists(idx) or g.get('index_sha256')!=sha(idx): bad.append('packed index missing or changed since the gate')
for s,h in (g.get('results_sha256') or {}).items():
    f=(g.get('analysis_dirs') or {}).get(s)
    if not f or not os.path.exists(f+'/results.json') or sha(f+'/results.json')!=h: bad.append('analysis record for s=%s missing or changed'%s)
if g.get('centers_sha256')!=sha(sys.argv[3]): bad.append('centres file differs from the one the gate was computed with')
D=g.get('design') or {}
if not (D.get('beta_halfwidth')==0.001 and D.get('window_exponent')==1.0 and D.get('reference_length')==16 and D.get('beta_points')==5): bad.append('gate D3 constants != production D3')
if g.get('packing',{}).get('cpu_mask')!=sys.argv[4] or g.get('packing',{}).get('slot_big')!=int(sys.argv[5]): bad.append('gate packing (mask/slot) != production packing')
if len(g.get('rows',[]))!=8 or any(not r.get('ok') for r in g.get('rows',[])): bad.append('gate rows incomplete or not all ok')
if 'tau_int <= 50' not in (g.get('rule') or ''): bad.append('gate record not evaluated under the revision-6 rule')
print('gate binding:', 'OK' if not bad else bad); sys.exit(0 if not bad else 1)
PY
TBIG=${TBIG:-$(python3 -c "import json;h=json.load(open('$GATE'))['array_A_wall_limit_hours'];print('%02d:00:00'%h)")}
echo "gate passed; pinned L=128 rate $(python3 -c "import json;print(round(json.load(open('$GATE'))['pinned_L128_median_ms'],1))") ms/sweep; array-A wall limit $TBIG (continuation behind it)"
[ -e $CAMP ] || python3 prepare.py --out $CAMP --dim 3 --s 1.55 1.6 1.7 1.75 1.8 1.85 1.9 1.95 --sizes 8 16 32 64 128 --centers <CODE_3D>/production_centers_3d.csv \
   --replicas 12 --measurements 1000000 --warmup 50000 --beta-points 5 --beta-halfwidth 0.001 --window-exponent 1.0 --reference-length 16 \
   --seed-base $SEEDBASE --campaign-id $ID --sampler hybrid --record extended > $C3/logs/prod_prepare.log 2>&1
echo "manifest sha $(sha256sum $CAMP/manifest.json | cut -c1-16); chains $(ls $CAMP/chains | wc -l)"
# FIT3D-011: validate the production manifest against the frozen design and bind the preflight temperatures to it (also when the campaign pre-existed)
python3 - "$CAMP/manifest.json" "$C3/preflight/manifest.json" "$CENTERS" <<'PY' || { echo "REFUSED: production manifest does not match the frozen design / preflight temperatures"; exit 1; }
import json,sys,csv,numpy as np
m=json.load(open(sys.argv[1])); pf=json.load(open(sys.argv[2])); c=m['config']; bad=[]
want=dict(replicas=12,measurements=1000000,warmup=50000,beta_points=5,beta_halfwidth=0.001,window_exponent=1.0,reference_length=16,dim=3)
for k,v in want.items():
    if c.get(k)!=v and not (isinstance(v,float) and c.get(k) is not None and abs(float(c[k])-v)<1e-12): bad.append(f'{k}={c.get(k)}!={v}')
if sorted(c.get('sizes',[]))!=[8,16,32,64,128]: bad.append(f"sizes {c.get('sizes')}")
if sorted(round(x,10) for x in c.get('s',[]))!=[1.55,1.6,1.7,1.75,1.8,1.85,1.9,1.95]: bad.append(f"s {c.get('s')}")
if len(m['tasks'])!=2400: bad.append(f"{len(m['tasks'])} tasks != 2400")
grid={(round(t['s'],10),t['L'],round(t['beta'],12)) for t in m['tasks']}
miss=[t for t in pf['tasks'] if (round(t['s'],10),t['L'],round(t['beta'],12)) not in grid]
if miss: bad.append(f'{len(miss)} preflight temperatures are not production temperatures')
ctr={(round(float(r['s']),10),int(r['L'])):float(r['beta']) for r in csv.DictReader(open(sys.argv[3])) if r['d']=='3' and r['L'].strip()}
off=sum(1 for t in m['tasks'] if np.min(np.abs(ctr[(round(t['s'],10),t['L'])]+np.linspace(-1,1,5)*0.001*(t['L']/16)**-1.0-t['beta']))>1e-12)
if off: bad.append(f'{off} production tasks off the frozen D3 grid')
print('production manifest:', 'OK' if not bad else bad); sys.exit(0 if not bad else 1)
PY
Q=$(squeue -u $USER -h -o "%j" 2>&1); QRC=$?; [ $QRC -eq 0 ] || { echo "REFUSED: squeue failed: scheduler state UNKNOWN"; exit 1; }
set +e; QUEUED=$(printf "%s\n" "$Q" | grep -cE "^lri3d_(A|B|A2|B2)$"); GRC=$?; set -e; [ $GRC -le 1 ] || { echo "REFUSED: grep failed"; exit 1; }
[ "$QUEUED" = 0 ] || { echo "REFUSED: $QUEUED lri3d_A/B jobs already queued or running"; exit 1; }
# FIT3D-008/010: concurrency cap 22 running normal-QOS jobs of mine: count ARRAY ELEMENTS (-r) of everything else of mine queued in normal QOS
# (a conservative bound: every queued element may run), check the query's exit status explicitly, and validate any throttle override
set +e; QN=$(squeue -u $USER -h -q normal -r -o "%j" 2>&1); QNRC=$?; set -e
[ $QNRC -eq 0 ] || { echo "REFUSED: squeue (normal QOS) failed: $QN — scheduler state UNKNOWN"; exit 1; }
OTHER=$(printf "%s\n" "$QN" | grep -vE "^lri3d_(A|B|A2|B2)$" | grep -c . || true)
ALLOW=$(( 22 - NSMALL - OTHER )); [ "$ALLOW" -gt 15 ] && ALLOW=15
[ "$ALLOW" -ge 1 ] || { echo "REFUSED: no free running-job slots (other normal-QOS array elements queued: $OTHER)"; exit 1; }
THROTTLE_A=${THROTTLE_A:-$ALLOW}
[ "$THROTTLE_A" -le "$ALLOW" ] && [ "$THROTTLE_A" -ge 1 ] || { echo "REFUSED: THROTTLE_A=$THROTTLE_A exceeds the allowance $ALLOW"; exit 1; }
echo "== other normal-QOS array elements of mine: $OTHER -> allowance $ALLOW, array A throttle %$THROTTLE_A (15 slots); compute idle: $(sinfo -p <PARTITION_NODE> -h -t idle -o %D | paste -sd+ | bc)"
[ "${SUBMIT:-0}" = 1 ] || { echo "(dry run; SUBMIT=1 to submit)"; exit 0; }
mkdir $CAMP/logs 2>/dev/null || true
mkdir $CAMP/logs/submission.lock 2>/dev/null || { echo "REFUSED: submission lock $CAMP/logs/submission.lock exists (a submission was started):"; cat $CAMP/logs/submitted.txt 2>/dev/null; exit 1; }   # FIT3D-006: atomic claim
echo "$(date) submission started: slotbig=$SLOTBIG mask=$MASK nsmall=$NSMALL tbig=$TBIG tsmall=$TSMALL throttleA=$THROTTLE_A gate=$(sha256sum $GATE | cut -c1-16)" >> $CAMP/logs/submitted.txt
PLANS=$(python3 <CODE_3D>/make_plan.py $CAMP --lbig 128 --slot-big $SLOTBIG --nslot-small $NSMALL | tail -1)
PB=$(echo "$PLANS" | python3 -c "import json,sys;print([p for p in json.load(sys.stdin) if 'plan_big' in p][0])"); PS=$(echo "$PLANS" | python3 -c "import json,sys;print([p for p in json.load(sys.stdin) if 'plan_small' in p][0])")
NB=$(python3 -c "import json;print(len(json.load(open('$PB'))['slots']))"); NS=$(python3 -c "import json;print(len(json.load(open('$PS'))['slots']))")
export LRI_ROOT=$ROOT LRI_CAMPAIGN=$CAMP LRI_AUTOREQUEUE=0 LRI_MEASUREMENTS=
COMMON="--export=ALL --mem=128G --account=<ACCOUNT> --partition=<PARTITION_NODE> --cpus-per-task=128"
sub(){ local out; out=$(sbatch "$@" 2>&1) || { echo "sbatch FAILED: $out" | tee -a $CAMP/logs/submitted.txt; exit 1; }; echo "$out" | grep -oE '[0-9]+$'; }
JA=$(LRI_PLAN=$PB LRI_WORKERS=$SLOTBIG LRI_CPUMASK=$MASK sub $COMMON --job-name=lri3d_A --array=0-$((NB-1))%$THROTTLE_A --time=$TBIG --output=$CAMP/logs/A_%A_%a.out --error=$CAMP/logs/A_%A_%a.err <CODE_3D>/cluster/array_pinned.slurm); echo "$(date) A=$JA" >> $CAMP/logs/submitted.txt
JB=$(LRI_PLAN=$PS LRI_WORKERS=128 LRI_CPUMASK= sub $COMMON --job-name=lri3d_B --array=0-$((NS-1))%$NS --time=$TSMALL --output=$CAMP/logs/B_%A_%a.out --error=$CAMP/logs/B_%A_%a.err <CODE_3D>/cluster/array_pinned.slurm); echo "$(date) B=$JB" >> $CAMP/logs/submitted.txt
JA2=$(LRI_PRED=$JA LRI_PLAN=$PB LRI_WORKERS=$SLOTBIG LRI_CPUMASK=$MASK sub $COMMON --job-name=lri3d_A2 --dependency=afterany:$JA --array=0-$((NB-1))%$THROTTLE_A --time=$TBIG --output=$CAMP/logs/A2_%A_%a.out --error=$CAMP/logs/A2_%A_%a.err <CODE_3D>/cluster/continue_3d.slurm); echo "$(date) A2=$JA2" >> $CAMP/logs/submitted.txt
JB2=$(LRI_PRED=$JB LRI_PLAN=$PS LRI_WORKERS=128 LRI_CPUMASK= sub $COMMON --job-name=lri3d_B2 --dependency=afterany:$JB --array=0-$((NS-1))%$NS --time=$TSMALL --output=$CAMP/logs/B2_%A_%a.out --error=$CAMP/logs/B2_%A_%a.err <CODE_3D>/cluster/continue_3d.slurm); echo "$(date) B2=$JB2" >> $CAMP/logs/submitted.txt
echo "submitted: array A $JA (+continuation $JA2): ${NB} x ${SLOTBIG} L=128 chains one per CCX, %$THROTTLE_A, $TBIG; array B $JB (+continuation $JB2): ${NS} slots, $TSMALL"
sleep 15; squeue -u $USER -h -o "%i %j %T %M %P %r" | grep lri3d | head -30
