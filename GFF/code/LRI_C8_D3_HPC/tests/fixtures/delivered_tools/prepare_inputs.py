#!/usr/bin/env python3
"""Pack original d=3 payloads; rebuild (never reuse) legacy d=2 offsets/hashes.

Immutable reference data are retained byte-for-byte. The old inventory supplies
only graph IDs and primitive flags. Allocation is from the d=3 frozen pilot.
"""
from pathlib import Path
import hashlib,json,shutil
from common import ROOT,load,dump,digest,pow2

def prepare():
    p=ROOT/'inputs';mf=p/'manifest.json'
    if mf.exists():
        d=load(mf)
        if d.get('schema')!='c7-d3-hpc-inputs-1' or d.get('dimension')!=3:raise ValueError('Wrong input manifest')
        return d
    p.mkdir(exist_ok=True);(p/'packs').mkdir(exist_ok=True)
    ref=ROOT/'reference';old=load(ref/'inputs/inventory.json');alloc=load(ref/'inputs/allocation.json');out={};hashes={}
    for name in ('two_loop.json','gamma_d3_7.txt'):
        shutil.copyfile(ref/'inputs'/name,p/name);hashes[name]=digest(p/name)
    if load(p/'two_loop.json')['dimension']!=3:raise ValueError('Wrong low-loop dimension')
    primitive=load(ref/'verification/primitive_checks.json')
    dump(p/'primitive_reference.json',{'mean':primitive['primitive_mean'],'sampling_se':primitive['primitive_sampling_se'],
      'source':'reference/verification/primitive_checks.json','source_sha256':digest(ref/'verification/primitive_checks.json'),
      'dimension':3,'order':7,'scope':'Only seven-loop primitive contribution. Independent of fresh campaigns; add once ONLY in retained mode.'})
    hashes['primitive_reference.json']=digest(p/'primitive_reference.json')
    for sector in ('free','power'):
        out[sector]={}
        for L in range(3,8):
            target=p/f'packs/{sector}_L{L}.pack';rows=[];seen=set()
            with target.open('xb') as f:
                for g in old[sector][str(L)]:
                    gi=g['id']
                    if gi in seen:raise ValueError('Duplicate graph ID')
                    seen.add(gi);src=ref/f'inputs/{sector}/L{L}/G{gi}.txt';payload=src.read_bytes()
                    h=payload.splitlines()[0].decode().split()
                    if h[0]!='C7D3GRAPH1' or int(h[1])!=L or int(h[2])!=gi:raise ValueError('Wrong graph identity')
                    n=int(alloc[sector][str(L)][str(gi)])
                    if not pow2(n):raise ValueError('Invalid allocation count')
                    rows.append(dict(id=gi,primitive=bool(g.get('primitive',False)),offset=f.tell(),length=len(payload),
                      sha256=hashlib.sha256(payload).hexdigest(),cost=max(1,int(h[-1])*int(h[-2])),monomials=int(h[-2]),terms=int(h[-1]),points=n))
                    f.write(payload)
            out[sector][str(L)]=rows;hashes[f'packs/{sector}_L{L}.pack']=digest(target)
    dump(p/'inventory.json',out);hashes['inventory.json']=digest(p/'inventory.json')
    doc=dict(schema='c7-d3-hpc-inputs-1',dimension=3,order=7,epsilon='2s-3',sha256=hashes,
       counts={s:{l:len(v)for l,v in ls.items()}for s,ls in out.items()},
       reference_manifest_sha256=digest(ref/'DELIVERY_MANIFEST.json'),
       reference_allocation_sha256=digest(ref/'inputs/allocation.json'),legacy_offsets_reused=False)
    dump(mf,doc);return doc
if __name__=='__main__':print(json.dumps(prepare(),indent=2))
