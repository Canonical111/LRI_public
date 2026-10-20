#!/usr/bin/env python3
"""The pilot's selection files (PLAN E.8, HD14; schema c8-d3-selection-1), deterministic from a registered seed.

  pilot_select.py stage-a --seed S --cost-model M --out FILE [--seeds-log LOG] [--inputs DIR]
  pilot_select.py confirm --screen PF_RUN --pa PA_RUN --seed S --out FILE [--cost-model M] [--seeds-log LOG]
                                                  (the runbook's step 7.3: the screen is computed here, pilot_report.screen)
  pilot_select.py confirm --screen SCREEN.json --pf PF_RUN --seed S --out FILE [--cost-model M] [--seeds-log LOG]
                                                  (a screen file written by `pilot_report.py screen`)
  pilot_select.py count FILE                    (a login-node query: schema check, prints the graph count)

stage-a (the PA file, role stage_a; L8 only): stage A = 1/8 of each stratum (sector x T bin x M tertile; T = terms in
bins 0-8, 8-24, 24-48, 48-96, > 96; M = monomials in tertiles per sector), uniform within the stratum, rounded half up,
plus the heaviest 1% per sector by measured cost (the campaign-keyed model, mean of a and b) with certainty (labelled
heaviest_1pct unless also drawn in their stratum). P1c = 1/32 of each stratum of stage A's STRATIFIED part, uniform
within the stratum (about 1/256 of L8; a heaviest_1pct graph only if also drawn in its stratum, HD14). Stage-A graphs
appear at 4,096 points labelled stratified or heaviest_1pct; P1c graphs once each as points 32,768 nest [4096] label
p1c (their stage-A statistics come from their 4,096-point prefix rows, E.6).
confirm (the PC file, role confirm; labels screen and ext_2b; every graph points 32,768 nest [4096]): the L8 graphs the
screen flagged, capped at 25% of PF's L8 cost (PF's measured L8 row seconds; a PC graph costs (c_a + c_b) x f x 32,768 x 8,
c from the cost model: --cost-model M, or PF's own measured model, its pinned cost_model.json, which must match PF's whole
HD11 identity, executable sha256, CPU model and MP self-check mode; f = the model's measured overhead factor for PF's MP
self-check mode, 1 in its own mode, as production.py plans; S3-003); when they cost more, a registered-seed subset
uniform within each stratum fills the cap, the flagged graphs of BOTH sectors allocated jointly over every stratum
(sector x T bin x M tertile; no sector first; S3-002): every stratum proposes the same fraction of its graphs in a seeded
random order, and when the proposals cost more than the budget the common fraction is lowered until they fit, so no
stratum is served before another (S3-R2-002); then seeded random leftovers while they fit. For every sector in which a P1c graph was confirmed WITHOUT a
screen flag (action 2b), a registered-seed random sample of that sector's unflagged graphs, uniform within strata,
extends the check inside what is left of the cap, the extension sectors again allocated jointly. No step ever exceeds
the cap, the first fraction-per-stratum allocation included, and the selection's cost is recomputed from its rows and
checked against the cap before it is written (S3-001). With no screened graph and no unscreened confirmation it writes
"groups": {} and an empty_reason giving both counts. The file records the screen it used ("screen") with PF's and PA's
campaign identities (manifest, role, selection sha256 and every group's scientific identity; S3-005, S3-R2-009: not the
merged.json bytes, which a timing-only re-merge changes): a screen file (--screen SCREEN.json) must name the given --pf
(and --pa, when given), else it is refused.
Zero-channel L8 graphs (s_G = 4, i.e. 3 w_B = w_A: the C8 Jacobian row at L8 is proportional to (-1, 3), so their C8
contribution is identically zero) are never selected, neither from the screen nor for the 2b extension: a heavy t tail
of such a graph is reported as "zero-channel heavy tail, not confirmed" and costs no PC budget (host refinement, Stage
3a repair round 3).
The seed must be in the seed log (--seeds-log, default $C8_SEEDS): every pilot seed is registered (HD6, A-DES-4). Never
a cost: no scheduling basis (prior_cost_model.json, the synthetic fixture, tools/bootstrap_proxy.json) is opened (D.5:
every campaign read here passes production.verify_base with scheduling_copies=False).
"""
from __future__ import annotations
import argparse,hashlib,itertools,json,math,os,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Refuse,digest,dump,load
import production as prod

