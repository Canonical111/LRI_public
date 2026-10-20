#!/usr/bin/env python3
"""Cost and variance shares of a finished C7(2) campaign, and MC-scaling projections of the opt-in allocation options.

  production_shares.py RUN [--output shares.json]

Measured: task CPU per sector/loop (primitive classes separately) = sum of per-task native seconds over the run's
checkpoints; Var(C7) contributions per sector/loop = error_by_loop of RUN/C7_result.json; the primitive block's
variance from groups/{a,b}_free_L7/graph_replicates.csv (h = (-b70 + 3 c70)/6561 per replicate; the same sum over
all free-L7 graphs reproduces error_by_loop free L7). Projections scale each part by MC rules at fixed M and R: power
variance x K and power cost / K; primitive cost by the frozen table's seconds per point, primitive variance by the
table's projected-SE ratio. Read-only; written for the 2026-09-30 symmetry production (plan M=4096, R=64, primitive
points 16384).
"""
from __future__ import annotations
import argparse,csv,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from common import dump,load
import primitive_allocation as pa

def measure(run:Path)->dict:
    m=load(run/'manifest.json');res=load(run/'C7_result.json');inv=load(ROOT/'inputs/inventory.json')
    prim={r['id']for r in inv['free']['7']if r['primitive']};sec={}
    for g in m['groups']:
        cfg=load(run/'groups'/g['name']/'config.json')
        for f in (run/'groups'/g['name']/'checkpoints').glob('*.json'):
            for r in load(f)['native']['rows']:
                k=f"{cfg['sector']}_L{cfg['L']}"+('_primitive'if cfg['sector']=='free'and cfg['L']==7 and r['graph']in prim else'')
                sec[k]=sec.get(k,0.)+r['seconds']
    V=res['sampling_standard_error']**2;ebl=res['error_by_loop']
    var={f'{s}_L{L}':ebl[L][s]**2 for L in ebl for s in ('free','power')}
    pv,allv=0.,0.
    for c in ('a','b'):
        rows={};allr={}
        with open(run/'groups'/f'{c}_free_L7'/'graph_replicates.csv')as f:
            for row in csv.DictReader(f):
                h=(-float(row['jet_0'])+3*float(row['jet_1']))/6561;rep=int(row['replicate'])
                allr[rep]=allr.get(rep,0.)+h
                if int(row['graph'])in prim:rows[rep]=rows.get(rep,0.)+h
        for d,acc in ((rows,'p'),(allr,'a')):
            x=list(d.values());n=len(x);mu=sum(x)/n;v=sum((y-mu)**2 for y in x)/(n-1)/n/4
            if acc=='p':pv+=v
            else:allv+=v
    tot=sum(sec.values())
    return {'run':str(run),'task_core_hours':tot/3600,'cpu_share':{k:v/tot for k,v in sorted(sec.items())},
            'power_cpu_share':sum(v for k,v in sec.items()if k.startswith('power'))/tot,'primitive_cpu_share':sec.get('free_L7_primitive',0.)/tot,
            'var_C7':V,'C7_se':res['sampling_standard_error'],'var_share':{k:v/V for k,v in var.items()},'power_var_share':sum(v for k,v in var.items()if k.startswith('power'))/V,
            'primitive_var':pv,'primitive_se':math.sqrt(pv),'primitive_var_share':pv/V,
            'check_free_L7_se_from_csv':math.sqrt(allv),'check_free_L7_se_error_by_loop':ebl['7']['free'],
            '_sec':sec}

def project(meas:dict,M:int=4096,R:int=64,u0:int=16384)->list:
    t=pa.load_table();sec=meas['_sec'];tot=sum(sec.values());V=meas['var_C7']
    P=sum(v for k,v in sec.items()if k.startswith('power'));Pr=sec.get('free_L7_primitive',0.);F=tot-P-Pr;pvar=meas['power_var_share']*V;prv=meas['primitive_var']
    cost_u=sum(u0*M*c['seconds_per_point']for c in t['classes']);se_u=pa.projected_se(t,pa.uniform(t,u0*M),R)
    def row(label,K,alloc,pp):
        cnt=pa.allocate(t,44*pp*M)if alloc=='neyman'else pa.uniform(t,pp*M)
        c=F+P/K+Pr*sum(cnt[x['id']]*x['seconds_per_point']for x in t['classes'])/cost_u
        v=V+(K-1)*pvar+prv*((pa.projected_se(t,cnt,R)/se_u)**2-1);ch=c/3600;se=math.sqrt(v)
        return {'plan':label,'core_hours':ch,'C7_se':se,'se_x_sqrt_core_hours':se*math.sqrt(ch),'core_hours_for_production_se':ch*v/V}
    return [row('2026 production (measured shares): K=1, uniform, primitive points 16384',1,'uniform',16384),
            row('--primitive-allocation neyman (budget unchanged)',1,'neyman',16384),
            row('--power-divisor 16',16,'uniform',16384),
            row('--power-divisor 16 --primitive-allocation neyman (plan recipe, primitive points 16384)',16,'neyman',16384),
            row('--power-divisor 16 --primitive-points 512 (uniform)',16,'uniform',512),
            row('--power-divisor 16 --primitive-allocation neyman --primitive-points 512',16,'neyman',512)]

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);ap.add_argument('run',type=Path);ap.add_argument('--output',type=Path);a=ap.parse_args()
    m=measure(a.run.resolve());out={**{k:v for k,v in m.items()if k!='_sec'},'task_core_hours_by_part':{k:v/3600 for k,v in sorted(m['_sec'].items())},
                                     'projections':project(m),'projection_note':'MC scaling at fixed M=4096, R=64 from the measured shares; projections, not measurements'}
    if a.output:dump(a.output,out)
    print(json.dumps(out,indent=2))
