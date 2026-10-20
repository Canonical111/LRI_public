#!/usr/bin/env python3
"""Forced binary128 (level 1) and 300-digit (level 2) tiers: new worker versus original code on matched points.

Normal replays rarely or never reach the promoted tiers (mp_fallbacks=0 in every matched replay). Here both codes
are built in a temporary directory with promotion forced at the existing decision points:
  new:      src/ compiled with -DC6_FORCE_LEVEL=1 or =2 (test-only hook; production builds never define it);
  original: a COPY of reference/code/kernel.hpp whose two threshold tests are patched (each exactly once), compiled
            with a copy of reference/code/experiment.cpp. reference/ itself is never modified.
Every point must be counted at the forced level by both codes, and the jets must agree (normalized <= 1e-15).
The unforced production worker is compared on the same workload as a control.
"""
from __future__ import annotations
import argparse,json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from common import cxx_command,load
from production import make_net
B=ROOT/'reference/baseline_previous'
PATCH={1:[('ratio<1e-9L','(true||ratio<1e-9L)')],2:[('ratio<1e-9L','(true||ratio<1e-9L)'),('absT(q.first)<Q(1e-23L)*q.second','(true||absT(q.first)<Q(1e-23L)*q.second)')]}
TOL=1e-15

def call(cmd,env=None):
    cp=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,env=env)
    if cp.returncode:raise RuntimeError(cp.stderr[-3000:]+'\n'+cp.stdout[-800:])
    return cp

def build_original(td:Path,level:int)->Path:
    d=td/f'original_l{level}';d.mkdir()
    header=(ROOT/'reference/code/kernel.hpp').read_text()
    for old,new in PATCH.get(level,[]):
        if header.count(old)!=1:raise AssertionError(f'expected exactly one "{old}" in reference/code/kernel.hpp')
        header=header.replace(old,new)
    (d/'kernel.hpp').write_text(header)
    src=(ROOT/'reference/code/experiment.cpp').read_text()
    if src.count('num_threads(4)')!=1 or src.count('#include "kernel.hpp"')!=1:raise AssertionError('unexpected reference/code/experiment.cpp')
    (d/'experiment.cpp').write_text(src.replace('num_threads(4)','num_threads(omp_get_max_threads())'))  # includes the patched copy
    exe=d/'experiment';call(cxx_command([d/'experiment.cpp'],exe,defines=['SPATIAL_D=2']));return exe

def build_new(td:Path,level:int)->Path:
    exe=td/f'new_l{level}';call(cxx_command([ROOT/'src/c6_integrate.cpp'],exe,defines=[f'C6_FORCE_LEVEL={level}']));return exe

def workload(inv,L):
    rows=inv[str(L)];pick=[r['id']for r in rows[:2]]
    if L==6:pick+=[r['id']for r in sorted(rows,key=lambda r:(-r['additions'],r['id']))[:2]]
    return sorted(set(pick))

def compare(td:Path,L:int,ids:list[int],old_exe:Path,new_exe:Path,tag:str,points:int,threads:int):
    inv=load(ROOT/'inputs/inventory.json');allids=[r['id']for r in inv[str(L)]]
    net=td/f'net_{tag}_{L}';make_net(net,2,4*L-1,60,991207+L);seed=5501977
    cf=td/f'counts_{tag}_{L}';cf.write_text(f'{len(allids)}\n'+''.join(f'{i} {points if i in ids else 0}\n'for i in allids))
    rate=B/'inputs/d2_full_rates_c6.txt'if L==6 else B/f'baseline/lri_C6_d2_complete_update/reproduction/mom_rates_c{L}.txt'
    oldout=td/f'old_{tag}_{L}.json'
    call([old_exe,B/f'baseline/lri_C6_d3_complete_update/inputs/forest_L{L}.txt',rate,cf,seed,net,oldout,ROOT/'inputs/gamma_d2.txt','rqmc',0,0,1],dict(os.environ,OMP_NUM_THREADS=str(threads)))
    old=json.loads(oldout.read_text(),parse_float=str);idx={g:i for i,g in enumerate(old['graph_ids'])}
    rows=[(len(ids)*b+i,b,g,0,points,points)for b in range(2)for i,g in enumerate(ids)]
    tf=td/f'tasks_{tag}_{L}';tf.write_text(f'C6TASKS1 {L} {len(rows)}\n'+''.join(' '.join(map(str,r))+'\n'for r in rows));newout=td/f'new_{tag}_{L}.json'
    call([new_exe,ROOT/'inputs/graphs',ROOT/'inputs/gamma_d2.txt',net,tf,newout,seed,0,1,threads,'legacy','-'])
    new=load(newout);err=0.
    for r in new['rows']:
        a=np.array(old['graph_batches'][r['rep']][idx[r['graph']]],dtype=np.longdouble);b=np.array(r['values'],dtype=np.longdouble)
        err=max(err,float(np.max(abs(a-b)/np.maximum(1,abs(a)))))
    nq=sum(r['quad']for r in new['rows']);nm=sum(r['mp']for r in new['rows']);N=len(rows)*points
    return {'L':L,'graphs':ids,'points':N,'max_normalized_jet_difference':err,'original':{'quad':old['quad_fallbacks'],'mp':old['mp_fallbacks']},'new':{'quad':nq,'mp':nm}}

def run(points:int,threads:int):
    inv=load(ROOT/'inputs/inventory.json');out=[];t0=time.time()
    with tempfile.TemporaryDirectory(prefix='c6_levels_')as td:
        td=Path(td)
        for level in (1,2):
            old_exe,new_exe=build_original(td,level),build_new(td,level)
            for L in range(3,7):
                r=compare(td,L,workload(inv,L),old_exe,new_exe,f'l{level}',points,threads);r['forced_level']=level
                assert r['max_normalized_jet_difference']<=TOL,r
                assert r['original']['quad']==r['points']and r['new']['quad']==r['points'],r
                if level==2:assert r['original']['mp']==r['points']and r['new']['mp']==r['points'],r
                else:assert r['original']['mp']==r['new']['mp'],r
                out.append(r);print(r,flush=True)
        old_exe=build_original(td,0)
        for L in range(3,7):
            r=compare(td,L,workload(inv,L),old_exe,ROOT/'bin/c6_integrate',f'l0',points,threads);r['forced_level']=0
            assert r['max_normalized_jet_difference']<=TOL and r['original']==r['new'],r
            out.append(r);print(r,flush=True)
    return {'status':'passed','test':'forced_precision_tiers','tolerance':TOL,'records':out,'seconds':time.time()-t0}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--points',type=int,default=4);p.add_argument('--threads',type=int,default=4);a=p.parse_args()
    print(json.dumps(run(a.points,a.threads),indent=2))
