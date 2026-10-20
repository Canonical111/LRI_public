#!/usr/bin/env python3
"""The C63d fallback of the pilot -> Neyman design (PLAN E.5, HD16; port of LRI_C8_HPC/tools/design8.py with the d=3
inputs). Labelled `fallback` in every bundle and report; it stands in only while H6 (C62d's design.py at the sha256 of
HANDOFF_design.json) is absent, and a non-test plan from a fallback bundle needs --approved-fallback "<user ref>".

  design_fallback.py freeze --pilot PF [--pc PC] --cost-model M --out BUNDLE (--target-se S | --target-rel R | --budget-core-hours B)
                     [--test-only] [--batches K] [--spent-core-hours X] [--total-cap Y] [--seeds-log FILE] [--eta-node E]
                     [--variance-margin 1.5] [--min-points 4096] [--min-replicates 32] [--max-replicates 128]
  design_fallback.py report --pilot PF [--pc PC] --cost-model M [--target-se S] [--json FILE]

Rules (design8.py's; the same A-DES-1 list as the vendored tool):
  * per graph and campaign sigma_g^2 = n_g Var_rep(J_8 . jets) (ddof 1) from PF's merged graph_replicates.csv, J the
    order-8 complex-step Jacobian at PF's means from the VENDORED order8_assembly.jacobians (inputs/two_loop.json,
    half_d 1.5): design8.py's d=1 coefficient code is not kept here;
  * c_g from the campaign-keyed cost model (campaign:sector:L:graph, C62d's R05), never from a scheduling basis (the
    campaign's prior_cost_model.json, synthetic_cost_model.json, tools/bootstrap_proxy.json are never opened: the
    campaign is read with production.verify_base(scheduling_copies=False), S3-013); a freeze of a campaign planned on
    another basis reads costs only from an explicitly supplied identity-matching measured model (D.5). The model must
    match the pilot's whole HD11 identity (executable sha256, the CPU model of its plan host, its MP self-check mode:
    production.identity_problems), and every c_g is the model's seconds per point times its measured overhead factor for
    the pilot's MP self-check mode (production.mp_factor, 1 in the model's own mode), as production.py plans (S3-003);
  * eta_node from the ledger accounting of the campaign (tools/accounting.py); --eta-node only for test-only freezes;
  * a sigma floor of 3% of the stratum median; per-graph Neyman base counts n_g ~ sigma_g/sqrt(c_g), powers of two,
    >= --min-points, with the stratum-median imputation only for the variance of unsampled graphs: every inventory
    graph, sampled or not, takes its own measured campaign-keyed c_g, and a graph without one is refused (S3-004);
  * stratum multipliers m ~ sqrt(V/C), split into replicates r in [32, 128] (equal for campaigns a and b of one
    (sector, L)) and a power-of-two sample multiplier s per stratum; predicted SE x --variance-margin against a target;
    an integer budget gate (--spent-core-hours, --total-cap); the minimum batch count K for the per-batch caps, and a
    smaller --batches refused;
  * the bundle (design.json, counts/<campaign>_<sector>_L<L>.txt, design_meta.json) is published atomically and never
    overwritten; design_meta.json lists the forbidden seeds (the pilot's and every seed of --seeds-log / $C8_SEEDS).
A pilot_subset campaign (PA, PC) has no design: refused with 65 before any group data is read (R01).
--pc PC (the conservative tail rule, RECON:1373; user decision 2026-10-08 "produce with the plan's conservative rule"):
  * PC is the pilot's confirm campaign (pilot_report.require_subset: pilot_subset, selection role confirm, its
    subset-check passed), read as pilot_report reads it, and bound to PF (bind_pc): its own verified selection.json is a
    confirm selection of PF's inputs manifest whose screen names PF's identity (pilot_report.bound: manifest sha256,
    campaign role, selection and every group's scientific identity), and PC has PF's inputs manifest, executable,
    backend, numerics, MP mode and test_only flag; a PC of another pilot is refused (1) before any allocation;
  * every graph-campaign of PC is allocated by max(sigma_PF, sigma_PC): sigma_PF the 3%-floored sigma above (PF's
    4,096 points), sigma_PC = sqrt(32768 Var_rep(J_8 . jets)) from PC's merged 32,768-point full-stream replicates
    (sigma_hat, the one normalisation of both; J_8 from PF's means); a PC graph at another length is refused;
  * design.json's conservative_tail_rule records every raised graph-campaign (both sigmas, the allocation sigma and the
    factor), the unchanged ones, and `monitored`: the graphs PC confirmed (pilot_report.confirm_graph: two-campaign mean
    xi(32,768) > 0.44; zero-channel graphs never), for the production tail monitor (assemble.tail_monitor has no input
    for a list: the bundle, which the production manifest names, carries it); design_meta.json binds PC's identity; the
    report carries the same block. Without --pc the bundle and the report are byte for byte as before.
"""
from __future__ import annotations
import argparse,hashlib,json,math,os,shutil,sys,tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,Refuse,digest,dump,load,utc
import assemble as asm
import production as prod
import pilot_report as pr

