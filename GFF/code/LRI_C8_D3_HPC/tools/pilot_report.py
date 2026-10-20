#!/usr/bin/env python3
"""The pilot report (PLAN E.6, E.7; RECON section 6.3.6; schema c8-d3-pilot-report-1). C63d's tool.

  pilot_report.py subset-check RUN                 (inside the merge job of a pilot_subset campaign, D.13)
  pilot_report.py stage-a RUN [--output FILE]      (PA: A-PIL-2's stage-A report with its GO/NO-GO; --out is an alias)
                  [--eta-node E] [--line-cap SU] [--spent SU] [--pf-nodes N] [--pc-nodes N]
  pilot_report.py screen --pf PF --pa PA --out FILE  (action 1 on every PF L8 graph + PA's unscreened confirmations)
  pilot_report.py full --pa PA --pf PF --pc-selection FILE [--pc PC] (--output FILE | --out DIR) [--markdown FILE]
                       [--cost-model M] [--eta-node E] [--design-bundle B] [--target-cost-model T]

stage-a: GO needs no mp_alarm in PA's graph_promotions.csv, no worker failure (failure records, failed work attempts)
and every pre-registered branch's peak reservation (PF at R = 8, PF with R = 16 at L8, action 4's mixed R, each with
its PC step) within the remaining pilot line, re-projected from the measured f_E, eta and per-graph cost; otherwise
NO-GO with the reasons, and the pilot stops and the user is asked (A-PIL-2). The line is C8_PILOT_SU_CAP (or
--line-cap) and its committed SU come from tools/budget.py (or --spent); eta from tools/accounting.py (or --eta-node).
full writes pilot_report.json (--output FILE, or DIR/pilot_report.json with --out DIR), growth_c63d.csv and
sigma_cost.csv next to it, and PILOT_REPORT.md with --markdown (A-PIL-5). Provenance (S3-005, S3-006, S3-R2-009): a
screen file records PF's and PA's campaign identities (manifest, role, selection sha256 and every group's SCIENTIFIC
identity, assemble.group_science: the scientific tables' sha256s and merged.json without its timing; the merged.json
sha256s are recorded but never compared, as a timing-only re-merge after a recovered index changes them); full refuses a
PC selection whose recorded screen names another PF or PA, and a C8_pilot_result.json that does not belong to PF (its
source manifest, merged files, scientific identities, role, test_only flag, build, numerics, MP mode, allocation and
two-loop pin against PF's current ones; a re-merged PF is re-assembled, as its merge job does, which supersedes a result
whose science is unchanged). A completed PC therefore stays usable after a timing-only re-merge of PA or PF; full
records the PC cap against PF's current L8 row seconds (pc_cap; informative, never a refusal).
Target site (S3-010): the cost table projects to the site of C8_SITE (tools/budget.py's profile; Expanse when unset) on
its lane node (allocated CPUs per node: Expanse compute 128, symmetry amdq 64, defq 80) and records the site, its unit,
the CPU of the lane PARTITION (budget.partition_cpu: symmetry defq and debugq are Intel Gold 6148; S3-R2-004) and the
CPU PF was measured on; PF's measurements project to another CPU only with --target-cost-model (a measured model on the
target CPU, which rescales every per-graph cost), else the report is refused. With a target model the MP self-check
columns use the TARGET model's measured overheads (S3-R2-005); an explicit --cost-model for those columns must be
measured on the target CPU, and the table records which model gave them (mp_check_ratio_model).
Length rule (R06): a statistic at length n < total uses only that graph's prefix rows with points = n
(graph_prefixes.csv), and full-stream fields (graph_replicates.csv, graph_tails.csv) only at n = total; a graph without
the length a statistic needs is an error, never a fallback. t = v_0 jac (C.3). The thresholds and actions 1-5 apply
to L8 only, as calibrated (RECON:1396); L <= 7 statistics are diagnostics. A replicate whose tail_sum is 0 or whose top
16 holds a zero, or a statistic that is not finite, makes the graph's entry "undefined (reason)": listed and counted,
never compared with a threshold. Paired-length statistics of a nested graph use y_r(n) = 3 jet_1 - jet_0 at L8 (the
top-slot combination) and V(n) = n Var_r y_r(n) (ddof 1). P8_hat = 1.0865 exp(0.0890 (Var(Q) - 1.8696)), Q = ln(s^2 of
replicates 1-4 / s^2 of 5-8) (cd3:tail_calib:29). Bootstrap bands resample graphs: a graph's two campaigns move
together (E.6 items 9-10). Zero-channel L8 graphs (s_G = 4) are reported as "zero-channel heavy tail, not confirmed"
and never take part in an action (zc_set; host refinement, Stage 3a repair round 3). Never a cost: no scheduling basis
is opened (D.5; every campaign is read with production.verify_base(scheduling_copies=False)); costs come from the merged
row seconds (graph_costs.csv) and the campaigns' measured models.
"""
from __future__ import annotations
import argparse,hashlib,json,math,os,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Refuse,canon,digest,dump,load,publish_bytes,supersede,utc
import production as prod

SCHEMA='c8-d3-pilot-report-1';SUBSET_SCHEMA='c8-d3-subset-1'
K=16;XI_SCREEN=0.38;SHARE_SCREEN=0.05;XI_CONFIRM=0.44;SCREEN_POINTS=4096;CONFIRM_POINTS=32768
P8G=1.0865;C1=0.0890;VQ0=1.8696;P8_R16=1.13;P8_STRATUM=1.196;P8_STRATUM_MIN=500;HOLD_SHARE=0.03
RHO=((math.sqrt(2)-1/math.sqrt(2))/math.log(2))**2
SE_ABS=(5,3,2,1.5,1,0.75,0.5,0.3,0.22);SE_REL=(1e-2,3e-3,1e-3,5e-4,2.5e-4,1.44e-4);FLOOR=4096;BOOT_SEED=20261004

# ---------------------------------------------------------------- estimators (oracle-tested, A-DES-3)
def hill(top)->float|None:
    """Hill estimate of xi from the 16 largest |t| (15 log-spacings above the 16th); None if undefined."""
    x=[float(v)for v in top]
    if len(x)<K or not all(math.isfinite(v)for v in x)or x[K-1]<=0:return None
    return sum(math.log(v/x[K-1])for v in x[:K-1])/(K-1)

def c4(R:int)->float:return math.sqrt(2/(R-1))*math.exp(math.lgamma(R/2)-math.lgamma((R-1)/2))
def kappa(R:int)->float:return 1/c4(R)**2
def m1(R:int,k:float)->float:
    a=1/(2/(R-1)+k/R);return math.exp(math.lgamma(a+.5)-math.lgamma(a))/math.sqrt(a)
def penk(R:int,k:float)->float:
    a=1/(2/(R-1)+k/R)
    if a<=.5:return math.inf
    return math.exp(math.lgamma(a+.5)-math.lgamma(a))/math.sqrt(a)*math.exp(math.lgamma(a-.5)-math.lgamma(a))*math.sqrt(a)
def k_of_p(P:float)->float:
    """The Gamma-model shape k >= 0 with penk(8, k) = P (k = 0 at or below the Gaussian 1.08650)."""
    if P<=penk(8,0.):return 0.
    lo,hi=0.,1.
    while penk(8,hi)<P:hi*=2
    for _ in range(200):
        mid=(lo+hi)/2
        if penk(8,mid)<P:lo=mid
        else:hi=mid
    return (lo+hi)/2
def realism(P:float,R:int)->dict:
    """F_G = P_G kappa_G rho (E.7): k from P_hat = penk(8, k); P_G = penk(R_G, k); kappa_G = 1/m1(R_G, k)^2."""
    k=k_of_p(P);PG=penk(R,k);kG=1/m1(R,k)**2
    return {'k':k,'P_G':PG,'kappa_G':kG,'rho':RHO,'F_G':PG*kG*RHO,'kappa_gauss':kappa(R)}
def p8_of_varq(vq:float)->float:return P8G*math.exp(C1*(vq-VQ0))
def split_q(y)->list:
    """Q values of one graph-campaign's replicate values: per disjoint block of 8 replicates, ln(s^2[1-4]/s^2[5-8])."""
    y=np.asarray(y,float);out=[]
    for b in range(0,len(y)-7,8):
        a=np.var(y[b:b+4],ddof=1);c=np.var(y[b+4:b+8],ddof=1)
        if a>0 and c>0:out.append(math.log(a/c))
    return out
def p8_pooled(qs:list)->float|None:return p8_of_varq(float(np.var(qs,ddof=1)))if len(qs)>1 else None
def alpha_hat(V2:list,V1:list)->float|None:
    s2,s1=sum(V2),sum(V1)
    return .5-math.log(s2/s1)/(2*math.log(8))if s1>0 and s2>0 else None
def share_fall(sh1:list,sh2:list)->float|None:
    if not sh1 or not sh2 or min(sh1+sh2)<=0:return None
    return math.exp(sum(math.log(x)for x in sh1)/len(sh1)-sum(math.log(x)for x in sh2)/len(sh2))
def skew(y)->float|None:
    y=np.asarray(y,float)
    if len(y)<3 or np.std(y)==0:return None
    z=(y-y.mean())/y.std();return float((z**3).mean())
def design_penalty_heldout(s_pa,s_pf,c,R_pf:int)->dict:
    """Item 12: a PA-based design (n ~ s_PA/sqrt(c)) evaluated with PF's replicates of the same graphs; raw x c4(R_PF)^2.
    One call covers graph-campaigns of one replicate count R_PF (one sector, heldout_by_sector)."""
    s_pa,s_pf,c=(np.asarray(x,float)for x in (s_pa,s_pf,c));w=np.sqrt(c)
    raw=float((s_pf**2/s_pa*w).sum()*(s_pa*w).sum()/(s_pf*w).sum()**2)
    return {'raw':raw,'corrected':raw*c4(R_pf)**2,'c4_sq':c4(R_pf)**2,'R_PF':int(R_pf),'graphs':int(len(c))}

def fin(x):
    """x if it is a finite number, else None: a supporting statistic that is not finite is reported as undefined (None),
    never as a NaN or an infinity."""
    return x if isinstance(x,(int,float))and not isinstance(x,bool)and math.isfinite(x)else None

# ---------------------------------------------------------------- campaign tables (the length rule)
def read_csv(path:Path)->list[dict]:
    lines=Path(path).read_text().splitlines();head=lines[0].split(',')
    return [dict(zip(head,l.split(',')))for l in lines[1:]]

ID_KEYS=('manifest_sha256','campaign_role','selection_sha256','science_sha256')
def identity(run,m:dict,mh:str,merged:dict,science:dict)->dict:
    """A campaign's identity (S3-005, S3-R2-009): its manifest sha256, campaign role, selection sha256 (pilot_subset) and
    every group's scientific identity (assemble.group_science of its validated merged.json), the ID_KEYS a screen or a
    selection is bound by; the sha256 of every group's merged.json, which records timing too, and the run path are
    informative only (a copied campaign, or one whose group was re-merged after a recovered index, keeps its identity)."""
    return {'run':str(Path(run).resolve()),'manifest_sha256':mh,'campaign_role':m['campaign_role'],'selection_sha256':(m.get('selection')or{}).get('sha256'),
            'science_sha256':dict(sorted(science.items())),'merged_sha256':dict(sorted(merged.items()))}

def campaign_identity(run)->dict:
    import assemble as asm
    run=Path(run).resolve();m,_,mh,_=prod.verify_base(run,check_executable=False,accept_tool_change=True,scheduling_copies=False);merged={};science={}
    for gr in m['groups']:
        p,cfg=prod.group_of(run,m,gr['name']);d=prod.validate_merged(p,cfg,m,mh);merged[gr['name']]=digest(p/'merged.json');science[gr['name']]=asm.group_science(d)
    return identity(run,m,mh,merged,science)

def bound(rec,cur:dict,what:str)->None:
    """S3-005, S3-R2-009: the recorded identity rec names the campaign cur (ID_KEYS: manifest, role, selection and the
    scientific identity of every group, not the merged.json bytes), else ValueError."""
    if not isinstance(rec,dict):raise ValueError(f'{what}: no recorded campaign identity (made by an older tool): recompute it from this pilot\'s campaigns')
    if not isinstance(rec.get('science_sha256'),dict):raise ValueError(f'{what}: no recorded scientific identity (made by an older tool, S3-R2-009): recompute it from this pilot\'s campaigns')
    diff=[k for k in ID_KEYS if rec.get(k)!=cur.get(k)]
    if diff:raise ValueError(f'{what} belongs to another campaign than {cur["run"]} ({", ".join(diff)} differ; recorded run {rec.get("run")})')

