#!/usr/bin/env python3
"""The summary of a measured cost model and its sweep (Stage 3b, J-SWEEP-1; PLAN D.14 and the Budgets "Pilot line").

  cost_summary.py RUN MODEL [--symmetry-model cost_models/gmp_symmetry_epyc7532.json] [--accounting FILE] [--output FILE]

RUN is the merged sweep campaign (tools/sweep.py), MODEL the cost model make_cost_model.py wrote from it. Read only;
nothing is planned and no seed is drawn. Per group (campaign, sector, L):
  * graphs, points, busy core-seconds (the sum of the row seconds, graph_costs.csv) and the busy seconds per point;
  * the model's per-graph seconds per point: mean, median, max (with its graph) and the share of the group's cost in
    its heaviest 1% of graphs;
  * the promotion rates from graph_promotions.csv: binary128 (quad) and MP points per point, the MP self-check alarms
    (mp_alarm, log10(|v|/err) < -320), the shifted (nondirect) and non-moderate points per point;
  * with --symmetry-model (C7(3)'s order-7 model, symmetry EPYC 7532, keys sector:L:graph): the ratio of this model's
    seconds per point (mean of campaigns a and b) to the symmetry model's, median over the group's L <= 7 graphs.
The cost estimate this model implies, in busy core-hours on the model's own CPU (EPYC 7742 on Expanse, EPYC 7543 on
symmetry; cpu_label of its cpu_model):
  * PF (pilot_full): every L3-L8 kernel at 4,096 points x R = 8 replicates, both campaigns; and the R = 16 branch at
    L8 (PLAN Budgets);
  * PA (stage A + P1c, tools/pilot_select.py's rule, as an expectation over its seeded draw, so no seed is used): the
    heaviest 1% per sector with certainty, 1/8 of every other graph of each stratum (sector x T bin x M tertile), at
    4,096 points; P1c graphs (1/32 of each stratum) at 32,768 points; R = 8, both campaigns;
  * PC: its cap, 25% of PF's L8 cost;
  * SU at allocated/busy eta: the plan's nominal 1.2 and, with --accounting (tools/accounting.py --json of the sweep),
    the whole sweep job's allocated/busy (build, plan, merge and model included; not a lane-mode eta); for comparison
    the plan's symmetry-basis busy core-hours (F24; PLAN Budgets).
"""
from __future__ import annotations
import argparse,json,math,re,statistics,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,digest,dump,host_info,load,utc

POINTS_PILOT=4096;POINTS_PC=32768;R=8;STAGE_A=8;P1C=32;HEAVIEST=0.01;PC_CAP=0.25;ETA_NOMINAL=1.2
PLAN_SYMMETRY={'PA':41.5,'PF':228.5,'PF_L8':219.1,'PF_L_le_7':9.4,'PF_R16_extra':219.1,'PC_cap':54.8}   # PLAN Budgets (busy core-h, symmetry basis)

def cpu_label(cpu)->str:
    """'EPYC 7742' of 'AMD EPYC 7742 64-Core Processor' (the first match of EPYC [0-9A-Z]+), else the whole normalized
    string (production.norm_cpu)."""
    s=' '.join(str(cpu or'').split());m=re.search(r'EPYC [0-9A-Z]+',s)
    return m.group(0)if m else s

def csv_rows(path:Path)->list[dict]:
    lines=Path(path).read_text().splitlines();head=lines[0].split(',')
    return [dict(zip(head,l.split(',')))for l in lines[1:]if l]

def t_bin(T:int)->int:
    for i,hi in enumerate((8,24,48,96)):
        if T<=hi:return i
    return 4

