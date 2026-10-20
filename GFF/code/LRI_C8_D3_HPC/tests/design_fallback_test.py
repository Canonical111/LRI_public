#!/usr/bin/env python3
"""A-DES-2: tools/design_fallback.py on synthetic full-size d=3 data (Mac; about a minute).

The data: 24,173 graphs (the d=3 L3..L7 inventory counts of inputs/manifest.json and 20,662 L8 graphs, 262 free L8
primitives), 16 replicates per graph and campaign, campaign b at 3x campaign a's cost for every second graph; the pilot
interface P of design_fallback.load_pilot is built in memory (load_pilot itself, the campaign path, runs in
tests/test_pipeline.py). Checked, the A-DES-1 list (C62d's D2PLAN:1339-1347) and the fallback specifics:
  * graph_table calls the VENDORED order8_assembly.jacobians once, with inputs/two_loop.json's B2, order 8 and half_d 1.5
    (spy), and design_fallback.py holds no d=1 coefficient code (no coefficients/jacobians/complex-step definition);
  * sigma_g = sqrt(n Var_rep(J_8 . jets)) with ddof 1; campaign-keyed costs: the per-campaign base counts equal the
    hand values max(4096, pow2_round(4096 sum c / sum sigma sqrt c x sigma_g / sqrt c_g)) per (campaign, sector, L) and
    stratum, and differ between a and b where b's cost differs non-uniformly;
  * a target-SE freeze: every count a power of two >= 4096, replicates in [32, 128], the predicted SE (x1.5 margin) <=
    the target, the per-batch caps hold at K and fail at K - 1 (the minimum batch count), a smaller --batches refused
    naming K;
  * an integer budget respected (cost <= budget), a non-integer budget refused, spent + budget or spent + design
    above --total-cap refused, an infeasible budget refused printing the minimum (= the design at r = 32, s = 1);
  * eta_node from the accounting: a fake accounting result (eta 1.25) multiplies the allocated cost of the same design by
    1.25 (the hand factor); --eta-node outside a test-only freeze refused;
  * freeze: design.json and design_meta.json labelled fallback, forbidden seeds = the pilot seed and every seed of
    --seeds-log, the bundle atomic (no temporary sibling left) and never overwritten;
  * S3-003: load_pilot (its campaign reader stubbed) checks the model's whole HD11 identity against the pilot (another
    executable, another CPU model, another MP mode without an overhead factor refused) and takes the MP factor: a pilot
    planned with mp_check on from an off-mode model with mp_check_overhead.on = 2 gets every graph cost doubled
    (graph_table), as production.py charges it;
  * S3-004: an unsampled graph imputes only its variance (the stratum median); its cost is its own measured
    campaign-keyed cost (x the MP factor), never the sampled graphs' median, and a graph without a model key is refused.
  * --pc, the conservative tail rule (RECON:1373; user decision 2026-10-08), on a small pilot (all 24 groups, PF sigma
    1 for every free L8 graph) and an injected PC (pilot_report.Camp without files: free L8 graphs 0 and 1 of both
    campaigns at 32,768 points, replicate values with sqrt(32768 Var) set exactly, graph 0's top 16 with Hill index
    0.7, graph 1's 0.1), through freeze and report (load_pilot and pilot_report.require_subset stubbed; bind_pc real):
    (raised) PC sigma 3 for graph 0: it is raised by the factor 3 in both campaigns, its base count goes 4,096 -> 8,192
    against the same freeze without --pc, graph 1 (PC sigma 0.5) is unchanged, graph 0 is the one monitored graph, and
    design.json, design_meta.json (PC's identity, bound to PF's) and the report record it; (unchanged) PC sigmas 0.5 and
    0.9: nothing raised, the counts files byte for byte and design.json apart from its conservative_tail_rule equal to
    the freeze without --pc; (foreign) a PC whose selection's screen names another PF (one group's scientific identity),
    one of another executable, and a stage-A selection are refused, leaving no bundle.
Usage: python3 -B tests/design_fallback_test.py"""
from __future__ import annotations
import argparse,ast,json,math,shutil,sys,tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import design_fallback as df  # noqa: E402
import pilot_report as pr  # noqa: E402
import assemble as asm  # noqa: E402
import production as prod  # noqa: E402
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,**info});print('PASS',name,flush=True)
COUNTS={'free':{3:5,4:16,5:76,6:395,7:2298,8:16326},'power':{3:1,4:3,5:20,6:107,7:590,8:4336}};PRIMS=262;R=16;SEED=4242