T_BINS=(8,24,48,96,math.inf);T_LABELS=('0-8','8-24','24-48','48-96','>96')
STAGE_A_FRACTION=8;P1C_FRACTION=32;HEAVIEST=0.01;PC_POINTS=32768;PC_NEST=[4096];PC_REPS=8;CAP_FRACTION=0.25;PILOT_POINTS=4096

def t_bin(T:int)->int:return next(i for i,u in enumerate(T_BINS)if T<=u)

ZERO_CHANNEL_SG=4
ZC_NOTE='zero-channel heavy tail, not confirmed'
def zero_channel(row:dict)->bool:
    """s_G = 12 w_B / w_A = 4, i.e. 3 w_B = w_A (tools/prepare_inputs.py): the top-slot combination 3 jet_1 - jet_0 of the
    graph vanishes identically. At L8 the C8 Jacobian row is proportional to (-1, 3), so an L8 zero-channel graph carries no
    C8 variance; its t = v_0 jac tail is weight-free and can still be heavy (power L7 G1601, Stage 3a repair round 2)."""
    return row.get('s_G')==ZERO_CHANNEL_SG

def zero_channel_l8(inv:dict)->set:
    """{(sector, graph)} of the L8 zero-channel graphs of an inventory (host refinement, Stage 3a repair round 3)."""
    return {(s,r['id'])for s in ('free','power')for r in (inv.get(s)or{}).get('8',[])if zero_channel(r)}

