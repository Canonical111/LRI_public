#!/usr/bin/env python3
"""Frozen variance table and Neyman allocation for the ten six-loop primitive strata (recompute mode).

The table comes from archived paired d=2 L6 records (auxiliary method-study data that no estimator uses). It only
reallocates points between independent strata: every primitive stays its own stratum, so the estimator is unbiased
for any allocation. Pure Python with math.fsum keeps the table bit-deterministic across NumPy/BLAS builds.
"""
from __future__ import annotations
import json,math,sys
from pathlib import Path
from common import ROOT,digest,dump,load
PIDS=(639,648,649,651,653,654,655,657,658,659)
RECORDS=tuple(f'reference/records/paired_{t}_d2_L6.json'for t in('new_a','new_b','prod_a','prod_b'))
# L=6 enters C6 linearly: dC6/d(b6,c6)=(-1,3)/2187 (finite-order fixed point; see tests/workflow.py).
GRADIENT=(-1.0,3.0)
SCHEMA='c6-d2-primitive-allocation-1'

def build_table(inventory_L6:list[dict],root:Path=ROOT)->dict:
    additions={int(r['id']):int(r['additions'])for r in inventory_L6}
    per={g:[]for g in PIDS};sources={}
    for rel in RECORDS:
        path=root/rel;sources[rel]=digest(path);d=json.loads(path.read_text(),parse_float=str)
        ids=[int(x)for x in d['graph_ids']];counts=[int(x)for x in d['counts_per_replicate']];reps=len(d['graph_batches'])
        if d['dimension']!=2 or d['L']!=6 or reps<2:raise ValueError('unexpected paired record '+rel)
        for g in PIDS:
            i=ids.index(g);n=counts[i]
            if n<1:raise ValueError(f'primitive {g} missing from {rel}')
            h=[math.fsum(c*float(v)for c,v in zip(GRADIENT,d['graph_batches'][b][i][:2]))/2187 for b in range(reps)]
            mean=math.fsum(h)/reps;var=math.fsum((x-mean)*(x-mean)for x in h)/(reps-1)  # x*x, never x**2: libm pow is not portable to the last bit
            per[g].append({'record':rel,'points':n,'replicates':reps,'per_point_variance':n*var})
    graphs=[]
    for g in PIDS:
        rows=per[g];dof=sum(r['replicates']-1 for r in rows)
        pooled=math.fsum((r['replicates']-1)*r['per_point_variance']for r in rows)/dof
        graphs.append({'id':g,'per_point_sd':math.sqrt(pooled),'cost_per_point':max(32,additions[g]),'records':rows})
    return {'schema':SCHEMA,'quantity':'per-point standard deviation of the C6-projected L6 integrand h=(-v0+3v1)/2187: '
            'points x replicate variance of the per-replicate graph mean (MC-scaling proxy for RQMC)',
            'pooling':'degrees-of-freedom weighted mean of the per-record per-point variances',
            'cost_model':'max(32, additions) per point, as tools/production.py estimates task cost',
            'use':'relative Neyman weights only; never an estimator input','graphs':graphs,'sources':sources}

def allocate(table:dict,n_uniform:int,bits:int)->dict[int,int]:
    """Power-of-two Neyman counts with total cost <= 1.1 x the uniform allocation's cost (n_uniform per primitive)."""
    if n_uniform<4:raise ValueError('recompute-mode Neyman allocation needs primitive_points x multiplier >= 4 '
                                    '(use --points for tiny smoke plans, or --primitive-allocation uniform)')
    rows=table['graphs'];cost={r['id']:r['cost_per_point']for r in rows};sd={r['id']:r['per_point_sd']for r in rows}
    budget=n_uniform*math.fsum(cost.values());norm=math.fsum(sd[g]*math.sqrt(cost[g])for g in cost)
    top=1<<bits;counts={}
    for g in cost:
        ideal=budget*(sd[g]/math.sqrt(cost[g]))/norm if norm>0 else n_uniform
        counts[g]=min(top,max(4,1<<max(0,round(math.log2(ideal)))if ideal>0 else 4))
    steps=sum(max(0,(n//4).bit_length()-1)for n in counts.values())
    for _ in range(steps+1):
        if math.fsum(counts[g]*cost[g]for g in cost)<=1.1*budget:return dict(sorted(counts.items()))
        g=max((g for g in counts if counts[g]>4),key=lambda g:(counts[g]*cost[g],g),default=None)
        if g is None:break
        counts[g]//=2
    raise ValueError('primitive allocation cannot meet its cost cap')

def uniform(n_uniform:int)->dict[int,int]:return {g:n_uniform for g in PIDS}

def projected_se(table:dict,counts:dict[int,int],replicates:int,campaigns:int=2)->float:
    """Projected SE of the equal-weight campaign mean of the primitive block (MC scaling; a projection only)."""
    sd={r['id']:r['per_point_sd']for r in table['graphs']}
    per_campaign=math.fsum(sd[g]*sd[g]/counts[g]for g in counts if counts[g])/replicates
    return math.sqrt(per_campaign/campaigns)

if __name__=='__main__':
    t=load(ROOT/'inputs/primitive_allocation_d2.json')
    for n in (16384,65536*4):
        ney=allocate(t,n,52);print(n,'neyman',ney,'SE',projected_se(t,ney,32 if n==16384 else 64),'uniform SE',projected_se(t,uniform(n),32 if n==16384 else 64))
    sys.exit(0)