def pilot()->dict:
    assert sum(sum(v.values())for v in COUNTS.values())==24173
    rng=np.random.default_rng(1);im=json.loads((ROOT/'inputs/manifest.json').read_bytes());I=prod.Inputs(ROOT/'inputs',im)
    inv={s:{str(L):[{'id':g,'primitive':bool(s=='free'and L==8 and g<PRIMS)}for g in range(n)]for L,n in v.items()}for s,v in COUNTS.items()}
    means={s:{L:rng.normal(size=2*(9-L))*(1. if s=='free'else .1)for L in range(3,9)}for s in COUNTS};groups={};costs={}
    for c in 'ab':
        for s,v in COUNTS.items():
            for L,n in v.items():
                k=2*(9-L);sig=np.exp(rng.normal(0,1,n))*10.**(-L/2);Y={}
                X=rng.normal(size=(n,R,k))*sig[:,None,None]/math.sqrt(4096)+means[s][L][None,None,:]
                for g in range(n):Y[g]={r:list(map(float,X[g,r]))for r in range(R)}
                groups[(c,s,L)]=dict(cfg={'campaign':c,'sector':s,'L':L},Y=Y,reps=R,points={g:4096 for g in range(n)})
                base=np.exp(rng.normal(-9+L/4,0.5,n))
                for g in range(n):costs[f'{c}:{s}:{L}:{g}']=float(base[g]*(3 if (c=='b'and g%2==0)else 1))if c=='b'else float(base[g])
    # campaign b's costs: 3x campaign a's for every second graph (the same base draw per graph)
    for s,v in COUNTS.items():
        for L,n in v.items():
            for g in range(n):costs[f'b:{s}:{L}:{g}']=costs[f'a:{s}:{L}:{g}']*(3 if g%2==0 else 1)
    return dict(run=Path('/nonexistent/PF'),m={'seed':SEED,'test_only':False,'inputs_manifest_sha256':'i'*64,'numerics':'exact','campaign_role':'pilot_full',
                                                'executable_sha256':'e'*64,'backend':'gmp','cost_basis':'measured','mp_check':'on','fingerprint':{'cpu_model':CPU}},
                mh='m'*64,I=I,inv=inv,groups=groups,means=means,model={'seconds_per_point':costs,'executable_sha256':'e'*64,'cpu_model':CPU,'mp_check':'on'},
                model_path=str(ROOT/'tools/bootstrap_proxy.json'),mpf=1.0)
CPU='AMD EPYC 7543 32-Core Processor'

def model_file(path:Path,keys:dict,**kw)->Path:
    """A measured c8-d3-cost-model-1 (production.read_cost_model's schema) with these seconds per point."""
    m={'schema':prod.COST_SCHEMA,'dimension':3,'order':8,'measured':True,'backend':'gmp','executable_sha256':'e'*64,'cpu_model':CPU,'mp_check':'on','seconds_per_point':keys}
    m.update(kw);path.write_text(json.dumps(m));return path