def pa_expectation(inv:dict,c:dict)->dict:
    """Expected PA busy core-seconds per sector and campaign: E[points_g] = 4096 P(g in stage A) + 28672 P(g in P1c)."""
    import pilot_select as ps
    st=ps.strata(inv);out={}
    for s in('free','power'):
        rows=inv[s].get('8',[])
        ids=[r['id']for r in rows];k=math.ceil(HEAVIEST*len(ids))
        heavy=set(sorted(ids,key=lambda g:(-(c[('a',s,8,g)]+c[('b',s,8,g)]),g))[:k])
        tot={'a':0.,'b':0.};pts=0.
        for key,v in st.items():
            if key[0]!=s:continue
            nA=(len(v)+STAGE_A//2)//STAGE_A;nP=(nA+P1C//2)//P1C
            for g in v:
                pa=1. if g in heavy else nA/len(v);pp=nP/len(v)
                e=POINTS_PILOT*pa+(POINTS_PC-POINTS_PILOT)*pp;pts+=e
                for cc in'ab':tot[cc]+=R*e*c[(cc,s,8,g)]
        out[s]={'heaviest_1pct':len(heavy),'expected_points_per_replicate':pts,'busy_core_seconds':tot}
    return out

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('run',type=Path);p.add_argument('model',type=Path);p.add_argument('--symmetry-model',type=Path);p.add_argument('--accounting',type=Path)
    p.add_argument('--output',type=Path);a=p.parse_args(argv)
    run=a.run.resolve();m=load(run/'manifest.json');model=load(a.model);spp=model['seconds_per_point']
    inv=load(ROOT/'inputs/inventory.json')
    c={}
    for k,v in spp.items():
        cc,s,L,g=k.split(':');c[(cc,s,int(L),int(g))]=float(v)
    sym=None
    if a.symmetry_model:
        sm=load(a.symmetry_model)['seconds_per_point'];sym={}
        for k,v in sm.items():
            s,L,g=k.split(':');sym[(s,int(L),int(g))]=float(v)
    groups={};pf={'L8':0.,'L_le_7':0.}
    for g in m['groups']:
        name=g['name'];cfg=load(run/'groups'/name/'config.json');cc,s,L=cfg['campaign'],cfg['sector'],cfg['L']
        gc=csv_rows(run/'groups'/name/'graph_costs.csv');pr=csv_rows(run/'groups'/name/'graph_promotions.csv')
        pts=sum(int(r['points'])for r in gc);sec=sum(float(r['row_seconds'])for r in gc)
        per=sorted(((c[(cc,s,L,int(r['graph']))],int(r['graph']))for r in gc),reverse=True)
        vals=[v for v,_ in per];k=max(1,math.ceil(HEAVIEST*len(vals)));top=sum(vals[:k])/sum(vals)if sum(vals)else None
        q=sum(int(r['quad'])for r in pr);mp=sum(int(r['mp'])for r in pr);al=sum(int(r['mp_alarm'])for r in pr)
        nd=sum(int(r['nondirect'])for r in pr);nm=sum(int(r['nonmoderate'])for r in pr);chk=sum(int(r['mp_checked'])for r in pr)
        row={'campaign':cc,'sector':s,'L':L,'graphs':len(gc),'points':pts,'busy_core_seconds':sec,'busy_seconds_per_point':sec/pts if pts else None,
             'model_seconds_per_point':{'mean':statistics.fmean(vals),'median':statistics.median(vals),'max':vals[0],'max_graph':per[0][1],
                                        'heaviest_1pct_cost_share':top},
             'promotion':{'quad_per_point':q/pts,'mp_per_point':mp/pts,'mp_checked':chk,'mp_alarm':al,'nondirect_per_point':nd/pts,'nonmoderate_per_point':nm/pts},
             'pf_busy_core_hours_R8':R*POINTS_PILOT*sum(vals)/3600}
        if sym is not None and L<=7:
            rat=[(c[('a',s,L,gi)]+c[('b',s,L,gi)])/2/sym[(s,L,gi)]for _,gi in per if (s,L,gi)in sym and ('a',s,L,gi)in c and ('b',s,L,gi)in c]
            row['ratio_to_symmetry_order7_model']={'median':statistics.median(rat)if rat else None,'graphs':len(rat)}
        groups[name]=row;pf['L8' if L==8 else 'L_le_7']+=row['pf_busy_core_hours_R8']
    pa=pa_expectation(inv,c);pa_h=sum(v['busy_core_seconds'][cc]for v in pa.values()for cc in'ab')/3600
    est={'PF_R8':pf['L8']+pf['L_le_7'],'PF_L8':pf['L8'],'PF_L_le_7':pf['L_le_7'],'PF_R16_extra':pf['L8'],'PA':pa_h,'PC_cap':PC_CAP*pf['L8']}
    est['default_pilot_PA_PF']=est['PA']+est['PF_R8'];est['with_every_branch']=est['default_pilot_PA_PF']+est['PF_R16_extra']+est['PC_cap']
    eta={'nominal':ETA_NOMINAL}
    if a.accounting:
        # billing = the job's allocated cores (128 on an Expanse compute node, 64 on a symmetry AMD node); the sweep is one
        # exclusive job (accounting.py classes its raw role "sweep1" or "sweep2" as
        # "other"): every attempt's allocated core-seconds over the checkpoint rows' busy core-seconds, the build, plan,
        # merge and model included (the whole sweep job, an upper bound of a lane's eta; not a lane-mode measurement)
        acc=load(a.accounting);alloc=sum(x['billing']*x['elapsed']for x in acc.get('attempts',[]))
        busy=acc.get('busy_core_seconds')or 0.
        eta['sweep_job_allocated_over_busy']=alloc/busy if alloc and busy else None
        eta['accounting']={k:acc.get(k)for k in('su_total','su_by_class','busy_core_seconds','attempts')}
    su={k:{'eta_nominal':v*ETA_NOMINAL,**({'eta_sweep_job':v*eta['sweep_job_allocated_over_busy']}if eta.get('sweep_job_allocated_over_busy')else{})}for k,v in est.items()}
    tot_sec=sum(r['busy_core_seconds']for r in groups.values());tot_pts=sum(r['points']for r in groups.values())
    out={'schema':'c8-d3-cost-summary-1','run':str(run),'manifest_sha256':digest(run/'manifest.json'),'model':str(a.model),'model_sha256':digest(a.model),
         'executable_sha256':model['executable_sha256'],'cpu_model':model['cpu_model'],'keys':len(spp),'mp_check':model['mp_check'],
         'sweep':{'points':tot_pts,'busy_core_hours':tot_sec/3600,'busy_seconds_per_point':tot_sec/tot_pts if tot_pts else None},
         'groups':groups,'pilot_estimate_busy_core_hours':est,'pilot_estimate_su':su,'eta':eta,'pa_detail':pa,
         'plan_symmetry_basis_busy_core_hours':PLAN_SYMMETRY,
         'ratio_to_plan_symmetry_basis':{k:est[k]/PLAN_SYMMETRY[k]for k in ('PA','PF_L8','PF_L_le_7','PC_cap')if k in est}|{'PF':est['PF_R8']/PLAN_SYMMETRY['PF']},
         'note':f'busy core-hours on {cpu_label(model.get("cpu_model"))} from the measured model (the sweep at 512 points, 2 replicates, both campaigns, --mp-check on); SU = busy x eta '
                '(allocated/busy); PA is an expectation over pilot_select\'s seeded stratified draw; nothing here is a design or a variance estimate',
         'made_on':host_info(),'made_utc':utc()}
    if a.output:dump(a.output,out)
    print(json.dumps({'sweep':out['sweep'],'pilot_estimate_busy_core_hours':est,'ratio_to_plan_symmetry_basis':out['ratio_to_plan_symmetry_basis']},indent=1))
    return 0

if __name__=='__main__':sys.exit(main())