LABEL='fallback'
SIGMA_FLOOR=0.03;COST_FLOOR=1e-9;TARGETS_REL=(1e-2,3e-3,1e-3,5e-4,2.5e-4,1.44e-4);C8_MAGNITUDE=1500.
PC_POINTS=pr.CONFIRM_POINTS   # 32,768: the length of PC's sigma_hat in the conservative tail rule (RECON:1373)
PC_RULE=('RECON:1373 (user decision 2026-10-08, "produce with the plan\'s conservative rule"): every graph-campaign of the PC campaign is '
         'allocated by max(sigma_PF, sigma_PC), sigma_PF the 3%-floored sqrt(n Var_rep(J_8 . jets)) of PF at its 4,096 points, sigma_PC the same '
         'sqrt(32768 Var_rep(J_8 . jets)) of PC\'s merged 32,768-point replicates (J_8 at PF\'s means); the graphs PC confirmed (two-campaign mean '
         'xi(32,768) > 0.44, pilot_report.confirm_graph) are monitored: they stay on the production tail monitor')
SECTORS,CAMPAIGNS,LOOPS=('free','power'),('a','b'),tuple(range(3,9))

def strata_names()->list:return [f'free_L{L}'for L in LOOPS]+['free_L8_primitive']+[f'power_L{L}'for L in LOOPS]
def rgroup(st:str)->str:return st.replace('_primitive','')
def pow2_round(x:float)->int:return 1<<max(0,int(round(math.log2(x))))if x>1 else 1
def pow2_floor(x:float)->int:return 1<<max(0,int(math.floor(math.log2(x))))if x>=1 else 1

class Infeasible(Exception):
    def __init__(self,minimum):super().__init__(f'the minimum design costs {minimum:.1f} core-hours');self.minimum=minimum
class BatchesTooFew(Exception):
    def __init__(self,k):super().__init__(f'--batches is below the minimum batch count {k} for which every batch meets the caps');self.k=k

def read_csv(path:Path)->list[dict]:
    lines=Path(path).read_text().splitlines();head=lines[0].split(',')
    return [dict(zip(head,l.split(',')))for l in lines[1:]]

def model_identity(m:dict,model:dict)->float:
    """S3-003: the measured model against the pilot's complete HD11 identity (executable sha256, the CPU model of its plan
    host, its MP self-check mode; production.identity_problems, as `plan` checks it); returns the MP factor every cost is
    multiplied by (production.mp_factor: 1 in the model's own mode, else its measured overhead for the pilot's mode)."""
    prob=prod.identity_problems(model,m['executable_sha256'],(m.get('fingerprint')or{}).get('cpu_model'),m['mp_check'])
    if prob:
        why='; '.join(f'{k} model {x!r} vs pilot {y!r}'for k,(x,y) in prob.items())
        if m['cost_basis']!='measured':raise ValueError(f'the pilot was planned on the {m["cost_basis"]} basis: a freeze reads costs only from an explicitly supplied '
                                                        f'identity-matching measured model (D.5); this one is not (HD11): {why}')
        raise ValueError(f'the cost model does not match the pilot\'s identity (HD11): {why}')
    return prod.mp_factor(model,m['mp_check'])