def identity_and_imputation(td:Path)->None:
    """S3-003 and S3-004 on a small pilot: load_pilot with its campaign reader stubbed (no group data: the identity check
    and the MP factor come before it), then graph_table on a hand-made group with one unsampled graph."""
    im=json.loads((ROOT/'inputs/manifest.json').read_bytes());I=prod.Inputs(ROOT/'inputs',im)
    m={'seed':SEED,'test_only':False,'campaign_role':'pilot_full','executable_sha256':'e'*64,'backend':'gmp','cost_basis':'measured','mp_check':'on','groups':[],
       'fingerprint':{'cpu_model':CPU},'inputs_manifest_sha256':'i'*64,'numerics':'exact'}
    keys={f'a:free:5:{g}':(1e-2 if g==10 else 1e-6)for g in range(11)}
    orig=prod.verify_base;seen=[]
    def fake_vb(run,**kw):seen.append(kw);return m,I,'m'*64,{}
    prod.verify_base=fake_vb
    try:
        P=df.load_pilot(td/'PF',model_file(td/'same.json',keys));assert P['mpf']==1.0 and seen[-1].get('scheduling_copies')is False,(P['mpf'],seen[-1])
        P2=df.load_pilot(td/'PF',model_file(td/'off.json',keys,mp_check='off',mp_check_overhead={'on':2.0}));assert P2['mpf']==2.0,P2['mpf']
        for name,kw,why in (('exe',{'executable_sha256':'f'*64},'executable_sha256'),('cpu',{'cpu_model':'AMD EPYC 7742 64-Core Processor'},'cpu_model'),
                            ('mode',{'mp_check':'off'},'mp_check')):
            try:df.load_pilot(td/'PF',model_file(td/f'{name}.json',keys,**kw));raise AssertionError(f'a model with another {name} accepted')
            except ValueError as e:assert why in str(e)and 'identity'in str(e),(name,str(e))
        m['cost_basis']='prior_model'
        try:df.load_pilot(td/'PF',model_file(td/'cpu2.json',keys,cpu_model='other'));raise AssertionError('a non-matching explicit model accepted')
        except ValueError as e:assert 'explicitly supplied identity-matching'in str(e),str(e)
        m['cost_basis']='measured'
    finally:prod.verify_base=orig
    # graph_table: 10 sampled cheap graphs and the unsampled expensive graph 10 of free L5 (campaign a)
    rng=np.random.default_rng(9);means={s:{L:rng.normal(size=2*(9-L))for L in range(3,9)}for s in ('free','power')};k=2*(9-5)
    Y={g:{r:list(map(float,rng.normal(size=k)*1e-3+means['free'][5]))for r in range(R)}for g in range(10)}
    inv={'free':{'5':[{'id':g}for g in range(11)]},'power':{}}
    Q=dict(run=td/'PF',m=m,mh='m'*64,I=I,inv=inv,groups={('a','free',5):dict(cfg={'campaign':'a','sector':'free','L':5},Y=Y,reps=R,points={g:4096 for g in range(10)})},
           means=means,model={'seconds_per_point':keys},model_path='x',mpf=2.0)
    T=df.graph_table(Q)[('a','free',5)]
    assert all(abs(T[g]['cost']-2e-6)<=1e-18 for g in range(10))and abs(T[10]['cost']-2e-2)<=1e-15 and not T[10]['piloted'],(T[0]['cost'],T[10]['cost'])
    assert T[10]['sigma']==float(np.median([T[g]['sigma']for g in range(10)])),T[10]['sigma']
    Q['model']={'seconds_per_point':{x:v for x,v in keys.items()if x!='a:free:5:10'}}
    try:df.graph_table(Q);raise AssertionError('an unsampled graph without its own cost accepted')
    except ValueError as e:assert 'a:free:5:10'in str(e),str(e)
    ok('S3-003/S3-004: load_pilot takes the model\'s MP factor for the pilot\'s mode (an off-mode model with overhead on = 2 doubles every cost, as '
       'production.py charges it) and refuses a model of another executable, CPU model or MP mode (and, on another basis, a non-matching explicit '
       'model), reading the campaign with scheduling_copies=False; graph_table imputes only the variance of an unsampled graph (the stratum median) '
       'and gives it its own measured cost x the MP factor (2e-2, not the sampled median 2e-6), and refuses a graph without its own key')

# ---------------------------------------------------------------- --pc: the conservative tail rule (RECON:1373)
MINI={'free':{3:2,4:2,5:2,6:2,7:2,8:6},'power':{3:1,4:2,5:2,6:2,7:2,8:4}};RM=8
def exact_reps(J,mean,sig:float,n:int,R:int=RM)->list:
    """R replicate jet vectors around `mean` whose J . jets alternate +-a with n Var_ddof1 = sig^2 exactly."""
    J=np.asarray(J,float);u=J/float(np.dot(J,J));a=math.sqrt((R-1)/R*sig**2/n)
    return [list(map(float,np.asarray(mean,float)+(a if r%2==0 else -a)*u))for r in range(R)]

