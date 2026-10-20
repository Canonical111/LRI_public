#!/usr/bin/env python3
"""Extract immutable per-graph work inputs, without altering original evidence.

prepare() verifies an existing inputs/ tree against its manifest. prepare(dest) on a new directory regenerates the
complete tree from reference/ (tests/check_inputs.py requires byte identity with the shipped inputs/).
"""
from __future__ import annotations
import json,shutil,sys
from pathlib import Path
from common import ROOT,digest,dump,load
from primitive_allocation import PIDS as _PRIMITIVES,build_table
PIDS=set(_PRIMITIVES)
SCHEMA='c6-d2-inputs-2'
def verify(dest:Path)->dict:
    m=load(dest/'manifest.json')
    if m.get('schema')!=SCHEMA:raise ValueError('inputs manifest schema '+str(m.get('schema'))+' is not '+SCHEMA)
    for name,h in m['sha256'].items():
        if digest(dest/name)!=h:raise ValueError('Changed prepared input: '+name)
    return m
def prepare(dest:Path=ROOT/'inputs'):
    R=ROOT/'reference';B=R/'baseline_previous';manifest=dest/'manifest.json'
    if manifest.exists():return verify(dest)
    inventory={};sources={}
    def source(p:Path)->Path:sources[str(p.relative_to(ROOT))]=digest(p);return p
    for L in range(3,7):
        f=source(B/f'baseline/lri_C6_d3_complete_update/inputs/forest_L{L}.txt')
        r=source(B/f'inputs/d2_full_rates_c6.txt' if L==6 else B/f'baseline/lri_C6_d2_complete_update/reproduction/mom_rates_c{L}.txt')
        it=iter(r.read_text().split());nr=int(next(it));rates={}
        for _ in range(nr):
            id,n=int(next(it)),int(next(it));rates[id]=[next(it)for j in range(n)]
        if next(it,None)is not None:raise ValueError('extra rates')
        it=iter(f.read_text().split());l,n=int(next(it)),int(next(it));assert l==L;rows=[]
        d=dest/f'graphs/L{L}';d.mkdir(parents=True,exist_ok=True)
        for _ in range(n):
            gi=int(next(it));wa,wb=next(it),next(it);M,T=int(next(it)),int(next(it));edges=[next(it)for j in range(4*L)];masks=[next(it)for j in range(M)]
            assert all(int(m).bit_count()==L for m in masks)
            lines=[f'C6GRAPH1 {L} {gi} {wa} {wb} {M} {T}',' '.join(masks)]
            additions=0
            for j in range(T):
                z=int(next(it));ids=[next(it)for k in range(z)];co=[next(it)for k in range(2*L)];additions+=z
                assert all(0<=int(i)<M for i in ids);lines.append(' '.join([str(z)]+ids+co))
            a=rates[gi];assert len(a)==1<<(2*L);lines.extend([str(len(a)),' '.join(a)])
            p=d/f'G{gi}.txt';p.write_text('\n'.join(lines)+'\n');rows.append(dict(id=gi,wa=wa,wb=wb,masks=M,terms=T,additions=additions,primitive=(L==6 and gi in PIDS),file=str(p.relative_to(dest)),sha256=digest(p)))
        if next(it,None)is not None:raise ValueError('extra graph data')
        assert len({x['id']for x in rows})==n;inventory[str(L)]=rows
        shutil.copyfile(source(R/f'inputs/frozen_d2_L{L}.json'),dest/f'counts_L{L}.json')
    shutil.copyfile(source(B/'inputs/gamma_d2.txt'),dest/'gamma_d2.txt')
    shutil.copyfile(source(R/'inputs/grid_d2_top11.txt'),dest/'grid_d2_top11.txt')
    ks=source(B/'baseline/lri_C6_d2_complete_update/reproduction/mom_known_sectors.json');known=load(ks)
    dump(dest/'primitive_reference.json',{'ids':sorted(PIDS),'mean':known['group_means'][0],'sampling_se':known['group_sampling_ses'][0],'quantity':'additive six-loop finite-MOM contribution to C6; not a standalone physical coefficient','source':str(ks.relative_to(ROOT)),'source_sha256':digest(ks)})
    tl=source(B/'baseline/lri_C6_d2_complete_update/reproduction/lri_C6_d2_two_forest_update/analytic/verification/two_loop_extended_reference.json');ref=load(tl)
    vals=ref['dimensions']['2']['A2'];dump(dest/'two_loop.json',{'B2':[-2*float(vals[str(i-1)])for i in range(5)],'A2_exact_record':vals,'normalization':'finite MOM regulator-dependent b2; c2=b2/6','source':str(tl.relative_to(ROOT)),'source_sha256':digest(tl)})
    table=build_table(inventory['6']);sources.update(table['sources']);dump(dest/'primitive_allocation_d2.json',table)
    dump(dest/'inventory.json',inventory)
    m={'schema':SCHEMA,'sources':dict(sorted(sources.items())),'sha256':{str(p.relative_to(dest)):digest(p)for p in sorted(dest.rglob('*'))if p.is_file()},'graph_counts':{l:len(rows)for l,rows in inventory.items()},'loops':list(range(3,7)),'dimension':2}
    dump(manifest,m);return m
if __name__=='__main__':
    dest=Path(sys.argv[1]).resolve()if len(sys.argv)>1 else ROOT/'inputs'
    print(json.dumps(prepare(dest)['graph_counts']))