def strata(inv:dict)->dict:
    """{(sector, T bin, M tertile): [graph ids]} of the L8 inventory."""
    out={}
    for s in ('free','power'):
        rows=inv.get(s,{}).get('8',[])
        if not rows:continue
        ms=sorted(r['monomials']for r in rows);q1=ms[len(ms)//3];q2=ms[(2*len(ms))//3]
        for r in rows:
            mt=0 if r['monomials']<q1 else(1 if r['monomials']<q2 else 2)
            out.setdefault((s,t_bin(r['terms']),mt),[]).append(r['id'])
    return {k:sorted(v)for k,v in sorted(out.items())}

def stratum_key(k)->str:return f'{k[0]}|T{T_LABELS[k[1]]}|M{k[2]}'

def registered(seed:int,log)->None:
    if log is None:raise Refuse(64,'give --seeds-log or set C8_SEEDS: every pilot seed is registered first (seeds.py add --seed S --label ...)')
    if seed not in prod.read_seed_file(Path(log)):raise Refuse(64,f'seed {seed} is not registered in {log}: run tools/seeds.py add --seed {seed} --label "pilot selection" first (HD6)')

def campaign_model(run:Path)->Path:
    """The measured cost model a campaign was planned with (its cost_model.json, pinned by the manifest's
    cost_model_sha256 and checked by verify_base); a campaign on any other basis has none (D.5) and is refused."""
    run=Path(run).resolve();m,_,_,_=prod.verify_base(run,check_executable=False,accept_tool_change=True,scheduling_copies=False)
    if m.get('cost_basis')!='measured'or not m.get('cost_model_sha256'):raise ValueError(f'{run}: cost basis {m.get("cost_basis")!r}, no measured cost model; give --cost-model')
    return run/'cost_model.json'

def costs(model_path:Path,backend='gmp',factor:float=1.0)->dict:
    m,_=prod.read_cost_model(model_path,backend)
    out={}
    for k,v in m['seconds_per_point'].items():
        c,s,L,g=k.split(':')
        if L=='8':out.setdefault((s,int(g)),{})[c]=float(v)*factor
    return out

def pc_costs(model_path:Path,pf:Path)->tuple[dict,dict]:
    """The PC pricing (S3-003): the model checked against PF's complete HD11 identity (executable sha256, the CPU model
    of PF's plan host, the MP self-check mode: production.identity_problems, as `plan` checks it) and its L8 seconds per
    point times its measured overhead factor for PF's MP self-check mode (production.mp_factor; 1 in the model's own
    mode), the factor production.py applies when it plans PC in that mode. Returns (costs, pricing record)."""
    run=Path(pf).resolve();m,_,_,_=prod.verify_base(run,check_executable=False,accept_tool_change=True,scheduling_copies=False)
    model,_=prod.read_cost_model(model_path,m['backend']);cpu=(m.get('fingerprint')or{}).get('cpu_model')
    prob=prod.identity_problems(model,m['executable_sha256'],cpu,m['mp_check'])
    if prob:raise ValueError(f'the cost model {model_path} does not match PF\'s identity (HD11): '+'; '.join(f'{k} model {x!r} vs PF {y!r}'for k,(x,y) in prob.items()))
    f=prod.mp_factor(model,m['mp_check'])
    return costs(model_path,m['backend'],f),{'mp_check':m['mp_check'],'mp_check_factor':f,'model_mp_check':model.get('mp_check'),'cpu_model':model.get('cpu_model'),
                                            'executable_sha256':model.get('executable_sha256'),'rule':'(c_a + c_b) x mp_check_factor x 32,768 x 8 (S3-003)'}

def draw(rng,ids:list,n:int)->list:
    n=max(0,min(n,len(ids)))
    return sorted(int(x)for x in rng.choice(np.asarray(ids),size=n,replace=False))if n else[]

def stage_a(inv:dict,im_sha:str,seed:int,cost:dict)->dict:
    rng=np.random.default_rng(seed);st=strata(inv);groups={};info={}
    drawn={k:draw(rng,ids,(len(ids)+STAGE_A_FRACTION//2)//STAGE_A_FRACTION)for k,ids in st.items()}
    for s in ('free','power'):
        ids=[r['id']for r in inv.get(s,{}).get('8',[])]
        if not ids:continue
        miss=[g for g in ids if (s,g)not in cost or set(cost[(s,g)])!={'a','b'}]
        if miss:raise ValueError(f'the cost model has no a and b key for {s} L8 graph {miss[0]}')
        k=math.ceil(HEAVIEST*len(ids));heavy=sorted(sorted(ids,key=lambda g:(-(cost[(s,g)]['a']+cost[(s,g)]['b']),g))[:k])
        strat={g for key,v in drawn.items()if key[0]==s for g in v}
        p1c=set()
        for key,v in drawn.items():
            if key[0]==s:p1c|=set(draw(rng,v,(len(v)+P1C_FRACTION//2)//P1C_FRACTION))
        rows=[]
        for g in sorted(strat|set(heavy)):
            if g in p1c:rows.append({'id':g,'points':PC_POINTS,'nest':list(PC_NEST),'label':'p1c'})
            else:rows.append({'id':g,'points':PILOT_POINTS,'label':'stratified'if g in strat else'heaviest_1pct'})
        groups[f'{s}:8']=rows
        info[s]={'graphs':len(ids),'stratified':len(strat),'heaviest_1pct':len(set(heavy)-strat),'p1c':len(p1c)}
    return {'schema':prod.SELECTION_SCHEMA,'inputs_manifest_sha256':im_sha,'role':'stage_a','seed':seed,'groups':groups,'empty_reason':None,
            'strata':{stratum_key(k):{'graphs':len(v),'stage_a':len(drawn[k])}for k,v in st.items()},'counts':info,
            'rule':'stage A 1/8 per stratum (sector x T bin x M tertile) + the heaviest 1% per sector; P1c 1/32 of each stratum of the stratified part (E.8, HD14)'}

def pf_l8_cost(pf:Path)->float:
    run=Path(pf).resolve();m,_,mh,_=prod.verify_base(run,check_executable=False,accept_tool_change=True,scheduling_copies=False)
    if m['campaign_role']!='pilot_full':raise ValueError(f'{pf} is not the pilot_full campaign (PF)')
    tot=0.
    for g in m['groups']:
        p,cfg=prod.group_of(run,m,g['name'])
        if cfg['L']!=8:continue
        prod.validate_merged(p,cfg,m,mh)
        for line in (p/'graph_costs.csv').read_text().splitlines()[1:]:tot+=float(line.split(',')[2])
    return tot

def proportional(rng,by:dict,cost_of,budget:float)->list:
    """A registered-seed subset uniform within each stratum filling `budget` and never above it (S3-001). Every stratum's
    items are put in a random order and each stratum proposes the first floor(f n_k) of them, the same fraction f of
    every stratum, f = budget / total cost. The proposals are resolved jointly (S3-R2-002): when they cost more than the
    budget, f is lowered to the largest common fraction whose proposals fit (no stratum is served before another, so
    the result does not depend on the strata's sort order; the rng draws are unchanged), and all of them are taken. Then
    the leftovers of every stratum, in one random order, while they fit. Items are sortable: graph ids, or (sector,
    graph) pairs for a joint allocation over both sectors' strata (S3-002)."""
    from fractions import Fraction
    budget=max(0.,float(budget));items=sorted(x for v in by.values()for x in v);tot=sum(cost_of(x)for x in items)
    if tot<=budget:return items
    perms=[]
    for k in sorted(by):v=sorted(by[k]);perms.append([v[int(i)]for i in rng.permutation(len(v))])
    pref=[[0.]+list(itertools.accumulate(cost_of(x)for x in p))for p in perms]   # each stratum's cost of its first j items
    def need(q):return math.fsum(c[j]for c,j in zip(pref,q))
    q0=[int(math.floor((budget/tot if tot>0 else 0.)*len(p)))for p in perms];q=q0
    if need(q0)>budget:
        # the largest common fraction c whose proposals floor(c n_k) fit: the quotas change only at c = j / n_k (exact
        # fractions; capped at the first proposals q0); need() is monotone in c, and c = 0 always fits
        def quota(c):return [min(j0,(c.numerator*len(p))//c.denominator)for p,j0 in zip(perms,q0)]
        cand=sorted({Fraction(0)}|{Fraction(j,len(p))for p,j0 in zip(perms,q0)for j in range(1,j0+1)});lo,hi=0,len(cand)-1
        while lo<hi:
            mid=(lo+hi+1)//2
            if need(quota(cand[mid]))<=budget:lo=mid
            else:hi=mid-1
        q=quota(cand[lo])
    chosen=[x for p,j in zip(perms,q)for x in p[:j]];used=need(q);left=[x for p,j in zip(perms,q)for x in p[j:]]
    if left:
        v=sorted(left)
        for x in [v[int(i)]for i in rng.permutation(len(v))]:
            if used+cost_of(x)<=budget:chosen.append(x);used+=cost_of(x)
    return sorted(chosen)

def check_cap(doc:dict,pc)->None:
    """S3-001: before a PC selection is published, its cost recomputed from its rows (pc of each (sector, graph)) is within
    the cap and equals the recorded used_seconds."""
    c=doc['cap'];used=sum(pc((k.split(':')[0],int(r['id'])))for k,v in doc['groups'].items()for r in v)
    if used>c['cap_seconds']*(1+1e-12):raise ValueError(f'internal: the PC selection costs {used:.6g} s, above its cap {c["cap_seconds"]:.6g} s (25% of PF\'s L8 cost, E.8)')
    if abs(used-c['used_seconds'])>1e-9*max(used,c['used_seconds'],1e-300):raise ValueError(f'internal: the PC selection\'s rows cost {used!r} s, its record says {c["used_seconds"]!r} s')

def confirm(screen:dict,im_sha:str,seed:int,cost:dict,inv:dict,cap_total:float)->dict:
    """The PC selection. cost: {(sector, graph): {'a': c_a, 'b': c_b}} in seconds per point in PF's MP self-check mode
    (pc_costs). The flagged graphs are allocated jointly over every stratum of both sectors, then the 2b extension jointly
    over the triggering sectors' strata from what is left of the cap (S3-002); no step exceeds the cap (S3-001)."""
    rng=np.random.default_rng(seed);st=strata(inv);where={(k[0],g):k for k,ids in st.items()for g in ids};zc=zero_channel_l8(inv)
    cap=CAP_FRACTION*cap_total;pc=lambda x:(cost[x]['a']+cost[x]['b'])*PC_POINTS*PC_REPS
    flagged={(x['sector'],int(x['graph']))for x in screen['flagged']};unscreened={(x['sector'],int(x['graph']))for x in screen['p1c_unscreened_confirmed']}
    # zero-channel L8 graphs never take PC budget (host refinement, Stage 3a repair round 3): a screen file that lists one
    # (an older screen) has it dropped here and recorded; the 2b extension never draws one
    zc_drop=sorted(x for x in flagged|unscreened if x in zc);flagged-=zc;unscreened-=zc
    zc_heavy=sorted({(x['sector'],int(x['graph']))for x in screen.get('zero_channel_heavy_tail')or[]}|set(zc_drop))
    # S3-002: the screened graphs of both sectors jointly over every stratum (sector x T bin x M tertile), no sector first;
    # then the 2b extension jointly over the strata of every sector with an unscreened confirmation, from what is left
    by={}
    for x in sorted(flagged):by.setdefault(where[x],[]).append(x)
    take=proportional(rng,by,pc,cap)if by else[];used=sum(pc(x)for x in take)
    trig={s for s,_ in unscreened};pool={}
    for k,ids in st.items():
        if k[0]in trig:
            v=[(k[0],g)for g in ids if (k[0],g)not in flagged and (k[0],g)not in zc]
            if v:pool[k]=v
    ext=proportional(rng,pool,pc,cap-used)if pool else[];used+=sum(pc(x)for x in ext)
    groups={};rec={}
    for s in ('free','power'):
        rows=[{'id':g,'points':PC_POINTS,'nest':list(PC_NEST),'label':'screen'}for ss,g in take if ss==s]
        rows+=[{'id':g,'points':PC_POINTS,'nest':list(PC_NEST),'label':'ext_2b'}for ss,g in ext if ss==s]
        rec[s]={'flagged':sum(1 for ss,_ in flagged if ss==s),'screen':sum(1 for ss,_ in take if ss==s),'ext_2b':sum(1 for ss,_ in ext if ss==s)}
        if rows:groups[f'{s}:8']=sorted(rows,key=lambda r:r['id'])
    empty=None
    if not groups:
        empty=(f'no L8 graph screened ({len(flagged)} of {screen.get("l8_graphs")}) and no P1c graph confirmed without a screen '
               f'({len(unscreened)} of {screen.get("p1c_graphs")}): PC is empty (action 2 and 2b have nothing to run)')
    doc={'schema':prod.SELECTION_SCHEMA,'inputs_manifest_sha256':im_sha,'role':'confirm','seed':seed,'groups':groups,'empty_reason':empty,
         'cap':{'pf_l8_seconds':cap_total,'fraction':CAP_FRACTION,'cap_seconds':cap,'used_seconds':used},'counts':rec,
         'zero_channel':{'status':ZC_NOTE,'heavy_tail':[{'sector':s,'graph':g}for s,g in zc_heavy],'dropped_from_screen':[{'sector':s,'graph':g}for s,g in zc_drop],
                         'rule':'zero-channel L8 graphs (s_G = 4) are never selected (host refinement, Stage 3a repair round 3)'},
         'rule':'PC: the screened L8 graphs of both sectors within 25% of PF\'s L8 cost (a subset uniform within strata, allocated jointly over both '
                'sectors\' strata, fills the cap), then the action-2b extension jointly from what is left (E.8; S3-001, S3-002)'}
    check_cap(doc,pc);return doc

def count(path:Path)->int:
    doc=json.loads(Path(path).read_bytes())
    if doc.get('schema')!=prod.SELECTION_SCHEMA or doc.get('role')not in('stage_a','confirm')or not isinstance(doc.get('groups'),dict):raise ValueError(f'{path} is not a {prod.SELECTION_SCHEMA} file')
    if not doc['groups']and not doc.get('empty_reason'):raise ValueError(f'{path} holds no group and no empty_reason')
    return sum(len(v)for v in doc['groups'].values())

def screen_input(a)->tuple[dict,Path]:
    """(screen document, PF run) of `confirm`: --screen is either PF's campaign directory (the runbook, step 7.3: the screen
    is computed here from PF and --pa, as `pilot_report.py screen` would) or a screen file of `pilot_report.py screen`
    (then --pf names PF). A --pf that differs from a --screen directory is refused. A screen file must record the
    identity of the given --pf, and of --pa when given (S3-005: manifest, role, selection and merged-file sha256s)."""
    import pilot_report as pr
    if Path(a.screen).is_dir():
        if a.pa is None:raise Refuse(64,'confirm --screen PF_RUN needs --pa PA_RUN (the screen is computed from PF and PA)')
        if a.pf is not None and Path(a.pf).resolve()!=Path(a.screen).resolve():raise Refuse(64,f'--pf {a.pf} differs from --screen {a.screen} (a campaign directory is PF)')
        return pr.screen(a.screen,a.pa),Path(a.screen)
    if a.pf is None:raise Refuse(64,'confirm --screen SCREEN.json needs --pf PF_RUN (the PC cap is 25% of PF\'s L8 cost)')
    scr=load(a.screen);pr.bound(scr.get('pf_identity'),pr.campaign_identity(a.pf),f'the screen {a.screen} (its PF)')
    if a.pa is not None:pr.bound(scr.get('pa_identity'),pr.campaign_identity(a.pa),f'the screen {a.screen} (its PA)')
    return scr,Path(a.pf)

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('stage-a');q.add_argument('--seed',type=int,required=True);q.add_argument('--cost-model',type=Path,required=True);q.add_argument('--out','--output',dest='out',type=Path,required=True)
    q.add_argument('--seeds-log',type=Path);q.add_argument('--inputs',type=Path)
    q=s.add_parser('confirm');q.add_argument('--screen',type=Path,required=True,help='PF\'s campaign directory (with --pa) or a screen file (with --pf)')
    q.add_argument('--pa',type=Path,help='PA (with --screen PF_RUN)');q.add_argument('--seed',type=int,required=True)
    q.add_argument('--cost-model',type=Path,help='default: PF\'s own measured model (its pinned cost_model.json)')
    q.add_argument('--pf',type=Path,help='PF (with --screen SCREEN.json)');q.add_argument('--out','--output',dest='out',type=Path,required=True);q.add_argument('--seeds-log',type=Path);q.add_argument('--inputs',type=Path)
    q=s.add_parser('count');q.add_argument('file',type=Path)
    a=p.parse_args(argv)
    try:
        if a.cmd=='count':print(count(a.file));return 0
        registered(a.seed,a.seeds_log or (Path(os.environ['C8_SEEDS'])if os.environ.get('C8_SEEDS')else None))
        if a.out.exists():raise FileExistsError(f'{a.out} exists; a selection file is never overwritten')
        import prepare_inputs as pi
        d=Path(a.inputs).resolve()if a.inputs else pi.inputs_dir();inv=load(d/'inventory.json');im_sha=digest(d/'manifest.json')
        if a.cmd=='stage-a':doc=stage_a(inv,im_sha,a.seed,costs(a.cost_model))
        else:
            scr,pf=screen_input(a);model=a.cost_model or campaign_model(pf);cost,pricing=pc_costs(model,pf)
            doc=confirm(scr,im_sha,a.seed,cost,inv,pf_l8_cost(pf));doc['pricing']=pricing
            doc['screen']={'source':str(Path(a.screen).resolve()),'pf':str(pf.resolve()),'cost_model':str(Path(model).resolve()),'cost_model_sha256':digest(model),
                           **{k:scr.get(k)for k in ('schema','pa','flagged','p1c_unscreened_confirmed','zero_channel_heavy_tail','l8_graphs','p1c_graphs','made_utc',
                                                    'pf_identity','pa_identity')}}
        if a.out.exists():raise FileExistsError(f'{a.out} exists; a selection file is never overwritten')
        dump(a.out,doc)
    except Refuse as e:print(f'pilot_select: {e}',file=sys.stderr);return e.code
    except (ValueError,OSError,KeyError)as e:print(f'pilot_select: {e}',file=sys.stderr);return 1
    print(json.dumps({'file':str(a.out),'role':doc['role'],'graphs':sum(len(v)for v in doc['groups'].values()),'empty_reason':doc['empty_reason']}));return 0
if __name__=='__main__':sys.exit(main())
