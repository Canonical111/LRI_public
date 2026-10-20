#!/usr/bin/env python3
"""Pre-registered per-campaign allocation for production batches (Neyman allocation over campaigns).

Uses only data that no production batch can influence: the archived components and an
independent pilot production. Per-graph allocations inside a campaign stay frozen; A/B pairs
form one group so their fixed design weights remain valid. Writes a --design file for
production.py plus a metadata record (variances, costs, predicted SE, K_max).
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from decimal import Decimal as D
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from campaign import dump,read
from production import PAIRS,specs

def split(m:float,B:list[int])->tuple[int,int]:
    """(replicate multiplier r, sample multiplier s) for one group with archived replicate counts B."""
    r=math.ceil(32/min(B))
    while max(B)*2*r<=128 and m/(2*r)>=1:r*=2
    s=1 if m<=r else 2**max(0,round(math.log2(m/r)))
    return r,s

def pilot_data(pilot:Path)->tuple[dict,dict]:
    """(CPU seconds per campaign over exactly the audited checkpoints, fresh assembly) of a verified, complete pilot."""
    from campaign import verify_campaign
    from assemble import assemble
    out={};cache={};mans={}
    for name in json.loads((pilot/'production.json').read_text())['campaigns']:
        r=verify_campaign(pilot/name);cache[(pilot/name).resolve()]=r;mans[name]=r['manifest'] # rejects quarantined, incomplete or altered campaigns
        out[name]=sum(float(x['seconds']) for s in r['audit']['sources'] for x in read(pilot/name/s['file'])['rows'])
    fresh=assemble(json.loads((pilot/'assembly.json').read_text()),pilot,cache)
    # The saved pilot result must carry the same scientific content as a fresh assembly of its verified streams.
    saved=json.loads((pilot/'C7_result.json').read_text());keys=('mean','sampling_se','covariance')
    if saved['C7_full']!=fresh['C7_full'] or saved['sampling_se']!=fresh['sampling_se'] or set(saved['components'])!=set(fresh['components']) or \
       any(saved['components'][n][k]!=fresh['components'][n][k] for n in fresh['components'] for k in keys):
        raise ValueError('pilot C7_result.json is stale: it differs from a fresh assembly of its verified campaigns')
    return out,fresh,mans

def check_pilot(pilot:Path,pprod:dict,ss:dict,mans:dict,arch:dict)->dict:
    """The pilot must be exactly the archived unit design (plus refine7): the complete campaign set, each assembly
    source bound to its own campaign with the frozen kind/weight/role/level/L/degrees, the exact per-graph count vector
    of the reference inputs at unit multiplier, integer replicate multiples, and an archived variance for every
    estimator campaign. Returns the replicate multiplier of each campaign derived from its verified manifest."""
    from campaign import plan_counts
    names=pprod['campaigns']
    if len(names)!=len(set(names)) or set(names)!=set(ss):raise ValueError('pilot campaigns must be exactly the design set; missing: '+', '.join(sorted(set(ss)-set(names)))+'; unknown: '+', '.join(sorted(set(names)-set(ss))))
    srcs=json.loads((pilot/'assembly.json').read_text())['sources'];bound={}
    for s in srcs: # each source must be its campaign's own merged output at the spec's degrees and frozen weights
        n=s['campaign'];p=ss.get(n);hi=max(p['degrees']) if p else None;lo=min(p['degrees']) if p and len(p['degrees'])==2 else None
        if n in bound or not p or s['name']!=n or Path(s['path']).parts[0]!=n or s['path']!=f'{n}/merged/N{hi}.json' or s.get('subtract')!=(f'{n}/merged/N{lo}.json' if lo is not None else None) \
           or (s['kind'],s['role'],s['level'],int(s['L']))!=('power' if p['mode']=='power' else 'free',p['role'],p['level'],p['L']) or float(s['weight'])!=float(p['weight']):
            raise ValueError('pilot assembly source does not match its campaign and the frozen design: '+str(s.get('name')))
        bound[n]=s
    if set(bound)!=set(names):raise ValueError('pilot assembly sources do not cover exactly its campaigns')
    rep={}
    for n in names:
        m=mans[n];s=ss[n];deg=[0] if s['mode']=='qmc' else sorted(s['degrees'])
        if (m['mode'],m['L'],m['degrees'],D(m['rate']))!=(s['mode'],s['L'],deg,D(s['rate'])):raise ValueError(n+': pilot manifest differs from the archived design')
        if m['replicates']%s['B'] or m['replicates']//s['B']!=pprod['settings'][n]['replicate_multiplier']:raise ValueError(n+': replicate count inconsistent with the archived design and the production settings')
        _,want=plan_counts(ROOT/'reference/inputs',s['L'],s['mode'],'free' if s['mode']=='qmc' else 'power',ROOT/'reference/inputs'/s['counts'] if s['counts'] else None,s['n'],1)
        if m['counts']!=want:raise ValueError(n+': pilot counts differ from the frozen unit allocation of the reference inputs (exact vector, zeros included)')
        if s['role']=='estimator':
            v=arch.get(n,{}).get('sampling_se',[None]*8)[7]
            if v is None or not math.isfinite(v) or v<0:raise ValueError(n+': archived estimator variance missing or invalid')
        rep[n]=m['replicates']//s['B']
    return rep

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pilot',type=Path,required=True);p.add_argument('--archive',type=Path,required=True,help='assemble.py --original output')
    p.add_argument('--target-se',type=float,default=200.);p.add_argument('--final-se',type=float,default=30.);p.add_argument('--threads',type=int,default=16)
    p.add_argument('--element-seconds',type=float,default=4500.);p.add_argument('--block-seconds',type=float,default=300.);p.add_argument('--efficiency',type=float,default=.85)
    p.add_argument('--chunk-points',type=int,default=65536);p.add_argument('--out',type=Path,required=True);p.add_argument('--meta',type=Path,required=True);a=p.parse_args()
    arch=json.loads(a.archive.read_text())['components'];pprod=json.loads((a.pilot/'production.json').read_text())
    bad=[n for n in pprod['campaigns'] if pprod['settings'].get(n,{}).get('multiplier')!=1]
    if bad:raise ValueError('pilot sample multipliers must be 1 for the pre-registered design: '+', '.join(bad))
    costs,pres,mans=pilot_data(a.pilot);pcomp={v['campaign']:v for v in pres['components'].values()};ss={s['name']:s for s in specs(bool(pprod.get('refine7')))}
    rep=check_pilot(a.pilot,pprod,ss,mans,arch);names=list(pprod['campaigns']);unit={}
    for n in names:
        r0=rep[n];pv=pcomp[n]['sampling_se'][7]**2*r0 # pilot variance at the archived replicate count
        av=arch[n]['sampling_se'][7]**2 if ss[n]['role']=='estimator' else None # checks (refine7) have no archived variance
        unit[n]={'variance':(av+pv)/2 if av is not None else pv,'archive_variance':av,'pilot_variance':pv,'cost':costs[n]/r0,'B':ss[n]['B']}
    pair_of={**{x:(x,y) for x,y in PAIRS},**{y:(x,y) for x,y in PAIRS}}
    groups=[];seen=set();checks=[n for n in names if ss[n]['role']=='check']
    for n in names:
        if n in seen or n in checks:continue
        g=[m for m in pair_of.get(n,(n,)) if m in unit];seen|=set(g);groups.append(g)
    V=lambda g:sum(unit[n]['variance'] for n in g);Cc=lambda g:sum(unit[n]['cost'] for n in g)
    S=sum(math.sqrt(V(g)*Cc(g)) for g in groups);design={};meta={'groups':[],'unit':unit};var=0.
    for g in groups:
        m=math.sqrt(V(g)/Cc(g))*S/a.target_se**2;r,s=split(m,[unit[n]['B'] for n in g]);var+=V(g)/(r*s)
        meta['groups'].append({'members':g,'neyman_m':m,'replicate_multiplier':r,'multiplier':s})
        for n in g:
            spec=ss[n];cost=unit[n]['cost']*r*s;budget=a.element_seconds*a.threads*a.efficiency;shards=max(1,math.ceil(cost/budget))
            counts=mans[n]['counts'] # verified unit counts
            chunk=a.chunk_points;units=spec['B']*r*sum(math.ceil(c*s/chunk) for c in counts if c)
            blocks=max(1,math.ceil(a.element_seconds/a.block_seconds));ck=max(1,math.ceil(units/shards/blocks))
            design[n]={'multiplier':s,'replicate_multiplier':r,'shards':min(shards,units),'checkpoint_tasks':ck,'chunk_points':chunk}
            meta.setdefault('campaigns',{})[n]={'cpu_seconds_per_batch':cost,'work_units':units,'predicted_se_C7':math.sqrt(unit[n]['variance']/(r*s))}
    # Check campaigns never enter C7: they take the (r, s) of the level they check and are excluded from the prediction.
    for n in checks:
        base=n.replace('refine7','refine6');r,s=design[base]['replicate_multiplier'],design[base]['multiplier'];spec=ss[n];cost=unit[n]['cost']*r*s
        counts=mans[n]['counts']
        units=spec['B']*r*sum(math.ceil(c*s/a.chunk_points) for c in counts if c);shards=max(1,math.ceil(cost/(a.element_seconds*a.threads*a.efficiency)))
        design[n]={'multiplier':s,'replicate_multiplier':r,'shards':min(shards,units),'checkpoint_tasks':max(1,math.ceil(units/min(shards,units)/max(1,math.ceil(a.element_seconds/a.block_seconds)))),'chunk_points':a.chunk_points}
        meta.setdefault('campaigns',{})[n]={'cpu_seconds_per_batch':cost,'work_units':units,'predicted_se_C7':math.sqrt(unit[n]['variance']/(r*s)),'role':'check (allocation of '+base+'; not in the C7 prediction)'}
    se=math.sqrt(var);kmax=math.ceil((se/a.final_se)**2)
    meta.update({'target_se_per_batch':a.target_se,'predicted_se_per_batch':se,'K_max':kmax,'final_se_target':a.final_se,'cpu_hours_per_batch':sum(v['cpu_seconds_per_batch'] for v in meta['campaigns'].values())/3600,
                 'pilot':str(a.pilot.resolve()),'pilot_result_sha256':hashlib.sha256((a.pilot/'C7_result.json').read_bytes()).hexdigest(),'archive_sha256':hashlib.sha256(a.archive.read_bytes()).hexdigest(),
                 'rule':'Neyman m=sqrt(v/c)*sum(sqrt(v c))/SE_b^2 per group; r from >=32 replicates, doubled while max(B*2r)<=128 and m/(2r)>=1; s=nearest power of two of m/r (>=1)'})
    dump(a.out,design);dump(a.meta,meta)
    print(json.dumps({'predicted_se_per_batch':se,'K_max':kmax,'cpu_hours_per_batch':meta['cpu_hours_per_batch'],'elements_per_batch':sum(d['shards'] for d in design.values())},indent=2))
if __name__=='__main__':main()
