#!/usr/bin/env python3
"""Replay the archived d=3 production streams with the new worker and rebuild C7(3).

Usage (on an x86-64 Linux node, after `make gmp` in the package):
  python3 replay_archived.py PKG OUTDIR --threads 32            # run + compare + assemble
  python3 replay_archived.py PKG OUTDIR --dry                   # copy archived rows as 'replayed' (tests the recipe)
"""
import argparse,json,hashlib,shutil,subprocess,sys,os
sys.dont_write_bytecode=True
from decimal import Decimal as D
from pathlib import Path
import numpy as np
ap=argparse.ArgumentParser();ap.add_argument('pkg',type=Path);ap.add_argument('out',type=Path)
ap.add_argument('--threads',type=int,default=8);ap.add_argument('--exe',default='bin/c7d3_gmp');ap.add_argument('--dry',action='store_true')
ap.add_argument('--tags',nargs='+',default=['production_a','production_b'])
a=ap.parse_args();P=a.pkg.resolve();R=P/'reference';O=a.out.resolve();O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(P/'tools'))
SEED_POWER_OFFSET=348612   # reference/code/run_campaign.py: seed+(348612 if power)
report=dict(groups={},max_normalized_difference='0',bitwise_rows=0,rows=0)
maxerr=D(0)
for tag in a.tags:
    cfg=json.load(open(R/'records'/tag/'config.json'));man=json.load(open(R/'records'/tag/'manifest.json'))
    for rec in man['records']:
        src=R/rec['file'];tasks=src.with_suffix('.tasks');net=R/'records'/tag/f"{rec['sector']}_L{rec['L']}.net"
        for p,h in ((src,rec['sha256']),(tasks,rec['tasks_sha256']),(net,rec['net_sha256'])):
            if hashlib.sha256(p.read_bytes()).hexdigest()!=h:raise SystemExit('hash mismatch '+str(p))
        seed=cfg['seed']+(SEED_POWER_OFFSET if rec['sector']=='power' else 0)
        dest=O/tag/src.name;dest.parent.mkdir(exist_ok=True)
        cmd=[str(P/a.exe),str(R/'inputs'/rec['sector']),str(P/'inputs/gamma_d3_7.txt'),str(net),str(tasks),str(dest),
             str(seed),str(cfg['layout']),str(cfg['rate']),str(a.threads),'compensated','-']
        if not dest.exists():
            if a.dry:shutil.copyfile(src,dest)
            else:subprocess.run(cmd,check=True)
        old=json.load(open(src));new=json.load(open(dest))
        if new['seed']!=seed or new['mp_backend']!=old['mp_backend'] or new['rate']!=old['rate']:raise SystemExit('metadata mismatch '+str(dest))
        g=report['groups'].setdefault(f"{tag}:{rec['sector']}:L{rec['L']}",dict(quad_old=0,quad_new=0,mp_old=0,mp_new=0,cmd_example=' '.join(cmd)))
        for x,y in zip(old['rows'],new['rows'],strict=True):
            if any(x[k]!=y[k] for k in ('uid','rep','graph','begin','end','total')):raise SystemExit('task mismatch')
            g['quad_old']+=x['quad'];g['quad_new']+=y['quad'];g['mp_old']+=x['mp'];g['mp_new']+=y['mp']
            e=max(abs(D(u)-D(v))/max(D(1),abs(D(u))) for u,v in zip(x['values'],y['values'],strict=True))
            maxerr=max(maxerr,e);report['rows']+=1;report['bitwise_rows']+=x['values']==y['values']
# Rebuild per-replicate arrays exactly as reference/code/analyze.py:load_campaign does (longdouble row sums).
ar={s:{t:{} for t in ('a','b')} for s in ('free','power')}
for tag,t in zip(a.tags,('a','b')):
    man=json.load(open(R/'records'/tag/'manifest.json'));B=man['args']['replicates']
    for rec in man['records']:
        s,L=rec['sector'],rec['L'];arr=ar[s][t].setdefault(L,np.zeros((B,2*(8-L)),dtype=np.longdouble))
        for row in json.load(open(O/tag/Path(rec['file']).name))['rows']:arr[row['rep']]+=np.array(row['values'],dtype=np.longdouble)
for s in ar:
    for t in ar[s]:
        ar[s][t]={L:np.asarray(x,dtype=float) for L,x in ar[s][t].items()}
from assemble import calculate
r=calculate(ar,None,0);base=json.load(open(R/'verification/C7_full_result.json'))
report.update(max_normalized_difference=str(maxerr),C7_full=r['C7_full'],sampling_standard_error=r['sampling_standard_error'],
  power_correction=r['power_correction'],archived_C7_full=base['C7_full'],archived_se=base['sampling_standard_error'],
  abs_diff_C7=abs(r['C7_full']-base['C7_full']),abs_diff_se=abs(r['sampling_standard_error']-base['sampling_standard_error']))
fb=[k for k,g in report['groups'].items() if g['quad_old']!=g['quad_new'] or g['mp_old']!=g['mp_new']]
report['fallback_mismatch_groups']=fb
json.dump(report,open(O/'replay_report.json','w'),indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='groups'},indent=2))
