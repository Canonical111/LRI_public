"""Reproducible small actual-graph workloads; not a random performance survey."""
from __future__ import annotations
import json, struct
from pathlib import Path
from campaign import inventory

def select(inputs:Path,L:int,mode:str,count:int=12):
    rows=inventory(inputs,L);zfile=inputs/f'exact_zero_L{L}.txt';zeros=set(map(int,zfile.read_text().split()[1:])) if zfile.exists() else set()
    from decimal import Decimal as D
    xs=[r for r in rows if r['id'] not in zeros and r['terms'] and bool(r['power'])==(mode=='power') and (mode!='qmc' or not r['primitive']) and (L<7 or abs(3*D(r['wb'])-D(r['wa']))>=D('1e-17'))]
    if not xs:raise ValueError('No requested test class')
    xs=sorted(xs,key=lambda r:r['terms']);ids=sorted({xs[int(k*(len(xs)-1)/max(1,count-1))]['id'] for k in range(count)})
    return rows,ids

def files(out:Path,inputs:Path,L:int,mode:str,points:int,reps:int,graph_count:int=12):
    out.mkdir(parents=True,exist_ok=True);rows,ids=select(inputs,L,mode,graph_count);counts=[points if r['id'] in ids else 0 for r in rows]
    f=out/f'{mode}{L}.counts';f.write_text(str(len(rows))+'\n'+''.join(f'{i} {n}\n' for i,n in enumerate(counts)))
    work=[(uid,rep,gi,0,points,points) for uid,(rep,gi) in enumerate((r,g) for r in range(reps) for g in ids)]
    t=out/f'{mode}{L}.tasks';t.write_text(f'C7TASKS1 {len(rows)} {len(work)}\n'+''.join(' '.join(map(str,w))+'\n' for w in work))
    info={'L':L,'mode':mode,'points_per_graph':points,'replicates':reps,'selected_graphs':[rows[i] for i in ids],'selection':'quantiles of forest term count among active nonprimitive graph classes; not a random sample'}
    (out/f'{mode}{L}_workload.json').write_text(json.dumps(info,indent=2));net=None
    if mode=='qmc':
        source=inputs/f'tprodA_L{L}.net';raw=source.read_bytes();B,dim,bits=struct.unpack('<III',raw[:12])
        if B<reps:raise ValueError('requested more replicates than reference net')
        net=out/f'L{L}_{reps}.net';net.write_bytes(struct.pack('<III',reps,dim,bits)+raw[12:12+reps*dim*bits*8])
    return {'counts':f,'tasks':t,'net':net,'info':info,'rows':work}
