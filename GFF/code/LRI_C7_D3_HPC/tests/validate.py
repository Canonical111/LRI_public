#!/usr/bin/env python3
"""Original-versus-optimized kernels, random-access streams and jet assembly."""
from pathlib import Path
import argparse,importlib.util,json,os,struct,subprocess,sys,tempfile
from decimal import Decimal as D
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from common import load,dump,digest
from production import make_net
from assemble import coefficients,jacobians

def run(cmd):
    p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True)
    if p.returncode:raise RuntimeError(p.stderr[-3000:])
    return p

def scientific(r):return {k:v for k,v in r.items()if k!='seconds'}

def tests(td,full=False):
    from benchmark import build_reference
    baseline=td/'baseline';build_reference(baseline);tests=[];backend_exes={'gmp':ROOT/'bin/c7d3_gmp'}
    if (ROOT/'bin/c7d3_decimal').exists():backend_exes['decimal']=ROOT/'bin/c7d3_decimal'
    if (ROOT/'bin/c7d3_gmp').exists():backend_exes['gmp']=ROOT/'bin/c7d3_gmp'
    inv=load(ROOT/'inputs/inventory.json');total=0
    for sector in ('free','power'):
      source=ROOT/'reference/inputs'/sector
      for L in range(3,8):
        ids=[r['id']for r in inv[sector][str(L)]]
        if not full:ids=sorted(set(ids[:8]+[r['id']for r in sorted(inv[sector][str(L)],key=lambda r:-r['cost'])[:8]]))
        n=8 if full else 32;net=td/f'{sector}{L}.net';make_net(net,2,4*L-1,60,983507+L+(11255 if sector=='power'else 0));errors={b:D(0)for b in backend_exes};fallbacks=0
        for off in range(0,len(ids),24):
            chosen=ids[off:off+24];rows=[(i,r,g,0,n,n)for i,(r,g)in enumerate((r,g)for r in range(2)for g in chosen)];tasks=td/'tasks';tasks.write_text(f'C7D3TASKS1 {L} {len(rows)}\n'+''.join(' '.join(map(str,r))+'\n'for r in rows));out=td/'out.json'
            base=[baseline,source,ROOT/'inputs/gamma_d3_7.txt',net,tasks,out,7738251,0,.8,1,'compensated','-'];run(base);ref=load(out);fallbacks+=sum(r['mp']for r in ref['rows'])
            for b,exe in backend_exes.items():
                cmd=base.copy();cmd[0]=exe;run(cmd);new=load(out)
                for x,y in zip(ref['rows'],new['rows']):
                    if x['quad']!=y['quad']or x['mp']!=y['mp']:raise AssertionError('Changed promotion count')
                    for u,v in zip(x['values'],y['values']):errors[b]=max(errors[b],abs(D(u)-D(v))/max(D(1),abs(D(u))))
            total+=len(chosen)
        for b,e in errors.items():
            if e>D('1e-13'):raise AssertionError((sector,L,b,e))
        tests.append(dict(test='matched_all_graphs'if full else'matched_graph_subset',sector=sector,L=L,graphs=len(ids),samples=2*n*len(ids),max_normalized_difference={b:str(v)for b,v in errors.items()},fallbacks_match=True,mp_calls=fallbacks));print(tests[-1],flush=True)
    # Arbitrary chunks, different layouts and worker counts reconstruct one net.
    for sector in ('free','power'):
      L=7;source=ROOT/'reference/inputs'/sector
      ids=[r['id']for r in sorted(inv[sector]['7'],key=lambda r:-r['cost'])[:3]];n=64;exe=backend_exes.get('gmp') or backend_exes['decimal']
      for layout in (0,1,2):
        net=td/f'split{sector}{layout}.net';make_net(net,2,2*L if layout==2 else 4*L-1,52,273845+layout)
        tasks=td/'tasks';out=td/'split.json';cmd=[exe,source,ROOT/'inputs/gamma_d3_7.txt',net,tasks,out,741987,layout,.9,1,'compensated','-']
        rows=[(i,r,g,0,n,n)for i,(r,g)in enumerate((r,g)for r in range(2)for g in ids)]
        def wt(rs):tasks.write_text(f'C7D3TASKS1 {L} {len(rs)}\n'+''.join(' '.join(map(str,r))+'\n'for r in rs))
        wt(rows);run(cmd);whole=load(out)
        split=[(i,r,g,start,min(n,start+23),n)for i,(r,g,start)in enumerate((r,g,st)for r in range(2)for g in ids for st in range(0,n,23))];wt(split);cmd[9]=4;run(cmd);many=load(out);cmd[9]=1;run(cmd);one=load(out)
        if [scientific(r)for r in many['rows']]!=[scientific(r)for r in one['rows']]:raise AssertionError('Thread dependent result')
        sums={}
        for r in one['rows']:
            key=(r['rep'],r['graph']);sums[key]=[a+D(v)for a,v in zip(sums.get(key,[D(0),D(0)]),r['values'])]
        e=max(abs(D(v)-z)/max(D(1),abs(D(v)))for r in whole['rows']for v,z in zip(r['values'],sums[(r['rep'],r['graph'])]))
        if e>D('1e-12'):raise AssertionError(('split',e))
        tests.append(dict(test='random_access_threads',sector=sector,layout=layout,max_normalized_difference=str(e),threads=[1,4],chunk_size=23))
    # Exact equality to original floating fixed-point routine on synthetic jets.
    spec=importlib.util.spec_from_file_location('ref_analyze',ROOT/'reference/code/analyze.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);rng=np.random.default_rng(51892)
    for _ in range(96):
        vals={L:rng.normal(size=2*(8-L))for L in range(3,8)}
        if not np.array_equal(coefficients(vals),module.coefficients(vals)):raise AssertionError('Assembly changed')
        if any(not np.array_equal(v,module.jacobians(vals)[L])for L,v in jacobians(vals).items()):raise AssertionError('Jacobian changed')
    tests.append(dict(test='assembly_reference',cases=96,identical=True))
    return dict(status='passed',full_inventory=full,total_graphs=total,tests=tests,normalized_tolerance='1e-13 graph replay; 1e-12 random access, |x-y|/max(1,|x|)')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--full',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='c7d3_validate_')as td:result=tests(Path(td),a.full)
    dest=a.output or ROOT/'benchmarks'/('full_validation.json'if a.full else'validation.json')
    if dest.exists():print(json.dumps(result,indent=2))
    else:dump(dest,result)
