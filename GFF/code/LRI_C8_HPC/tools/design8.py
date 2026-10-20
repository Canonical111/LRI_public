#!/usr/bin/env python3
"""Pre-registered production design from an independent pilot batch (never part of the estimate).

1. Per graph (every sampled campaign): sigma_g^2 = samples x Var_replicates(stream estimate projected on C8) and the
   CPU cost per sample c_g, from the audited pilot checkpoints. Paired levels use the within-replicate difference.
   Projection: J8 row (free) or the frozen controlled row (power). sigma_g is floored at 3% of the campaign median
   (the archived C7 rule) so no active graph is starved; every active graph keeps >= 1 sample (unbiasedness).
2. Per-graph Neyman counts n_g ~ sigma_g/sqrt(c_g) (powers of two for QMC), A/B pairs share one counts file.
3. Across campaign groups: Neyman over the predicted per-replicate variance V and ALLOCATED cost for the given budget.
   Allocated cost = integration thread-seconds / efficiency, with each campaign's efficiency measured end to end from
   the pilot's Slurm accounting (sum of row seconds over elapsed x allocated CPUs of its elements; preparation,
   hashing, start-up, publication and idle threads included). The production budget plus the core-hours already
   spent must not exceed the total cap.
Writes: per-campaign counts files, a production unit design and a --design file, plus a metadata record.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, shutil, subprocess, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from campaign import verify_campaign,dump,read,identity,blocks,digest,campaign_inputs
from c8lib import NW,NV,TOP

def per_graph(camp:Path,proj:np.ndarray)->tuple[dict,dict,dict]:
    """(stream estimates {(rep,g): y}, samples {g: n}, seconds {g: s}) of a verified campaign, top-degree minus paired lower."""
    r=verify_campaign(camp);m=r['manifest'];degs=m['degrees'];hi=max(degs);lo=min(degs) if len(degs)==2 else None
    y={};secs={};n={}
    for shard,part,block,_ in blocks(camp,m):
        for N in degs:
            d=read(camp/'checkpoints'/(identity(shard['id'],part,N)+'.json'))
            for row in d['rows']:
                v=float(np.array([float(x) for x in row['value']])@proj);k=(row['replicate'],row['graph'])
                y[k]=y.get(k,0.)+(v if N==hi else -v);secs[row['graph']]=secs.get(row['graph'],0.)+float(row['seconds'])
                if N==hi:n[row['graph']]=row['total']
    return y,n,secs

def allocate(y:dict,n:dict,secs:dict,reps:int,qmc:bool,unit_total:float)->tuple[dict,float,float]:
    """Neyman per-graph counts for a campaign with pilot data; returns (counts, predicted var per replicate, cost per replicate)."""
    gs=sorted(n);sig={};cost={}
    for g in gs:
        vals=np.array([y.get((r,g),0.) for r in range(reps)]);sig[g]=math.sqrt(max(0.,vals.var(ddof=1))*n[g]);cost[g]=secs[g]/(reps*n[g])
    med=float(np.median([s for s in sig.values() if s>0])) if any(s>0 for s in sig.values()) else 1.
    for g in gs:sig[g]=max(sig[g],.03*med);cost[g]=max(cost[g],1e-7)
    k=unit_total/sum(sig[g]*math.sqrt(cost[g]) for g in gs) # scale: total cost equals the pilot's unit cost
    counts={}
    for g in gs:
        x=max(1.,k*sig[g]/math.sqrt(cost[g]))
        counts[g]=int(2**max(0,round(math.log2(x)))) if qmc else int(max(1,round(x)))
    V=sum(sig[g]**2/counts[g] for g in gs);C=sum(cost[g]*counts[g] for g in gs);return counts,V,C,sig,cost

def efficiencies(prod:dict,attempts:list[str],rowsecs:dict)->dict:
    """Per-campaign end-to-end efficiency of the pilot (row seconds / allocated core-seconds) over EVERY submission
    attempt ("JOBID" or "JOBID:OFFSET", the C8_INDEX_OFFSET of that submission): failed, cancelled and retried elements
    all count as allocated time, and every planned element must have at least one COMPLETED row."""
    alloc={};done=set();n=len(prod['jobs'])
    for att in attempts:
        job,_,off=att.partition(':');off=int(off or 0)
        out=subprocess.run(['sacct','-j',job,'-X','-n','-P','-o','JobID,ElapsedRaw,AllocCPUS,State'],capture_output=True,text=True,check=True).stdout
        for line in out.splitlines():
            jid,el,cpu,state=line.split('|')
            if '_' not in jid or '[' in jid:continue
            idx=off+int(jid.split('_')[1])
            if not 0<=idx<n:raise ValueError(f'accounting row {jid} maps outside the planned elements (offset {off})')
            c=prod['jobs'][idx]['campaign'];alloc[c]=alloc.get(c,0.)+float(el)*float(cpu)
            if state.startswith('COMPLETED'):done.add(idx)
    missing=sorted(set(range(n))-done)
    if missing:raise ValueError(f'{len(missing)} planned pilot elements have no COMPLETED accounting row (e.g. {missing[:5]}); give every submission attempt')
    out={}
    for c in prod['campaigns']:
        e=rowsecs[c]/alloc[c]
        if not 0<e<=1.0001:raise ValueError(f'{c}: inconsistent accounting (row seconds {rowsecs[c]:.0f} vs allocated {alloc[c]:.0f})')
        out[c]={'row_seconds':rowsecs[c],'allocated_core_seconds':alloc[c],'efficiency':e}
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pilot',type=Path,required=True);p.add_argument('--affine',type=Path,required=True,help='frozen c8-full-affine-1 map')
    p.add_argument('--budget-core-hours',type=float,required=True,help='total production budget (all batches)');p.add_argument('--batches',type=int,default=4)
    p.add_argument('--threads',type=int,default=16);p.add_argument('--element-seconds',type=float,default=3600.)
    p.add_argument('--pilot-job',nargs='+',required=True,help='every Slurm submission attempt of the pilot, JOBID or JOBID:OFFSET (end-to-end efficiency from sacct)')
    p.add_argument('--spent-core-hours',type=float,required=True,help='core-hours already used (development, exact stage, pilot)');p.add_argument('--total-cap',type=float,default=50000.)
    p.add_argument('--chunk-points',type=int,default=65536);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--max-replicates',type=int,default=128,help='replicates per campaign before the sample multiplier takes over (C7 rule)')
    p.add_argument('--qmc-min-points',type=int,default=256,help='minimum QMC points per active graph in production (heavy-tailed integrands)')
    p.add_argument('--max-task-seconds',type=float,default=1800.,help='bound on one power task (sample interval): measured per-sample cost x chunk');a=p.parse_args()
    if a.max_task_seconds*4>a.element_seconds*16:raise ValueError('max-task-seconds must leave room for several tasks per element')
    if a.budget_core_hours+a.spent_core_hours>a.total_cap:raise ValueError(f'budget {a.budget_core_hours} + spent {a.spent_core_hours} exceeds the total cap {a.total_cap}')
    pilot=a.pilot.resolve();prod=json.loads((pilot/'production.json').read_text());unit=json.loads((pilot/'unit_design.json').read_text())
    aff=json.loads(a.affine.read_text());J={int(L):np.array(v['J']) for L,v in aff['loops'].items()};A={int(L):np.array(v['adjusted']) for L,v in aff['loops'].items()}
    specs={s['name']:s for s in unit['campaigns'] if s['mode']!='exact'};final=a.out.resolve()
    if final.exists():raise FileExistsError(f'{final} exists: a frozen design bundle is never overwritten')
    out=final.with_name(final.name+f'.staging.{os.getpid()}');out.mkdir(parents=True) # the complete bundle is published by one rename
    groups=[];seen=set()
    for name,s in specs.items():
        if name in seen:continue
        g=[name]+([s['pair']] if s.get('pair') else []);seen|=set(g);groups.append(g)
    per={};counts_files={};rowsecs={}
    for g in groups:
        s=specs[g[0]];proj=(A if s['mode']=='power' else J)[s['L']][TOP]
        y={};n={};secs={};reps=0
        for name in g: # pool A/B pilot replicates (same estimator, same per-graph allocation in production)
            yy,nn,ss=per_graph(pilot/name,proj);mreps=json.loads((pilot/name/'manifest.json').read_text())['replicates']
            for (r,gr),v in yy.items():y[(r+reps,gr)]=v
            for gr,v in nn.items():n[gr]=v
            for gr,v in ss.items():secs[gr]=secs.get(gr,0.)+v
            rowsecs[name]=sum(ss.values());reps+=mreps
        counts,V0,C0,sig,gcost=allocate(y,n,secs,reps,s['mode']=='qmc',sum(secs.values())/reps)
        cf=f'counts_{g[0]}.txt';ng=json.loads((pilot/g[0]/'manifest.json').read_text())['inventory_count']
        # replicate multiplier r scales every member: var(r)=V1/r with V1=V0*sum(w^2/B), cost(r)=C1*r with C1=C0*sum(B)
        V1=V0*sum(float(specs[x]['weight'])**2/int(specs[x]['B']) for x in g);C1i=C0*sum(int(specs[x]['B']) for x in g)
        per['+'.join(g)]={'members':g,'role':s['role'],'level':s['level'],'L':s['L'],'mode':s['mode'],'V0_per_replicate':V0,'cost_per_replicate_seconds':C0,'V1':V1,'C1_integration':C1i,'pilot_replicates':reps,'active_graphs':len(counts),'counts_file':cf,'units_per_replicate':sum(1 for c in counts.values() if c),
                          '_counts':counts,'_sig':sig,'_cost':gcost,'_ng':ng,'_wfac':sum(float(specs[x]['weight'])**2/int(specs[x]['B']) for x in g),'_Bsum':sum(int(specs[x]['B']) for x in g),'_Bmax':max(int(specs[x]['B']) for x in g)}
        for x in g:counts_files[x]=cf
    eff=efficiencies(prod,a.pilot_job,rowsecs)
    for v in per.values(): # allocated core-seconds per unit replicate multiplier, at the measured end-to-end efficiency of the group
        e=sum(eff[x]['row_seconds'] for x in v['members'])/sum(eff[x]['allocated_core_seconds'] for x in v['members'])
        v['efficiency']=e;v['C1']=v['C1_integration']/v['efficiency']
    est={k:v for k,v in per.items() if v['role']=='estimator'};chk={k:v for k,v in per.items() if v['role']!='estimator'}
    budget=a.budget_core_hours*3600/a.batches;S=sum(math.sqrt(v['V1']*v['C1']) for v in est.values())
    def checked_level(v):
        lo=[x for x in est.values() if x['L']==v['L'] and x['level']=='refine8']
        if len(lo)!=1:raise ValueError('a check level needs exactly one refine8 group at the same loop')
        return lo[0]
    def split(m:float,Bmax:int)->tuple[int,int]:
        """(replicate multiplier r, sample multiplier s) for a Neyman multiplier m: replicates at most 128 per campaign
        (the C7 rule), the rest as a power-of-two sample multiplier on the frozen per-graph counts."""
        r=1
        while Bmax*2*r<=a.max_replicates and m/(2*r)>=1:r*=2
        s=1 if m<=r else 2**max(0,round(math.log2(m/r)));return r,s
    def finalize(v): # counts with the QMC per-graph floor at the chosen s; variance and allocated cost per batch
        c=dict(v['_counts'])
        if v['mode']=='qmc':
            need=max(1,math.ceil(a.qmc_min_points/v['s']));need=1<<(need-1).bit_length()
            c={g:max(n,need) for g,n in c.items()}
        V0=sum(v['_sig'][g]**2/c[g] for g in c);C0=sum(v['_cost'][g]*c[g] for g in c)
        v['counts_final']=c;v['var_batch']=V0*v['_wfac']/(v['r']*v['s']);v['cost_batch']=C0*v['_Bsum']*v['r']*v['s']/v['efficiency']
    def batch_cost():return sum(v['cost_batch'] for v in per.values())
    estb=budget
    for _ in range(60):
        for v in est.values():v['neyman_m']=estb*math.sqrt(v['V1']/v['C1'])/S;v['r'],v['s']=split(v['neyman_m'],v['_Bmax'])
        for v in chk.values():c=checked_level(v);v['r'],v['s']=c['r'],c['s']
        for v in per.values():finalize(v)
        if batch_cost()<=budget:break
        estb*=budget/batch_cost()*.97
    while batch_cost()>budget: # rounding: halve the sample multiplier (else the replicates) with the least variance loss per saved cost
        cand=[v for v in est.values() if v['s']>1 or v['r']>1]
        if not cand:raise ValueError(f'infeasible: the minimum design costs {batch_cost()/3600:.1f} core-hours per batch > budget {budget/3600:.1f}')
        def loss(v):
            f=2 if v['s']>1 else v['r']/max(1,v['r']//2);return v['var_batch']*(f-1)/(v['cost_batch']*(1-1/f))
        v=min(cand,key=loss)
        if v['s']>1:v['s']//=2
        else:v['r']//=2
        finalize(v)
        for c in chk.values():
            lv=checked_level(c);c['r'],c['s']=lv['r'],lv['s'];finalize(c)
    design={};newunit={'campaigns':[]};var=0.
    for key,v in per.items():
        r,s_=v['r'],v['s']
        if v['role']=='estimator':var+=v['var_batch']
        full=[0]*v['_ng']
        for gr,c in v['counts_final'].items():full[gr]=c
        (out/v['counts_file']).write_text(str(v['_ng'])+'\n'+''.join(f'{i} {c}\n' for i,c in enumerate(full)))
        # R26: bounded tasks. A task is a contiguous sample interval of one (replicate, graph) stream; its duration is at most
        # chunk x (largest measured per-sample cost of the group), so it always fits a checkpoint well inside the element limit.
        worst=max(v['_cost'][g] for g in v['counts_final']);chunk_power=max(1,int(a.max_task_seconds//worst))
        v['max_task_seconds_predicted']=min(chunk_power,max(c*s_ for c in v['counts_final'].values()))*worst if v['mode']=='power' else None
        for x in v['members']:
            sp=specs[x];cost=v['cost_batch']*int(sp['B'])/v['_Bsum'];shards=max(1,math.ceil(cost/(a.element_seconds*a.threads)))
            chunk=a.chunk_points if sp['mode']=='qmc' else chunk_power
            units=int(sp['B'])*r*sum((math.ceil(c*s_/chunk) if chunk else 1) for c in v['counts_final'].values());shards=min(shards,units)
            ck=max(16*a.threads,math.ceil(units/shards/8)) # >= 16 tasks per thread per invocation; about 8 checkpoints per element
            design[x]={'multiplier':s_,'replicate_multiplier':r,'shards':shards,'checkpoint_tasks':ck,'chunk_points':chunk}
            newunit['campaigns'].append({**{k:sp[k] for k in sp if k!='counts'},'n':0,'counts':counts_files[x]})
    for v in per.values():
        for k in [k for k in v if k.startswith('_')]+['counts_final']:v.pop(k,None)
    cost_batch=batch_cost()/3600
    if cost_batch*a.batches>a.budget_core_hours*(1+1e-9):raise ArithmeticError('design exceeds the budget')
    se_batch=math.sqrt(var);meta={'groups':per,'budget_core_hours':a.budget_core_hours,'batches':a.batches,'predicted_se_per_batch':se_batch,'predicted_se_total':se_batch/math.sqrt(a.batches),
        'predicted_allocated_core_hours_per_batch':cost_batch,'predicted_allocated_core_hours_total':cost_batch*a.batches,'spent_core_hours':a.spent_core_hours,'total_cap':a.total_cap,'pilot_efficiency':eff,'pilot_job':a.pilot_job,'pilot':str(pilot),'pilot_production_sha256':hashlib.sha256((pilot/'production.json').read_bytes()).hexdigest(),'affine_sha256':hashlib.sha256(a.affine.read_bytes()).hexdigest(),
        'rule':'per-graph Neyman n_g~sigma_g/sqrt(c_g) (floor 3% of median, >=1, QMC powers of two); group Neyman multiplier m~sqrt(V1/C1) split into replicates (<= max_replicates per campaign) and a power-of-two sample multiplier; QMC per-graph floor qmc_min_points; integer allocation within the budget; checks take the multipliers of refine8'}
    pm={c:json.loads((pilot/c/'manifest.json').read_text()) for c in prod['campaigns']}
    trained={int(x['seed']) for v in aff['loops'].values() for x in v.get('training',[]) if 'seed' in x}
    meta['forbidden_seeds']=sorted({int(m['seed']) for m in pm.values()}|trained) # production may never reuse pilot or training streams
    meta['forbidden_batch_seeds']=[int(prod['seed'])]
    # Expected numerical inputs of production (R16): the pilot's verified hashes, plus the exact-zero lists of the pilot
    # snapshot (pilot manifests predate exact-zero hashing), all identical across the pilot's campaigns of one loop.
    exp={}
    for c,m in pm.items():
        L=int(m['L']);ins=campaign_inputs(pilot/c,m)
        for name,h in m['input_sha256'].items():
            if exp.setdefault(name,h)!=h:raise ValueError(f'pilot campaigns disagree on input {name}')
        z=ins/f'exact_zero_L{L}.txt';hz=digest(z) if z.exists() else 'absent'
        if exp.setdefault(z.name,hz)!=hz:raise ValueError(f'pilot campaigns disagree on {z.name}')
    meta['expected_input_sha256']=exp
    s5=aff.get('sources',{}).get('5') # the deterministic loop-5 input is frozen with the design (R19)
    if not s5 or len(s5['degrees'])<2:raise ValueError('the affine map must carry an exact loop-5 campaign with at least two degrees')
    meta['exact_loop5']={'manifest_sha256':s5['manifest_sha256'],'chosen_degree':s5['degrees'][-1],'previous_degree':s5['degrees'][-2]}
    dump(out/'design.json',design);dump(out/'unit_production.json',newunit)
    meta['design_sha256']=digest(out/'design.json');meta['unit_sha256']=digest(out/'unit_production.json')
    meta['counts_sha256']={cf:digest(out/cf) for cf in sorted(set(counts_files.values()))}
    dump(out/'design_meta.json',meta);os.rename(out,final);out=final
    print(json.dumps({**{k:meta[k] for k in ('predicted_se_per_batch','predicted_se_total','predicted_allocated_core_hours_per_batch','predicted_allocated_core_hours_total','batches')},
                      'groups':{k:{'r':v['r'],'s':v['s'],'eff':round(v['efficiency'],3),'sd_C8_contribution':math.sqrt(v['var_batch']),'core_hours':round(v['cost_batch']/3600,1)} for k,v in per.items()}},indent=1))
if __name__=='__main__':main()
