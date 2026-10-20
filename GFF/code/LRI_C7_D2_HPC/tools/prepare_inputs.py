#!/usr/bin/env python3
"""Pack immutable reference kernels for indexed node-local block staging.

Reference graph text is not altered. Packed payloads reduce shared-filesystem
metadata operations; a run only reads and hashes the graph members it needs.
"""
from pathlib import Path
import json,sys,shutil
from common import ROOT,load,dump,digest


def prepare():
    p=ROOT/'inputs'
    if (p/'manifest.json').exists():
        return load(p/'manifest.json')
    p.mkdir(exist_ok=True);(p/'packs').mkdir(exist_ok=True)
    ref=ROOT/'reference';old=ref/'LRI_C7_d2_progress';allinv={};hashes={}
    for name in ('two_loop.json','gamma_d2_7.txt'):
        shutil.copyfile(old/'inputs'/name,p/name);hashes[name]=digest(p/name)
    reference=load(ref/'verification/C7_full_result.json')['primitive']
    # Final reference uses se, not sampling_se; retain complete record.
    dump(p/'primitive_reference.json',{'mean':reference['mean'],'sampling_se':reference['se'],
      'source':'reference/verification/C7_full_result.json','source_sha256':digest(ref/'verification/C7_full_result.json'),
      'scope':'Only seven-loop primitive contribution. Never add in recompute mode.'})
    hashes['primitive_reference.json']=digest(p/'primitive_reference.json')
    for sector,source in [('free',old),('power',ref/'power_mass')]:
        allocation=load(source/'inputs'/('allocation.json'if sector=='free'else'production_plan.json'))
        if sector=='power':allocation=allocation['allocations']
        allinv[sector]={}
        for L in range(3,8):
            inventory=load(source/f'inputs/L{L}/inventory.json');target=p/f'packs/{sector}_L{L}.pack';rows=[]
            with target.open('wb')as f:
                for g in inventory:
                    if g['status']!='finite-kernel' or (L==7 and g['mass_numerator']==4):continue
                    src=source/f'inputs/L{L}/G{g["id"]}.txt';payload=src.read_bytes();offset=f.tell();f.write(payload)
                    h=payload.splitlines()[0].decode().split()
                    rows.append(dict(id=g['id'],primitive=bool(g.get('primitive',False)),offset=offset,length=len(payload),sha256=digest(src),
                       cost=max(1,int(h[-1])*int(h[-2])),monomials=int(h[-2]),terms=int(h[-1]),
                       points=int(allocation.get(str(L),{}).get(str(g['id']),0))))
            allinv[sector][str(L)]=rows
            hashes[f'packs/{sector}_L{L}.pack']=digest(target)
    dump(p/'inventory.json',allinv);hashes['inventory.json']=digest(p/'inventory.json')
    doc={'schema':'c7-d2-hpc-inputs-1','dimension':2,'order':7,'epsilon':'2s-2','sha256':hashes,
         'counts':{s:{l:len(v)for l,v in loops.items()}for s,loops in allinv.items()},
         'reference_manifest_sha256':digest(ref/'SHA256SUMS')}
    dump(p/'manifest.json',doc);return doc
if __name__=='__main__':print(json.dumps(prepare(),indent=2))
