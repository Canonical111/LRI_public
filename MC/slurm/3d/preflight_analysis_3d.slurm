#!/bin/bash
#SBATCH -J lri3d_pf_an
#SBATCH -A <ACCOUNT>
#SBATCH -p <PARTITION_SHARED>
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8 --mem=32G
#SBATCH -t 02:00:00
#SBATCH -o <SCRATCH>/lri3d/logs/preflight_analysis_%j.out
# 3D preflight GATE (FIT_MODEL_3D §5.1/§7, FIT3D-005): requires the complete chain set and all eight analyses, evaluates every gate condition,
# writes $CAMP/GATE_<jobid>.json (decision, pinned rate, wall limit, per-point rows, input hashes; one immutable record per attempt). Exit 0 only if
# the gate passes; production submission requires a passed record whose path is given explicitly (GATE=... submit_production_3d.sh).
set -uo pipefail
source /etc/profile.d/modules.sh; module purge >/dev/null 2>&1; <LOAD_MODULES> || exit 1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd <CODE_2D>/code; C3=<SCRATCH>/lri3d; CAMP=$C3/preflight
N=$(ls $CAMP/chains/*/DONE.json 2>/dev/null | wc -l); T=$(python3 -c "import json;print(len(json.load(open('$CAMP/manifest.json'))['tasks']))")
echo "$(date) 3D preflight gate; DONE chains $N/$T"
[ "$N" -eq "$T" ] || { echo "GATE: incomplete chain set ($N/$T); not evaluating; exit 64"; exit 64; }
# FIT3D-012: attempt-scoped, immutable artifacts — this job id names the packed index and the analysis directories; nothing left by an
# interrupted attempt is reused; a complete packed index from an earlier attempt of the SAME manifest may be reused only after verification
A=$SLURM_JOB_ID; HIST=$CAMP/hist_b500_$A
MSHA=$(sha256sum $CAMP/manifest.json | cut -d" " -f1)
for old in $CAMP/hist_b500_*/index.json; do   # FIT3D-012/017: reuse only a complete, verified index of THIS manifest (all task ids, no skipped, packed files present)
  [ -s "$old" ] || continue
  python3 - "$old" "$CAMP/manifest.json" "$MSHA" <<'PY2' 2>/dev/null && { HIST=$(dirname $old); echo "reusing verified packed index $HIST"; break; }
import json,sys,os
i=json.load(open(sys.argv[1])); m=json.load(open(sys.argv[2])); d=os.path.dirname(sys.argv[1])
ok=(i.get('manifest_sha256')==sys.argv[3] and not i.get('skipped') and sorted(t['id'] for t in i.get('tasks',[]))==sorted(t['id'] for t in m['tasks'])
    and all(os.path.exists(os.path.join(d,t['histogram'])) for t in i.get('tasks',[])))
sys.exit(0 if ok else 1)
PY2
done
[ -s $HIST/index.json ] || python3 pack_histograms.py $CAMP --block 500 --out $HIST > $C3/logs/preflight_pack_$A.log 2>&1 || { echo "GATE: pack failed"; tail -3 $C3/logs/preflight_pack_$A.log; exit 65; }
[ -s $HIST/index.json ] || { echo "GATE: no packed index"; exit 65; }
for s in 1.55 1.6 1.7 1.75 1.8 1.85 1.9 1.95; do
  python3 precision_analysis.py $HIST/index.json --dim 3 --s $s --bootstrap 100 --out $CAMP/analysis_${A}_s$s > $C3/logs/preflight_an_${A}_s$s.log 2>&1 || { echo "GATE: analysis s=$s failed"; tail -3 $C3/logs/preflight_an_${A}_s$s.log; exit 66; }
  [ -s $CAMP/analysis_${A}_s$s/results.json ] && [ -s $CAMP/analysis_${A}_s$s/bootstrap.npy ] || { echo "GATE: analysis s=$s incomplete"; exit 66; }
done
python3 - "$CAMP" "$A" "$HIST" <<'PY'
import json,glob,sys,hashlib,collections,math,time,os
C=sys.argv[1]; A=sys.argv[2]; HIST=sys.argv[3]; S=[1.55,1.6,1.7,1.75,1.8,1.85,1.9,1.95]; reasons=[]; rows=[]
sha=lambda p: hashlib.sha256(open(p,'rb').read()).hexdigest()
msha=sha(C+'/manifest.json'); isha=sha(HIST+'/index.json'); man=json.load(open(C+'/manifest.json')); cfg=man['config']
idx=json.load(open(HIST+'/index.json'))
if idx.get('manifest_sha256')!=msha: reasons.append('packed index does not belong to this manifest')
# FIT3D-011: the gate is bound to the design it tested: D3 constants, centres file, packing (mask, slot size) from the submission journal
design=dict(beta_halfwidth=cfg.get('beta_halfwidth'),window_exponent=cfg.get('window_exponent'),reference_length=cfg.get('reference_length'),beta_points=cfg.get('beta_points'),sizes=sorted(cfg.get('sizes',[])),s=sorted(cfg.get('s',[])))
centers=os.path.expanduser('<CODE_3D>/production_centers_3d.csv'); csha=sha(centers)
sub=open(C+'/logs/submitted.txt').read() if os.path.exists(C+'/logs/submitted.txt') else ''
import re
mk=re.search(r'mask=(\S+)',sub); sb=re.search(r'slotbig=(\d+)',sub)
packing=dict(cpu_mask=(mk.group(1) if mk else None),slot_big=(int(sb.group(1)) if sb else None))
# pinned L=128 rate and L=64 rate from DONE.json
sp=collections.defaultdict(list)
for f in glob.glob(C+'/chains/*/DONE.json'):
    d=json.load(open(f)); sp[d['L']].append(1e3*d['last_invocation_seconds']/max(1,d['last_invocation_sweeps']))
rates={L:dict(n=len(v),median=sorted(v)[len(v)//2],min=min(v),max=max(v)) for L,v in sp.items()}
for L in sorted(rates): print(f"L={L}: {rates[L]['n']} chains, ms/sweep median {rates[L]['median']:.2f} min {rates[L]['min']:.2f} max {rates[L]['max']:.2f}")
r=rates.get(128,{}).get('median'); 
if r is None: reasons.append('no L=128 rate')
else:
    hours=1.4*r*1e-3*1.05e6/3600; tbig=min(46,math.ceil(hours)); print(f"pinned L=128 median rate r={r:.1f} ms/sweep -> 1.4 x r x 1.05e6 = {hours:.1f} h -> array-A wall limit {tbig} h (capped 46; continuation covers the rest)")
    if r*1e-3*1.05e6/3600>80: reasons.append(f'L=128 chain time {r*1e-3*1.05e6/3600:.0f} h > 80 h: production not submitted, plan returns to review')
inputs={}
dirs={}
for s in S:
    d=f'{C}/analysis_{A}_s{s}'; f=d+'/results.json'
    if not os.path.exists(f): reasons.append(f's={s}: no analysis'); continue
    res=json.load(open(f)); inputs[str(s)]=sha(f); dirs[str(s)]=d; ch=res['chains']
    if res.get('campaign_id')!=man['campaign_id'] or res.get('manifest_sha256')!=msha or res.get('index_sha256')!=isha: reasons.append(f's={s}: analysis record not from this manifest/index')
    if len(res['rows'])!=1: reasons.append(f's={s}: {len(res["rows"])} pairs (expected 1: 64->128)')
    for row in res['rows']:
        v=row['values']; dg=row['diagnostics']; lo,hi=dg['beta_bracket']; pos=(v[0]-lo)/(hi-lo); ess=dg['ESS_fraction']; ff=row.get('bootstrap_failure_fraction',1.0)
        tau=max(max(c['tau'].values()) for c in ch); z=max(abs(c['half_drift_z']) for c in ch)
        ok=(0<pos<1) and min(ess)>=0.5 and ff==0 and tau<=50   # amended rule (revision 6): block/tau >= 20 at the smallest production block b=1000
        rows.append(dict(s=s,beta_x=v[0],bracket_position=pos,ESS=ess,D_U4=v[2],D_Y=v[1],sigma_U4=(row.get('statistical_stderr') or [None]*5)[2],bootstrap_failure_fraction=ff,max_tau=tau,max_half_drift_z=z,ok=ok))
        print(f"s={s}: 64->128 beta_x={v[0]:.6f} at {pos:.2f} of bracket ESS={ess[0]:.2f}/{ess[1]:.2f} D_U4={v[2]:.3f} D_Y={v[1]:.3f} fail={ff} tau_max={tau:.1f} |z|max={z:.2f} -> {'ok' if ok else 'FAIL'}")
        if not ok: reasons.append(f's={s}: bracket position {pos:.2f}, ESS {min(ess):.2f}, fail {ff}, tau {tau:.1f}')
    for w in res['warnings']: print(f"s={s}: WARNING",w)
passed=(not reasons) and len(rows)==len(S)
gate=dict(passed=passed,reasons=reasons,time=time.strftime('%F_%T'),attempt=A,manifest_sha256=msha,index_path=HIST+'/index.json',index_sha256=isha,results_sha256=inputs,analysis_dirs=dirs,
          centers=centers,centers_sha256=csha,design=design,packing=packing,
          rates_ms_per_sweep=rates,pinned_L128_median_ms=r,array_A_wall_limit_hours=(min(46,math.ceil(1.4*r*1e-3*1.05e6/3600)) if r else None),rows=rows,
          rule='FIT_MODEL_3D §5.1 (revision 6): every 64->128 U4 crossing inside its bracket, ESS >= 0.5 at both sizes, no bootstrap failures, tau_int <= 50 (block/tau >= 20 at b=1000); wall limit 1.4 x r x 1.05e6 capped at 46 h')
out=f'{C}/GATE_{A}.json'   # one immutable record per attempt (the submission script is given the record path explicitly)
if os.path.exists(out): print(out,'exists; not overwriting (immutable)'); sys.exit(2)
json.dump(gate,open(out,'x'),indent=1); print('GATE', 'PASSED' if passed else 'FAILED', reasons, '->', out)
sys.exit(0 if passed else 1)
PY
rc=$?; echo "$(date) PREFLIGHT GATE exit $rc"; exit $rc