def load_pilot(run:Path,model_path:Path)->dict:
    """PF through the campaign interface: verified manifest, configs, merged tables (never a scheduling copy, S3-013);
    the measured cost model, identity-matching, with its MP factor (S3-003); PF's campaign identity (pilot_report.identity,
    what a PC's screen records and bind_pc compares)."""
    run=Path(run).resolve();m,I,mh,_=prod.verify_base(run,check_executable=False,accept_tool_change=True,vendored=True,scheduling_copies=False)
    asm.refuse_subset(m,'design_fallback.py')
    model,_=prod.read_cost_model(model_path,m['backend']);mpf=model_identity(m,model)
    groups={};means={'free':{},'power':{}};acc={};merged={};science={}
    for g in m['groups']:
        p,cfg=prod.group_of(run,m,g['name']);d=prod.validate_merged(p,cfg,m,mh);k=2*(9-cfg['L'])
        merged[g['name']]=digest(p/'merged.json');science[g['name']]=asm.group_science(d)
        rows=read_csv(p/'graph_replicates.csv');Y={}
        for r in rows:Y.setdefault(int(r['graph']),{})[int(r['replicate'])]=[float(r[f'jet_{i}'])for i in range(k)]
        groups[(cfg['campaign'],cfg['sector'],cfg['L'])]=dict(cfg=cfg,Y=Y,reps=cfg['replicates'],points={int(a):int(b)for a,b in cfg['counts'].items()})
        acc.setdefault((cfg['sector'],cfg['L']),[]).append(np.asarray(d['batches'],float).mean(0))
    for (s,L),v in acc.items():means[s][L]=sum(v)/len(v)
    inv=load(I.where('inventory.json'))
    return dict(run=run,m=m,mh=mh,I=I,inv=inv,groups=groups,means=means,model=model,model_path=str(model_path),mpf=mpf,
                identity=pr.identity(run,m,mh,merged,science))

def jacobian_rows(P:dict)->dict:
    B2,_=asm.two_loop(8,P['I'].dir,P['I'].m['sha256'])
    loops=[L for L in LOOPS if L in P['means']['free']and L in P['means']['power']]
    tot={L:P['means']['free'][L]+P['means']['power'][L]for L in loops}
    if loops!=list(LOOPS):raise ValueError('the pilot does not hold every loop 3..8 in both sectors')
    J=asm.vendored().jacobians(tot,B2,8,asm.HALF_D)
    return {L:np.asarray(J[L])[8]for L in loops}

def sigma_hat(J,reps:dict,n:int)->float:
    """sigma_g = sqrt(n Var_rep(J . jets)) (ddof 1) of one graph-campaign from its replicate jets {replicate: jets} at its
    n points: PF's sigma in graph_table and PC's in pc_raise (the conservative tail rule), one normalisation."""
    y=np.array([np.dot(J,reps[r])for r in sorted(reps)]);return math.sqrt(max(0.,n*float(np.var(y,ddof=1))))

def graph_table(P:dict,J8:dict|None=None)->dict:
    """{(c, s, L): {graph: dict(sigma, cost, piloted, stratum)}} for every inventory graph; the variance of an unsampled
    graph takes the stratum median, its cost is its own (S3-004); every cost is the model's campaign-keyed seconds per
    point x the pilot's MP factor (S3-003); a sigma floor of 3% of the stratum median. J8: jacobian_rows(P), computed
    here when not given."""
    J8=jacobian_rows(P)if J8 is None else J8;costs=P['model']['seconds_per_point'];mpf=float(P['mpf']);out={}
    def cost_of(c,s,L,g):
        key=f'{c}:{s}:{L}:{g}'
        if key not in costs:raise ValueError(f'the cost model has no key {key}: every inventory graph needs its own measured campaign-keyed cost (S3-004)')
        return max(COST_FLOOR,float(costs[key])*mpf)
    for (c,s,L),G in P['groups'].items():
        rows=P['inv'][s][str(L)];prim={r['id']:bool(r.get('primitive'))for r in rows};T={}
        for g,reps in G['Y'].items():
            n=G['points'][g];T[g]=dict(sigma=sigma_hat(J8[L],reps,n),cost=cost_of(c,s,L,g),piloted=True,stratum=prod.stratum_of(s,L,prim[g]),n_pilot=n)
        for st in {prod.stratum_of(s,L,prim[r['id']])for r in rows}:
            mem=[r['id']for r in rows if prod.stratum_of(s,L,prim[r['id']])==st];pil=[g for g in mem if g in T and T[g]['sigma']>0]
            if not pil:pil=[g for g in T if T[g]['sigma']>0]
            if not pil:raise ValueError(f'{c}_{s}_L{L}: no piloted graph with nonzero variance in stratum {st}')
            for g in mem:
                if g not in T:
                    T[g]=dict(sigma=float(np.median([T[x]['sigma']for x in pil])),cost=cost_of(c,s,L,g),piloted=False,stratum=st,n_pilot=0)
            med=float(np.median([T[g]['sigma']for g in mem if T[g]['piloted']and T[g]['sigma']>0]or[T[g]['sigma']for g in mem]))
            for g in mem:T[g]['sigma']=max(T[g]['sigma'],SIGMA_FLOOR*med)
        out[(c,s,L)]=T
    return out

