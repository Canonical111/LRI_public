#!/usr/bin/env python3
"""Independent recomputation of graph_prefixes.csv from the checkpoints (PLAN C.3, D.13, A-DES-8 (c)).

  prefix_verify.py RUN [--group G] [--json]

Its own checkpoint parser (json; the payload digest recomputed here), exact fractions.Fraction sums, its own top-16
union (ties to the smaller point index) and no import from production.py. The expected rows come from the pinned
configuration, never from the checkpoints that happen to exist (S3-012): each group's config.json must equal the sha256
the manifest pins, and every nested graph g (config "nest") x replicate 0..replicates-1 x prefix P of nest[g] is a row.
Each graph-replicate's checkpoint tasks must exist and cover [0, max P] contiguously without overlap (sorted by begin:
the first at 0, each next beginning where the last ended), with the configured total and a task boundary at every P.
Each row is recomputed: jet_i = (total/P) x the sum of jet_i over the graph-replicate's tasks with end <= P; tail_sum
the sum of their tail_sum; the 16 largest of their tail_top; the argmax of the union. It is compared with the merged
graph_prefixes.csv: jets and tail_sum to 1e-40 relative, the top 16 and the argmax identical (as numbers); a missing or
extra row fails. Exit 0 when every row agrees, 1 otherwise.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from fractions import Fraction
from decimal import Decimal
from pathlib import Path
REL=Fraction(1,10**40)

def frac(x)->Fraction:return Fraction(Decimal(str(x)))

def canon_hash(obj)->str:return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def pinned_config(run:Path,name:str)->dict:
    """The group's config.json, read only when its sha256 equals the manifest's pin (S3-012)."""
    m=json.loads((Path(run)/'manifest.json').read_bytes());pin=next((g['sha256']for g in m['groups']if g['name']==name),None)
    data=(Path(run)/'groups'/name/'config.json').read_bytes()
    if pin is None:raise ValueError(f'{name}: not a group of the manifest')
    if hashlib.sha256(data).hexdigest()!=pin:raise ValueError(f'{name}: config.json differs from the manifest\'s pin')
    return json.loads(data)

def recompute(run:Path,name:str)->dict:
    p=Path(run)/'groups'/name;cfg=pinned_config(run,name);nest={int(k):v for k,v in (cfg.get('nest')or{}).items()}
    if not nest:return {}
    counts={int(k):int(v)for k,v in cfg['counts'].items()};R=int(cfg['replicates']);rows={}
    for f in sorted((p/'checkpoints').glob('*.json')):
        doc=json.loads(f.read_bytes())
        if canon_hash(doc['native'])!=doc.get('payload_sha256'):raise ValueError(f'{f}: payload digest mismatch')
        for r in doc['native']['rows']:
            if r['graph']in nest:rows.setdefault((r['rep'],r['graph']),[]).append(r)
    want={(rep,g)for g in nest for rep in range(R)}   # S3-012: the expected keys from the pinned configuration
    if set(rows)-want:raise ValueError(f'{name}: checkpoint rows of graph-replicates the configuration does not hold: {sorted(set(rows)-want)[:5]}')
    if want-set(rows):raise ValueError(f'{name}: no checkpoint rows for graph-replicate(s) {sorted(want-set(rows))[:5]} of the configuration\'s nested graphs')
    out={}
    for (rep,g),rs in sorted(rows.items()):
        rs.sort(key=lambda r:(r['begin'],r['end']));end=0
        for r in rs:   # contiguous, non-overlapping coverage from 0 through the last prefix boundary (S3-012)
            if r['total']!=counts[g]:raise ValueError(f'{name} replicate {rep} graph {g}: a task of total {r["total"]}, the configuration {counts[g]}')
            if r['begin']<end:raise ValueError(f'{name} replicate {rep} graph {g}: tasks overlap at point {r["begin"]}')
            if r['begin']>end:
                if end<max(nest[g]):raise ValueError(f'{name} replicate {rep} graph {g}: tasks leave a gap at point {end}')
                break
            end=r['end']
        if end<max(nest[g]):raise ValueError(f'{name} replicate {rep} graph {g}: tasks cover [0, {end}), not through the prefix boundary {max(nest[g])}')
        for P in nest[g]:
            sel=[r for r in rs if r['end']<=P]
            if not sel or sel[-1]['end']!=P:raise ValueError(f'{name} replicate {rep} graph {g}: no task boundary at {P}')
            total=sel[0]['total'];w=len(sel[0]['values']);scale=Fraction(total,P)
            jets=[scale*sum(frac(r['values'][i])for r in sel)for i in range(w)]
            tsum=sum(frac(r['tail_sum'])for r in sel)
            tops=sorted((frac(v)for r in sel for v in r['tail_top']),reverse=True)[:16]
            best=None
            for r in sel:
                if r['tail_top']:
                    v=frac(r['tail_top'][0])
                    if best is None or v>best[0]or (v==best[0]and r['tail_argmax']<best[1]):best=(v,r['tail_argmax'])
            out[(rep,g,P)]={'total':total,'jets':jets,'tail_sum':tsum,'top':tops,'argmax':best[1]if best else None}
    return out

def read_csv(path:Path)->dict:
    lines=path.read_text().splitlines();head=lines[0].split(',');out={}
    for l in lines[1:]:
        d=dict(zip(head,l.split(',')));k=(int(d['replicate']),int(d['graph']),int(d['points']))
        if k in out:raise ValueError(f'{path}: row {k} appears twice')
        w=sum(1 for h in head if h.startswith('jet_'))
        out[k]={'total':int(d['total']),'jets':[frac(d[f'jet_{i}'])for i in range(w)],'tail_sum':frac(d['tail_sum']),
                'top':[frac(d[f'tail_top_{i+1}'])for i in range(16)if d.get(f'tail_top_{i+1}')],'argmax':int(d['tail_argmax'])if d['tail_argmax']not in('','None')else None}
    return out

def close(a:Fraction,b:Fraction)->bool:return a==b or abs(a-b)<=REL*max(abs(a),abs(b))

def verify(run:Path,group:str|None=None)->dict:
    m=json.loads((Path(run)/'manifest.json').read_bytes());names=[group]if group else[g['name']for g in m['groups']];bad=[];checked=0
    for name in names:
        f=Path(run)/'groups'/name/'graph_prefixes.csv'
        try:want=recompute(run,name)
        except (ValueError,KeyError,OSError)as e:bad.append(f'{name}: {e}'if not str(e).startswith(name)else str(e));continue
        if not want:
            if f.exists():bad.append(f'{name}: graph_prefixes.csv exists without nested graphs')
            continue
        if not f.exists():bad.append(f'{name}: graph_prefixes.csv is missing');continue
        got=read_csv(f)
        for k in sorted(set(want)^set(got)):bad.append(f'{name}: row {k} '+('missing'if k in want else'extra'))
        for k in sorted(set(want)&set(got)):
            a,b=want[k],got[k];checked+=1
            if a['total']!=b['total']or len(a['jets'])!=len(b['jets'])or not all(close(x,y)for x,y in zip(a['jets'],b['jets'])):bad.append(f'{name}: row {k}: jets differ')
            if not close(a['tail_sum'],b['tail_sum']):bad.append(f'{name}: row {k}: tail_sum differs')
            if a['top']!=b['top']:bad.append(f'{name}: row {k}: top 16 differ')
            if a['argmax']!=b['argmax']:bad.append(f'{name}: row {k}: argmax {b["argmax"]} != {a["argmax"]}')
    return {'verified':not bad,'rows_checked':checked,'problems':bad[:50]}

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('run',type=Path);p.add_argument('--group');a=p.parse_args(argv)
    try:r=verify(a.run,a.group)
    except (ValueError,OSError,KeyError)as e:print(f'prefix_verify: {e}',file=sys.stderr);return 1
    print(json.dumps(r));return 0 if r['verified']else 1
if __name__=='__main__':sys.exit(main())
