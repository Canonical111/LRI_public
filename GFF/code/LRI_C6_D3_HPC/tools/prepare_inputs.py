#!/usr/bin/env python3
"""Extract immutable per-graph work inputs, without altering original evidence.

prepare() verifies an existing inputs/ tree against its manifest. prepare(dest) on a new directory regenerates the
complete tree from reference/ (tests/check_inputs.py requires byte identity with the shipped inputs/).
"""
from __future__ import annotations
import json,shutil,sys
from pathlib import Path
from common import ROOT,digest,dump,load
PIDS={639,648,649,651,653,654,655,657,658,659}
SCHEMA='c6-d3-inputs-1'
def verify(dest:Path)->dict:
    m=load(dest/'manifest.json')
    if m.get('dimension')!=3 or m.get('schema')!=SCHEMA:raise ValueError('not d=3 prepared inputs')
    for name,h in m['sha256'].items():
        if digest(dest/name)!=h:raise ValueError('Changed prepared input: '+name)
    return m
def prepare(dest:Path=ROOT/'inputs'):
    R=ROOT/'reference';B=R/'baseline_previous';manifest=dest/'manifest.json'
    if manifest.exists():return verify(dest)
    inventory={};sources={}
    for L in range(3,7):
        f=B/f'baseline/lri_C6_d3_complete_update/inputs/forest_L{L}.txt'
        r=B/f'baseline/lri_C6_d3_complete_update/inputs/rates_L{L}_0.8.txt'
        sources[str(f.relative_to(ROOT))]=digest(f);sources[str(r.relative_to(ROOT))]=digest(r)
        it=iter(r.read_text().split());nr=int(next(it));rates={}
        for _ in range(nr):
            id,n=int(next(it)),int(next(it));rates[id]=[next(it)for j in range(n)]
        if next(it,None)is not None:raise ValueError('extra rates')
        it=iter(f.read_text().split());l,n=int(next(it)),int(next(it));assert l==L;rows=[]
        d=dest/f'graphs/L{L}';d.mkdir(parents=True,exist_ok=True)
        for _ in range(n):
            gi=int(next(it));wa,wb=next(it),next(it);M,T=int(next(it)),int(next(it));edges=[next(it)for j in range(4*L)];masks=[next(it)for j in range(M)]
            assert all(int(m).bit_count()==L for m in masks)
            lines=[f'C6GRAPH3D1 {L} {gi} {wa} {wb} {M} {T}',' '.join(masks)]
            additions=0
            for j in range(T):
                z=int(next(it));ids=[next(it)for k in range(z)];co=[next(it)for k in range(2*L)];additions+=z
                assert all(0<=int(i)<M for i in ids);lines.append(' '.join([str(z)]+ids+co))
            a=rates[gi];assert len(a)==1<<(2*L);lines.extend([str(len(a)),' '.join(a)])
            p=d/f'G{gi}.txt';p.write_text('\n'.join(lines)+'\n');rows.append(dict(id=gi,wa=wa,wb=wb,masks=M,terms=T,additions=additions,primitive=(L==6 and gi in PIDS),file=str(p.relative_to(dest)),sha256=digest(p)))
        if next(it,None)is not None:raise ValueError('extra graph data')
        assert len({x['id']for x in rows})==n;inventory[str(L)]=rows
        if L>=3:
            cp=R/f'inputs/frozen_d3_L{L}.json'
            if load(cp).get('dimension')!=3:raise ValueError('wrong-dimensional frozen allocation')
            sources[str(cp.relative_to(ROOT))]=digest(cp)
            shutil.copyfile(cp,dest/f'counts_L{L}.json')
    sources[str((B/'inputs/gamma_d3.txt').relative_to(ROOT))]=digest(B/'inputs/gamma_d3.txt')
    shutil.copyfile(B/'inputs/gamma_d3.txt',dest/'gamma_d3.txt')
    sources[str((R/'inputs/grid_d3_top11.txt').relative_to(ROOT))]=digest(R/'inputs/grid_d3_top11.txt')
    shutil.copyfile(R/'inputs/grid_d3_top11.txt',dest/'grid_d3_top11.txt')
    refpath=B/'baseline/lri_C6_d3_complete_update/records/two_loop_d3.json'
    ref=load(refpath)
    vals=ref['records'][0]['b2_jets']
    dump(dest/'two_loop.json',{'dimension':3,'B2':[float(v) for v in vals],
        'B2_decimal':vals,'normalization':'finite MOM regulator-dependent b2; c2=b2/6',
        'source':str(refpath.relative_to(ROOT)), 'source_sha256':digest(refpath)})
    sources[str(refpath.relative_to(ROOT))]=digest(refpath)
    dump(dest/'inventory.json',inventory)
    m={'schema':SCHEMA,'sources':sources,'sha256':{str(p.relative_to(dest)):digest(p)for p in sorted(dest.rglob('*'))if p.is_file()},'graph_counts':{l:len(rows)for l,rows in inventory.items()},'loops':list(range(3,7)),'dimension':3}
    dump(manifest,m);return m
if __name__=='__main__':
    dest=Path(sys.argv[1]).resolve()if len(sys.argv)>1 else ROOT/'inputs'
    print(json.dumps(prepare(dest)['graph_counts']))