# ---------------------------------------------------------------- the conservative tail rule (--pc; RECON:1373)
def load_pc(run:Path,P:dict):
    """--pc: the PC campaign as pilot_report reads it (require_subset: pilot_subset, selection role confirm, its subset-check
    passed; never a scheduling copy), bound to the pilot P (bind_pc)."""
    C=pr.require_subset(Path(run),'confirm');C.bound=bind_pc(C,P);return C

PC_SAME=('inputs_manifest_sha256','executable_sha256','backend','numerics','mp_check','test_only')
def bind_pc(C,P:dict)->dict:
    """The PC campaign C belongs to the pilot PF P, as pilot_report full binds a PC selection (S3-005, S3-R2-009): C is a
    pilot_subset campaign of a confirm selection (manifest and its own verified selection.json) of PF's inputs manifest,
    whose screen names PF's identity (pilot_report.bound: manifest sha256, campaign role, selection and every group's
    scientific identity), with PF's PC_SAME fields; else ValueError naming what differs (a PC of another pilot).
    Returns the identity record design_meta.json keeps: PC's identity (manifest, role, selection, scientific and merged
    sha256 per group), its selection role and seed, its seed, and the PF identity it was bound to."""
    m=C.m;pm=P['m'];sel=C.sel
    if m.get('campaign_role')!='pilot_subset'or sel.get('role')!='confirm'or(m.get('selection')or{}).get('role')!='confirm':
        raise ValueError(f'{C.run}: not a PC campaign (a pilot_subset campaign of a confirm selection)')
    for k in PC_SAME:
        if m.get(k)!=pm.get(k):raise ValueError(f'the PC campaign {C.run} has another {k} than PF ({m.get(k)!r} against {pm.get(k)!r}): a PC of another pilot')
    if sel.get('inputs_manifest_sha256')!=pm['inputs_manifest_sha256']:raise ValueError(f'the PC campaign {C.run}: its selection is not of PF\'s inputs manifest')
    pr.bound((sel.get('screen')or{}).get('pf_identity'),P['identity'],f'the PC campaign {C.run} (its selection\'s screen\'s PF)')
    return {**C.identity,'selection_role':sel.get('role'),'selection_seed':(m.get('selection')or{}).get('seed'),'seed':m.get('seed'),
            'pf_identity':{k:P['identity'].get(k)for k in ('run',)+pr.ID_KEYS}}

def pc_raise(T:dict,C,J8:dict)->dict:
    """RECON:1373 on the graph table T, in place: every graph-campaign (c, s, 8, g) of PC gets sigma = max(its sigma in T,
    sigma_hat(J_8, PC's replicate jets, 32768)); PC's graphs must be L8 at 32,768 points and in T. Returns the record:
    the rule, PC's identity, `raised` (sigma_before, sigma_pc_32768, sigma_alloc, factor), `unchanged`, `monitored` (the
    graphs PC confirmed, pilot_report.confirm_graph) and `undefined` (confirmations with an undefined tail statistic)."""
    raised=[];same=[];monitored=[];undefined=[]
    for (c,s,L),G in sorted(C.g.items()):
        if L!=8 or (c,s,L)not in T:raise ValueError(f'PC group {c}_{s}_L{L}: the conservative tail rule acts on L8 groups of PF only')
        for g in sorted(G['total']):
            n=G['total'][g]
            if n!=PC_POINTS:raise ValueError(f'PC {c}_{s}_L{L} graph {g}: {n} points, not {PC_POINTS} (RECON:1373 takes the 32,768-point sigma_hat)')
            if g not in T[(c,s,L)]:raise ValueError(f'PC {c}_{s}_L{L} graph {g} is not in PF\'s graph table')
            x=T[(c,s,L)][g];spc=sigma_hat(J8[L],{r:G['jets'][(r,g)]for r in range(G['reps'])},n);before=x['sigma']
            e={'campaign':c,'sector':s,'L':L,'graph':g,'points_pf':x['n_pilot'],'sigma_before':before,'sigma_pc_32768':spc}
            if spc>before:x['sigma']=spc;raised.append({**e,'sigma_alloc':spc,'factor':spc/before if before>0 else None})
            else:same.append(e)
    for key in sorted(C.sel['groups']):
        s=key.split(':')[0]
        for r in C.sel['groups'][key]:
            x=pr.confirm_graph(C,s,r['id'])
            if x.get('confirmed'):monitored.append({'sector':s,'graph':r['id'],'xi_mean_32768':x['xi_mean_32768']})
            elif x.get('undefined'):undefined.append({'sector':s,'graph':r['id'],'undefined':x['undefined']})
    return {'rule':PC_RULE,'pc':{k:C.bound.get(k)for k in ('run','manifest_sha256','campaign_role','selection_sha256','selection_seed','seed')},
            'graph_campaigns':len(raised)+len(same),'raised':raised,'unchanged':same,
            'monitored':sorted(monitored,key=lambda x:(x['sector'],x['graph'])),'undefined':undefined}