class Camp:
    """A merged pilot campaign: per group, the full-stream rows and the prefix rows by (rep, graph[, points])."""
    def __init__(self,run:Path,roles=None):
        self.run=Path(run).resolve();self.m,self.I,self.mh,_=prod.verify_base(self.run,check_executable=False,accept_tool_change=True,scheduling_copies=False)
        if roles and self.m['campaign_role']not in roles:raise ValueError(f'{run}: campaign_role {self.m["campaign_role"]} is not {roles}')
        import assemble as asm
        self.inv=load(self.I.where('inventory.json'));self.g={};merged={};science={}
        for gr in self.m['groups']:
            p,cfg=prod.group_of(self.run,self.m,gr['name']);d=prod.validate_merged(p,cfg,self.m,self.mh);k=2*(9-cfg['L']);merged[gr['name']]=digest(p/'merged.json')
            science[gr['name']]=asm.group_science(d)
            G={'cfg':cfg,'reps':cfg['replicates'],'total':{int(a):int(b)for a,b in cfg['counts'].items()},'jets':{},'tails':{},'prefix':{},'cost':{},'promo':[]}
            for r in read_csv(p/'graph_replicates.csv'):G['jets'][(int(r['replicate']),int(r['graph']))]=[float(r[f'jet_{i}'])for i in range(k)]
            for r in read_csv(p/'graph_tails.csv'):
                G['tails'][(int(r['replicate']),int(r['graph']))]=(int(r['points']),float(r['tail_sum']),[float(r[f'tail_top_{i+1}'])for i in range(K)if r.get(f'tail_top_{i+1}')],r['tail_argmax'])
            if d.get('graph_prefixes_sha256'):
                for r in read_csv(p/'graph_prefixes.csv'):
                    G['prefix'][(int(r['replicate']),int(r['graph']),int(r['points']))]=([float(r[f'jet_{i}'])for i in range(k)],float(r['tail_sum']),
                                                                                         [float(r[f'tail_top_{i+1}'])for i in range(K)if r.get(f'tail_top_{i+1}')],r['tail_argmax'])
            for r in read_csv(p/'graph_costs.csv'):G['cost'][int(r['graph'])]=(int(r['points']),float(r['row_seconds']))
            G['promo']=read_csv(p/'graph_promotions.csv')
            self.g[(cfg['campaign'],cfg['sector'],cfg['L'])]=G
        self.identity=identity(self.run,self.m,self.mh,merged,science)
    def at(self,key,g,n):
        """(jets per rep, tails per rep) of graph g at length n under the length rule; KeyError naming the gap."""
        G=self.g[key];total=G['total'][g];jets=[];tails=[]
        for r in range(G['reps']):
            if n==total:jets.append(G['jets'][(r,g)]);t=G['tails'][(r,g)];tails.append((t[1],t[2],t[0]))
            else:
                if (r,g,n)not in G['prefix']:raise KeyError(f'{self.run.name} {key} graph {g}: no prefix row at {n} points (length rule, R06)')
                x=G['prefix'][(r,g,n)];jets.append(x[0]);tails.append((x[1],x[2],n))
        return jets,tails

def rows_at(c,key,g,n):
    """c.at(key, g, n) with the length rule asserted (R06, A-DES-8 (b)): every tail row used at length n is an n-point
    row (the full stream only when n is the graph's total; otherwise its graph_prefixes.csv row)."""
    jets,tails=c.at(key,g,n)
    for t in tails:
        if len(t)<3 or int(t[2])!=int(n):raise AssertionError(f'length rule (R06): {key} graph {g}: a statistic at {n} points read a {t[2] if len(t)>2 else "unlabelled"}-point row')
    if len(jets)!=len(tails):raise AssertionError(f'length rule (R06): {key} graph {g}: {len(jets)} jet rows, {len(tails)} tail rows')
    return jets,tails

def excess_hill(top,tsum:float,n:int)->float|None:
    """The Hill index on the excesses over the replicate mean |t| = tail_sum(n)/n (E.6; tail_calib.py:214-220: excesses
    floored at 1e-300)."""
    if len(top)<K or n<=0:return None
    mu=float(tsum)/n;ex=[max(float(v)-mu,1e-300)for v in top[:K]]
    return sum(math.log(v/ex[K-1])for v in ex[:K-1])/(K-1)

def tail_stats(tails)->dict:
    """Per graph-campaign: mean Hill xi over replicates, the largest share (max over replicates), the log-mean share and
    the mean excess Hill index; rows are (tail_sum, top 16, points)."""
    hs=[];sh=[];ex=[]
    for t in tails:
        tsum,top=t[0],t[1]
        if not math.isfinite(tsum):return {'undefined':'a replicate with a non-finite tail_sum'}
        if tsum<=0:return {'undefined':'a replicate with tail_sum 0'}
        if len(top)<K or min(top)<=0:return {'undefined':'a replicate whose top 16 holds a zero or fewer than 16 values'}
        h=hill(top)
        if h is None or not math.isfinite(h):return {'undefined':'a non-finite Hill index'}
        hs.append(h);sh.append(top[0]/tsum)
        if len(t)>2:ex.append(excess_hill(top,tsum,int(t[2])))
    xe=sum(ex)/len(ex)if ex and all(x is not None and math.isfinite(x)for x in ex)else None
    return {'xi':sum(hs)/len(hs),'share_max':max(sh),'share_logmean':sum(math.log(x)for x in sh)/len(sh),'xi_excess':xe,'shares':sh}

def y_top(jets):return [3*j[1]-j[0]for j in jets]   # L8 top-slot combination (proportional to the C8 contribution)

# ---------------------------------------------------------------- subset-check (D.13)
def subset_check(run:Path)->dict:
    run=Path(run).resolve();m,I,mh,_=prod.verify_base(run,check_executable=False,accept_tool_change=True,scheduling_copies=False)
    if m['campaign_role']!='pilot_subset':raise Refuse(64,f'subset-check is for pilot_subset campaigns; {run} is {m["campaign_role"]}')
    sel_bytes=(run/'selection.json').read_bytes()
    if hashlib.sha256(sel_bytes).hexdigest()!=m['selection']['sha256']:raise ValueError('selection.json differs from the manifest\'s pin')
    sel=json.loads(sel_bytes);problems=[];files={}
    planned={g['name']for g in m['groups']};present={p.name for p in (run/'groups').iterdir()if p.is_dir()}
    if present!=planned:problems.append(f'group directories {sorted(present-planned)} not planned, {sorted(planned-present)} missing')
    import prefix_verify as pv
    graphs=0;points=0
    for gr in m['groups']:
        p,cfg=prod.group_of(run,m,gr['name'])
        try:d=prod.validate_merged(p,cfg,m,mh)
        except (ValueError,OSError)as e:problems.append(f'{gr["name"]}: {e}');continue
        key=f'{cfg["sector"]}:{cfg["L"]}';want={r['id']:r for r in sel['groups'].get(key,[])}
        rows=read_csv(p/'graph_replicates.csv');seen={}
        for r in rows:seen.setdefault(int(r['graph']),[]).append(int(r['replicate']))
        if set(seen)!=set(want):problems.append(f'{gr["name"]}: graph set differs from the selection ({sorted(set(seen)^set(want))[:5]})')
        for g,reps in seen.items():
            if sorted(reps)!=list(range(cfg['replicates'])):problems.append(f'{gr["name"]}: graph {g} replicates {sorted(reps)} are not 0..{cfg["replicates"]-1} once each')
        for r in read_csv(p/'graph_tails.csv'):
            g=int(r['graph'])
            if g in want and int(r['points'])!=want[g]['points']:problems.append(f'{gr["name"]}: graph {g} has {r["points"]} points, the selection {want[g]["points"]}')
        res=pv.verify(run,gr['name'])
        if not res['verified']:problems+=res['problems']
        exp=cfg['replicates']*sum(len(v.get('nest')or[])for v in want.values())
        if d['prefix_rows']!=exp:problems.append(f'{gr["name"]}: {d["prefix_rows"]} prefix rows, the selection needs {exp}')
        graphs+=len(want);points+=sum(v['points']for v in want.values())*cfg['replicates']
        files[gr['name']]={f:digest(p/f)for f in ('merged.json','graph_replicates.csv','graph_tails.csv','graph_promotions.csv','graph_costs.csv')+(('graph_prefixes.csv',)if d['graph_prefixes_sha256']else())}
    if problems:raise ValueError('subset-check failed: '+'; '.join(problems[:12]))
    doc={'schema':SUBSET_SCHEMA,'campaign_role':'pilot_subset','selection_role':sel.get('role'),'selection_sha256':m['selection']['sha256'],'seed':m['seed'],
         'groups':sorted(planned),'graphs':graphs,'points':points,'merged_sha256':files,'coefficients':None,'final':False,
         'scope':'pilot subset: tail and sizing diagnostics only; no coefficient assembly'}
    return {**doc,'state':publish_summary(run/'subset_summary.json',doc)}

SUMMARY_TIMING=('merged.json','graph_costs.csv')   # the digests of merged_sha256 that record timing (F8-d3)
def publish_summary(dest:Path,doc:dict)->str:
    """Publish subset_summary.json (no-clobber, idempotent): an identical summary is kept. A group re-merged after a
    recovered index changes only its timing digests (SUMMARY_TIMING: merged.json and graph_costs.csv record lane and row
    seconds); such a summary is superseded, the old bytes kept as subset_summary.superseded.<sha12>.json (F8-d3). Any
    other change, a scientific table's digest included, is refused. Returns the state."""
    data=(json.dumps(doc,indent=1,sort_keys=True)+'\n').encode()
    if dest.exists():
        old=dest.read_bytes()
        if old==data:return 'identical summary kept'
        prev=json.loads(old)
        strip=lambda d:{**d,'merged_sha256':{g:{f:h for f,h in fs.items()if f not in SUMMARY_TIMING}for g,fs in (d.get('merged_sha256')or{}).items()}}  # noqa: E731
        if not isinstance(prev,dict)or canon(strip(prev))!=canon(strip(json.loads(data))):raise ValueError(f'{dest} exists and differs: not overwritten')
        keep=supersede(dest,data,old,'result_publish')
        if keep is None:return publish_summary(dest,doc)   # dest changed between the read and the link: decide again
        return f'superseded: only timing digests changed; previous summary kept as {keep}'
    try:publish_bytes(dest,data,'result_publish')
    except FileExistsError:
        if dest.read_bytes()!=data:raise ValueError(f'a different {dest} was published concurrently')
    return 'written'

# ---------------------------------------------------------------- zero channel (host refinement, Stage 3a repair round 3)
def zc_set(c)->set:
    """{(sector, graph)} of the L8 zero-channel graphs of a campaign's inventory (pilot_select.zero_channel_l8: s_G = 4,
    i.e. 3 w_B = w_A). The C8 Jacobian row at L8 is proportional to (-1, 3), so their C8 contribution is identically zero
    and they carry no C8 variance, although their t = v_0 jac tail (weight-free) may be heavy (power L7 G1601 in Stage 3a).
    Such a graph is reported as "zero-channel heavy tail, not confirmed"; it is never flagged (action 1), confirmed
    (actions 2, 2b), selected for PC (pilot_select) or counted in the 3% hold test (action 3), and its replicate values
    (the rounding noise of a zero channel) enter no C8-variance statistic (P8_hat of actions 4-5, alpha_hat of item 10,
    item 12). Empty for a camp without an inventory (the injected test camps)."""
    z=getattr(c,'_zc',None)
    if z is None:
        import pilot_select as ps
        inv=getattr(c,'inv',None);z=ps.zero_channel_l8(inv)if isinstance(inv,dict)else set();c._zc=z
    return z

def zc_mark(r:dict,heavy:bool)->dict:
    import pilot_select as ps
    r.update(zero_channel=True,heavy_tail=bool(heavy),
             status=ps.ZC_NOTE if heavy else 'zero channel (C8 contribution identically zero): never flagged or confirmed')
    return r

# ---------------------------------------------------------------- stage A (PA) and the screen
def require_subset(run:Path,role:str)->Camp:
    c=Camp(run,('pilot_subset',))
    sel=load(c.run/'selection.json')
    if sel.get('role')!=role:raise ValueError(f'{run}: its selection role is {sel.get("role")!r}, not {role}')
    if not (c.run/'subset_summary.json').exists():raise ValueError(f'{run}: no subset_summary.json (the merge job\'s subset-check has not passed)')
    c.sel=sel;return c

def screen_graph(c:Camp,s:str,g:int,n:int)->dict:
    out={}
    for t in ('a','b'):
        _,tails=rows_at(c,(t,s,8),g,n);out[t]=tail_stats(tails)
    # E.6 items 2-3: flagged if either campaign's DEFINED entry passes a threshold; an undefined entry is listed and never
    # compared, and it does not suppress the other campaign's flag (Stage 3a repair round 1)
    heavy=any(('undefined'not in x)and(x['xi']>XI_SCREEN or x['share_max']>SHARE_SCREEN)for x in out.values())
    und=[f'{t}: {x["undefined"]}'for t,x in out.items()if 'undefined'in x]
    r={'sector':s,'graph':g,'campaigns':{t:{k:v for k,v in x.items()if k!='shares'}for t,x in out.items()},'flag':heavy,'undefined':und or None}
    if (s,g)in zc_set(c):r['flag']=False;zc_mark(r,heavy)   # a zero-channel graph is never flagged (repair round 3)
    return r