def mini_pilot()->tuple[dict,dict]:
    """(P, J8): an in-memory pilot of every group (load_pilot's dict) with sigma = 1 for every free L8 graph-campaign
    (equal costs there) and PF's identity record."""
    rng=np.random.default_rng(5);im=json.loads((ROOT/'inputs/manifest.json').read_bytes());I=prod.Inputs(ROOT/'inputs',im)
    inv={s:{str(L):[{'id':g,'primitive':False}for g in range(n)]for L,n in v.items()}for s,v in MINI.items()}
    means={s:{L:rng.normal(size=2*(9-L))*(1. if s=='free'else .1)for L in range(3,9)}for s in MINI}
    m={'seed':SEED,'test_only':True,'inputs_manifest_sha256':'i'*64,'numerics':'exact','campaign_role':'pilot_full','executable_sha256':'e'*64,'backend':'gmp',
       'cost_basis':'measured','mp_check':'on','fingerprint':{'cpu_model':CPU}}   # test-only: freeze --test-only and report take --eta-node
    names=[f'{c}_{s}_L{L}'for c in 'ab'for s in MINI for L in MINI[s]]
    ident={'run':'/nonexistent/PF','manifest_sha256':'m'*64,'campaign_role':'pilot_full','selection_sha256':None,
           'science_sha256':{n:{'graph_replicates.csv':'1'*64,'graph_tails.csv':'2'*64,'graph_promotions.csv':'3'*64,'graph_prefixes.csv':None,'merged_science':'4'*64}for n in names},
           'merged_sha256':{n:'5'*64 for n in names}}
    P=dict(run=Path('/nonexistent/PF'),m=m,mh='m'*64,I=I,inv=inv,groups={},means=means,model={'seconds_per_point':{},'executable_sha256':'e'*64,'cpu_model':CPU,'mp_check':'on'},
           model_path=str(ROOT/'tools/bootstrap_proxy.json'),mpf=1.0,identity=ident)
    J8=df.jacobian_rows(P);costs=P['model']['seconds_per_point']
    for c in 'ab':
        for s,v in MINI.items():
            for L,n in v.items():
                k=2*(9-L);Y={}
                for g in range(n):
                    reps=exact_reps(J8[L],means[s][L],1.0 if (s,L)==('free',8)else float(np.exp(rng.normal(0,.5))),4096)
                    Y[g]={r:reps[r]for r in range(RM)};costs[f'{c}:{s}:{L}:{g}']=1e-4 if L==8 else float(np.exp(rng.normal(-9,.3)))
                P['groups'][(c,s,L)]=dict(cfg={'campaign':c,'sector':s,'L':L},Y=Y,reps=RM,points={g:4096 for g in range(n)})
    return P,J8

def top16(xi:float)->list:
    """A top 16 whose Hill index (pilot_report.hill) is xi."""
    k=xi/(sum(math.log(16/(i+1))for i in range(15))/15);return [((i+1)/16)**(-k)for i in range(16)]

def fake_pc(P:dict,J8:dict,sig:dict,heavy:set):
    """An injected PC campaign (pilot_report.Camp without files) of PF P: free L8 graphs sig's keys in campaigns a and b at
    32,768 points (nest 4,096), sqrt(32768 Var_rep(J_8 . jets)) = sig[g] exactly, top 16 with Hill index 0.7 (heavy) or
    0.1; manifest, selection (its screen names P's identity) and identity as require_subset leaves them."""
    C=pr.Camp.__new__(pr.Camp);C.run=Path('/nonexistent/PC');C.g={};gs=sorted(sig)
    C.m={**{k:P['m'][k]for k in df.PC_SAME},'campaign_role':'pilot_subset','selection':{'sha256':'6'*64,'role':'confirm','seed':4242001},'seed':4242002}
    C.sel={'schema':'c8-d3-selection-1','role':'confirm','inputs_manifest_sha256':P['m']['inputs_manifest_sha256'],'screen':{'pf_identity':json.loads(json.dumps(P['identity']))},
           'groups':{'free:8':[{'id':g,'points':32768,'nest':[4096],'label':'screen'}for g in gs]}}
    C.identity={'run':str(C.run),'manifest_sha256':'c'*64,'campaign_role':'pilot_subset','selection_sha256':'6'*64,
                'science_sha256':{f'{t}_free_L8':{'graph_replicates.csv':'7'*64}for t in 'ab'},'merged_sha256':{f'{t}_free_L8':'8'*64 for t in 'ab'}}
    for t in 'ab':
        G={'reps':RM,'total':{},'jets':{},'tails':{},'prefix':{},'cost':{},'promo':[]}
        for g in gs:
            G['total'][g]=32768;top=top16(0.7 if g in heavy else 0.1);reps=exact_reps(J8[8],P['means']['free'][8],sig[g],32768)
            for r in range(RM):G['jets'][(r,g)]=reps[r];G['tails'][(r,g)]=(32768,2*sum(top),top,'0');G['prefix'][(r,g,4096)]=(reps[r],2*sum(top),top,'0')
        C.g[(t,'free',8)]=G
    return C