def base_counts(T:dict,min_points:int,pilot_points:int)->dict:
    out={}
    for key,TT in T.items():
        byst={}
        for g,x in TT.items():byst.setdefault(x['stratum'],[]).append(g)
        cnt={}
        for st,gs in byst.items():
            unit=pilot_points*sum(TT[g]['cost']for g in gs);den=sum(TT[g]['sigma']*math.sqrt(TT[g]['cost'])for g in gs);k=unit/den if den>0 else 0.
            for g in gs:cnt[g]=max(min_points,pow2_round(max(1.,k*TT[g]['sigma']/math.sqrt(TT[g]['cost']))))
        out[key]=cnt
    return out

def stratum_sums(T:dict,b:dict,eta:float)->dict:
    out={st:dict(V1=0.,C1=0.,V1_imputed=0.,graphs=0)for st in strata_names()}
    for key,TT in T.items():
        for g,x in TT.items():
            o=out[x['stratum']];v=.25*x['sigma']**2/b[key][g];o['V1']+=v;o['C1']+=x['cost']*b[key][g]/eta;o['graphs']+=1
            if not x['piloted']:o['V1_imputed']+=v
    return out

class Opts:
    def __init__(self,a):
        self.min_points=a.min_points;self.min_reps=a.min_replicates;self.max_reps=a.max_replicates;self.margin=a.variance_margin
        self.task_seconds=60.;self.min_chunk=256;self.max_task_seconds=120.;self.threads=16;self.index_hours=1.5;self.max_tasks=5*10**7
        self.max_checkpoints=2*10**5;self.max_batches=64
        if not(1<=self.min_reps<=self.max_reps)or self.min_reps<32 or self.max_reps>128:raise ValueError('replicates must lie in [32, 128] (E.5)')
        if self.min_points<4096 or not prod.pow2(self.min_points):raise ValueError('--min-points must be a power of two >= 4096 (E.5)')

def evaluate(S,r,s,K,margin)->dict:
    act=[k for k in S if S[k]['graphs']]
    var=sum(S[k]['V1']/(r[rgroup(k)]*s[k])for k in act);cost=sum(S[k]['C1']*r[rgroup(k)]*s[k]for k in act)
    vim=sum(S[k]['V1_imputed']/(r[rgroup(k)]*s[k])for k in act)
    return dict(variance_per_batch=var,se_raw_total=math.sqrt(var/K),se_total=margin*math.sqrt(var/K),cost_per_batch_core_hours=cost/3600,
                cost_total_core_hours=K*cost/3600,imputed_variance_share=vim/var if var>0 else 0.)

def split(S,m,o)->tuple[dict,dict]:
    r={};s={}
    for grp in {rgroup(k)for k in S}:
        mm=max([m[k]for k in S if rgroup(k)==grp]+[0.]);rr=o.min_reps
        while 2*rr<=o.max_reps and mm/(2*rr)>=1:rr*=2
        r[grp]=rr
    for k in S:s[k]=pow2_round(m[k]/r[rgroup(k)])if m[k]>r[rgroup(k)]else 1
    return r,s