def confirm_graph(c:Camp,s:str,g:int,alpha:float|None=None)->dict:
    """Action 2: the two-campaign mean xi(32,768) > 0.44, with the supporting evidence (E.6 item 4): the share fall, the
    variance ratio V(32,768)/V(4,096) and, given the sector's alpha_hat, the ratio divided by 8^-(2 alpha - 1), the excess
    Hill index at both lengths and the cross-campaign shift. A zero-channel graph is never confirmed (zc_set)."""
    st={};sup={};zc=(s,g)in zc_set(c)
    for t in ('a','b'):
        j2,t2=rows_at(c,(t,s,8),g,CONFIRM_POINTS);j1,t1=rows_at(c,(t,s,8),g,SCREEN_POINTS)
        a2,a1=tail_stats(t2),tail_stats(t1);st[t]=(a1,a2)
        if 'undefined'in a2 or 'undefined'in a1:continue
        y1,y2=y_top(j1),y_top(j2);V1=fin(SCREEN_POINTS*float(np.var(y1,ddof=1)));V2=fin(CONFIRM_POINTS*float(np.var(y2,ddof=1)))
        vr=fin(V2/V1)if V1 and V2 is not None else None   # V1 = 0 (a zero channel's replicate values) or not finite: None
        sup[t]={'share_fall':fin(share_fall(a1['shares'],a2['shares'])),'V_ratio':vr,'V_ratio_normalized':(fin(vr/8**(-(2*alpha-1)))if vr is not None and alpha is not None else None),
                'alpha':alpha,'xi_4096':a1['xi'],'xi_32768':a2['xi'],'xi_excess_4096':a1.get('xi_excess'),'xi_excess_32768':a2.get('xi_excess')}
    und=[f'{t}: {x[1]["undefined"]}'for t,x in st.items()if 'undefined'in x[1]]
    if und:
        r={'sector':s,'graph':g,'undefined':und,'confirmed':False}
        return zc_mark(r,False)if zc else r
    mean=fin((st['a'][1]['xi']+st['b'][1]['xi'])/2)
    if mean is None:
        r={'sector':s,'graph':g,'undefined':['the two-campaign mean xi(32,768) is not finite'],'confirmed':False}
        return zc_mark(r,False)if zc else r
    conf=mean>XI_CONFIRM and not zc
    r={'sector':s,'graph':g,'xi_mean_32768':mean,'confirmed':conf,'possible_infinite_variance':conf,'supporting':sup,
       'cross_campaign_shift':{'xi_a':st['a'][1]['xi'],'xi_b':st['b'][1]['xi'],'face_model_xi_b':1-(8/7)*(1-st['a'][1]['xi'])}}
    return zc_mark(r,mean>XI_CONFIRM)if zc else r

def zc_entries(rows:list,stage:str)->list:
    """The compact 'zero-channel heavy tail, not confirmed' entries of screen or confirmation rows."""
    return [{'sector':x['sector'],'graph':x['graph'],'stage':stage,'status':x['status'],
             **({'xi_mean_32768':x['xi_mean_32768']}if 'xi_mean_32768'in x else{'xi':{t:v.get('xi')for t,v in x.get('campaigns',{}).items()}})}
            for x in rows if x.get('zero_channel')and x.get('heavy_tail')]

def stage_a_core(c:Camp)->dict:
    """The stage-A screen (action 1 at 4,096 points), the P1c confirmations (actions 2, 2b) and action 4 (P8_hat per sector
    pooled over the stage-A graph-campaigns, zero-channel graphs excluded) of a PA campaign."""
    rows=[];p1c=[];units={'free':{},'power':{}};undef=[];zc=zc_set(c)
    for key in sorted(c.sel['groups']):
        s,L=key.split(':');L=int(L)
        if L!=8:raise ValueError('stage A selects L8 graphs only')
        for r in c.sel['groups'][key]:
            g=r['id'];sc=screen_graph(c,s,g,SCREEN_POINTS);sc['label']=r['label'];rows.append(sc)
            if sc['undefined']:undef.append(sc)
            if (s,g)not in zc:
                for t in ('a','b'):
                    jets,_=rows_at(c,(t,s,8),g,SCREEN_POINTS);units[s].setdefault(g,[]).extend(split_q(y_top(jets)))
            if r['label']=='p1c':
                cf=confirm_graph(c,s,g);cf['screened']=sc['flag'];p1c.append(cf)
    sec={};zseen={(x['sector'],x['graph'])for x in rows if (x['sector'],x['graph'])in zc}
    for s,u in units.items():
        q=[x for g in sorted(u)for x in u[g]];p=p8_pooled(q)
        sec[s]={'graph_campaigns':len(q),'graphs':len(u),'P8_hat':p,'R':16 if p is not None and p>P8_R16 else 8,'switch_threshold':P8_R16,
                'zero_channel_excluded':sorted(g for ss,g in zseen if ss==s)}
    unscreened=[x for x in p1c if x.get('confirmed')and not x['screened']]
    return {'rows':rows,'undefined':undef,'p1c':p1c,'unscreened':unscreened,'action4':sec,
            'zero_channel_heavy_tail':zc_entries(rows,'stage-A screen (4,096 points)')+zc_entries(p1c,'P1c confirmation (32,768 points)')}

def alpha_p1c(A:Camp,graphs:list)->dict:
    """E.6 item 10 on PA's P1c graphs [(sector, graph)]: per sector alpha_hat = 1/2 - ln(sum V(32,768)/sum V(4,096))/(2 ln 8)
    over its graph-campaigns, with a 68% bootstrap band over GRAPHS (a graph's two campaigns are one resampling unit, so
    they move together, E.6), and the replicate skewness of y_r at both lengths. The central value used by E.7 is the mean
    of the sector values; its band comes from the same graph bootstrap, stratified by sector. Zero-channel graphs are
    excluded (zc_set)."""
    zc=zc_set(A);units={}
    for s,g in graphs:
        if (s,g)in zc:continue
        u=[]
        for t in ('a','b'):
            j1,_=rows_at(A,(t,s,8),g,SCREEN_POINTS);j2,_=rows_at(A,(t,s,8),g,CONFIRM_POINTS);y1,y2=y_top(j1),y_top(j2)
            u.append((SCREEN_POINTS*float(np.var(y1,ddof=1)),CONFIRM_POINTS*float(np.var(y2,ddof=1)),skew(y1),skew(y2)))
        units.setdefault(s,{})[g]=u
    st=lambda vv:alpha_hat([x[1]for u in vv for x in u],[x[0]for u in vv for x in u])
    by={}
    for s in sorted(units):
        v=[units[s][g]for g in sorted(units[s])];flat=[x for u in v for x in u]
        by[s]={'alpha':st(v),'band68':boot_band(v,st),'skew_4096':[x[2]for x in flat],'skew_32768':[x[3]for x in flat],'graphs':len(v),'graph_campaigns':len(flat)}
    vals=[v['alpha']for v in by.values()if v['alpha']is not None]
    allu=[(s,units[s][g])for s in sorted(units)for g in sorted(units[s])]
    def central(vv):
        a=[st([u for ss,u in vv if ss==s])for s in sorted(units)];a=[x for x in a if x is not None]
        return float(np.mean(a))if a else None
    band=boot_band(allu,central,strata=[s for s,_ in allu])if vals else None
    return {'central':float(np.mean(vals))if vals else 0.5,'band68':band,'by_sector':by,'bootstrap_unit':'graph (both campaigns together)',
            'central_rule':'mean of the sector values (0.5 when no P1c graph-campaign has V > 0)','zero_channel_excluded':sorted(f'{s}:{g}'for s,g in graphs if (s,g)in zc)}

FAIL_STATES=frozenset(('FAILED','NODE_FAIL','OUT_OF_MEMORY','BOOT_FAIL','TIMEOUT','DEADLINE','PREEMPTED'))
def worker_failures(run:Path,acct:dict|None)->dict:
    """Worker failures of a campaign (A-PIL-2: GO needs none): the package's failure records (a native block's
    groups/<g>/logs/*.failure.*, a lane's lanes/failures/*.json) and, when the accounting ran, every work attempt (lane
    worker or array element) that sacct shows in a failure state."""
    run=Path(run)
    rec=sorted(str(p.relative_to(run))for p in run.glob('groups/*/logs/*.failure.*'))+sorted(str(p.relative_to(run))for p in run.glob('lanes/failures/*.json'))
    sch=[{k:x.get(k)for k in ('job','name','state','elapsed')}for x in (acct or{}).get('attempts',[])if x.get('class')=='work'and x.get('state')in FAIL_STATES]
    return {'records':rec,'scheduler_attempts':sch,'scheduler_evaluated':acct is not None,'count':len(rec)+len(sch),'failure_states':sorted(FAIL_STATES)}

def queue_latency(acct:dict|None)->dict|None:
    """Queue latency per role class (submission to start of every sacct attempt, E.7: reported apart from eta, which
    counts allocated over busy time only)."""
    if acct is None:return None
    import datetime
    def ts(x):
        try:return datetime.datetime.strptime(str(x),'%Y-%m-%dT%H:%M:%S').timestamp()
        except (TypeError,ValueError):return None
    by={}
    for x in acct.get('attempts',[]):
        s0,s1=ts(x.get('submit')),ts(x.get('start'))
        if s0 is not None and s1 is not None:by.setdefault(x.get('class')or'other',[]).append(max(0.,s1-s0))
    return {k:{'attempts':len(v),'mean_seconds':sum(v)/len(v),'max_seconds':max(v)}for k,v in sorted(by.items())}

def try_account(run:Path,env:dict)->tuple[dict|None,str|None]:
    """tools/accounting.py on a campaign, or (None, the reason) when the scheduler or the ledger cannot be read."""
    import accounting
    try:return accounting.account(run,env),None
    except Refuse as e:return None,f'accounting refused ({e.code}): {e}'
    except (ValueError,KeyError,OSError)as e:return None,f'accounting failed: {e}'

def measured_vs_model(c:Camp)->tuple[dict,dict]:
    """f_E (A-PIL-2): a campaign's measured busy seconds (graph_costs.csv row seconds) over the busy seconds its measured
    cost model (the pinned cost_model.json) predicts for the same work: seconds per point x points x the plan's MP
    self-check factor. Returns (record, model)."""
    m=c.m
    if m.get('cost_basis')!='measured'or not m.get('cost_model_sha256'):raise ValueError(f'{c.run}: cost basis {m.get("cost_basis")!r}: f_E and the re-projection need its measured model')
    model,_=prod.read_cost_model(c.run/'cost_model.json',m['backend']);spp=model['seconds_per_point'];mpf=float(m.get('mp_check_factor')or 1.);meas=pred=0.
    for (t,s,L),G in c.g.items():
        for g,(pts,sec) in G['cost'].items():meas+=sec;pred+=float(spp[f'{t}:{s}:{L}:{g}'])*pts*mpf
    return ({'f_E':meas/pred if pred>0 else None,'busy_core_hours_measured':meas/3600,'busy_core_hours_model':pred/3600,'mp_check':m['mp_check'],'mp_check_factor':mpf,
             'cost_model_sha256':m['cost_model_sha256'],'cost_model_executable_sha256':m.get('cost_model_executable_sha256'),
             'rule':'f_E = measured busy / the measured model\'s prediction for the same graphs, points and replicates'},model)

# The Stage-7 runbook's shared jobs (CPUs, GiB, hours): plans, the PC selection, the full report, the merges (Budgets)
RUNBOOK_SHARED={'pf_plan':(8,16,1.),'select':(16,32,1.),'pc_plan':(8,16,1.),'report':(32,64,2.),'pf_merge':(24,48,2.),'pc_merge':(24,48,1.)}
PC_CAP=0.25
def site_shape(env:dict)->tuple:
    """(site profile, lane shape) of the pilot's PF and PC lanes (Amendment A1): the site of C8_SITE (tools/budget.py
    profile) and slurm_submit.lane_shape of C8_SBATCH_ARGS (the site's default lane arguments when unset, or when they
    name no lane partition, e.g. an arrays or debug profile): Expanse compute (128 cores, f_class 1, at most 47:30:00);
    symmetry amdq (64 cores, f_class 1) or defq (40 cores, f_class 1.5), at most 23:30:00."""
    import budget,slurm_submit as ss
    prof=budget.profile(env);sh=ss.lane_shape(prof,ss.tokens_of(env,'C8_SBATCH_ARGS',prof.lane_args))
    if sh['partition']not in prof.lane_partitions:sh=ss.lane_shape(prof,ss.tokens_of({},'C8_SBATCH_ARGS',prof.lane_args))
    sh['node_billing']=prof.billing_value(sh['partition'],1,sh['cores'],0.)   # per node-hour: Expanse SU 128, symmetry core-h 64 (AMD) or 80 (Intel)
    return prof,sh

def shared_su(k:str,prof=None,shape=None)->float:
    """A runbook job at its reservation in the site's unit: Expanse `shared` (F39: max(CPUs, GiB/2) per hour); symmetry
    a whole node (every partition is exclusive), amdq for plans, the selection and the report (raw jobs on Intel are
    refused), and the merges on the lanes' partition (one CPU vendor per campaign)."""
    import budget
    prof=prof or budget.EXPANSE;c,mem,h=RUNBOOK_SHARED[k];part=prof.runbook_partition
    if prof.name=='symmetry'and k.endswith('_merge')and shape:part=shape['partition']
    return prof.billing_value(part,1,c,mem*1024.)*h

