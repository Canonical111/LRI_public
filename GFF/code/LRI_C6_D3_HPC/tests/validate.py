#!/usr/bin/env python3
"""Matched-reference jets, Sobol random access, parallelism and input rejection."""
from __future__ import annotations
import argparse,ctypes,decimal,importlib.util,json,os,shutil,struct,subprocess,sys,tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from common import cxx_command,dump,digest,load
from production import make_net
from assemble import coefficients

def call(cmd,env=None):
    cp=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,env=env)
    if cp.returncode:raise RuntimeError(cp.stderr[-4000:]+'\n'+cp.stdout[-1000:])
    return cp

def build_baseline(path):
    src=(ROOT/'reference/code/experiment.cpp').read_text().replace('num_threads(4)','num_threads(omp_get_max_threads())').replace('#include "kernel.hpp"',f'#include "{ROOT}/reference/code/kernel.hpp"')
    path.with_suffix('.cpp').write_text(src)
    call(cxx_command([path.with_suffix('.cpp')],path,defines=['SPATIAL_D=3']))

def scientific(r):return {k:v for k,v in r.items()if k!='seconds'}
def run(td:Path):
    baseline=td/'baseline';build_baseline(baseline);inv=load(ROOT/'inputs/inventory.json');B=ROOT/'reference/baseline_previous';tests=[]
    for L in range(3,7):
        ids=[r['id']for r in inv[str(L)]];n=64;cp=td/f'counts{L}';cp.write_text(str(len(ids))+'\n'+''.join(f'{i} {n}\n'for i in ids))
        net=td/f'net{L}';make_net(net,2,4*L-1,60,828193+L);oldout=td/f'old{L}.json';seed=8710912
        rate=B/f'baseline/lri_C6_d3_complete_update/inputs/rates_L{L}_0.8.txt'
        basecmd=[baseline,B/f'baseline/lri_C6_d3_complete_update/inputs/forest_L{L}.txt',rate,cp,seed,net,oldout,ROOT/'inputs/gamma_d3.txt','rqmc',0,0,1]
        call(basecmd,dict(os.environ,OMP_NUM_THREADS='2'));old=json.loads(oldout.read_text(),parse_float=str)
        rows=[(len(ids)*b+i,b,g,0,n,n)for b in range(2)for i,g in enumerate(ids)]
        tp=td/f'tasks{L}';tp.write_text(f'C6TASKS3D1 {L} {len(rows)}\n'+''.join(' '.join(map(str,r))+'\n'for r in rows));out=td/f'new{L}.json'
        cmd=[ROOT/'bin/c6_integrate',ROOT/'inputs/graphs',ROOT/'inputs/gamma_d3.txt',net,tp,out,seed,0,1,2,'legacy','-'];call(cmd);new=load(out);idx={g:i for i,g in enumerate(ids)}
        error=0
        for r in new['rows']:
            a=np.array(old['graph_batches'][r['rep']][idx[r['graph']]],dtype=np.longdouble);b=np.array(r['values'],dtype=np.longdouble);error=max(error,float(max(abs(a-b)/np.maximum(1,abs(a)))))
        assert error<1e-15,(L,error)
        assert old['quad_fallbacks']==sum(r['quad']for r in new['rows']);assert old['mp_fallbacks']==sum(r['mp']for r in new['rows'])
        tests.append({'test':'all_graph_reference_replay','L':L,'graphs':len(ids),'samples':n*2*len(ids),'max_normalized_jet_difference':error,'quad_fallbacks':old['quad_fallbacks'],'mp_fallbacks':old['mp_fallbacks']})
        # Arbitrary, non-power-of-two execution chunks still reconstruct the full net.
        split=[]
        for b in range(2):
            for g in ids:
                for st in range(0,n,23):split.append((len(split),b,g,st,min(n,st+23),n))
        tp.write_text(f'C6TASKS3D1 {L} {len(split)}\n'+''.join(' '.join(map(str,r))+'\n'for r in split));cmd[10]='compensated';cmd[9]=4;call(cmd);parts=load(out);acc={}
        for r in parts['rows']:
            key=(r['rep'],r['graph']);acc.setdefault(key,np.zeros(2*(7-L),dtype=np.longdouble));acc[key]+=np.array(r['values'],dtype=np.longdouble)
        error2=0
        for r in new['rows']:
            a=np.array(r['values'],dtype=np.longdouble);b=acc[(r['rep'],r['graph'])];error2=max(error2,float(max(abs(a-b)/np.maximum(1,abs(a)))))
        assert error2<1e-14,(L,error2)
        cmd[9]=1;call(cmd);single=load(out)
        assert [scientific(r)for r in single['rows']]==[scientific(r)for r in parts['rows']]
        tests.append({'test':'random_access_and_threads','L':L,'chunk_size':23,'max_normalized_split_difference':error2,'identical_thread_outputs':True,'threads':[1,4]})
    # Frozen grid at L=6: same point transform and no endpoint renormalization.
    L=6;net=td/'gridnet';make_net(net,2,23,52,81725);selected={r['id']for r in inv['6'][:16]};cp=td/'gridcounts';cp.write_text(str(len(inv['6']))+'\n'+''.join(f'{r["id"]} {64 if r["id"] in selected else 0}\n'for r in inv['6']))
    oldout=td/'gridold.json';basecmd=[baseline,B/'baseline/lri_C6_d3_complete_update/inputs/forest_L6.txt',B/'baseline/lri_C6_d3_complete_update/inputs/rates_L6_0.8.txt',cp,seed,net,oldout,ROOT/'inputs/gamma_d3.txt','rqmc',0,0,1]
    call(basecmd,dict(os.environ,OMP_NUM_THREADS='2',GRID_FILE=str(ROOT/'inputs/grid_d3_top11.txt')));old=json.loads(oldout.read_text(),parse_float=str)
    rows=[(len(selected)*b+i,b,g,0,64,64)for b in range(2)for i,g in enumerate(sorted(selected))];tp=td/'gridtasks';tp.write_text(f'C6TASKS3D1 6 {len(rows)}\n'+''.join(' '.join(map(str,r))+'\n'for r in rows));out=td/'gridnew.json';cmd=[ROOT/'bin/c6_integrate',ROOT/'inputs/graphs',ROOT/'inputs/gamma_d3.txt',net,tp,out,seed,0,1,2,'legacy',ROOT/'inputs/grid_d3_top11.txt'];call(cmd);new=load(out);idx={g:i for i,g in enumerate(old['graph_ids'])};er=0
    for r in new['rows']:
        a=np.array(old['graph_batches'][r['rep']][idx[r['graph']]],dtype=np.longdouble);b=np.array(r['values'],dtype=np.longdouble);er=max(er,float(max(abs(a-b)/np.maximum(1,abs(a)))))
    assert er<1e-14;tests.append({'test':'frozen_grid_replay','max_normalized_difference':er})
    # Metadata/dimension and wrong coverage fail closed at the native boundary.
    valid=tp.read_text();bad=['C6TASKS3D1 6 1\n0 0 159 0 64 63\n','C6TASKS3D1 6 1\n0 100 159 0 64 64\n','C6TASKS3D1 6 2\n0 0 159 0 64 64\n0 0 159 0 64 64\n']
    for text in bad:
        tp.write_text(text);rc=subprocess.run(list(map(str,cmd)),capture_output=True).returncode;assert rc!=0
    tp.write_text(valid);tests.append({'test':'invalid_native_inputs_rejected','cases':len(bad)})
    # Standalone fixed-point implementation vs untouched archived implementation.
    path=B/'baseline/lri_C6_d3_complete_update/code/analyze_d3.py';spec=importlib.util.spec_from_file_location('original_assembly',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rng=np.random.default_rng(827411)
    for _ in range(64):
        means={L:rng.normal(size=2*(7-L))for L in range(3,7)};assert np.array_equal(coefficients(means),module.coefficients(means))
    tests.append({'test':'fixed_point_reference_agreement','cases':64,'identical':True})
    return tests
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='c6_validate_')as td:results=run(Path(td))
    record={'status':'passed','tests':results}
    if a.output:dump(a.output,record)  # optional record; the shipped benchmarks/ evidence is never rewritten
    print(json.dumps(record,indent=2))
