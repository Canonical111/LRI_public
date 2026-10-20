#!/usr/bin/env python3
"""Pack complete d=2 forest inputs for order eight, with an audited coverage map.

Regenerate raw inputs with generator/ first. Every finite L3--L7 graph is kept;
only at L8 can the exact top-channel identity s_G=4 exclude a graph.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from common import ROOT, digest, dump, load, read_verified

COUNTS={3:8,4:27,5:129,6:660,7:3986,8:26540}
SCHEMA='c8-d2-hpc-inputs-1'


def prepare(dest:Path|None=None):
    p=ROOT/'inputs' if dest is None else Path(dest)
    if (p/'manifest.json').exists():
        return load(p/'manifest.json')
    p.mkdir(parents=True,exist_ok=True)
    (p/'packs').mkdir(exist_ok=True)
    for name in ('two_loop.json','gamma_d2_8.txt'):
        if not (p/name).is_file():
            raise FileNotFoundError(f'Run tools/analytic_inputs.py first: missing {p/name}')
    b2=load(p/'two_loop.json')['B2']
    if len(b2)!=7:
        raise ValueError('C8 requires the two-loop jet through z^6, seven coefficients')
    raw=p/'raw'
    inv={s:{} for s in ('free','power')}
    coverage={}
    hashes={n:digest(p/n) for n in ('two_loop.json','gamma_d2_8.txt')}
    for L,number in COUNTS.items():
        sources={s:load(raw/s/f'L{L}/inventory.json') for s in inv}
        for s,rows in sources.items():
            if len(rows)!=number or {g['id'] for g in rows}!=set(range(number)):
                raise ValueError(f'Incomplete or duplicate {s} L{L} canonical inventory')
            sources[s]={g['id']:g for g in rows}
        for gid in range(number):
            f,pw=(sources[s][gid] for s in ('free','power'))
            for key in ('key','mass_numerator','denominator','power_subgraphs','log_subgraphs','primitive'):
                if str(f[key])!=str(pw[key]):
                    raise ValueError(f'Sector identity mismatch at L{L} G{gid}: {key}')
            ispower=bool(f['power_subgraphs'])
            inactive='free' if ispower else 'power'
            active='power' if ispower else 'free'
            if sources[active][gid]['status'] not in ('finite-kernel','exact-zero-kernel'):
                raise ValueError(f'Unresolved active forest kernel: {active} L{L} G{gid}')
            if sources[inactive][gid]['status']=='finite-kernel':
                raise ValueError(f'Graph assigned to both sectors: L{L} G{gid}')
        summary={'all_classes':number,'sectors':{}}
        for sector in inv:
            target=p/f'packs/{sector}_L{L}.pack'
            rows=[]
            finite=zero=excluded=primitive=0
            with target.open('wb') as out:
                for gid,g in sorted(sources[sector].items()):
                    status=g['status']
                    if status=='exact-zero-kernel':zero+=1
                    if status!='finite-kernel':continue
                    finite+=1
                    if L==8 and g['mass_numerator']==4:
                        excluded+=1
                        continue
                    src=raw/sector/f'L{L}/G{gid}.txt'
                    payload=src.read_bytes()
                    h=payload.splitlines()[0].decode().split()
                    if h[0] not in ('C7D2GRAPH1','C8D2GRAPH1') or int(h[1])!=L or int(h[2])!=gid:
                        raise ValueError(f'Graph header mismatch: {src}')
                    if L==8 and h[0]!='C8D2GRAPH1':
                        raise ValueError('L8 graphs require their own schema')
                    offset=out.tell();out.write(payload)
                    primitive+=bool(g.get('primitive'))
                    rows.append({'id':gid,'primitive':bool(g.get('primitive',False)),
                                 'mass_numerator':g['mass_numerator'],'denominator':g['denominator'],
                                 'offset':offset,'length':len(payload),'sha256':digest(src),
                                 'cost':max(1,int(h[-1])*int(h[-2])),
                                 'monomials':int(h[-2]),'terms':int(h[-1]),'points':4096})
            inv[sector][str(L)]=rows
            hashes[str(target.relative_to(p))]=digest(target)
            summary['sectors'][sector]={'finite_kernels':finite,'exact_zero_kernels':zero,
                                       'excluded_top_channel':excluded,'integrated':len(rows),
                                       'integrated_primitives':primitive,
                                       'raw_inventory_sha256':digest(raw/sector/f'L{L}/inventory.json')}
        coverage[str(L)]=summary
    if len(inv['free']['7'])!=2441 or len(inv['power']['7'])!=709:
        raise ValueError('All 3150 finite seven-loop kernels must be restored for C8')
    if sum(r['primitive'] for r in inv['free']['8'])!=248:
        raise ValueError('Expected all 248 eight-loop primitive classes')
    dump(p/'inventory.json',inv)
    hashes['inventory.json']=digest(p/'inventory.json')
    dump(p/'coverage.json',coverage)
    hashes['coverage.json']=digest(p/'coverage.json')
    m={'schema':SCHEMA,'dimension':2,'order':8,'epsilon':'2s-2','sha256':hashes,
       'counts':{s:{l:len(rows) for l,rows in groups.items()} for s,groups in inv.items()},
       'graph_coverage':'All finite L3--L7 jets; all L8 finite kernels with nonzero exact top channel',
       'regulator_orders':{str(L):8-L for L in range(2,9)},
       'allocation_note':'4096 per graph is an untrained default; use an independent pilot to choose production counts.'}
    dump(p/'manifest.json',m)
    return m


def verify(folder:Path|None=None,expected_manifest_sha256:str|None=None):
    p=ROOT/'inputs' if folder is None else Path(folder)
    m=read_verified(p/'manifest.json',expected_manifest_sha256) if expected_manifest_sha256 else load(p/'manifest.json')
    if m.get('schema')!=SCHEMA or m.get('dimension')!=2 or m.get('order')!=8:
        raise ValueError('Not a complete C8(2) input manifest')
    for name,h in m['sha256'].items():
        q=p/name
        if not q.is_file() or digest(q)!=h:
            raise ValueError(f'Input checksum mismatch: {name}')
    return m


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--verify',action='store_true')
    args=ap.parse_args()
    print(json.dumps(verify() if args.verify else prepare(),indent=2))