def lane_step(busy_model:float,fE:float,eta_ab:float,n:int,threads:int,H:float,shape:dict|None=None)->dict:
    """One lane-mode step (D.10): the auto lane time of slurm_submit.auto_lane_time for the model's estimate or the
    measured projection f_E x model, whichever is larger (indices of at most H x 3600 x threads x 0.9 core-seconds, the
    plan's index sizing), on the site's lane shape (site_shape: cores, f_class, longest lane time); reservation N x the
    node's billing per hour (Expanse 128 SU, symmetry 64 or 80 core-h) x T_lane; expected spend = projected busy x eta
    (allocated/busy)."""
    import slurm_submit as ss
    sh=shape or{'partition':'compute','cores':ss.LANE_NODE_CORES,'f':1.0,'tmax':ss.LANE_TIME_MAX,'node_billing':float(ss.LANE_NODE_CORES)}
    proj=busy_model*fE;est=max(busy_model,proj);cap=H*3600*threads*0.9;k=max(1,math.ceil(est/cap))if est>0 else 0
    lt=ss.auto_lane_time({'threads':threads},[(i,est/k)for i in range(k)],n,sh['cores'],sh['f'],sh['tmax'])
    res=n*sh['node_billing']*lt['seconds']/3600;spend=proj*eta_ab/3600
    return {'nodes':n,'partition':sh['partition'],'busy_core_hours_model':busy_model/3600,'busy_core_hours_projected':proj/3600,'W_hours':lt['W']/3600,
            'T_lane':ss.hms(lt['seconds']),'lane_reservation_su':res,'lane_expected_su':spend,'more_than_one_round':spend>res+1e-9,
            'capped_at_tmax':lt['capped'],'T_lane_max':ss.hms(sh['tmax'])}

def reproject(c:Camp,fe:dict,model:dict,eta_ab:float,action4:dict,o,env:dict)->dict:
    """A-PIL-2's re-projection of PF and every pre-registered branch (Budgets): PF with R = 8 everywhere, PF with R = 16 at
    L8 (action 4 or the user), action 4's per-sector R when it is mixed, and after each the PC step at its cap (25% of
    PF's L8 cost, pilot_select), from the measured f_E, eta and the measured model's per-graph seconds (every inventory
    graph, both campaigns, 4,096 points), in both terms: expected spend, and peak reservation = the line's committed SU
    (tools/budget.py's total: spent + live reservations + unresolved intents + the other site's carry, A1.3) + what the
    branch spends before the step + the step's reservation (N x the lane node's billing x T_lane + its merge; the
    runbook's jobs at their reservations; all in the site's unit: site_shape, shared_su). GO needs every branch's peak
    within the line (C8_PILOT_SU_CAP or --line-cap); a branch that exceeds it stops the pilot."""
    spp=model['seconds_per_point'];mpf=fe['mp_check_factor'];f=fe['f_E']if fe['f_E']is not None else 1.;threads=int(c.m['threads'])
    H=float((c.m.get('index_sizing')or{}).get('index_hours')or 0.25);base={}
    for s in ('free','power'):
        for L,rows in (c.inv.get(s)or{}).items():
            for r in rows:
                for t in ('a','b'):
                    k=f'{t}:{s}:{L}:{r["id"]}'
                    if k not in spp:raise ValueError(f'the measured model holds no key {k}: PF cannot be projected')
                    base[(s,int(L)==8)]=base.get((s,int(L)==8),0.)+float(spp[k])*SCREEN_POINTS*mpf
    cap=o.line_cap;S0=o.spent;why=[]
    import budget
    prof,shape=site_shape(env);rb=lambda k:shared_su(k,prof,shape)
    if cap is None:
        try:cap=budget.line_cap('pilot',env)[0]
        except Refuse as e:why.append(str(e))
    if S0 is None:
        try:S0=float(budget.report(env)['lines']['pilot']['total'])
        except Refuse as e:why.append(f'budget.py refused ({e.code}): {e}')
        except (ValueError,KeyError,OSError)as e:why.append(f'budget.py failed: {e}')
    a4={s:int(v['R'])for s,v in action4.items()}
    br={'PF R=8':{'free':8,'power':8},'PF R=16 at L8':{'free':16,'power':16}}
    if set(a4.values())=={8,16}:br[f'PF action 4 (free R={a4.get("free",8)}, power R={a4.get("power",8)})']={'free':a4.get('free',8),'power':a4.get('power',8)}
    out={}
    for name,R8 in br.items():
        busy=sum(v*(R8[s]if l8 else 8)for (s,l8),v in base.items());busy8=sum(v*R8[s]for (s,l8),v in base.items()if l8)
        pf=lane_step(busy,f,eta_ab,o.pf_nodes,threads,H,shape);pc=lane_step(PC_CAP*f*busy8,f,eta_ab,o.pc_nodes,threads,H,shape)
        steps=[('PF plan',rb('pf_plan'),rb('pf_plan')),
               ('PF lanes + merge',max(pf['lane_reservation_su'],pf['lane_expected_su'])+rb('pf_merge'),pf['lane_expected_su']+rb('pf_merge')),
               ('PC selection',rb('select'),rb('select')),('PC plan',rb('pc_plan'),rb('pc_plan')),
               ('PC lanes + merge',max(pc['lane_reservation_su'],pc['lane_expected_su'])+rb('pc_merge'),pc['lane_expected_su']+rb('pc_merge')),
               ('full report',rb('report'),rb('report'))]
        cum=S0 or 0.;rows=[]
        for st,res,spend in steps:rows.append({'step':st,'reservation_su':res,'peak_su':cum+res,'expected_su':spend});cum+=spend
        peak=max(x['peak_su']for x in rows)
        out[name]={'R':R8,'pf':pf,'pc':pc,'steps':rows,'peak_su':peak,'expected_total_su':cum,'within_line':(peak<=cap+1e-9)if cap is not None and S0 is not None else None}
    return {'evaluated':cap is not None and S0 is not None,'not_evaluated_because':why or None,'line':'pilot','cap_su':cap,'committed_su':S0,
            'remaining_su':(cap-S0)if cap is not None and S0 is not None else None,'f_E':f,'eta_allocated_over_busy':eta_ab,
            'assumptions':{'pf_nodes':o.pf_nodes,'pc_nodes':o.pc_nodes,'threads':threads,'index_hours':H,'pc_cap_fraction':PC_CAP,'shared_jobs':RUNBOOK_SHARED,
                           'site':prof.name,'unit':prof.unit,'lane_shape':shape,'runbook_job_su':{k:rb(k)for k in RUNBOOK_SHARED},
                           'note':'L <= 7 at R = 8; PF at 4,096 points; T_lane from slurm_submit.auto_lane_time on the site\'s lane shape; merges and the '
                                  'runbook\'s jobs at their reservations in the site\'s unit (Expanse shared billing; symmetry whole nodes, A1.3)'},
            'branches':out}

class StageAOptions:
    def __init__(self,eta_node=None,line_cap=None,spent=None,pf_nodes=4,pc_nodes=2):
        self.eta_node=eta_node;self.line_cap=line_cap;self.spent=spent;self.pf_nodes=pf_nodes;self.pc_nodes=pc_nodes

def stage_a(run:Path,o:StageAOptions|None=None,env:dict|None=None)->dict:
    """The stage-A report (A-PIL-2, E.6): the MP self-check histogram and alarm, the tail screen of the stage-A graphs,
    the P1c confirmations, P8_hat per sector and the R decision (action 4), alpha and the skewness from P1c, the measured
    allocated/busy, queue latency and f_E, the worker failures, and the re-projection of PF and every branch in expected
    spend and peak reservation. GO needs: no mp_alarm, no worker failure, every branch's peak reservation within the
    remaining pilot line; otherwise NO-GO with the reasons (the pilot stops and the user is asked)."""
    o=o or StageAOptions();env=dict(os.environ)if env is None else env
    c=require_subset(run,'stage_a');core=stage_a_core(c);hist=histograms(c)
    al=alpha_p1c(c,[(x['sector'],x['graph'])for x in core['p1c']])
    acct,acct_why=try_account(c.run,env);fail=worker_failures(c.run,acct)
    if o.eta_node is not None:eta_ab=1/o.eta_node;eta_src=f'--eta-node {o.eta_node} (busy/allocated; a test pilot)'
    elif acct and acct.get('eta_node'):eta_ab=float(acct['eta_node']);eta_src='tools/accounting.py (allocated work core-seconds / busy core-seconds of PA)'
    else:eta_ab=None;eta_src=acct_why or 'tools/accounting.py gave no eta_node'
    reasons=[]
    if hist['alarm']:reasons.append(f'MP self-check alarm: {hist["mp_alarm_total"]} alarmed points in graph_promotions.csv')
    if fail['count']:reasons.append(f'worker failure: {len(fail["records"])} failure records, {len(fail["scheduler_attempts"])} work attempts in a failure state')
    if not fail.get('scheduler_evaluated',False):reasons.append(f'worker failures not evaluated against the scheduler: {acct_why or "tools/accounting.py gave no result"}')
    fe=None;rp=None
    try:
        fe,model=measured_vs_model(c)
        if eta_ab is None:raise ValueError(f'eta (allocated/busy) unknown: {eta_src}')
        rp=reproject(c,fe,model,eta_ab,core['action4'],o,env)
    except (ValueError,KeyError,OSError)as e:reasons.append(f're-projection not evaluated: {e}')
    if rp is not None:
        if not rp['evaluated']:reasons.append('re-projection not evaluated against the line: '+'; '.join(rp['not_evaluated_because']or[]))
        else:
            for name,b in rp['branches'].items():
                if not b['within_line']:reasons.append(f'branch {name}: peak reservation {b["peak_su"]:.1f} SU exceeds the pilot line {rp["cap_su"]:.0f} SU '
                                                       f'(committed {rp["committed_su"]:.1f}, remaining {rp["remaining_su"]:.1f}): the pilot stops and the user is asked')
    go='NO-GO'if reasons else 'GO'
    return {'schema':SCHEMA,'part':'stage_a','campaign':str(c.run),'manifest_sha256':c.mh,'selection_sha256':c.m['selection']['sha256'],'made_utc':utc(),
            'histograms':hist,
            'screen':{'flagged':[x for x in core['rows']if x['flag']],'graphs':len(core['rows']),'undefined':core['undefined'],
                      'zero_channel_heavy_tail':core['zero_channel_heavy_tail'],'rule':f'xi > {XI_SCREEN} or largest share > {SHARE_SCREEN} in either campaign at 4096 points (L8)'},
            'p1c':{'graphs':len(core['p1c']),'confirmations':core['p1c'],'unscreened_confirmed':core['unscreened']},
            'action4':core['action4'],'alpha':al,
            'efficiency':{'eta_allocated_over_busy':eta_ab,'eta_source':eta_src,**(fe or{'f_E':None})},
            'queue_latency':queue_latency(acct),'accounting':({'su_total':acct['su_total'],'su_by_class':acct['su_by_class']}if acct else acct_why),
            'failures':fail,'reprojection':rp,'go':go,'go_reasons':reasons,'undefined_tail_entries':len(core['undefined']),
            'go_rule':'GO needs no mp_alarm, no worker failure and every branch\'s peak reservation within the remaining pilot line (A-PIL-2)',
            'notes':'R per sector from action 4 (P8_hat > 1.13 -> R = 16 in PF)'}

def screen(pf:Path,pa:Path)->dict:
    P=Camp(pf,('pilot_full',));A=require_subset(pa,'stage_a');rows=[];undef=[]
    for s in ('free','power'):
        for g in sorted(P.g.get(('a',s,8),{'total':{}})['total']):
            sc=screen_graph(P,s,g,SCREEN_POINTS);rows.append(sc)
            if sc['undefined']:undef.append(sc)
    core=stage_a_core(A)
    return {'schema':'c8-d3-screen-1','pf':str(P.run),'pa':str(A.run),'pf_identity':P.identity,'pa_identity':A.identity,'flagged':[{'sector':x['sector'],'graph':x['graph']}for x in rows if x['flag']],
            'p1c_unscreened_confirmed':[{'sector':x['sector'],'graph':x['graph']}for x in core['unscreened']],
            'zero_channel_heavy_tail':zc_entries(rows,'PF screen (4,096 points)')+core['zero_channel_heavy_tail'],
            'l8_graphs':len(rows),'p1c_graphs':len(core['p1c']),'undefined':undef,'made_utc':utc()}

# ---------------------------------------------------------------- the full report
def jac8(P:Camp)->dict:
    import assemble as asm
    acc={}
    for (t,s,L),G in P.g.items():
        d=load(P.run/'groups'/f'{t}_{s}_L{L}'/'merged.json');acc.setdefault(L,[]).append(np.asarray(d['batches'],float).mean(0))
    means={L:sum(v)/2 for L,v in acc.items()}   # free + power, each the mean of its two campaigns (weights 1/2)
    B2,_=asm.two_loop(8,P.I.dir,P.I.m['sha256'])
    return {L:np.asarray(v)[8]for L,v in asm.vendored().jacobians(means,B2,8,asm.HALF_D).items()}