def conservative_tail_rule(td:Path)->None:
    P,J8=mini_pilot();orig=(df.load_pilot,pr.require_subset);pc=[None]
    df.load_pilot=lambda run,model:P;pr.require_subset=lambda run,role:pc[0]
    def freeze(name,**kw):
        r=df.freeze(A(out=td/name,test_only=True,eta_node=0.9,target_se=0.05,**kw))
        return r,json.loads((td/name/'design.json').read_text()),json.loads((td/name/'design_meta.json').read_text()),{p.name:p.read_bytes()for p in (td/name/'counts').iterdir()}
    def count(cnt,c,g):return int(dict(ln.split()for ln in cnt[f'{c}_free_L8.txt'].decode().splitlines())[str(g)])
    try:
        r0,d0,m0,c0=freeze('nopc')
        assert 'conservative_tail_rule'not in d0 and 'pc'not in m0 and 'conservative_tail_rule'not in r0 and all(count(c0,c,g)==4096 for c in 'ab'for g in range(6)),c0
        # (raised) graph 0's PC sigma 3 > its PF sigma 1; graph 1's 0.5 < 1
        pc[0]=fake_pc(P,J8,{0:3.0,1:0.5},{0});r1,d1,m1,c1=freeze('raised',pc=Path('/nonexistent/PC'))
        tr=d1['conservative_tail_rule'];R={(x['campaign'],x['graph']):x for x in tr['raised']};U={(x['campaign'],x['graph']):x for x in tr['unchanged']}
        assert set(R)=={('a',0),('b',0)}and set(U)=={('a',1),('b',1)}and tr['graph_campaigns']==4,(sorted(R),sorted(U))
        assert all(abs(x['sigma_before']-1)<=1e-9 and abs(x['sigma_pc_32768']-3)<=1e-9 and x['sigma_alloc']==x['sigma_pc_32768']and abs(x['factor']-3)<=1e-9 and x['points_pf']==4096
                   for x in R.values()),R
        assert all(abs(x['sigma_pc_32768']-.5)<=1e-9 and abs(x['sigma_before']-1)<=1e-9 for x in U.values()),U
        assert [(x['sector'],x['graph'])for x in tr['monitored']]==[('free',0)]and abs(tr['monitored'][0]['xi_mean_32768']-.7)<=1e-9 and tr['undefined']==[],tr['monitored']
        assert all(count(c1,c,0)==8192 for c in 'ab')and all(count(c1,c,g)==4096 for c in 'ab'for g in range(1,6)),c1   # 4096 x 6 x 3 / 8 = 9216 -> 8192
        assert c1['a_free_L8.txt']!=c0['a_free_L8.txt']and all(c1[k]==c0[k]for k in c0 if 'free_L8'not in k)
        assert d1['strata']['free_L8']['V1']>d0['strata']['free_L8']['V1']and tr['rule'].startswith('RECON:1373')and tr['pc']['manifest_sha256']=='c'*64
        assert m1['pc']['manifest_sha256']=='c'*64 and m1['pc']['selection_role']=='confirm'and m1['pc']['pf_identity']['manifest_sha256']=='m'*64 and m1['monitored_graphs']==tr['monitored']
        assert m1['pc']['science_sha256']==pc[0].identity['science_sha256']and r1['conservative_tail_rule']=={'raised':2,'unchanged':2,'monitored':1},r1
        rep=df.report(A(pilot=Path('/nonexistent/PF'),pc=Path('/nonexistent/PC'),eta_node=0.9));rep0=df.report(A(pilot=Path('/nonexistent/PF'),eta_node=0.9))
        assert rep['conservative_tail_rule']['raised']==tr['raised']and 'conservative_tail_rule'not in rep0
        assert rep['rows'][0]['variance_per_batch']>rep0['rows'][0]['variance_per_batch'],(rep['rows'][0],rep0['rows'][0])
        # (unchanged) both PC sigmas below PF's: nothing raised, the allocation as without --pc
        pc[0]=fake_pc(P,J8,{0:0.5,1:0.9},{0});r2,d2,m2,c2=freeze('unchanged',pc=Path('/nonexistent/PC'))
        tr2=d2.pop('conservative_tail_rule');assert tr2['raised']==[]and len(tr2['unchanged'])==4 and [x['graph']for x in tr2['monitored']]==[0],tr2
        assert c2==c0 and d2==d0,'the allocation changed although no PC sigma exceeds PF\'s'
        # (foreign) a PC of another pilot: its selection's screen names another PF; another executable; a stage-A selection
        for tag,mod,why in (('science',lambda C:C.sel['screen']['pf_identity']['science_sha256']['a_free_L3'].__setitem__('graph_tails.csv','0'*64),'another campaign'),
                            ('manifest',lambda C:C.sel['screen']['pf_identity'].__setitem__('manifest_sha256','0'*64),'another campaign'),
                            ('exe',lambda C:C.m.__setitem__('executable_sha256','f'*64),'another executable_sha256'),
                            ('stage_a',lambda C:(C.sel.__setitem__('role','stage_a'),C.m['selection'].__setitem__('role','stage_a')),'not a PC campaign')):
            C=fake_pc(P,J8,{0:3.0,1:0.5},{0});mod(C);pc[0]=C
            for fn in (lambda:freeze(f'foreign_{tag}',pc=Path('/nonexistent/PC')),lambda:df.report(A(pilot=Path('/nonexistent/PF'),pc=Path('/nonexistent/PC'),eta_node=0.9))):
                try:fn();raise AssertionError(f'a foreign PC ({tag}) accepted')
                except ValueError as e:assert why in str(e),(tag,str(e))
            assert not (td/f'foreign_{tag}').exists()and not [p for p in td.iterdir()if '.tmp.'in p.name]
    finally:df.load_pilot,pr.require_subset=orig
    ok('--pc (RECON:1373, user decision 2026-10-08): a PC sigma(32,768) of 3 against PF\'s 1 raises graph 0 by the factor 3 in both campaigns '
       '(base count 4,096 -> 8,192), graph 1 (PC 0.5) unchanged, graph 0 (Hill 0.7) the one monitored graph, recorded in design.json, design_meta.json '
       '(PC identity bound to PF\'s) and the report; PC sigmas below PF\'s leave the counts and design.json as without --pc; a PC whose screen names '
       'another PF (scientific identity or manifest), of another executable, or of a stage-A selection is refused by freeze and report, no bundle left')