def optimize(S,K,o,target_se=None,budget_ch=None):
    act=[k for k in S if S[k]['graphs']and S[k]['V1']>0];root=sum(math.sqrt(S[k]['V1']*S[k]['C1'])for k in act)
    lam=o.margin**2*root/(K*target_se**2)if target_se is not None else (budget_ch*3600/(K*root)if root>0 else 0.)
    m={k:(lam*math.sqrt(S[k]['V1']/S[k]['C1'])if k in act else 0.)for k in S}
    r,s=split(S,m,o);ev=evaluate(S,r,s,K,o.margin)
    if target_se is not None:
        while act and ev['se_total']>target_se*(1+1e-12):
            k=max(act,key=lambda k:(S[k]['V1']/(2*r[rgroup(k)]*s[k]))/(S[k]['C1']*r[rgroup(k)]*s[k]));s[k]*=2;ev=evaluate(S,r,s,K,o.margin)
    else:
        while ev['cost_total_core_hours']>budget_ch*(1+1e-12):
            cand=[k for k in act if s[k]>1]
            if cand:k=min(cand,key=lambda k:(S[k]['V1']/(r[rgroup(k)]*s[k]))/(S[k]['C1']*r[rgroup(k)]*s[k]/2));s[k]//=2
            else:
                grps=[g for g in r if r[g]>o.min_reps]
                if not grps:raise Infeasible(evaluate(S,{g:o.min_reps for g in r},{k:1 for k in S},K,o.margin)['cost_total_core_hours'])
                g=max(grps,key=lambda g:sum(S[k]['C1']for k in S if rgroup(k)==g));r[g]//=2
            ev=evaluate(S,r,s,K,o.margin)
    return r,s,ev