def per_graph_sigma(P:Camp,J8:dict)->dict:
    """{(c, s, L, g): (sigma per point on the C8 Jacobian, busy seconds per point, R, n_ref)} from PF."""
    out={}
    for (t,s,L),G in P.g.items():
        for g,n in G['total'].items():
            y=[float(np.dot(J8[L],G['jets'][(r,g)]))for r in range(G['reps'])]
            pts,sec=G['cost'][g];out[(t,s,L,g)]=(math.sqrt(n*float(np.var(y,ddof=1))),sec/pts,G['reps'],n)
    return out

def optimum(pop:dict,SE:float,alpha:float,R:int=64,floor:int=FLOOR)->dict:
    """min sum R n_g c_g s.t. Var(C8) = SE^2, n_g >= floor, Var = sum (1/4) sigma^2 n_ref^(2a-1) / (R n^(2a)) (RECON:1085-1095)."""
    sig=np.array([v[0]for v in pop.values()]);c=np.array([v[1]for v in pop.values()]);nref=np.array([v[3]for v in pop.values()],float)
    k=0.25*sig**2*nref**(2*alpha-1)/R
    def alloc(lam,fl):return np.maximum(fl,(lam*2*alpha*k/(R*np.maximum(c,1e-300)))**(1/(2*alpha+1)))
    def var(n):return float((k/n**(2*alpha)).sum())
    def solve(fl):
        lo,hi=1e-60,1e60
        for _ in range(400):
            mid=math.sqrt(lo*hi)
            if var(alloc(mid,fl))>SE**2:lo=mid
            else:hi=mid
        n=alloc(hi,fl);return n,float((R*n*c).sum())/3600
    n,busy=solve(floor);bound=n<=floor*1.000001
    return {'busy_core_hours':busy,'floor_busy_core_hours':float((R*n*c*bound).sum())/3600,'floor_fraction':float(bound.mean()),'n':n,'keys':list(pop)}

MP_MODES=('on','off','stride16')
def mp_ratios(model:dict|None,mode:str,source:str)->dict:
    """Production cost per MP self-check mode relative to the measured mode (E.7, C.4, HD11): f(k)/f(mode), with f = 1 in
    the model's own mode and f(k) = its mp_check_overhead[k] (P1's measured self-check overhead); "pending P1" for a mode
    whose overhead is not measured."""
    def f(k):
        if model is None:return None
        if model.get('mp_check')==k:return 1.
        v=(model.get('mp_check_overhead')or{}).get(k);return float(v)if v is not None else None
    base=f(mode);out={}
    for k in MP_MODES:
        if k==mode:continue
        fk=f(k);out[k]=fk/base if fk is not None and base else f'pending P1 (no measured mp_check overhead for {k} in {source})'
    return out

def target_site(P:Camp,env:dict,target_model:Path|None=None)->dict:
    """S3-010: the site E.7's cost table projects to: C8_SITE's profile (tools/budget.py; Expanse when unset or fake) and
    its lane node (site_shape: the partition, physical cores and allocated CPUs per node = the node's billing per hour, in
    which tools/accounting.py counts the allocated work core-seconds of eta: Expanse compute 128, symmetry amdq 64, defq
    80); the target CPU (the CPU of the lane PARTITION, budget.partition_cpu: the site's cost-model CPU on Expanse compute
    and symmetry's AMD pool, Intel Gold 6148 on symmetry defq and debugq, S3-R2-004; not evaluated for the Mac fakes,
    C8_SITE=fake) and the CPU PF was measured on (its plan host's, which HD11 pins to PF's cost model and slurm/site.sh to
    its lanes). When they differ, PF's measurements project to the target only with target-site measurements:
    target_model, a measured model on the target CPU, scales every per-graph cost by its seconds per point over PF's own
    measured model's (both in PF's MP self-check mode); without one the projection is refused (ValueError)."""
    import budget
    prof,sh=site_shape(env);tcpu=None if (env or{}).get('C8_SITE')=='fake'else budget.partition_cpu(prof,sh['partition']);mcpu=(P.m.get('fingerprint')or{}).get('cpu_model')
    rec={'site':prof.name,'unit':prof.unit,'partition':sh['partition'],'cores_per_node':int(sh['cores']),'allocated_cpus_per_node':float(sh['node_billing']),
         'target_cpu':tcpu,'measured_cpu':mcpu,'target_cost_model':None,'cost_scale':None}
    differs=tcpu is not None and prod.norm_cpu(tcpu)!=prod.norm_cpu(mcpu)
    if target_model is None:
        if differs:raise ValueError(f'PF was measured on {mcpu!r} but the target site {prof.name} (C8_SITE; partition {sh["partition"]}) runs {tcpu!r}: a projection '
                                    f'to {prof.name} {sh["partition"]} needs target-site measurements (--target-cost-model, a measured model on {tcpu}), or run the report '
                                    f'with C8_SITE and C8_SBATCH_ARGS of the site and partition PF ran on (S3-010, S3-R2-004)')
        rec['cpu_check']='the target CPU is PF\'s'if tcpu is not None else'not evaluated (C8_SITE=fake: the Mac fakes)';return rec
    T,_=prod.read_cost_model(Path(target_model),P.m['backend']);mode=P.m['mp_check']
    if tcpu is not None and prod.norm_cpu(T.get('cpu_model'))!=prod.norm_cpu(tcpu):raise ValueError(f'--target-cost-model {target_model} was measured on {T.get("cpu_model")!r}, not the target site\'s {tcpu!r} (partition {sh["partition"]})')
    if P.m.get('cost_basis')!='measured'or not P.m.get('cost_model_sha256'):raise ValueError(f'{P.run}: no measured cost model to scale PF\'s costs from (basis {P.m.get("cost_basis")!r})')
    M,_=prod.read_cost_model(P.run/'cost_model.json',P.m['backend'])
    for x,name in ((T,'--target-cost-model'),(M,'PF\'s cost_model.json')):
        if x.get('mp_check')!=mode and not (x.get('mp_check_overhead')or{}).get(mode):raise ValueError(f'{name} has no measured overhead factor for PF\'s MP self-check mode {mode}')
    fT,fM=prod.mp_factor(T,mode),prod.mp_factor(M,mode);ts,ms=T['seconds_per_point'],M['seconds_per_point'];scale={}
    for (t,s,L),G in P.g.items():
        for g in G['total']:
            k=f'{t}:{s}:{L}:{g}'
            if k not in ts or k not in ms:raise ValueError(f'no seconds per point for {k} in '+('--target-cost-model'if k not in ts else'PF\'s cost_model.json'))
            scale[(t,s,L,g)]=float(ts[k])*fT/(float(ms[k])*fM)
    rec.update(cost_scale=scale,cpu_check=('target-site model on the target CPU'if tcpu is not None else'not evaluated (C8_SITE=fake)'),
               target_cost_model={'path':str(Path(target_model).resolve()),'sha256':digest(target_model),'cpu_model':T.get('cpu_model'),'executable_sha256':T.get('executable_sha256'),
                                  'mp_check':T.get('mp_check'),'rule':'c_g(target) = c_g(PF row seconds) x (T_g f_T)/(M_g f_M), T the target model, M PF\'s, f their MP factors for PF\'s mode'})
    return rec

def cost_table(P:Camp,J8:dict,eta:float,alpha:dict,p8:dict,heldout:dict|None,c8:float,p8_band:dict|None=None,c8_se:float|None=None,
               mp_ratio:dict|None=None,latency:dict|None=None,site:dict|None=None)->dict:
    """E.7. alpha: {'central', 'band68'} (item 10); p8: {(sector, class): PF-pooled P8_hat} and p8_band: {(sector, class):
    [lo, hi]} (item 9, the 68% graph-bootstrap band); heldout: {sector: item 12's corrected value} or None, which enters
    P_hat of that sector's L8 groups only; c8 and c8_se: PF's C8 and its sampling SE (the |C8| band is |C8| -+ SE);
    mp_ratio: production cost per MP self-check mode relative to PF's (mp_ratios); latency: queue latency per step.
    Per row (absolute and relative SE targets, R = 64 and, for SE >= 3, R = 32): the plug-in optimum at the central alpha,
    F = sum w_G F_G and its three factors per group, a Gaussian-kappa column, the realistic cost; F at both ends of the
    P8_hat band; the optimum at both ends of the alpha band; for relative targets the SE at both ends of the |C8| band;
    the row's band = the envelope of the realistic cost over every combination of those ends, in busy core-hours,
    allocated SU and wall hours on 4 and 22 nodes; the allocated SU per MP self-check mode. site (target_site): the lane
    node the allocated units and wall hours refer to (allocated CPUs per node; S3-010) and, with target-site
    measurements, the per-graph cost scale; None is Expanse compute (128 per node) without a scale."""
    if site is None:prof,sh=site_shape({});site={'site':prof.name,'unit':prof.unit,'partition':sh['partition'],'cores_per_node':int(sh['cores']),
                                              'allocated_cpus_per_node':float(sh['node_billing']),'target_cpu':None,'measured_cpu':None,'target_cost_model':None,'cost_scale':None}
    pop=per_graph_sigma(P,J8);groups={}
    if site.get('cost_scale'):pop={k:(v[0],v[1]*site['cost_scale'][k],v[2],v[3])for k,v in pop.items()}
    for key,(sig,cg,R,n) in pop.items():groups.setdefault((key[0],key[1],key[2]),R)
    def F_of(P8hat_by_class,opt):
        # w_G: share of the non-floor busy cost in this row's plug-in optimum
        nf={};tot=0.
        for (t,s,L,g),n in zip(opt['keys'],opt['n']):
            if n>FLOOR*1.000001:x=n*pop[(t,s,L,g)][1];nf[(t,s,L)]=nf.get((t,s,L),0.)+x;tot+=x
        F=0.;parts={}
        for G,x in nf.items():
            cls='L8'if G[2]==8 else'L<=7';ho=(heldout or{}).get(G[1])if cls=='L8'else None
            Phat=max(P8hat_by_class.get((G[1],cls))or 0.,ho or 0.,penk(8,0.))
            r=realism(Phat,groups[G]);parts[f'{G[0]}_{G[1]}_L{G[2]}']={**r,'P_hat':Phat,'w':x/tot if tot else 0.};F+=(x/tot if tot else 0.)*r['F_G']
        return F,parts
    def real_of(opt,P8map):
        F,parts=F_of(P8map,opt);return F,parts,opt['floor_busy_core_hours']+F*(opt['busy_core_hours']-opt['floor_busy_core_hours'])
    cache={}
    def opt_at(SE,a,R):
        k=(SE,a,R)
        if k not in cache:cache[k]=optimum(pop,SE,a,R)
        return cache[k]
    a_c=alpha.get('central',0.5);a_band=alpha.get('band68')
    pb=p8_band or{};p8_lo={k:(pb.get(k)or[v,v])[0]for k,v in p8.items()};p8_hi={k:(pb.get(k)or[v,v])[1]for k,v in p8.items()}
    have_p8_band=any(pb.get(k)for k in p8)
    c8a=abs(c8);c8_lo=c8a-c8_se if c8_se else None;c8_hi=c8a+c8_se if c8_se else None
    nb=float(site['allocated_cpus_per_node']);su=lambda x:x/eta;w4=lambda x:x/eta/(4*nb);w22=lambda x:x/eta/(22*nb)
    rows=[]
    for kind,lst in (('absolute',SE_ABS),('relative',SE_REL)):
        for v in lst:
            SE=v if kind=='absolute'else v*c8a
            if not(SE>0 and math.isfinite(SE)):rows.append({'kind':kind,'target':v,'SE':None,'undefined':'|C8| of the pilot is 0'});continue
            SEs=[SE]
            if kind=='relative'and c8_hi is not None:SEs+=[v*c8_hi]+([v*c8_lo]if c8_lo>0 else[])
            for R in ((64,32)if SE>=3 else(64,)):
                opt=opt_at(SE,a_c,R);F,parts,real=real_of(opt,p8);nonfloor=opt['busy_core_hours']-opt['floor_busy_core_hours']
                Fg=sum(x['w']*x['P_G']*x['kappa_gauss']*RHO for x in parts.values());half=opt_at(SE,0.5,R);alloc=su(real)
                row={'kind':kind,'target':v,'SE':SE,'R':R,'alpha':a_c,'plugin_busy_core_hours':opt['busy_core_hours'],'floor_fraction':opt['floor_fraction'],
                     'F':F,'factors':parts,'realistic_busy_core_hours':real,'allocated_su':alloc,'wall_hours_4_nodes':w4(real),'wall_hours_22_nodes':w22(real),
                     'plugin_busy_alpha_half':half['busy_core_hours'],'F_kappa_gauss':Fg,'realistic_busy_core_hours_kappa_gauss':opt['floor_busy_core_hours']+Fg*nonfloor}
                if have_p8_band:
                    lo,hi=real_of(opt,p8_lo),real_of(opt,p8_hi)
                    row['band_p8']={'F':[lo[0],hi[0]],'realistic_busy_core_hours':[lo[2],hi[2]],'allocated_su':[su(lo[2]),su(hi[2])]}
                if a_band:
                    ra=[real_of(opt_at(SE,a,R),p8)[2]for a in a_band]
                    row['band_alpha']={'alpha':list(a_band),'realistic_busy_core_hours':ra,'allocated_su':[su(x)for x in ra]}
                if len(SEs)>1:
                    rc=[real_of(opt_at(x,a_c,R),p8)[2]for x in SEs[1:]]
                    row['band_c8']={'C8_abs':[c8_hi]+([c8_lo]if c8_lo>0 else[]),'SE':SEs[1:],'realistic_busy_core_hours':rc,'allocated_su':[su(x)for x in rc],
                                    'unbounded_above':not c8_lo>0}
                env=[real_of(opt_at(x,a,R),pm)[2]for x in SEs for a in [a_c]+list(a_band or[])for pm in ([p8,p8_lo,p8_hi]if have_p8_band else[p8])]
                row['band']={'realistic_busy_core_hours':[min(env),max(env)],'allocated_su':[su(min(env)),su(max(env))],
                             'wall_hours_4_nodes':[w4(min(env)),w4(max(env))],'wall_hours_22_nodes':[w22(min(env)),w22(max(env))],'corners':len(env),
                             'from':[n for n,b in (('alpha',a_band),('P8_hat',have_p8_band),('|C8|',len(SEs)>1))if b],
                             'unbounded_above':bool(kind=='relative'and c8_lo is not None and not c8_lo>0)}
                row['allocated_su_by_mp_check']={P.m['mp_check']:alloc,**{k:(alloc*x if isinstance(x,float)else x)for k,x in (mp_ratio or{}).items()}}
                rows.append(row)
    return {'rows':rows,'eta_allocated_over_busy':1/eta,'rho':RHO,'c8_pilot':c8,'c8_pilot_se':c8_se,'alpha':{'central':a_c,'band68':a_band},
            'p8_hat':{f'{s}|{c}':{'central':v,'band68':pb.get((s,c))}for (s,c),v in p8.items()},'heldout':heldout,
            'measured':'sigma, cost, eta, alpha, the design penalty','projected':'production-scale variance at alpha != 1/2; the +-1.5x post-pilot SE residual (RECON:1449-1452)',
            'mp_check':P.m['mp_check'],'mp_check_ratios':mp_ratio,
            'note':'cost basis: PF row seconds with --mp-check '+P.m['mp_check']+'; off and stride16 by P1\'s measured self-check overhead (C.4, HD11), or pending P1',
            'queue_latency':latency,'queue_latency_note':'submission to start per step (sacct), reported apart from eta, which counts allocated over busy time only',
            'site':{**{k:v for k,v in site.items()if k!='cost_scale'},'cost_scaled':bool(site.get('cost_scale'))},
            'site_note':f'allocated units in {site["unit"]} on {site["site"]} ({site["partition"]}); wall hours = allocated / (N x {nb:g} allocated CPUs per node)'}

