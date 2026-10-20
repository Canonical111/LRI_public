#!/usr/bin/env python3
"""Compare replayed checkpoints of batch b1 elements with the Expanse checkpoints of the same identities.
For every mode and element, the expected set is derived from the frozen manifest (every part of the element's shard
at every degree); each must exist in both trees, with identical row identities and 16 values per row. Checks
(amendment A1, revised after the first replay and inspection round 6):
  1. row sanity: max |diff| / row scale <= ROW_THRESHOLD (long-double values parsed exactly);
  2. estimator scale: a conservative bound on the shift of the campaign's C8 contribution in one batch,
       (w/B) * sum_k |M[8,k]| * sum over replayed rows (both degrees of a paired level) of |diff_k|,
     with M the frozen controlled map (power) or Jacobian (free/exact) of the loop, w the campaign's assembly weight
     and B its replicate count, extrapolated linearly from the replayed shard's work units to the whole campaign and
     divided by the campaign's per-batch C8 sampling SE (2 x its SE in the 4-batch base combination);
     it must be <= EST_THRESHOLD;
  3. thread-count independence: every mode equals the first in row identities and exact values (timings excluded).
Exits 1 on any missing file or violation, 3 when the element set or modes do not qualify (unless the explicit leading
flag --diagnostic is given, which reduced test runs pass and smoke8.slurm never does). Usage:
smoke_compare.py [--diagnostic] SMOKE_DIR B1_DIR ROW_THRESHOLD EST_THRESHOLD AFFINE_JSON BASE_RESULT_JSON MODE[,MODE] ELEMENT...
"""
import json,os,sys,decimal
from pathlib import Path
sys.path.insert(0,os.environ['C8_ROOT']+'/tools')
from campaign import blocks,identity
D=decimal.Decimal;decimal.getcontext().prec=60
argv=sys.argv[1:];diagnostic=bool(argv) and argv[0]=='--diagnostic' # explicit flag only; smoke8.slurm never passes it
if diagnostic:argv=argv[1:]
sm,b1=Path(argv[0]),Path(argv[1]);thr=D(argv[2]);ethr=D(argv[3]);aff=json.loads(Path(argv[4]).read_text());base=json.loads(Path(argv[5]).read_text())
modes=argv[6].split(',');elements=list(map(int,argv[7:]))
REQUIRED={5,84,9,10,11,12} # qualifying element set of amendment A1 (power L6 degrees 1 and 5-9, QMC L8)
if not elements or not modes or not all(modes):sys.exit('no elements or modes to compare')
prod=json.loads((b1/'production.json').read_text());weights={s['campaign']:D(str(s['weight'])) for s in json.loads((b1/'assembly.json').read_text())['sources']}
key=lambda rows:[(tuple(r[k] for k in ('uid','replicate','graph','begin','end','total')),[str(v) for v in r['value']]) for r in rows]
fail=0;worst_row=D(0);worst_est=D(0);nfiles=0
for mode in modes:
    for i in elements:
        j=prod['jobs'][i];c=j['campaign'];camp=b1/c;man=json.loads((camp/'manifest.json').read_text())
        M=aff['loops'][str(man['L'])]['adjusted' if man['mode']=='power' else 'J'][8];absdiff=[D(0)]*16;missing=False
        for shard,part,block,_ in blocks(camp,man,j['index']):
            for N in man['degrees']:
                name=identity(shard['id'],part,N)+'.json';p=sm/mode/'b1'/c/'checkpoints'/name;ref=camp/'checkpoints'/name
                if not p.is_file() or not ref.is_file():print(f'FAIL {mode} element {i} {c}/{name}: missing replay or reference');fail=1;missing=True;continue
                a=json.loads(p.read_text(),parse_float=D);b=json.loads(ref.read_text(),parse_float=D);nfiles+=1
                if len(a['rows'])!=len(b['rows']) or len(a['rows'])!=len(block):print(f'FAIL {mode} {c}/{name}: row count {len(a["rows"])} vs {len(b["rows"])} (plan {len(block)})');fail=1;missing=True;continue
                worst=D(0);ident=0;bad=False
                for ra,rb,w in zip(a['rows'],b['rows'],block):
                    ka=tuple(ra[k] for k in ('uid','replicate','graph','begin','end','total'));kb=tuple(rb[k] for k in ('uid','replicate','graph','begin','end','total'))
                    if ka!=kb or ka!=tuple(w) or len(ra['value'])!=16 or len(rb['value'])!=16:print(f'FAIL {mode} {c}/{name}: row identity or width differs at {ka}');fail=1;bad=missing=True;break
                    va=[D(str(x)) for x in ra['value']];vb=[D(str(x)) for x in rb['value']];scale=max(abs(x) for x in vb) or D(1)
                    dv=[abs(x-y) for x,y in zip(va,vb)];absdiff=[s+d for s,d in zip(absdiff,dv)]
                    d=max(dv)/scale;worst=max(worst,d);ident+=d==0
                if bad:continue
                if mode!=modes[0]:
                    p0=sm/modes[0]/'b1'/c/'checkpoints'/name
                    if not p0.is_file() or key(json.loads(p0.read_text(),parse_float=D)['rows'])!=key(a['rows']):print(f'FAIL {mode} {c}/{name}: differs from mode {modes[0]}');fail=1
                worst_row=max(worst_row,worst);ok=worst<=thr;fail|=not ok
                print(f"{'ok  ' if ok else 'FAIL'} {mode} element {i} {c}/{name}: rows {len(a['rows'])}, bitwise rows {ident}, payload identical {a['provenance']['payload_sha256']==b['provenance']['payload_sha256']}, max |diff|/row scale {float(worst):.3e}")
        if missing:continue
        se=D(str(base['campaign_aggregates'][c]['sampling_se_C8']))*2;B=D(man['replicates']);w=weights[c]
        bound=w/B*sum(abs(D(str(m)))*s for m,s in zip(M,absdiff))*D(man['total_work_units'])/D(man['shards'][j['index']]['work_units'])
        ratio=bound/se if se>0 else (D(0) if bound==0 else D('Infinity'));worst_est=max(worst_est,ratio);ok=ratio<=ethr;fail|=not ok
        print(f"{'ok  ' if ok else 'FAIL'} {mode} element {i} {c}: C8 shift bound {float(bound):.3e} (extrapolated to the campaign) / per-batch SE {float(se):.3e} = {float(ratio):.3e}")
if nfiles==0:print('FAIL: no checkpoint compared');fail=1
qualifying=set(elements)>=REQUIRED and set(modes)>={'phys','ht'}
if not qualifying:
    print('NOT QUALIFYING: the amendment requires elements',sorted(REQUIRED),'in modes phys and ht'+(' (diagnostic run: reported, not a gate)' if diagnostic else ''))
    if not diagnostic:fail=fail or 3
print(f'compared {nfiles} checkpoints; worst row {float(worst_row):.3e} (bound {thr}); worst estimator-scale ratio {float(worst_est):.3e} (bound {ethr}):','PASS' if not fail else 'FAIL')
sys.exit(fail)