def caps(T,b,r,s,o)->dict:
    Tck=max(16*o.threads,256);tasks={c:0 for c in CAMPAIGNS};ckpt=0;maxtask=0.;worst=None
    for (c,sec,L),TT in T.items():
        n_g=0;secs=0.
        for g,x in TT.items():
            n=b[(c,sec,L)][g]*s[x['stratum']];cg=x['cost'];ch=pow2_floor(o.task_seconds/cg)if o.task_seconds>=cg else 1
            ch=min(max(o.min_chunk,ch),n);rr=r[rgroup(x['stratum'])];n_g+=rr*(n//ch);secs+=rr*n*cg
            if ch*cg>maxtask:maxtask=ch*cg;worst=(c,sec,L,g)
        tasks[c]+=n_g;nsh=max(1,math.ceil(secs/(o.index_hours*3600*o.threads*0.9)));ckpt+=math.ceil(n_g/Tck)+nsh
    ok=all(v<=o.max_tasks for v in tasks.values())and ckpt<=o.max_checkpoints and max(r.values())<=o.max_reps
    return dict(ok=ok,tasks_per_campaign=tasks,checkpoints=ckpt,max_replicates=max(r.values()),predicted_max_task_seconds=maxtask,worst_task=worst,task_ok=maxtask<=o.max_task_seconds)

def design_for(T,o,eta,target_se=None,budget_ch=None,batches=None,pilot_points=4096)->dict:
    b=base_counts(T,o.min_points,max(pilot_points,o.min_points));S=stratum_sums(T,b,eta);kmin=None;out=None
    for K in range(1,o.max_batches+1):
        r,s,ev=optimize(S,K,o,target_se,budget_ch);cp=caps(T,b,r,s,o)
        if not cp['task_ok']:raise ValueError(f'graph {cp["worst_task"]}: the shortest allowed task is predicted at {cp["predicted_max_task_seconds"]:.1f} s > 120 s')
        if cp['ok']:kmin=K;out=(r,s,ev,cp);break
    if kmin is None:raise ValueError('no batch count up to 64 meets the per-batch caps')
    if batches is not None:
        if batches<kmin:raise BatchesTooFew(kmin)
        r,s,ev=optimize(S,batches,o,target_se,budget_ch);cp=caps(T,b,r,s,o);out=(r,s,ev,cp)
    r,s,ev,cp=out
    return dict(b=b,S=S,r=r,s=s,ev=ev,caps=cp,K=batches or kmin,K_min=kmin)

def eta_node(P:dict,test_only:bool,override)->tuple[float,str]:
    if override is not None:
        if not test_only:raise ValueError('--eta-node is for test-only freezes; a real freeze takes eta_node from the ledger accounting')
        return float(override),'--eta-node (test-only)'
    import accounting
    r=accounting.account(P['run'],dict(os.environ))
    if not r['eta_node']:raise ValueError('eta_node is unavailable from the accounting (no work attempt)')
    return 1.0/max(1.0,r['eta_node']),'tools/accounting.py (busy / allocated core-seconds of the work roles)'

def seeds_from_log(path)->list:
    if path is None or not Path(path).exists():return []
    return sorted(prod.read_seed_file(Path(path)))

def publish_bundle(out:Path,files:dict)->None:
    """Atomic and never overwritten: the bundle is written in a temporary sibling and renamed (no clobber)."""
    out=Path(out).resolve()
    if out.exists():raise FileExistsError(f'{out} exists: a frozen bundle is never overwritten')
    tmp=Path(tempfile.mkdtemp(prefix=out.name+'.tmp.',dir=out.parent))
    try:
        for rel,data in files.items():(tmp/rel).parent.mkdir(parents=True,exist_ok=True);(tmp/rel).write_bytes(data)
        os.rename(tmp,out)
    except BaseException:shutil.rmtree(tmp,ignore_errors=True);raise

def freeze(a)->dict:
    o=Opts(a);P=load_pilot(a.pilot,a.cost_model);C=load_pc(a.pc,P)if getattr(a,'pc',None)else None   # a PC of another pilot: refused here
    if not a.test_only and P['m']['test_only']:raise ValueError('a test-only pilot gives only a --test-only bundle')
    eta,src=eta_node(P,a.test_only,a.eta_node)
    targets=[x is not None for x in (a.target_se,a.target_rel,a.budget_core_hours)]
    if sum(targets)!=1:raise ValueError('give exactly one of --target-se, --target-rel and --budget-core-hours')
    target=a.target_se if a.target_se is not None else(a.target_rel*a.c8_magnitude if a.target_rel is not None else None)
    budget=None
    if a.budget_core_hours is not None:
        if a.budget_core_hours!=int(a.budget_core_hours):raise ValueError('--budget-core-hours must be an integer')
        budget=a.budget_core_hours
        if a.total_cap is not None and a.spent_core_hours+budget>a.total_cap:raise ValueError(f'--spent-core-hours {a.spent_core_hours:g} + budget {budget:g} > --total-cap {a.total_cap:g}')
    J8=jacobian_rows(P);T=graph_table(P,J8);tail=pc_raise(T,C,J8)if C is not None else None
    try:D=design_for(T,o,eta,target,budget,a.batches,max([G['points'][g]for G in P['groups'].values()for g in G['points']]+[4096]))
    except Infeasible as e:raise ValueError(f'infeasible budget: {e}; the minimum is {e.minimum:.1f} core-hours')
    except BatchesTooFew as e:raise ValueError(f'{e} (K = {e.k})')
    if a.total_cap is not None and a.spent_core_hours+D['ev']['cost_total_core_hours']>a.total_cap:
        raise ValueError(f'the design costs {D["ev"]["cost_total_core_hours"]:.1f} core-hours; with --spent-core-hours {a.spent_core_hours:g} it exceeds --total-cap {a.total_cap:g}')
    files={}
    for (c,s,L),cnt in sorted(D['b'].items()):files[f'counts/{c}_{s}_L{L}.txt']=''.join(f'{g} {cnt[g]}\n'for g in sorted(cnt)).encode()
    design={'schema':prod.DESIGN_SCHEMA,'label':LABEL,'strata':{st:{'s':int(D['s'][st]),**{k:float(v)for k,v in D['S'][st].items()}}for st in D['S']},
            'replicates':{f'{s}_L{L}':int(D['r'][f'{s}_L{L}'])for s in SECTORS for L in LOOPS},'batches':int(D['K']),'batches_minimum':int(D['K_min']),
            'prediction':D['ev'],'caps':D['caps'],'eta':{'value':eta,'source':src},'rule':'design8.py rules (E.5): n_g ~ sigma_g/sqrt(c_g), sigma floor 3% of the stratum median, >= 4096, powers of two, r in [32, 128], margin x'+f'{o.margin:g}'}
    if tail is not None:design['conservative_tail_rule']=tail
    files['design.json']=(json.dumps(design,indent=1,sort_keys=True)+'\n').encode()
    forb=sorted({int(P['m']['seed'])}|set(seeds_from_log(a.seeds_log or os.environ.get('C8_SEEDS'))))
    meta={'schema':prod.DESIGN_SCHEMA,'label':LABEL,'test_only':bool(a.test_only),'design_sha256':hashlib.sha256(files['design.json']).hexdigest(),
          'counts_sha256':{k:hashlib.sha256(v).hexdigest()for k,v in files.items()if k.startswith('counts/')},'inputs_manifest_sha256':P['m']['inputs_manifest_sha256'],
          'numerics':P['m']['numerics'],'pilot':{'run':str(P['run']),'manifest_sha256':P['mh'],'seed':P['m']['seed'],'campaign_role':P['m']['campaign_role']},
          'cost_model':{'path':P['model_path'],'sha256':digest(P['model_path']),'executable_sha256':P['model']['executable_sha256'],'cpu_model':P['model'].get('cpu_model'),
                        'mp_check':P['model'].get('mp_check'),'mp_check_factor':P['mpf'],'pilot_mp_check':P['m']['mp_check']},
          'executable_sha256':P['m']['executable_sha256'],'forbidden_seeds':forb,'target_se':target,'budget_core_hours':budget,'spent_core_hours':a.spent_core_hours,
          'made_utc':utc(),'tool':'tools/design_fallback.py','tool_sha256':digest(Path(__file__))}
    if C is not None:meta['pc']=C.bound;meta['monitored_graphs']=tail['monitored']
    files['design_meta.json']=(json.dumps(meta,indent=1,sort_keys=True)+'\n').encode()
    publish_bundle(a.out,files)
    return {'bundle':str(Path(a.out).resolve()),'label':LABEL,'batches':D['K'],'batches_minimum':D['K_min'],'prediction':D['ev'],'replicates':design['replicates'],
            'meta_sha256':hashlib.sha256(files['design_meta.json']).hexdigest(),
            **({'conservative_tail_rule':{'raised':len(tail['raised']),'unchanged':len(tail['unchanged']),'monitored':len(tail['monitored'])}}if tail else{})}

def report(a)->dict:
    o=Opts(a);P=load_pilot(a.pilot,a.cost_model);C=load_pc(a.pc,P)if getattr(a,'pc',None)else None
    eta,src=eta_node(P,P['m']['test_only'],a.eta_node);J8=jacobian_rows(P);T=graph_table(P,J8);tail=pc_raise(T,C,J8)if C is not None else None
    rows=[]
    for rel in TARGETS_REL:
        se=rel*a.c8_magnitude
        try:D=design_for(T,o,eta,se);rows.append({'target_rel':rel,'target_se':se,'batches':D['K'],**D['ev']})
        except (ValueError,Infeasible)as e:rows.append({'target_rel':rel,'target_se':se,'error':str(e)})
    if a.target_se is not None:
        D=design_for(T,o,eta,a.target_se);rows.append({'target_se':a.target_se,'batches':D['K'],**D['ev']})
    # the plug-in SE of its own design at alpha = 1/2 (E.7 cross-check): sum over graphs of sigma^2/(4 n R)
    return {'label':LABEL,'eta':{'value':eta,'source':src},'alpha':0.5,'rows':rows,'graphs':sum(len(v)for v in T.values()),
            **({'conservative_tail_rule':tail}if tail is not None else{})}

def common(q):
    q.add_argument('--pilot',type=Path,required=True);q.add_argument('--cost-model',type=Path,required=True);q.add_argument('--eta-node',type=float)
    q.add_argument('--pc',type=Path,help='the pilot\'s PC campaign (confirm): the conservative tail rule (RECON:1373)')
    q.add_argument('--variance-margin',type=float,default=1.5);q.add_argument('--min-points',type=int,default=4096);q.add_argument('--min-replicates',type=int,default=32)
    q.add_argument('--max-replicates',type=int,default=128);q.add_argument('--c8-magnitude',type=float,default=C8_MAGNITUDE);q.add_argument('--target-se',type=float)

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('freeze');common(q);q.add_argument('--out',type=Path,required=True);q.add_argument('--test-only',action='store_true')
    q.add_argument('--target-rel',type=float);q.add_argument('--budget-core-hours',type=float);q.add_argument('--batches',type=int)
    q.add_argument('--spent-core-hours',type=float,default=0.);q.add_argument('--total-cap',type=float);q.add_argument('--seeds-log',type=Path)
    q=s.add_parser('report');common(q);q.add_argument('--json',type=Path)
    a=p.parse_args(argv)
    try:
        r=freeze(a)if a.cmd=='freeze'else report(a)
        if a.cmd=='report'and a.json:dump(a.json,r)
    except Refuse as e:print(f'design_fallback: {e}',file=sys.stderr);return e.code
    except (ValueError,FileExistsError,OSError)as e:print(f'design_fallback: {e}',file=sys.stderr);return 1
    print(json.dumps(r,indent=1,default=str));return 0
if __name__=='__main__':sys.exit(main())