def plugin_se_of_bundle(P:Camp,J8:dict,bundle:Path)->float:
    """The independent alpha = 1/2 SE of a frozen design (the cross-check of E.7): sqrt(sum sigma^2 / (4 n_g R))."""
    meta=load(Path(bundle)/'design_meta.json');d=load(Path(bundle)/'design.json');pop=per_graph_sigma(P,J8);var=0.
    for (t,s,L,g),(sig,cg,R,n) in pop.items():
        cnt={int(a):int(b)for a,b in (l.split()for l in (Path(bundle)/f'counts/{t}_{s}_L{L}.txt').read_text().splitlines()if l.strip())}
        st=prod.stratum_of(s,L,bool(next(r for r in P.inv[s][str(L)]if r['id']==g).get('primitive')));ng=cnt[g]*int(d['strata'][st]['s']);Rg=int(d['replicates'][f'{s}_L{L}'])
        var+=0.25*sig**2/(ng*Rg)
    return math.sqrt(var/int(d['batches']))

def histograms(P:Camp)->dict:
    out={}
    tb=lambda T:next(i for i,u in enumerate((8,24,48,96,math.inf))if T<=u)
    for (t,s,L),G in P.g.items():
        inv={r['id']:r for r in P.inv[s][str(L)]}
        for r in G['promo']:
            g=int(r['graph']);row=inv[g];key=f'{s}|T{tb(row["terms"])}|fmax{row["fmax"]}'
            e=out.setdefault(key,{'quad':0,'mp':0,'nondirect':0,'nonmoderate':0,'mp_checked':0,'mp_alarm':0,'mp_hist':[0]*prod.MP_BINS})
            for f in ('quad','mp','nondirect','nonmoderate','mp_checked','mp_alarm'):e[f]+=int(r[f])
            e['mp_hist']=[x+int(r[f'mp_hist_{i}'])for i,x in enumerate(e['mp_hist'])]
    alarm=sum(e['mp_alarm']for e in out.values())
    return {'by_sector_Tbin_fmax':out,'mp_alarm_total':alarm,'alarm':alarm>0}

def new_slots(P:Camp,J8:dict)->dict:
    """Item 11 (RECON:705-731): per (sector, L <= 7, campaign) from the group batches: beta = Cov(new, top)/Var(top),
    c = corr(new, top) and the inflation F = Var(C8 contribution)/Var(old-slot contribution)."""
    out={}
    for (t,s,L),G in P.g.items():
        if L>7:continue
        d=load(P.run/'groups'/f'{t}_{s}_L{L}'/'merged.json');X=np.asarray(d['batches'],float);k=9-L;j=J8[L]
        top=lambda X,i:3*X[:,k+i]-X[:,i]
        new=top(X,k-1);old_top=top(X,k-2)if k>=2 else None
        full=X@j;mask=np.ones(2*k,bool);mask[k-1]=False;mask[2*k-1]=False;old=X[:,mask]@j[mask]
        r={'F':float(np.var(full,ddof=1)/np.var(old,ddof=1))if np.var(old)>0 else None}
        if old_top is not None and np.var(old_top)>0:r.update(beta=float(np.cov(new,old_top)[0,1]/np.var(old_top,ddof=1)),c=float(np.corrcoef(new,old_top)[0,1]))
        out[f'{t}_{s}_L{L}']=r
    return out

def boot_band(units:list,stat,seed=BOOT_SEED,n=400,strata=None)->list|None:
    """The 68% bootstrap band [16th, 84th percentile] of stat over resamples of UNITS. A unit is one graph with the
    entries of all its campaigns (E.6 items 9-10: "a 68% bootstrap band over graphs"), so a graph's two campaigns, which
    share its integrand, are drawn together. With strata (a label per unit) the units are resampled within each stratum,
    whose size stays fixed. Fixed seed."""
    if len(units)<2:return None
    rng=np.random.default_rng(seed);xs=[]
    blocks=[np.arange(len(units))]if strata is None else [np.asarray([i for i,x in enumerate(strata)if x==k])for k in sorted(set(strata))]
    for _ in range(n):
        idx=[int(i)for b in blocks for i in b[rng.integers(len(b),size=len(b))]];v=stat([units[i]for i in idx])
        if v is not None:xs.append(v)
    return [float(np.percentile(xs,16)),float(np.percentile(xs,84))]if xs else None