class A(argparse.Namespace):
    def __init__(self,**k):
        d=dict(min_points=4096,min_replicates=32,max_replicates=128,variance_margin=1.5,eta_node=None,test_only=False,batches=None,spent_core_hours=0.,
               total_cap=None,seeds_log=None,target_se=None,target_rel=None,budget_core_hours=None,c8_magnitude=1500.,pilot=Path('/nonexistent/PF'),cost_model=None)
        d.update(k);super().__init__(**d)

def main()->int:
    with tempfile.TemporaryDirectory(prefix='c8d3_dfid_')as tdi:identity_and_imputation(Path(tdi))
    with tempfile.TemporaryDirectory(prefix='c8d3_dfpc_')as tdp:conservative_tail_rule(Path(tdp))
    P=pilot()
    # the vendored Jacobian spy, and no d=1 coefficient code in the file
    calls=[];oa=asm.vendored();real=oa.jacobians
    def spy(means,B2,order,half_d):calls.append((np.asarray(B2).tolist(),order,half_d,sorted(means)));return real(means,B2,order,half_d)
    oa.jacobians=spy
    try:T=df.graph_table(P)
    finally:oa.jacobians=real
    B2,_=asm.two_loop(8,P['I'].dir,P['I'].m['sha256'])
    assert len(calls)==1 and calls[0][0]==np.asarray(B2).tolist()and calls[0][1]==8 and calls[0][2]==1.5 and calls[0][3]==list(range(3,9)),calls[:1]
    assert json.loads((ROOT/'inputs/two_loop.json').read_text())and len(calls[0][0])==7
    tree=ast.parse((ROOT/'tools/design_fallback.py').read_text());defs={n.name for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)}
    assert not defs&{'coefficients','jacobians','complex_step','affine','ms8_value'}and '1j'not in (ROOT/'tools/design_fallback.py').read_text()
    J8=df.jacobian_rows(P);g0=next(iter(P['groups'][('a','free',8)]['Y']));y=[float(np.dot(J8[8],P['groups'][('a','free',8)]['Y'][g0][r]))for r in range(R)]
    want=math.sqrt(4096*float(np.var(y,ddof=1)));assert abs(T[('a','free',8)][g0]['sigma']-max(want,0))<=1e-12*want or T[('a','free',8)][g0]['sigma']>=want
    ok('A-DES-2: graph_table calls the vendored order8_assembly.jacobians once with inputs/two_loop.json\'s 7-entry B2, order 8 and half_d 1.5 (spy) '
       'on 24,173 graphs x 16 replicates x 2 campaigns; design_fallback.py defines no coefficient, Jacobian or complex-step code; sigma uses ddof 1')
    # campaign-keyed base counts: hand values
    b=df.base_counts(T,4096,4096);differ=0
    for key,TT in T.items():
        byst={}
        for g,x in TT.items():byst.setdefault(x['stratum'],[]).append(g)
        for st,gs in byst.items():
            k=4096*sum(TT[g]['cost']for g in gs)/sum(TT[g]['sigma']*math.sqrt(TT[g]['cost'])for g in gs)
            for g in gs:
                h=max(4096,df.pow2_round(max(1.,k*TT[g]['sigma']/math.sqrt(TT[g]['cost']))));assert b[key][g]==h,(key,g,b[key][g],h)
    for s,v in COUNTS.items():
        for L in v:differ+=sum(1 for g in b[('a',s,L)]if b[('a',s,L)][g]!=b[('b',s,L)][g])
    assert differ>0 and all(prod.pow2(n)and n>=4096 for cnt in b.values()for n in cnt.values())
    ok('A-DES-2: campaign-keyed costs (b at 3x for every second graph): the per-campaign base counts equal the hand values per (campaign, sector, L) '
       'and stratum, are powers of two >= 4096, and differ between a and b for %d graphs'%differ)
    # a target-SE design: the A-DES-1 list
    o=df.Opts(A());D=df.design_for(T,o,1.0,target_se=0.5)
    assert all(4096<=n*D['s'][T[k][g]['stratum']]and prod.pow2(n*D['s'][T[k][g]['stratum']])for k,cnt in D['b'].items()for g,n in cnt.items())
    assert all(32<=r<=128 for r in D['r'].values())and D['ev']['se_total']<=0.5*(1+1e-12)and D['caps']['ok']
    K=D['K_min']
    if K>1:
        r,s,ev=df.optimize(D['S'],K-1,o,0.5);assert not df.caps(T,D['b'],r,s,o)['ok']
    mn=df.caps(T,D['b'],{g:32 for g in D['r']},{k:1 for k in D['S']},o)['tasks_per_campaign']['a'];tse=0.5
    while df.design_for(T,o,1.0,target_se=tse)['caps']['tasks_per_campaign']['a']<4*mn:tse/=2
    o2=df.Opts(A());o2.max_tasks=2*mn;D2=df.design_for(T,o2,1.0,target_se=tse)
    assert D2['K_min']>1 and D2['caps']['ok'];r,s,ev=df.optimize(D2['S'],D2['K_min']-1,o2,tse);assert not df.caps(T,D2['b'],r,s,o2)['ok']
    try:df.design_for(T,o2,1.0,target_se=tse,batches=D2['K_min']-1);raise AssertionError('too few batches accepted')
    except df.BatchesTooFew as e:assert e.k==D2['K_min']and str(D2['K_min'])in str(e)
    ok('A-DES-1 list on the fallback (target SE 0.5): every count a power of two >= 4096, replicates in [32, 128], the predicted SE x1.5 within the '
       'target, the caps hold at K = %d; with a per-batch task cap of twice the minimal design\'s the minimum K = %d at SE %g, the caps fail at '
       'K - 1 and --batches K - 1 is refused naming K'%(K,D2['K_min'],tse))
    # budgets
    Db=df.design_for(T,o,1.0,budget_ch=20000.);assert Db['ev']['cost_total_core_hours']<=20000*(1+1e-12)
    try:df.design_for(T,o,1.0,budget_ch=1.);raise AssertionError('an infeasible budget accepted')
    except df.Infeasible as e:
        mn=df.evaluate(D['S'],{g:32 for g in D['r']},{k:1 for k in D['S']},1,1.5)['cost_total_core_hours'];assert abs(e.minimum-mn)<=1e-9*mn and f'{mn:.1f}'in str(e)
    # eta from the accounting: the hand factor
    import accounting
    orig=accounting.account
    try:
        accounting.account=lambda run,env:{'eta_node':1.25};eta,src=df.eta_node(P,False,None);assert eta==0.8 and 'accounting'in src
        S1=df.stratum_sums(T,D['b'],1.0);S2=df.stratum_sums(T,D['b'],eta)
        c1=df.evaluate(S1,D['r'],D['s'],D['K'],1.5)['cost_total_core_hours'];c2=df.evaluate(S2,D['r'],D['s'],D['K'],1.5)['cost_total_core_hours'];assert abs(c2/c1-1.25)<=1e-12
        try:df.eta_node(P,False,0.9);raise AssertionError('--eta-node in a real freeze accepted')
        except ValueError as e:assert 'test-only'in str(e)
    finally:accounting.account=orig
    ok('A-DES-1/2 budgets: an integer budget of 20,000 core-h respected; an infeasible budget refused printing the minimum (the design at r = 32, s = 1); '
       'eta_node from the accounting (1.25) multiplies the allocated cost of the same design by 1.25; --eta-node refused outside a test-only freeze')
    # freeze through the CLI function with the in-memory pilot: labels, seeds, total cap, integer budget, atomic and never overwritten
    td=Path(tempfile.mkdtemp(prefix='c8d3_dftest_'))
    orig_lp=df.load_pilot
    try:
        df.load_pilot=lambda run,model:P
        log=td/'seeds.json';log.write_text(json.dumps({'schema':'c8-d3-seeds-1','seeds':[{'seed':77,'label':'x'},{'seed':88,'label':'y'}]}))
        r=df.freeze(A(out=td/'bundle',test_only=True,eta_node=0.9,target_se=0.5,seeds_log=log))
        dj=json.loads((td/'bundle/design.json').read_text());meta=json.loads((td/'bundle/design_meta.json').read_text())
        assert r['label']==dj['label']==meta['label']=='fallback'and meta['forbidden_seeds']==sorted({SEED,77,88})and meta['test_only']
        assert sorted(p.name for p in (td/'bundle/counts').iterdir())==sorted(f'{c}_{s}_L{L}.txt'for c in 'ab'for s in COUNTS for L in range(3,9))
        assert not [p for p in td.iterdir()if '.tmp.'in p.name]
        for kw,why in ((dict(out=td/'bundle',test_only=True,eta_node=0.9,target_se=0.5),'never overwritten'),
                       (dict(out=td/'b2',test_only=True,eta_node=0.9,budget_core_hours=100.5),'integer'),
                       (dict(out=td/'b3',test_only=True,eta_node=0.9,budget_core_hours=1000,spent_core_hours=600,total_cap=1500),'--total-cap'),
                       (dict(out=td/'b4',test_only=True,eta_node=0.9,target_se=0.5,spent_core_hours=10**9,total_cap=10**9+1),'--total-cap'),
                       (dict(out=td/'b5',test_only=True,eta_node=0.9,budget_core_hours=1),'the minimum is'),
                       (dict(out=td/'b6',test_only=True,eta_node=0.9,target_se=0.5,budget_core_hours=10),'exactly one')):
            try:df.freeze(A(**kw));raise AssertionError(f'accepted: {why}')
            except (ValueError,FileExistsError)as e:assert why in str(e),(why,str(e))
        assert not any((td/x).exists()for x in ('b2','b3','b4','b5','b6'))and json.loads((td/'bundle/design.json').read_text())==dj
        P['m']['test_only']=True;rep=df.report(A(eta_node=0.9));P['m']['test_only']=False;assert rep['label']=='fallback'and rep['graphs']==2*24173
    finally:
        df.load_pilot=orig_lp;shutil.rmtree(td,ignore_errors=True)
    ok('A-DES-2 freeze: design.json, design_meta.json and the report labelled fallback; forbidden seeds = the pilot seed and every --seeds-log seed; '
       'the bundle atomic (no temporary sibling) and never overwritten; a non-integer budget, spent + budget or spent + design above --total-cap, '
       'an infeasible budget (minimum printed) and two targets refused, none leaving a bundle')
    print(json.dumps({'status':'passed','tests':len(RESULTS)}));return 0
if __name__=='__main__':sys.exit(main())