def model_for_ratios(P:Camp,explicit:Path|None,site:dict|None=None)->tuple[dict|None,str]:
    """The measured model whose mp_check_overhead gives E.7's off/stride16 columns, measured on the CPU the table projects
    to (S3-R2-005): --cost-model, which must be measured on the target CPU (site['target_cpu'], or the target model's CPU;
    not evaluated for the Mac fakes); else, with target-site measurements (site['target_cost_model'], target_site), the
    TARGET model, read back at its recorded sha256; else PF's own pinned cost_model.json (measured basis, on PF's CPU,
    which is then the target's); None when PF has none."""
    tm=(site or{}).get('target_cost_model');want=(site or{}).get('target_cpu')or(tm or{}).get('cpu_model')
    if explicit:
        m,_=prod.read_cost_model(Path(explicit),P.m['backend'])
        if want is not None and prod.norm_cpu(m.get('cpu_model'))!=prod.norm_cpu(want):
            raise ValueError(f'--cost-model {explicit} was measured on {m.get("cpu_model")!r}: the MP self-check columns need a model on the target CPU {want!r} (S3-R2-005)')
        return m,f'--cost-model {Path(explicit).resolve()} (sha256 {digest(explicit)}, CPU {m.get("cpu_model")})'
    if tm:
        data=Path(tm['path']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=tm['sha256']:raise ValueError(f'--target-cost-model {tm["path"]} changed since the projection read it')
        m,_=prod.read_cost_model(Path(tm['path']),P.m['backend']);return m,f'--target-cost-model {tm["path"]} (sha256 {tm["sha256"]}, CPU {m.get("cpu_model")})'
    if P.m.get('cost_basis')=='measured'and P.m.get('cost_model_sha256'):
        m,_=prod.read_cost_model(P.run/'cost_model.json',P.m['backend']);return m,'PF\'s cost_model.json'
    return None,'no measured model'

def full(a)->dict:
    import pilot_select as ps
    P=Camp(a.pf,('pilot_full',));A=require_subset(a.pa,'stage_a');sel=load(a.pc_selection);nsel=ps.count(a.pc_selection)
    if a.pc is not None and nsel==0:raise ValueError('--pc given with an empty PC selection: an empty PC is never planned (D.3)')
    if a.pc is None and nsel>0:raise ValueError(f'the PC selection holds {nsel} graphs: --pc RUN is required')
    C=None
    if a.pc is not None:
        C=require_subset(a.pc,'confirm')
        if C.m['selection']['sha256']!=digest(a.pc_selection):raise ValueError('the --pc campaign was planned from another selection file')
    # S3-005: the PC selection (empty or not) belongs to this PF and PA: its recorded screen names their identities
    if sel.get('role')!='confirm'or sel.get('inputs_manifest_sha256')!=P.m['inputs_manifest_sha256']:raise ValueError(f'{a.pc_selection} is not a confirm selection of PF\'s inputs manifest')
    ss=sel.get('screen')or{};bound(ss.get('pf_identity'),P.identity,f'the PC selection {a.pc_selection} (its screen\'s PF)');bound(ss.get('pa_identity'),A.identity,f'the PC selection {a.pc_selection} (its screen\'s PA)')
    prf,pres=verify_pf(P);env=dict(os.environ);site=target_site(P,env,getattr(a,'target_cost_model',None))
    # S3-R2-009: the PC cap (25% of PF's L8 row seconds, E.8) against PF's CURRENT L8 row seconds, which a timing-only
    # re-merge of PF changes; recorded for the report, never a refusal (a completed PC is not re-run)
    cap=sel.get('cap')or{};l8=sum(sec for (t,s,L),G in P.g.items()if L==8 for pts,sec in G['cost'].values())
    pccap={'recorded_pf_l8_seconds':cap.get('pf_l8_seconds'),'current_pf_l8_seconds':l8,'fraction':cap.get('fraction'),'used_seconds':cap.get('used_seconds'),
           'within_cap_at_current':(cap['used_seconds']<=cap['fraction']*l8*(1+1e-12))if isinstance(cap.get('used_seconds'),(int,float))and isinstance(cap.get('fraction'),(int,float))else None}
    J8=jac8(P);core=stage_a_core(A)
    # item 2-3: per-graph tails on PF (all loops; actions on L8 only)
    tails=[];undef=[];zc=zc_set(P)
    for (t,s,L),G in P.g.items():
        for g in G['total']:
            _,tl=rows_at(P,(t,s,L),g,G['total'][g]);x=tail_stats(tl)
            e={'campaign':t,'sector':s,'L':L,'graph':g,**({k:v for k,v in x.items()if k!='shares'}),**({'zero_channel':True}if L==8 and (s,g)in zc else{})}
            (undef if 'undefined'in x else tails).append(e)
    scr=action1_screen(P)
    # item 10: alpha per sector from P1c's paired lengths (graph bootstrap), skewness at both lengths
    acen=alpha_p1c(A,[(x['sector'],x['graph'])for x in core['p1c']]);alpha=acen['by_sector']
    conf=[confirm_graph(C,key.split(':')[0],r['id'],(alpha.get(key.split(':')[0])or{}).get('alpha'))for key,lst in (C.sel['groups'].items()if C else[])for r in lst]
    conf_all=[x for x in conf+core['p1c']if x.get('confirmed')]
    # action 3: proportional hold per sector
    pop=per_graph_sigma(P,J8);hold=action3_hold(P,A,C,J8,conf_all,pop)
    inv8={s:{r['id']:r for r in P.inv[s].get('8',[])}for s in ('free','power')}
    massc={}
    for x in conf_all:
        k=f'{x["sector"]}|double_lift={inv8[x["sector"]][x["graph"]]["double_lift"]}';massc.setdefault(k,[]).append(x['graph'])
    # action 5: P8 per stratum (PF) and pooled per sector and L class, with the graph-bootstrap band
    strata,pooled=action5(P,J8,ps.strata(P.inv))
    p8cls={(k.split('|')[0],k.split('|')[1]):v['P8_hat']for k,v in pooled.items()};p8band={(k.split('|')[0],k.split('|')[1]):v['band68']for k,v in pooled.items()}
    # item 12: the held-out R = 8 design penalty on the 1/8 overlap, per sector with that sector's R_PF
    ho=heldout_by_sector(A,P,J8)
    # item 13: the cost table
    eta=a.eta_node if a.eta_node is not None else eta_from_ledger(P)
    lat={}
    for name,camp in (('PA',A),('PF',P),('PC',C)):
        if camp is None:continue
        acct,why=try_account(camp.run,env);lat[name]=queue_latency(acct)if acct else why
    res=pres['sizing_only'];c8=float(res['C8_full']);c8se=res.get('sampling_standard_error')   # the verified, PF-bound result (S3-006)
    model,msrc=model_for_ratios(P,getattr(a,'cost_model',None),site)   # S3-R2-005: the target CPU's MP overheads
    table=cost_table(P,J8,eta,acen,p8cls,{s:v['corrected']for s,v in ho.items()}if ho else None,c8,p8band,float(c8se)if c8se is not None else None,
                     mp_ratios(model,P.m['mp_check'],msrc),lat,site)
    table['mp_check_ratio_model']=msrc
    cross=None
    if a.design_bundle:
        se=plugin_se_of_bundle(P,J8,a.design_bundle);d=load(Path(a.design_bundle)/'design.json');theirs=d['prediction']['se_raw_total']
        cross={'bundle':str(a.design_bundle),'label':d.get('label'),'se_recomputed_alpha_half':se,'se_of_the_design_tool':theirs,'relative_difference':abs(se-theirs)/theirs,
               'agree_1pct':abs(se-theirs)<=0.01*theirs,'column':'plug-in (no realism factor, no same-data correction), alpha = 1/2'}
    # item 14: the growth file for C62d
    growth=[]
    D80=abs(sum(np.mean([y_top([G['jets'][(r,g)]])[0]for r in range(G['reps'])])for (t,s,L),G in P.g.items()if L==8 for g in G['total'])/2)
    for (t,s,L,g),(sig,cg,R,n) in pop.items():
        if L==8:growth.append({'campaign':t,'sector':s,'graph':g,'sigma':sig,'sigma_over_C8':sig/abs(c8)if c8 else None,'sigma_over_D80':sig/D80 if D80 else None,'cost_per_point':cg})
    sigma_cost=[{'campaign':t,'sector':s,'L':L,'graph':g,'R':R,'points':n,'sigma':sig,'cost_per_point':cg,'zero_channel':L==8 and (s,g)in zc}for (t,s,L,g),(sig,cg,R,n) in pop.items()]
    pc_note=('PC: no graph selected ('+str(sel.get('empty_reason'))+')')if nsel==0 else f'PC: {nsel} graphs'
    zch=zc_entries(scr,'PF screen (4,096 points)')+core['zero_channel_heavy_tail']+zc_entries(conf,'PC confirmation (32,768 points)')
    return {'schema':SCHEMA,'part':'full','made_utc':utc(),'pa':str(A.run),'pf':str(P.run),'pc':str(C.run)if C else None,'pc_note':pc_note,'pf_result':prf,'pc_cap':pccap,
            'histograms':histograms(P),'tails':{'defined':len(tails),'undefined':undef,'per_graph':tails},
            'action1_screen':{'flagged':[x for x in scr if x['flag']],'graphs':len(scr)},
            'action2_confirm':{'confirmations':conf,'possible_infinite_variance':[x for x in conf if x.get('confirmed')]},
            'action2b':{'p1c':{'graphs':len(core['p1c']),'confirmations':core['p1c'],'unscreened_confirmed':core['unscreened']},
                        'ext_2b':[r for key,lst in (sel['groups'].items())for r in lst if r.get('label')=='ext_2b']},
            'zero_channel_heavy_tail':{'status':ps.ZC_NOTE,'graphs':zch,'rule':'L8 graphs with s_G = 4 (3 w_B = w_A): the C8 contribution is identically zero; never '
                                       'flagged, confirmed, selected for PC or counted in the 3% hold test, and excluded from P8_hat, alpha_hat and item 12 (host refinement, Stage 3a repair round 3)'},
            'action3_hold':hold,'action3b_classes':{'by_double_lift':massc,'argmax_points':'regenerate with bin/c8d3_inspect --point on Expanse (C.7)'},
            'action4':core['action4'],'action5':{'strata':strata,'pooled':pooled},'alpha':acen,'new_slots':new_slots(P,J8),'design_penalty_heldout':ho,
            'cost_table':table,'crosscheck':cross,'growth':growth,'sigma_cost':sigma_cost}

def heldout_by_sector(A,P,J8)->dict|None:
    """E.6 item 12 per sector (E.7's P_hat is per sector): {sector: design_penalty_heldout(...)} over the sector's stage-A
    stratified graph-campaigns (campaigns a and b pooled), each corrected with c4(R_PF)^2 of that sector's PF L8 groups.
    After action 4 the sectors may differ (R = 8 in one, 16 in the other); within a sector both campaigns' PF L8 groups
    must have one replicate count (else refused). None when no stratified graph-campaign has s_PA, s_PF > 0. The result
    does not depend on the order of the selection's keys. Zero-channel graphs are excluded (zc_set)."""
    rows={};zc=zc_set(P)|zc_set(A)
    for key in sorted(A.sel['groups']):
        s=key.split(':')[0]
        for r in A.sel['groups'][key]:
            if r['label']!='stratified'or (s,r['id'])in zc:continue
            for t in ('a','b'):
                jA,_=rows_at(A,(t,s,8),r['id'],SCREEN_POINTS);G=P.g[(t,s,8)]
                yP=[float(np.dot(J8[8],G['jets'][(rr,r['id'])]))for rr in range(G['reps'])];yA=[float(np.dot(J8[8],v))for v in jA]
                sA,sP=float(np.std(yA,ddof=1)),float(np.std(yP,ddof=1));pts,sec=G['cost'][r['id']]
                if sA>0 and sP>0:rows.setdefault(s,[]).append((sA,sP,sec/pts))
    out={}
    for s in sorted(rows):
        Rs=sorted({P.g[(t,s,8)]['reps']for t in ('a','b')})
        if len(Rs)!=1:raise ValueError(f'item 12: the {s} sector\'s PF L8 groups have replicate counts {Rs}; one R_PF per sector is required (E.6 item 12, E.7)')
        out[s]=design_penalty_heldout([x[0]for x in rows[s]],[x[1]for x in rows[s]],[x[2]for x in rows[s]],Rs[0])
    return out or None

def action1_screen(P)->list:
    """Action 1 on PF: every L8 graph of each sector at 4,096 points (L <= 7 graphs are never screened, RECON:1396)."""
    out=[]
    for s in ('free','power'):
        for g in sorted(P.g.get(('a',s,8),{'total':{}})['total']):out.append(screen_graph(P,s,g,SCREEN_POINTS))
    return out

def sigma_32768(camps,key,g,J8)->list:
    """sigma_hat(32,768) = sqrt(32768 Var_ddof1(J8 . jets)) of graph g from every campaign in `camps` that holds its
    32,768-point rows (PA for P1c graphs, PC for screened and ext_2b graphs; the length rule, R06)."""
    out=[]
    for c in camps:
        if c is None or key not in c.g or g not in c.g[key]['total']:continue
        G=c.g[key]
        if G['total'][g]!=CONFIRM_POINTS and (0,g,CONFIRM_POINTS)not in G.get('prefix',{}):continue
        j2,_=rows_at(c,key,g,CONFIRM_POINTS)
        out.append(math.sqrt(CONFIRM_POINTS*float(np.var([float(np.dot(J8[8],v))for v in j2],ddof=1))))
    return out

def action3_hold(P,A,C,J8,conf_all:list,pop:dict)->dict:
    """Action 3 (E.6 item 6): per sector, the confirmed graphs' share of the projected L8 variance (sigma_hat sqrt(c) over
    the sector's sum) and of the projected cost (confirmed graphs at the sector's 90th percentile of n_g); > 3% holds the
    sector. sigma_hat of a confirmed graph is the larger of PF's 4,096-point estimate and its 32,768-point estimates,
    from PA (P1c graphs) and from PC (screened and ext_2b graphs), whichever hold its 32,768-point rows; an empty PC
    (C None) leaves PA's (R01). Zero-channel graphs never count as confirmed here (zc_set; they are never confirmed)."""
    hold={};zc=zc_set(P)
    for s in ('free','power'):
        keys=[k for k in pop if k[1]==s and k[2]==8]
        if not keys:continue
        sig={k:pop[k][0]for k in keys};c={k:pop[k][1]for k in keys};src={}
        conf_s=[x for x in conf_all if x['sector']==s and (s,x['graph'])not in zc]
        for x in conf_s:
            for t in ('a','b'):
                k=(t,s,8,x['graph'])
                if k not in sig:continue
                cand=sigma_32768((A,C),(t,s,8),x['graph'],J8)
                if cand and max(cand)>sig[k]:sig[k]=max(cand);src[k]='32768'
        cg={x['graph']for x in conf_s};tot=sum(sig[k]*math.sqrt(c[k])for k in keys);shv=sum(sig[k]*math.sqrt(c[k])for k in keys if k[3]in cg)
        n={k:sig[k]/math.sqrt(c[k])for k in keys};n90=float(np.percentile(list(n.values()),90))if n else 0.
        cost_fixed=sum((n90 if k[3]in cg else n[k])*c[k]for k in keys);shc=sum(n90*c[k]for k in keys if k[3]in cg)
        hold[s]={'confirmed':len(cg),'variance_share':shv/tot if tot else 0.,'cost_share':shc/cost_fixed if cost_fixed else 0.,
                 'hold':(shv/tot if tot else 0.)>HOLD_SHARE or (shc/cost_fixed if cost_fixed else 0.)>HOLD_SHARE,
                 'sigma_from_32768':sorted(f'{k[0]}:{k[3]}'for k in src),
                 'zero_channel_excluded':sorted({x['graph']for x in conf_all if x['sector']==s and (s,x['graph'])in zc})}
    return hold

def action5(P,J8,strata_of:dict)->tuple[dict,dict]:
    """Action 5 (E.6 item 9): P8_hat per PF stratum of L8 graph-campaigns (>= 500 Q values and > 1.196 flags; no stratum is
    re-run), and the same estimator pooled per sector and L class (L8; L <= 7, the C8 Jacobian combination) with a 68%
    bootstrap band over GRAPHS (a graph's Q values from both campaigns form one resampling unit), which feeds E.7. L <= 7
    graphs enter no stratum and no flag; zero-channel L8 graphs enter neither (zc_set)."""
    import pilot_select as ps
    where={(k[0],g):ps.stratum_key(k)for k,ids in strata_of.items()for g in ids};qs={};units={};zc=zc_set(P)
    for (t,s,L),G in P.g.items():
        for g in G['total']:
            if L==8 and (s,g)in zc:continue
            jets,_=rows_at(P,(t,s,L),g,G['total'][g]);y=y_top(jets)if L==8 else[float(np.dot(J8[L],v))for v in jets];q=split_q(y)
            if L==8:qs.setdefault(where[(s,g)],[]).extend(q)
            units.setdefault((s,'L8'if L==8 else'L<=7'),{}).setdefault((L,g),[]).extend(q)
    strata={k:{'graph_campaign_Q':len(v),'P8_hat':p8_pooled(v),'flag':len(v)>=P8_STRATUM_MIN and (p8_pooled(v)or 0)>P8_STRATUM}for k,v in qs.items()}
    pool=lambda vv:p8_pooled([q for x in vv for q in x]);pooled={}
    for (s,c),u in units.items():
        v=[u[k]for k in sorted(u)]
        pooled[f'{s}|{c}']={'P8_hat':pool(v),'band68':boot_band(v,pool),'graphs':len(v),'Q_values':sum(len(x)for x in v),'bootstrap_unit':'graph (both campaigns together)'}
    return strata,pooled

def verify_pf(P:Camp)->tuple[dict,dict]:
    """PF's C8_pilot_result.json verified (tools/verify_result.py) and bound to PF (S3-006: verify_result.bind, its source
    manifest, merged files, role, test_only, build, numerics, MP mode, allocation and two-loop pin are PF's current ones).
    Returns (record, the verified result)."""
    import verify_result as vr
    f=P.run/'C8_pilot_result.json'
    if not f.exists():raise ValueError(f'{P.run}: no C8_pilot_result.json (assemble PF first)')
    data=f.read_bytes();doc=json.loads(data);vr.verify(doc)
    try:vr.bind(doc,P.m,P.mh,P.I,P.identity['merged_sha256'],P.identity['science_sha256'])
    except vr.Mismatch as e:raise ValueError(f'{f}: {e}')
    return {'path':str(f),'sha256':hashlib.sha256(data).hexdigest(),'verified':True,'bound_to':{k:P.identity[k]for k in ('manifest_sha256','campaign_role')}},doc

def eta_from_ledger(P:Camp)->float:
    import accounting
    r=accounting.account(P.run,dict(os.environ))
    if not r['eta_node']:raise ValueError('no eta from the accounting: give --eta-node for a test pilot')
    return 1/r['eta_node']

# ---------------------------------------------------------------- PILOT_REPORT.md (A-PIL-5)
def _f(x,p=4):
    if x is None:return 'n/a'
    if isinstance(x,bool):return 'yes'if x else 'no'
    if isinstance(x,(int,float)):return f'{x:.{p}g}'
    return str(x)
def _band(b,p=4):return f'[{_f(b[0],p)}, {_f(b[1],p)}]'if b else 'n/a'

def markdown(r:dict)->str:
    """PILOT_REPORT.md: the human-readable view of pilot_report.json (A-PIL-5): the campaigns, the tail actions with every
    flagged, confirmed or held graph, the zero-channel heavy tails, P8_hat and alpha with their bands, the design penalty,
    the cost-vs-precision table with its bands, the measured/projected statement, queue latency, and the decisions the
    user now faces. The JSON is the record; this file adds nothing to it."""
    t=r['cost_table'];L=[]
    L+=['# C8(3) pilot report','',f'Made {r["made_utc"]} by tools/pilot_report.py (schema {r["schema"]}). The record is pilot_report.json; this page is its summary.','',
        f'- PA: `{r["pa"]}`',f'- PF: `{r["pf"]}` (C8_pilot_result.json sha256 `{r["pf_result"]["sha256"][:12]}`, verified; for sizing only, never an estimate)',
        f'- PC: `{r["pc"]}`'if r['pc']else '- PC: none',f'- {r["pc_note"]}','']
    h=r['histograms'];L+=['## MP self-check','',f'Alarmed points: {h["mp_alarm_total"]} ({"ALARM" if h["alarm"] else "no alarm"}).','']
    L+=['## Tail actions (L8; thresholds as pre-registered)','',f'Per-graph tail statistics: {r["tails"]["defined"]} defined, {len(r["tails"]["undefined"])} undefined (listed in the JSON, never compared).','']
    fl=r['action1_screen']['flagged'];L+=[f'### Action 1 (screen): {len(fl)} of {r["action1_screen"]["graphs"]} L8 graphs flagged','']
    if fl:
        L+=['| sector | graph | xi a | xi b | share a | share b |','|---|---:|---:|---:|---:|---:|']
        for x in fl:
            ca=x['campaigns'];L.append(f'| {x["sector"]} | {x["graph"]} | {_f(ca["a"].get("xi"))} | {_f(ca["b"].get("xi"))} | {_f(ca["a"].get("share_max"))} | {_f(ca["b"].get("share_max"))} |')
        L.append('')
    pv=r['action2_confirm']['possible_infinite_variance'];L+=[f'### Action 2 (confirm, PC): {len(pv)} possible infinite variance of {len(r["action2_confirm"]["confirmations"])} checked','']
    for x in pv:L.append(f'- {x["sector"]} {x["graph"]}: mean xi(32,768) = {_f(x["xi_mean_32768"])}')
    p1=r['action2b']['p1c'];L+=['',f'### Action 2b (P1c): {p1["graphs"]} graphs; confirmed without a screen flag: {len(p1["unscreened_confirmed"])}; extension graphs: {len(r["action2b"]["ext_2b"])}','']
    for x in p1['unscreened_confirmed']:L.append(f'- {x["sector"]} {x["graph"]}: mean xi(32,768) = {_f(x.get("xi_mean_32768"))}')
    z=r['zero_channel_heavy_tail'];L+=['',f'### Zero-channel heavy tails: {len(z["graphs"])} ({z["status"]})','',z['rule'],'']
    for x in z['graphs']:L.append(f'- {x["sector"]} {x["graph"]} ({x["stage"]}): {x["status"]}')
    L+=['','### Action 3 (proportional hold, 3%)','','| sector | confirmed | variance share | cost share | hold |','|---|---:|---:|---:|---|']
    for s,x in r['action3_hold'].items():L.append(f'| {s} | {x["confirmed"]} | {_f(x["variance_share"])} | {_f(x["cost_share"])} | {"HOLD" if x["hold"] else "no"} |')
    L+=['','### Action 3b (classes)','']+[f'- {k}: {v}'for k,v in r['action3b_classes']['by_double_lift'].items()]+['']
    L+=['### Action 4 (stage A) and action 5 (PF): P8_hat','','| sector | stage-A P8_hat | R for PF |','|---|---:|---:|']
    for s,x in r['action4'].items():L.append(f'| {s} | {_f(x["P8_hat"])} | {x["R"]} |')
    fs=[k for k,v in r['action5']['strata'].items()if v['flag']]
    L+=['',f'Strata flagged (>= 500 Q values and P8_hat > 1.196; no stratum is re-run): {fs or "none"}','','| sector and class | pooled P8_hat | 68% graph-bootstrap band | graphs |','|---|---:|---|---:|']
    for k,x in r['action5']['pooled'].items():L.append(f'| {k} | {_f(x["P8_hat"])} | {_band(x["band68"])} | {x["graphs"]} |')
    al=r['alpha'];L+=['','## alpha (P1c paired lengths)','',f'Central {_f(al["central"])}, 68% graph-bootstrap band {_band(al["band68"])}.','']
    for s,x in al['by_sector'].items():L.append(f'- {s}: alpha {_f(x["alpha"])}, band {_band(x["band68"])}, {x["graphs"]} graphs')
    L+=['','## Design penalty on the 1/8 overlap (item 12)','']
    for s,x in (r['design_penalty_heldout']or{}).items():L.append(f'- {s}: raw {_f(x["raw"])}, corrected {_f(x["corrected"])} (R_PF {x["R_PF"]}, {x["graphs"]} graph-campaigns)')
    if not r['design_penalty_heldout']:L.append('None: no stage-A stratified graph-campaign (zero channels excluded) has s_PA, s_PF > 0.')
    L+=['','## Cost vs precision (E.7)','',t['note']+'.',f'eta (allocated/busy) {_f(t["eta_allocated_over_busy"])}; |C8| of the pilot {_f(t["c8_pilot"])} +- {_f(t["c8_pilot_se"])} (sizing only).',
        f'Target site {t["site"]["site"]} ({t["site"]["partition"]}, {_f(t["site"]["allocated_cpus_per_node"])} allocated CPUs per node, CPU {t["site"]["target_cpu"]}; PF measured on '
        f'{t["site"]["measured_cpu"]}{", costs scaled by the target-site model" if t["site"]["cost_scaled"] else ""}): SU columns in {t["site"]["unit"]}.','',
        '| target | R | plug-in core-h | F [P8 band] | realistic core-h | SU | SU band | wall h, 4 nodes | wall h, 22 nodes | SU by mp-check |',
        '|---|---:|---:|---|---:|---:|---|---:|---:|---|']
    for x in t['rows']:
        if x.get('SE')is None:L.append(f'| {x["kind"]} {x["target"]} | | | {x["undefined"]} | | | | | | |');continue
        tg=f'SE {x["target"]}'if x['kind']=='absolute'else f'{x["target"]} x |C8| (SE {_f(x["SE"],3)})'
        fb=_band(x['band_p8']['F'])if x.get('band_p8')else 'n/a'
        mp=', '.join(f'{k}: {_f(v,4) if isinstance(v,float) else "pending P1"}'for k,v in x['allocated_su_by_mp_check'].items())
        L.append(f'| {tg} | {x["R"]} | {_f(x["plugin_busy_core_hours"])} | {_f(x["F"])} {fb} | {_f(x["realistic_busy_core_hours"])} | {_f(x["allocated_su"])} | '
                 f'{_band(x["band"]["allocated_su"])}{" (unbounded above)" if x["band"]["unbounded_above"] else ""} | {_f(x["wall_hours_4_nodes"],3)} | {_f(x["wall_hours_22_nodes"],3)} | {mp} |')
    L+=['','Bands: the envelope over the ends of the alpha, P8_hat and |C8| bands (68% each). Measured: '+t['measured']+'. Projected: '+t['projected']+'.','']
    if r.get('crosscheck'):
        x=r['crosscheck'];L+=[f'Design cross-check ({x["label"]}): recomputed SE {_f(x["se_recomputed_alpha_half"])} vs the tool\'s {_f(x["se_of_the_design_tool"])} '
                              f'({"agree" if x["agree_1pct"] else "DIFFER"} to 1%, {x["column"]}).','']
    L+=['## Queue latency (submission to start; apart from eta)','']
    for k,v in (t.get('queue_latency')or{}).items():
        if isinstance(v,dict):L.append(f'- {k}: '+', '.join(f'{c} {x["attempts"]} attempts, mean {_f(x["mean_seconds"],3)} s, max {_f(x["max_seconds"],3)} s'for c,x in v.items()))
        else:L.append(f'- {k}: {v}')
    held=[s for s,x in r['action3_hold'].items()if x['hold']]
    L+=['','## Decisions for the user','','- the production target SE (table above);','- R for production (stage-A action 4: '+', '.join(f'{s} R={x["R"]}'for s,x in r['action4'].items())+');',
        f'- held sectors for the margin re-derivation: {held or "none"};','- the MP tier policy (RECON D2; the off/stride16 columns).','',
        'No production job is planned or submitted by this report.','']
    return '\n'.join(L)

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('subset-check');q.add_argument('run',type=Path)
    q=s.add_parser('stage-a');q.add_argument('run',type=Path);q.add_argument('--output','--out',dest='output',type=Path,help='the stage-A report (JSON)')
    q.add_argument('--eta-node',type=float,help='busy/allocated efficiency (test pilots; default from tools/accounting.py)')
    q.add_argument('--line-cap',type=float,help='the pilot line in SU (default C8_PILOT_SU_CAP)');q.add_argument('--spent',type=float,help='committed pilot-line SU (default tools/budget.py)')
    q.add_argument('--pf-nodes',type=int,default=4);q.add_argument('--pc-nodes',type=int,default=2)
    q=s.add_parser('screen');q.add_argument('--pf',type=Path,required=True);q.add_argument('--pa',type=Path,required=True);q.add_argument('--out','--output',dest='out',type=Path,required=True)
    q=s.add_parser('full');q.add_argument('--pa',type=Path,required=True);q.add_argument('--pf',type=Path,required=True);q.add_argument('--pc-selection',type=Path,required=True)
    q.add_argument('--pc',type=Path);o=q.add_mutually_exclusive_group(required=True)
    o.add_argument('--output',type=Path,help='pilot_report.json; the growth and sigma/cost files go next to it')
    o.add_argument('--out',type=Path,help='a directory: DIR/pilot_report.json and the growth and sigma/cost files')
    q.add_argument('--markdown',type=Path,help='PILOT_REPORT.md');q.add_argument('--cost-model',type=Path,help='the measured model for the mp-check columns (default PF\'s own)')
    q.add_argument('--eta-node',type=float,help='busy/allocated efficiency (test pilots)')
    q.add_argument('--design-bundle',type=Path)
    q.add_argument('--target-cost-model',type=Path,help='a measured model on the target site\'s CPU: required when C8_SITE names a site whose CPU PF was not measured on (S3-010)')
    a=p.parse_args(argv)
    try:
        if a.cmd=='subset-check':r=subset_check(a.run)
        elif a.cmd=='stage-a':
            r=stage_a(a.run,StageAOptions(a.eta_node,a.line_cap,a.spent,a.pf_nodes,a.pc_nodes))
            if a.output:dump(a.output,r)
            if r['go']!='GO':print('pilot_report: stage A NO-GO: '+'; '.join(r['go_reasons']),file=sys.stderr)
        elif a.cmd=='screen':r=screen(a.pf,a.pa);dump(a.out,r)
        else:
            r=full(a);js=a.output if a.output else a.out/'pilot_report.json';d=js.parent;d.mkdir(parents=True,exist_ok=True);sc=r.pop('sigma_cost')
            r['side_files']={'growth':'growth_c63d.csv','sigma_cost':'sigma_cost.csv','markdown':str(a.markdown)if a.markdown else None};dump(js,r)
            (d/'growth_c63d.csv').write_text('campaign,sector,graph,sigma,sigma_over_C8,sigma_over_D80,cost_per_point\n'+
                                             ''.join(f'{x["campaign"]},{x["sector"]},{x["graph"]},{x["sigma"]},{x["sigma_over_C8"]},{x["sigma_over_D80"]},{x["cost_per_point"]}\n'for x in r['growth']))
            (d/'sigma_cost.csv').write_text('campaign,sector,L,graph,R,points,sigma,cost_per_point,zero_channel\n'+
                                            ''.join(f'{x["campaign"]},{x["sector"]},{x["L"]},{x["graph"]},{x["R"]},{x["points"]},{x["sigma"]},{x["cost_per_point"]},{int(x["zero_channel"])}\n'for x in sc))
            if a.markdown:a.markdown.parent.mkdir(parents=True,exist_ok=True);a.markdown.write_text(markdown(r))
    except Refuse as e:print(f'pilot_report: {e}',file=sys.stderr);return e.code
    except (ValueError,KeyError,OSError)as e:print(f'pilot_report: {e}',file=sys.stderr);return 1
    print(json.dumps({k:v for k,v in r.items()if k in('schema','part','state','graphs','campaign','pc_note','go','go_reasons')},default=str));return 0
if __name__=='__main__':sys.exit(main())
