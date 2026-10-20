#!/usr/bin/env python3
"""Orchestration tests with the fake worker (tests/fake_worker.py) and the stateful fake Slurm; no native build. Mac.

The 15 C7(3) test functions ported to C8(3) (24 groups, HD5) and the Stage-3a items of PLAN F's unit_orchestration
row: seeds and the HD6 registry, allocation sources and bundle refusals (A-ORC-2), selection files and nest
boundaries, chunking and sizing with per-campaign costs, the validation and non-measured roles, the first-sweep
bootstrap and its never-a-cost spy (A-ORC-3), blocks at plan level, atomic plans with SQLite built in scratch, the
scale and Lustre guards with EDQUOT at every publish point (A-ORC-15), per-index task files with the bytes-per-claim spy
and the subprocess platform contract (A-ORC-13), immutable SQLite opens (A-ORC-14), staging (A-ORC-16), the parallel
merge (A-ORC-6, Mac part), lanes (A-ORC-4) and the campaign entry points on the fake Slurm (A-ORC-10, the auto lane
time, held jobs, drill mode), the merge job after a recovered index (F8-d3, recovery_merge), array recovery and the
carried-over safety features (A-ORC-7). Every fake lane-mode test
plans with role campaign on a model that make_cost_model.py measured from a fake cost_sweep (HC7).

Each scratch package (tests/c8pkg.py) holds synthetic complete inputs, so non-test plans are possible there. Nothing in
the real package is written. Usage: python3 -B tests/unit_orchestration.py [--only NAME,...] [--keep]
"""
from __future__ import annotations
import ast,concurrent.futures,hashlib,json,math,os,re,shutil,signal,sqlite3,subprocess,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import c8pkg
from c8pkg import tool,manifest,config,tree
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,**info});print('PASS',name,flush=True)
def must(cp,code,*needles):
    out=(cp.stdout or'')+(cp.stderr or'')
    assert cp.returncode==code and all(n in out for n in needles),(cp.returncode,code,needles,out[-1500:])
    return cp
SEED=771100231
SPY=r'''
import atexit,json,os,runpy,sys
_ev=[]
def _hook(e,a):
    try:
        if e=='open'and a and isinstance(a[0],(str,bytes)):_ev.append(['open',os.path.realpath(os.fsdecode(a[0])),str(a[1])if len(a)>1 else'r'])
        elif e=='subprocess.Popen':_ev.append(['popen',[os.fsdecode(x)for x in (a[1]if isinstance(a[1],(list,tuple))else[a[1]])]])
        elif e=='sqlite3.connect':_ev.append(['sqlite',str(a[0])])
    except Exception:pass
sys.addaudithook(_hook)
def _dump():
    with open(os.environ['C8_SPY_OUT'],'w')as f:json.dump(_ev,f)
atexit.register(_dump)
_tool=sys.argv[1];sys.argv=sys.argv[1:];sys.path.insert(0,os.path.dirname(_tool));runpy.run_path(_tool,run_name='__main__')
'''

def spy(pkg:Path,td:Path,script:str,*args,**extra)->tuple:
    """Run tools/<script> under an audit-hook spy: (completed process, events [('open', path, mode) | ('popen', argv) |
    ('sqlite', path)])."""
    out=td/f'spy_{time.time_ns()}.json';sp=td/'spy_prelude.py';sp.write_text(SPY)
    cp=subprocess.run([sys.executable,'-B',str(sp),str(pkg/'tools'/script),*map(str,args)],capture_output=True,text=True,env=c8pkg.env(C8_SPY_OUT=out,**extra))
    ev=json.loads(out.read_text())if out.exists()else[]
    return cp,ev

def opened(ev,read_only=True)->list:return [e[1]for e in ev if e[0]=='open'and(not read_only or 'w'not in e[2]and 'a'not in e[2]and '+'not in e[2])]

class Env:
    """One scratch package and the helpers every test shares (a fake measured model per spec, cached)."""
    def __init__(self,td:Path,name='pkg',**kw):
        self.td=td/name;self.td.mkdir(parents=True);self.pkg=c8pkg.make(self.td,**kw);self.scr=self.td/'scratch';self.scr.mkdir();self.models={}
        self.root=self.td/'c8root';self.root.mkdir();self.reserved=0   # the session lock of the seed reservations (S2-002)
        # the seed log starts as a copy of the package mirror, as A1 requires of symmetry's $C8_SEEDS (HD6; seeds.py init --from)
        self.seeds=self.td/'seeds.json';tool(self.pkg,'seeds.py','init','--log',self.seeds,'--from',self.pkg/'designs/forbidden_seeds.json')
    def t(self,script,*args,check=True,**extra):return tool(self.pkg,script,*args,check=check,**extra)
    def plan(self,d,*args,check=True,seed=None,job=True,inject=None,**extra):
        """production.py plan with --scratch; job=True emulates the plan job (slurm/plan.sh sets SLURM_JOB_ID), which a non-test
        plan needs (D.4). A plan that checks seeds (--forbid-seeds-from) reserves its seed in the same log, as slurm/plan.sh
        does (S2-002; production.py refuses it otherwise, 65): unless the call names --reserve-seed itself, its first
        forbidden-seed log is copied to a file of this call alone and named as both, so the logs the tests share never
        grow (every plan checks the same entries as before), under this Env's session lock (C8_ROOT; C8_SITE fake unless
        given)."""
        if job:extra.setdefault('SLURM_JOB_ID','9999')
        args=list(args)
        if '--forbid-seeds-from'in args and '--reserve-seed'not in args:
            i=args.index('--forbid-seeds-from')+1;self.reserved+=1;cp=self.td/'reserved'/f'{self.reserved}_{Path(args[i]).name}'
            cp.parent.mkdir(exist_ok=True);shutil.copy2(args[i],cp);args[i]=cp;args+=['--reserve-seed',cp]
            extra.setdefault('C8_ROOT',self.root);extra.setdefault('C8_SITE','fake')
        return tool(self.pkg,'production.py','plan',d,'--seed',seed if seed is not None else SEED,*args,'--scratch',self.scr,check=check,inject=inject,**extra)
    def run_all(self,d,threads=2,**extra):
        for j in manifest(d)['jobs']:self.t('production.py','run',d,'--index',j['id'],'--threads',threads,'--scratch',self.scr,**extra)
    def merge(self,d,*args,**extra):return self.t('production.py','merge',d,'--scratch',self.scr,*args,**extra)
    def model(self,key='default',spp=None,spp_file=None,points=512,graphs='all')->Path:
        """make_cost_model.py on a fake cost_sweep (bootstrap basis) of this package: the measured model of every fake
        lane-mode plan (HC7). spp / spp_file set the fake seconds (C8_FAKE_SPP, C8_FAKE_SPP_FILE)."""
        if key in self.models:return self.models[key]
        d=self.td/f'sweep_{key}';x={}
        if spp is not None:x['C8_FAKE_SPP']=spp
        if spp_file is not None:x['C8_FAKE_SPP_FILE']=spp_file
        self.plan(d,'--pilot','--points',points,'--replicates',2,'--test-graphs',graphs,'--plan-role','cost_sweep','--bootstrap-chunk',min(512,points),'--shards',2,
                  '--threads',2,seed=SEED+hash(key)%100000)
        self.run_all(d,**x);self.merge(d,'--jobs',2);out=self.td/f'model_{key}.json';self.t('make_cost_model.py',d,out)
        self.models[key]=out;return out

def flip(path:Path,at=None)->bytes:
    data=path.read_bytes();b=bytearray(data);b[len(b)//2 if at is None else at]^=1;path.unlink();path.write_bytes(bytes(b));return data

# =====================================================================================================================
# seeds, nets, manifests (A-ORC-1, A-ORC-7's Sobol export at every C8 shape)
NET_TESTS=('tests/validate.py','tests/class_b.py','tests/forced_tiers.py','tests/inspect_check.py','tests/sanitize.py','tests/thread_identity.py','tests/first_error.py')
def stage3a_net_seeds(have:set,forb:dict)->int:
    """HD6 (Stage 3a repair round 3, follow-up): tests/fixtures/stage3a_test_seeds.json lists, per nc.net call site of the
    real-worker tests, the seed expression, the values the Stage-3a runs bound to its names and the seeds. Checks: the
    fixture's call sites are exactly the files' (a new or changed site fails until it is listed and registered); each seed
    is the expression evaluated at its binding (module int constants such as SEED included); the zero-channel tails seeds
    equal the net seeds of the pinned repair3b rows; every seed is in the committed mirror and refused as a plan seed."""
    import production as prod
    fx=json.loads((ROOT/'tests/fixtures/stage3a_test_seeds.json').read_text());assert fx['schema']=='c8-d3-stage3a-test-seeds-1'
    n=0
    for f in NET_TESTS:
        tree=ast.parse((ROOT/f).read_text());exprs={ast.unparse(e)for e in ast.walk(tree)if isinstance(e,ast.expr)}
        sites=sorted(ast.unparse(c.args[3])for c in ast.walk(tree)if isinstance(c,ast.Call)and isinstance(c.func,ast.Attribute)
                     and c.func.attr=='net'and isinstance(c.func.value,ast.Name)and c.func.value.id=='nc')
        ents=[e for e in fx['entries']if e['file']==f];assert sites==sorted(e['expr']for e in ents if e['kind']=='net'),(f,sites)
        consts={t.id:a.value.value for a in tree.body if isinstance(a,ast.Assign)and isinstance(a.value,ast.Constant)and type(a.value.value)is int
                for t in a.targets if isinstance(t,ast.Name)}
        draws={ast.unparse(c.args[0])for c in ast.walk(tree)if isinstance(c,ast.Call)and ast.unparse(c.func)in('random.Random','Random')and c.args}
        for e in ents:
            src=e.get('define',e['expr']);assert src in exprs,(f,src)   # the defining expression is the file's
            if e['kind']=='draw':assert e['expr']in draws,(f,e['expr'])
            got=[eval(src,{'__builtins__':{}},{**consts,**b})for b in e['bindings']];assert got==e['seeds'],(f,e['part'],got,e['seeds'])
            for sd in e['seeds']:
                assert sd in have,(f,e['part'],sd);assert prod.seed_refusal(sd,forb),sd;n+=1
    zc=json.loads((ROOT/'tests/fixtures/zero_channel_tails.json').read_text())
    pinned={c['net_seed']for k in zc['kernels']for c in k['campaigns'].values()}
    assert pinned==set(next(e for e in fx['entries']if e['expr']=='nseed')['seeds']),pinned
    assert {c['seed']for k in zc['kernels']for c in k['campaigns'].values()}<=have
    distinct={sd for e in fx['entries']for sd in e['seeds']}
    assert n==sum(len(e['seeds'])for e in fx['entries'])and len(distinct)<=n   # every listed seed checked (one may serve two sites)
    return len(distinct)

def test_seeds_and_nets(E:Env,td:Path):
    import production as prod
    s=[]
    for c,sec,L in prod.GROUPS:x=prod.derive_seeds(SEED,c,sec,L);s+=[x['native'],x['net']]
    assert len(set(s))==48 and prod.derive_seeds(SEED,'a','free',3)!=prod.derive_seeds(SEED+1,'a','free',3)
    fx=json.loads((ROOT/'tests/fixtures/run1_groups.json').read_text())
    assert prod.seed_refusal(4805754955154533039,{})and 'used base seed'in prod.seed_refusal(4805754955154533039,{})   # C7(3) run1 base
    for b in prod.C7_USED_BASE_SEEDS:assert prod.seed_refusal(b,{})
    g=fx['groups']['b_power_L7'];assert prod.seed_refusal(g['seed'],{})and prod.seed_refusal(g['net']['seed'],{})   # run1 group seeds
    forb={123456:'test'};assert 'forbidden'in prod.seed_refusal(123456,forb)
    d=prod.derive_seeds(123456,'a','power',8)['net'];assert 'derived group seed'in prod.seed_refusal(d,forb)
    assert prod.seed_refusal(SEED,{})is None
    must(E.plan(td/'nonforbid','--pilot','--replicates',2,'--cost-model',E.model(),check=False),1,'--forbid-seeds-from')
    assert not (td/'nonforbid').exists()
    # seeds.py add: atomic under concurrency (the session lock), nothing lost
    root=td/'seedroot';root.mkdir();log=td/'seedlog.json'
    must(tool(E.pkg,'seeds.py','add','--seed',999,'--label','x','--log',log,check=False,C8_SITE='fake',C8_ROOT=root),64,'does not exist','seeds.py init')
    assert not log.exists()   # add never creates a log (A1: a site's log never starts empty by accident)
    must(tool(E.pkg,'seeds.py','init','--log',log,check=False,C8_SITE='fake',C8_ROOT=root),0,'"state": "created"')
    with concurrent.futures.ThreadPoolExecutor(8)as ex:
        cps=list(ex.map(lambda i:tool(E.pkg,'seeds.py','add','--seed',1000+i,'--label',f'l{i}','--log',log,check=False,C8_SITE='fake',C8_ROOT=root),range(8)))
    assert all(c.returncode==0 for c in cps),[c.stderr for c in cps]
    have=json.loads(log.read_text())['seeds'];assert sorted(e['seed']for e in have)==list(range(1000,1008))
    must(tool(E.pkg,'seeds.py','check','1003','--log',log,check=False,C8_SITE='fake',C8_ROOT=root),1)
    # the HD6 mirror (Stage 3a repair round 2): designs/forbidden_seeds.json := a byte copy of the log, append-only
    mir=td/'designs/forbidden_seeds.json';must(tool(E.pkg,'seeds.py','mirror','--log',log,'--to',mir,check=False),0,'"state": "written"')
    assert mir.read_bytes()==log.read_bytes();must(tool(E.pkg,'seeds.py','mirror','--log',log,'--to',mir,check=False),0,'"state": "identical"')
    short=td/'seedlog_short.json';doc=json.loads(log.read_text());doc['seeds']=doc['seeds'][1:];short.write_text(json.dumps(doc,indent=1)+'\n')
    before=mir.read_bytes();must(tool(E.pkg,'seeds.py','mirror','--log',short,'--to',mir,check=False),64,'append-only');assert mir.read_bytes()==before
    (td/'notalog.json').write_text('{"seeds": []}');must(tool(E.pkg,'seeds.py','mirror','--log',td/'notalog.json','--to',mir,check=False),64,'c8-d3-seeds-1')
    tool(E.pkg,'seeds.py','add','--seed',2000,'--label','later','--log',log,C8_SITE='fake',C8_ROOT=root)
    must(tool(E.pkg,'seeds.py','mirror','--log',log,'--to',mir,check=False),0,'"added": 1');assert mir.read_bytes()==log.read_bytes()
    com=json.loads((ROOT/'designs/forbidden_seeds.json').read_text())   # the package's committed mirror
    assert com['schema']=='c8-d3-seeds-1'and any(e['seed']==20261004 and e['source'].startswith('G-RUN1 selection')for e in com['seeds']),com
    # HD6 after Stage 3a repair round 3: the A-IN-6 L=2 control (base, native and net seeds of val3a) and the other base and
    # native seeds of the Stage-3a test runs are registered; the mirror refuses the control's seeds as plan seeds
    have={e['seed']for e in com['seeds']};stage3a={6602215,6602267,6602275,220052,220060,7738251,741987,6619043,6619044,6619045,4401,4242,1,7611826,816615,816616}
    assert stage3a<=have,sorted(stage3a-have)
    forb=prod.read_seed_file(ROOT/'designs/forbidden_seeds.json')
    for sd in (6602215,6602267,6602275,220052,220060):assert prod.seed_refusal(sd,forb),sd
    # Stage 3b: the native and draw seed of tests/thread_identity.py (8806401) and its chunk draw (8806402) are registered too
    assert {8806401,8806402}<=have,sorted({8806401,8806402}-have)
    nnet=stage3a_net_seeds(have,forb)
    # C7 and dimension-2 manifests are refused with their messages
    for sch,want in (('c7-d3-production-2','LRI_C7_D3_HPC@a6ce987'),('c8-d2-production-1','dimension-2')):
        d=td/f'man_{sch}';d.mkdir();(d/'manifest.json').write_text(json.dumps({'schema':sch,'dimension':3 if sch.startswith('c7')else 2,'order':7}))
        try:prod.verify_base(d);raise AssertionError('accepted '+sch)
        except ValueError as e:assert want in str(e),e
    # the three-way Sobol export at every C8 shape (dimensions 7..31 and 16; bits 52 and 60)
    for dim in (7,11,15,16,19,23,27,31):
        for bits in (52,60):
            info=prod.make_net(td/f'net_{dim}_{bits}.bin',2,dim,bits,dim*bits,4096)
            assert info['checks']==['public_api','fresh_engine','gf2_structure']and info['columns_checked']==12
    ok('A-ORC-1: hashed group seeds distinct over 24 groups x roles; the HD6 registry refuses C7(3) base seeds, run1 group native and net seeds, '
       'forbidden seeds and their derived group seeds; a non-test plan without --forbid-seeds-from refuses; seeds.py add is atomic under 8 '
       'concurrent writers; seeds.py mirror writes a byte copy, refuses a log that drops an entry or is not a seed log (64), and takes appended '
       'entries; the committed designs/forbidden_seeds.json holds the G-RUN1 seed 20261004, the L=2 control\'s base, native and net seeds (refused as '
       f'plan seeds) and the Stage-3a test seeds, with the {nnet} net and random.Random seeds of '
       'tests/fixtures/stage3a_test_seeds.json (every nc.net call site of the real-worker tests listed, each seed recomputed from '
       'the call\'s expression and refused as a plan seed); C7 and dimension-2 manifests are refused; the '
       'three-way Sobol export passes at every C8 shape (dims 7-31, 16; bits 52, 60)')

# =====================================================================================================================
# allocation sources, bundles, selection files (A-ORC-2)
def write_bundle(td:Path,name:str,inv:dict,im_sha:str,s=1,reps=32,count=4096,**meta)->Path:
    import production as prod
    b=td/name;(b/'counts').mkdir(parents=True);files={}
    for c,sec,L in prod.GROUPS:
        data=''.join(f'{r["id"]} {count}\n'for r in inv[sec][str(L)]).encode();(b/f'counts/{c}_{sec}_L{L}.txt').write_bytes(data)
        files[f'counts/{c}_{sec}_L{L}.txt']=hashlib.sha256(data).hexdigest()
    strata=[f'free_L{L}'for L in range(3,9)]+['free_L8_primitive']+[f'power_L{L}'for L in range(3,9)]
    d={'schema':'c8-d3-design-1','strata':{st:{'s':s}for st in strata},'replicates':{f'{x}_L{L}':reps for x in('free','power')for L in range(3,9)},'batches':2}
    dd=(json.dumps(d)+'\n').encode();(b/'design.json').write_bytes(dd)
    m={'schema':'c8-d3-design-1','design_sha256':hashlib.sha256(dd).hexdigest(),'counts_sha256':files,'inputs_manifest_sha256':im_sha,'numerics':'exact',**meta}
    (b/'design_meta.json').write_text(json.dumps(m)+'\n');return b

def test_allocation(E:Env,td:Path):
    import production as prod
    M=E.model();common=['--replicates',2,'--threads',2,'--cost-model',M,'--forbid-seeds-from',E.seeds]
    for args,why in (([],'exactly one allocation source'),(['--pilot','--design',td],'exactly one allocation source'),(['--points',4096],'exactly one allocation source')):
        d=td/f'al_{len(args)}';must(E.plan(d,*args,*common,check=False),1,why);assert not d.exists()
    must(E.plan(td/'p2048','--pilot','--points',2048,*common,check=False),1,'unless a test-only plan')
    E.plan(td/'p2048t','--pilot','--points',2048,'--test-graphs','all',*common)
    d=td/'al_pilot';E.plan(d,'--pilot','--group-replicates','power:8=4',*common)
    m=manifest(d);assert m['campaign_role']=='pilot_full'and not m['test_only']
    for g in m['groups']:
        c=config(d,g['name']);assert set(c['counts'].values())=={4096},c['counts']
        assert c['replicates']==(4 if (c['sector'],c['L'])==('power',8)else 2),(g['name'],c['replicates'])
    # stratified test selection: N/2 cheapest + N/2 heaviest, every L7 primitive, >= 16 L8 primitives, deterministic
    S=Env(td,'strat',counts={'free':{3:2,4:2,5:3,6:3,7:12,8:40},'power':{3:1,4:2,5:2,6:3,7:3,8:5}},primitives={('free',7):6,('free',8):20})
    Ms=S.model();sel=[]
    for k in (1,2):
        d=td/f'strat{k}';S.plan(d,'--pilot','--test-graphs',4,'--test-selection','stratified','--replicates',2,'--threads',2,'--cost-model',Ms,seed=SEED+k)
        sel.append({g['name']:sorted(map(int,config(d,g['name'])['counts']))for g in manifest(d)['groups']})
    assert sel[0]==sel[1];inv=json.loads((S.pkg/'inputs/inventory.json').read_text())
    p7={r['id']for r in inv['free']['7']if r['primitive']};p8={r['id']for r in inv['free']['8']if r['primitive']}
    assert p7<=set(sel[0]['a_free_L7'])and len(p8&set(sel[0]['a_free_L8']))>=16
    # --design: counts x s with the bundle's replicates, the bundle sha recorded; the refusals of E.5
    inv=json.loads((E.pkg/'inputs/inventory.json').read_text());im=hashlib.sha256((E.pkg/'inputs/manifest.json').read_bytes()).hexdigest()
    b=write_bundle(td,'bundle_ok',inv,im,s=2,reps=4,count=4096,test_only=True)
    d=td/'al_design';E.plan(d,'--design',b,'--test-only','--threads',2,'--cost-model',M)
    m=manifest(d);assert m['design']['meta_sha256']==hashlib.sha256((b/'design_meta.json').read_bytes()).hexdigest()and m['allocation']['source']=='design'
    assert all(set(config(d,g['name'])['counts'].values())=={8192}and config(d,g['name'])['replicates']==4 for g in m['groups'])
    prov=td/'bundle_prov';prov.mkdir();(prov/'design_meta.json').write_text(json.dumps({'schema':'c8-d3-design-1','provisional':True,'measurement_campaign':'RUN_X'}))
    for extra in ([],['--test-only']):
        must(E.plan(td/'d_prov','--design',prov,*extra,'--threads',2,'--cost-model',M,'--forbid-seeds-from',E.seeds,check=False),1,'provisional','RUN_X','fresh')
    must(E.plan(td/'d_to','--design',b,'--threads',2,'--cost-model',M,'--forbid-seeds-from',E.seeds,check=False),1,'--test-only bundle')
    bf=write_bundle(td,'bundle_forb',inv,im,forbidden_seeds=[SEED+7])
    must(E.plan(td/'d_forb','--design',bf,'--test-only','--threads',2,'--cost-model',M,seed=SEED+7,check=False),1,'forbidden seed')
    bfb=write_bundle(td,'bundle_fb',inv,im,label='fallback')
    must(E.plan(td/'d_fb','--design',bfb,'--threads',2,'--cost-model',M,'--forbid-seeds-from',E.seeds,check=False),1,'--approved-fallback')
    E.plan(td/'d_fb_ok','--design',bfb,'--threads',2,'--cost-model',M,'--forbid-seeds-from',E.seeds,'--approved-fallback','PLAN-REVIEW-LOG.md:1 test')
    assert manifest(td/'d_fb_ok')['design']['approved_fallback'].startswith('PLAN-REVIEW-LOG')
    for x in ('d_prov','d_to','d_forb','d_fb'):assert not (td/x).exists()
    ok('A-ORC-2: no or two allocation sources refuse creating nothing; --pilot gives every graph P points per replicate; --points 2048 needs '
       '--test-graphs; --group-replicates sets per-group R in both campaigns; stratified selection holds every L7 and >= 16 L8 primitives and is '
       'deterministic; --design reproduces counts x s with the bundle replicates and records its sha256; a provisional bundle (test-only too, naming '
       'the measurement campaign and the fresh freeze), a test-only bundle in a non-test plan, a forbidden seed and an unapproved fallback bundle refuse')

def selection(inv:dict,im:str,groups:dict,role='stage_a',seed=5)->dict:
    return {'schema':'c8-d3-selection-1','inputs_manifest_sha256':im,'role':role,'seed':seed,'groups':groups,'empty_reason':None}

def test_selection_files(E:Env,td:Path):
    M=E.model();inv=json.loads((E.pkg/'inputs/inventory.json').read_text());im=hashlib.sha256((E.pkg/'inputs/manifest.json').read_bytes()).hexdigest()
    common=['--pilot','--replicates',2,'--threads',2,'--cost-model',M]
    doc=selection(inv,im,{'free:8':[{'id':0,'points':4096,'label':'stratified'},{'id':1,'points':32768,'nest':[4096],'label':'p1c'}],'power:5':[{'id':1,'points':8192,'nest':[1024,4096],'label':'x'}]})
    f=td/'sel.json';f.write_text(json.dumps(doc));d=td/'sel_run'
    E.plan(d,'--graphs',f,*common,'--forbid-seeds-from',E.seeds)
    m=manifest(d);assert m['campaign_role']=='pilot_subset'and sorted(g['name']for g in m['groups'])==['a_free_L8','a_power_L5','b_free_L8','b_power_L5']
    assert m['selection']['sha256']==hashlib.sha256(f.read_bytes()).hexdigest()and (d/'selection.json').read_bytes()==f.read_bytes()
    c=config(d,'a_free_L8');assert c['counts']=={'0':4096,'1':32768}and c['nest']=={'1':[4096]}
    import production as prod
    rows=[r for j in m['jobs']if j['group']=='a_free_L8'for r in prod.job_rows(d,j)if r[2]==1]
    ends={r[4]for r in rows};assert 4096 in ends or any(r[3]==4096 for r in rows),'the 4,096-point prefix is a set of whole tasks'
    assert all(not(r[3]<4096<r[4])for r in rows)
    bad=[('dup',{'free:8':[{'id':0,'points':4096},{'id':0,'points':4096}]},'twice'),('unknown',{'free:8':[{'id':999,'points':4096}]},'not in the inventory'),
         ('points',{'free:8':[{'id':0,'points':3000}]},'power of two'),('nest',{'free:8':[{'id':0,'points':8192,'nest':[8192]}]},'nest'),
         ('nest2',{'free:8':[{'id':0,'points':8192,'nest':[4096,2048]}]},'nest'),('key',{'free:9':[{'id':0,'points':4096}]},'sector:L'),
         ('emptykey',{'free:8':[]},'no empty group')]
    for name,groups,want in bad:
        f2=td/f'sel_{name}.json';f2.write_text(json.dumps(selection(inv,im,groups)))
        must(E.plan(td/f'sb_{name}','--graphs',f2,*common,'--forbid-seeds-from',E.seeds,check=False),1,want);assert not (td/f'sb_{name}').exists()
    e=selection(inv,im,{});e['empty_reason']='no flag';f3=td/'sel_empty.json';f3.write_text(json.dumps(e))
    must(E.plan(td/'sb_empty','--graphs',f3,*common,'--forbid-seeds-from',E.seeds,check=False),65,'empty selection');assert not (td/'sb_empty').exists()
    w=selection(inv,'0'*64,{'free:8':[{'id':0,'points':4096}]});f4=td/'sel_im.json';f4.write_text(json.dumps(w))
    must(E.plan(td/'sb_im','--graphs',f4,*common,'--forbid-seeds-from',E.seeds,check=False),1,'another inputs manifest')
    ok('D.3 selection files: --graphs plans exactly the named groups in both campaigns as pilot_subset with per-graph points and nest boundaries '
       '(recorded in the group config; the 4,096-point prefix of a nested graph is a set of whole tasks), copies the file and pins its sha256; '
       'a repeated id, an unknown id, points or nest boundaries off the rule, a bad key, an empty key, another inputs manifest and an empty '
       'selection (65) are refused before anything is created')

# =====================================================================================================================
# chunking, sizing, roles, the first-sweep bootstrap (A-ORC-3)
def synthetic(E)->Path:return E.pkg/'tests/fixtures/cost_model_synthetic.json'

def test_chunking_synthetic(E:Env,td:Path):
    import production as prod
    fx=json.loads(synthetic(E).read_text())
    inv=json.loads((E.pkg/'inputs/inventory.json').read_text());im=hashlib.sha256((E.pkg/'inputs/manifest.json').read_bytes()).hexdigest()
    f=td/'sel_chunk.json';f.write_text(json.dumps(selection(inv,im,{'free:8':[{'id':0,'points':65536,'nest':[4096,16384],'label':'p1c'}],'free:3':[{'id':0,'points':65536}]},role='other')))
    d=td/'chunk';E.plan(d,'--pilot','--graphs',f,'--test-only','--replicates',2,'--threads',2,'--plan-role','validation','--cost-model',synthetic(E),'--index-hours',0.001)
    m=manifest(d);assert m['cost_basis']=='synthetic'and (d/'synthetic_cost_model.json').exists()and not (d/'cost_model.json').exists()
    assert m['estimates']['label']==prod.SYNTHETIC_LABEL
    for g in m['groups']:
        c=config(d,g['name']);cg=fx['seconds_per_point_by_group'][f'{c["campaign"]}:{c["sector"]}:{c["L"]}']
        for gid,ch in c['chunks'].items():
            n=c['counts'][gid];want=min(max(256,1<<int(math.floor(math.log2(60/cg)))),n)
            assert ch==want and prod.pow2(ch),(g['name'],ch,want)
        rows=[r for j in m['jobs']if j['group']==g['name']for r in prod.job_rows(d,j)]
        assert all((r[4]-r[3])*cg<=120 for r in rows)
        if c['nest']:assert all(not(r[3]<b<r[4])for r in rows for b in (4096,16384))
        C=sum(c['counts'][x]for x in c['counts'])*c['replicates']*cg;want=max(1,math.ceil(C/(0.001*3600*2*0.9)))
        assert c['shards']==min(want,c['tasks']),(g['name'],c['shards'],want)
    a=sum(j['est_core_seconds']for j in m['jobs']if j['campaign']=='a');b=sum(j['est_core_seconds']for j in m['jobs']if j['campaign']=='b')
    assert abs(b/a-3)<1e-9,(a,b)
    must(E.plan(td/'chunk_bad','--pilot','--points',16384,'--test-graphs',1,'--replicates',2,'--threads',2,'--plan-role','validation','--cost-model',synthetic(E),
                '--min-chunk',8192,check=False),1,'graph','--max-task-seconds');assert not (td/'chunk_bad').exists()
    ok('A-ORC-3 chunking: with the labelled synthetic fixture (campaign b at 3x a; --plan-role validation, the only role that admits it) chunks are '
       'powers of two in [256, n_g] = 60/c_g clamped, cut at nest boundaries, every task <= 120 s (a --min-chunk that breaks it refuses naming '
       'the graph); shard counts follow --index-hours; the fixture is copied as synthetic_cost_model.json and every estimate carries its label')

def test_roles(E:Env,td:Path):
    """Validation plans and the non-measured roles (HC1, HC5; D.5, HD11)."""
    M=E.model();site=c8pkg.SlurmSite(td,'roles')
    base=['--pilot','--points',4096,'--test-graphs',2,'--replicates',2,'--threads',2]
    d1=td/'val_boot';E.plan(d1,*base,'--plan-role','validation','--bootstrap-chunk',512,'--shards',2)
    d2=td/'val_syn';E.plan(d2,*base,'--plan-role','validation','--cost-model',synthetic(E))
    for d,basis in ((d1,'bootstrap'),(d2,'synthetic')):
        m=manifest(d);assert m['plan_role']=='validation'and m['cost_basis']==basis and m['campaign_role']=='test'and not (d/'cost_model.json').exists()
    assert manifest(d1)['estimates']['estimate']=='unavailable (bootstrap)'and manifest(d1)['bootstrap_proxy']['label'].startswith('preliminary_proxy')
    nt=['--pilot','--replicates',2,'--threads',2,'--forbid-seeds-from',E.seeds]
    for name,args,why in (('nontest',[*nt,'--plan-role','validation','--bootstrap-chunk',512,'--shards',2],'non-measured role'),
                          ('measured',[*base,'--plan-role','validation','--cost-model',M],'refuses a measured model'),
                          ('prior',[*base,'--plan-role','validation','--prior-cost-model',M],'refuses --prior-cost-model'),
                          ('design',['--design',td,'--test-only','--plan-role','validation','--cost-model',synthetic(E)],'refuses --design')):
        must(E.plan(td/f'vr_{name}',*args,check=False),1,why);assert not (td/f'vr_{name}').exists()
    for role in ('campaign','cost_sweep','cost_refresh','flag_check'):
        must(E.plan(td/f'syn_{role}',*base,'--plan-role',role,'--cost-model',synthetic(E),check=False),1,'validation-only')
        must(E.plan(td/f'syn_{role}_nt','--pilot','--replicates',2,'--threads',2,'--forbid-seeds-from',E.seeds,'--plan-role',role,'--cost-model',synthetic(E),check=False),1)
    # role coverage: every non-measured role accepted on its basis, refused by lane mode; the same arguments as role campaign refuse
    runs={}
    for role,extra in (('cost_sweep',['--bootstrap-chunk',512,'--shards',2]),('cost_refresh',['--bootstrap-chunk',512,'--shards',2]),
                       ('flag_check',['--bootstrap-chunk',512,'--shards',2]),('validation',['--cost-model',synthetic(E)])):
        d=site.run_dir(f'role_{role}');E.plan(d,*base,'--plan-role',role,*extra);runs[role]=d
        for dry in (True,False):
            n0=len(site.history());must(site.submit(E.pkg,'lanes','1',*(['--dry-run']if dry else[]),C8_RUN=d),65,'lane mode runs only role campaign');assert len(site.history())==n0
        must(E.plan(td/f'campaign_{role}',*base,'--plan-role','campaign',*extra,check=False),1)
    # lanes.py on a validation plan, drill mode included: 65 before any claim
    for drill in ('0','1'):
        cp=E.t('lanes.py','worker',runs['validation'],check=False,SLURM_JOB_ID='77',C8_LANE_DRILL=drill,C8_LANE_SECONDS='3600')
        must(cp,65,'lane mode runs only role campaign');assert not (runs['validation']/'lanes/claims').exists()
    # after a fake run and merge make_cost_model refuses the validation campaign and cost_identity fails on it
    E.run_all(d2);E.merge(d2,'--jobs',2)
    must(E.t('make_cost_model.py',d2,td/'m_val.json',check=False),65,'validation campaign');assert not (td/'m_val.json').exists()
    must(E.t('cost_identity.py','check',d2,check=False),1)
    # the never-a-cost spy: no cost consumer opens a scheduling basis
    forbidden=('synthetic_cost_model.json','cost_model_synthetic.json','bootstrap_proxy.json','prior_cost_model.json')
    sweep=E.td/'sweep_default'
    cp,ev=spy(E.pkg,td,'make_cost_model.py',sweep,td/'m_spy.json');assert cp.returncode==0,cp.stderr
    bad=[p for p in opened(ev,False)if any(p.endswith(x)for x in forbidden)];assert not bad,bad
    ok('HC1/HC5 roles: validation plans on the bootstrap basis and on the synthetic fixture are accepted (role and basis recorded; the fixture as '
       'synthetic_cost_model.json, no cost_model.json); the role in a non-test plan, with a measured model, --prior-cost-model or --design refuses; '
       'the fixture under every other role refuses; each non-measured role is accepted on its basis while lanes 1 and --dry-run exit 65 with no '
       'sbatch and the same arguments with role campaign refuse; lanes.py refuses a validation plan (drill mode too) before any claim; '
       'make_cost_model.py refuses a validation campaign and cost_identity fails on it; make_cost_model.py opens no scheduling basis (spy)')

def test_first_sweep_bootstrap(E:Env,td:Path):
    import production as prod,bootstrap_proxy as bp
    B=Env(td,'bigA',counts={'free':{3:1,4:1,5:1,6:1,7:1,8:2},'power':{3:1,4:1,5:1,6:1,7:1,8:1}})
    ip=B.pkg/'inputs/inventory.json';inv=json.loads(ip.read_text());row=inv['free']['8'][1];row['products']=54326;row['addends']=108652-54326
    data=(json.dumps(inv,indent=1)+'\n').encode();ip.unlink();ip.write_bytes(data)
    mp=B.pkg/'inputs/manifest.json';m=json.loads(mp.read_text());m['sha256']['inventory.json']=hashlib.sha256(data).hexdigest();mp.unlink();mp.write_text(json.dumps(m,indent=2)+'\n')
    sw=['--pilot','--points',512,'--replicates',2,'--test-graphs','all','--plan-role','cost_sweep','--bootstrap-chunk',512,'--shards',32,'--threads',2]
    d=td/'sweep1';B.plan(d,*sw)
    mm=manifest(d);doc=json.loads((B.pkg/'tools/bootstrap_proxy.json').read_text());want=bp.seconds_per_point(doc,108652)*512
    c=config(d,'a_free_L8');assert c['chunks']=={'0':512,'1':512}and abs(c['preliminary_max_task_seconds']-want)<1e-9 and want<=120,(c,want)
    assert mm['estimates']['estimate']=='unavailable (bootstrap)'and all(j['est_core_seconds']is None for j in mm['jobs'])
    site=c8pkg.SlurmSite(td,'boot');ds=site.run_dir('sweep1');shutil.copytree(d,ds)
    must(site.submit(B.pkg,'lanes','1','--dry-run',C8_RUN=ds),65,'lane mode')
    for args,why in ((['--cost-model',synthetic(B)],'one cost basis'),(['--index-hours',1],'--bootstrap-chunk refuses --index-hours')):
        must(B.plan(td/'bb',*sw[:-6],'--bootstrap-chunk',512,'--threads',2,*args,'--plan-role','cost_sweep',*(['--shards',2]if '--index-hours'not in args else[]),check=False),1,why)
    must(B.plan(td/'bb','--pilot','--replicates',2,'--threads',2,'--forbid-seeds-from',B.seeds,'--plan-role','cost_sweep','--bootstrap-chunk',512,'--shards',2,check=False),1,'non-measured role')
    must(B.plan(td/'bb',*sw[:7],'--plan-role','campaign','--bootstrap-chunk',512,'--shards',2,'--threads',2,check=False),1,'with --plan-role campaign')
    must(B.plan(td/'bb','--pilot','--points',4096,'--replicates',2,'--test-graphs','all','--plan-role','cost_sweep','--bootstrap-chunk',4096,'--shards',2,'--threads',2,check=False),
         1,'a_free_L8 graph 1','preliminary seconds')
    assert not (td/'bb').exists()
    # bootstrap_proxy.py: byte for byte in a git-archive export (no .git, no git process), refuses a one-byte change of the pinned log
    exp=td/'export';exp.mkdir()
    if (ROOT/'.git').exists():subprocess.run(f'git -C {ROOT} archive HEAD tools reference/SHA256SUMS_c8 reference/c8d3_recon/out | tar -x -C {exp}',shell=True,check=True)
    else:   # the package is itself a git-archive export (J-VAL-1 on the cluster, the Mac export check): copy the same three paths
        shutil.copytree(ROOT/'tools',exp/'tools',ignore=shutil.ignore_patterns('__pycache__'));(exp/'reference').mkdir()
        shutil.copy2(ROOT/'reference/SHA256SUMS_c8',exp/'reference/SHA256SUMS_c8');shutil.copytree(ROOT/'reference/c8d3_recon/out',exp/'reference/c8d3_recon/out')
    shutil.copy2(ROOT/'tools/bootstrap_proxy.py',exp/'tools/bootstrap_proxy.py');shutil.copy2(ROOT/'tools/bootstrap_proxy.json',exp/'tools/bootstrap_proxy.json')
    assert not (exp/'.git').exists()
    cp,ev=spy(exp,td,'bootstrap_proxy.py','--check');assert cp.returncode==0 and '"identical": true'in cp.stdout,cp.stdout+cp.stderr
    assert not [p for p in opened(ev,False)if '/.git/'in p]and not [e for e in ev if e[0]=='popen'and 'git'in e[1][0]]
    flip(exp/'reference/c8d3_recon/out/l8cost.log',100);must(tool(exp,'bootstrap_proxy.py','--check',check=False),1,'Checksum mismatch')
    # after the fake sweep has run and merged: the first measured model, then a test-only lane-mode plan with chunks from 60/c_g
    B.run_all(d);B.merge(d,'--jobs',2);B.t('make_cost_model.py',d,td/'first.json')
    first=json.loads((td/'first.json').read_text());assert first['scheduled_with']=={'basis':'bootstrap','model_sha256':None,'executable_sha256':None}
    d2=site.run_dir('lanetest');B.plan(d2,'--pilot','--test-only','--replicates',2,'--threads',2,'--cost-model',td/'first.json','--index-hours',0.25)
    c=config(d2,'a_free_L8');cg=first['seconds_per_point']['a:free:8:0'];assert c['chunks']['0']==min(max(256,1<<int(math.floor(math.log2(60/cg)))),4096)
    must(site.submit(B.pkg,'lanes','1','--dry-run',C8_RUN=d2),0,'dry run')
    ok('A-ORC-3 first-sweep bootstrap: the J-SWEEP-1 arguments publish a test-only plan with 512-point tasks whose preliminary seconds (an L8 graph '
       'at A = 108,652) equal s(A) x 512 <= 120 s, estimates "unavailable (bootstrap)", refused by lane mode; --bootstrap-chunk with a model, with '
       '--index-hours, in a non-test plan or with role campaign refuses, and a P above 120 preliminary seconds refuses naming the graph; '
       'bootstrap_proxy.py regenerates the JSON byte for byte in a git-archive export (no .git opened, no git started) and refuses a one-byte '
       'change of the pinned log; the fake sweep gives the first measured model and a lane-mode plan with chunks from 60/c_g')

# =====================================================================================================================
# blocks at plan level (A-ORC-3 "Blocks", R10)
def test_blocks_plan_level(E:Env,td:Path):
    import production as prod,numpy as np
    GB=10**9
    g={'name':'x','counts':{1:1,2:1,3:1},'reps':1,'ntasks':5,'nshards':1,'tb':{1:[(0,1),(1,2)],2:[(0,1),(1,2)],3:[(0,1)]},
       'per':{1:5.,2:3.,3:4.},'prelim':{},'byid':{1:{'kernel_bytes':GB},2:{'kernel_bytes':GB//10},3:{'kernel_bytes':3*GB}}}
    # graphs A=1 (cost 5 per task), C=3 (4), B=2 (3): pos order A, A, C, B, B (cost descending)
    prod._lpt_blocks(g,4,1e9,1,False,1);sj=g['shard_jobs'][0]
    assert sj['block_tasks']==[3,2],sj   # greedy [A,A,C,B] | [B] -> rebalanced [A,A,C] | [B,B]
    assert sj['est_peak_bytes']==4*GB+4*2**20+2**29,sj['est_peak_bytes']
    assert sj['est_core_seconds']==5+5+4+3+3 and sj['blocks']==2 and sj['block_wall']==[14.,6.]and sj['block_phi']==[0.75,0.5]
    # D.6: a task with s_t/w > S/2 is refused, naming its group, graph, replicate and points (the fixture's free L8: 2,048-point
    # chunks of 41.9 s at --threads 1 against --block-seconds 60), before anything is created
    s2=td/'s2';cp=must(E.plan(s2,'--pilot','--points',4096,'--test-graphs',1,'--replicates',2,'--threads',1,'--checkpoint-tasks',256,'--plan-role','validation',
                              '--cost-model',synthetic(E),'--block-seconds',60,'--shards',1,check=False),1,'> --block-seconds/2 = 30 s','D.6')
    assert re.search(r'group [ab]_(free|power)_L8 graph \d+ replicate \d+ points \[\d+, \d+\) of \d+: ',cp.stderr)and not s2.exists(),cp.stderr[-400:]
    # the 257-task plan through run, merge, status and lanes 1 (role campaign on a fake-sweep model giving every task 1 s)
    S=Env(td,'b257',counts={'free':{3:1,4:1,5:1,6:1,7:1,8:1},'power':{3:1,4:1,5:1,6:1,7:1,8:1}})
    spp=td/'spp257.json';spp.write_text(json.dumps({'3:0':1/256}))
    M=S.model('t257',spp_file=spp,points=512)
    inv=json.loads((S.pkg/'inputs/inventory.json').read_text());im=hashlib.sha256((S.pkg/'inputs/manifest.json').read_bytes()).hexdigest()
    f=td/'sel257.json';f.write_text(json.dumps(selection(inv,im,{'free:3':[{'id':0,'points':256}]},role='other')))
    site=c8pkg.SlurmSite(td,'b257site');d=site.run_dir('p257')
    S.plan(d,'--pilot','--graphs',f,'--test-only','--replicates',257,'--threads',16,'--checkpoint-tasks',256,'--shards',1,'--cost-model',M,'--min-chunk',256)
    m=manifest(d);ja=next(j for j in m['jobs']if j['group']=='a_free_L3')
    bd=json.loads((d/ja['blocks_file']).read_text());assert ja['tasks']==257 and bd['block_tasks']==[129,128],bd
    assert all(abs(x-1/16*n)<1e-9 for x,n in zip(bd['pred_wall_seconds'],bd['block_tasks']))
    before=site.jobs();must(site.submit(S.pkg,'lanes','1',C8_RUN=d),0)
    lane=next(j for j in site.jobs()if j['name'].startswith('c8d3-lane-'))
    S.t('lanes.py','worker',d,**site.env(C8_RUN=d,SLURM_JOB_ID=lane['id'],C8_LANES='1',SLURM_TMPDIR=S.scr))
    must(S.t('production.py','status',d,check=False),0,'every checkpoint block is committed')
    S.merge(d,'--jobs',2);assert json.loads((d/'groups/a_free_L3/merged.json').read_text())['blocks']==2
    # no ceil(n/N) block counts and no islice(..., checkpoint_tasks) in tools/
    hits=[]
    for p in (ROOT/'tools').glob('*.py'):
        t=p.read_text()
        if re.search(r'\bblocks_of\s*\(',t)or re.search(r'islice\([^)]*checkpoint_tasks',t)or re.search(r'ceil\(\s*\w*tasks\w*\s*/\s*\w*\s*T\b',t):hits.append(p.name)
        for n in ast.walk(ast.parse(t)):
            if isinstance(n,ast.FunctionDef)and n.name=='blocks_of':hits.append(p.name+':blocks_of')
    assert not hits,hits
    ok('A-ORC-3 blocks at plan level: the final-boundary fixture (N = 4, w = 1; A, A, C, B, B with 1 GB, 3 GB, 0.1 GB) cuts [A,A,C] | [B,B] with '
       'est_peak_bytes 4.0 GB + 4 MB + 0.5 GB (not the greedy 4.1 GB) and the hand W and phi; a task with s_t/w > S/2 refuses naming its group, graph, '
       'replicate and points, creating nothing; the 257-task plan (1 s per task from a fake-sweep '
       'model, role campaign) freezes 129 + 128 and runs through lanes 1, status (exit 0) and merge; no ceil(n/N) or islice(..., '
       'checkpoint_tasks) block derivation remains in tools/')

# =====================================================================================================================
# atomic plans, scale and Lustre guards (D.4, D.7, A-ORC-15)
def test_atomic_and_guards(E:Env,td:Path):
    import production as prod
    M=E.model();shared=td/'shared';shared.mkdir();base=['--pilot','--test-only','--replicates',2,'--threads',2,'--cost-model',M]
    cp,ev=spy(E.pkg,td,'production.py','plan',shared/'a1','--seed',SEED+11,*base,'--scratch',E.scr)
    assert cp.returncode==0,cp.stderr[-800:]
    sq=[e[1]for e in ev if e[0]=='sqlite'];assert sq and all(str(E.scr.resolve())in os.path.realpath(p)for p in sq),sq
    # outside a job: a non-test plan refuses; a test-only plan needs --scratch
    must(E.plan(shared/'nj1','--pilot','--replicates',2,'--threads',2,'--cost-model',M,'--forbid-seeds-from',E.seeds,job=False,check=False),1,'outside a Slurm job')
    must(E.t('production.py','plan',shared/'nj2','--seed',SEED+14,*base,check=False),1,'outside a Slurm job');E.plan(shared/'nj3',*base,seed=SEED+15,job=False)
    assert not (shared/'nj1').exists()and not (shared/'nj2').exists()
    # SIGKILL during the build: no target directory and no SQLite file on the shared path; a rerun succeeds
    p=subprocess.Popen([sys.executable,'-B',str(E.pkg/'tools/production.py'),'plan',str(shared/'k1'),'--seed',str(SEED+12),*map(str,base),'--scratch',str(E.scr)],
                       env=c8pkg.env(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    t0=time.time()
    while time.time()-t0<60 and not list(E.scr.glob('c8d3_plan_*/campaign/groups/*/tasks.sqlite')):time.sleep(0.01)
    p.send_signal(signal.SIGKILL);p.wait()
    assert not (shared/'k1').exists()and not [x for x in shared.rglob('*.sqlite')if 'k1'in str(x)]
    E.plan(shared/'k1',*base,seed=SEED+12);assert manifest(shared/'k1')['seed']==SEED+12 and not list(shared.glob('k1.tmp.*'))
    # the scale guards and the Lustre file guard with a fake lfs (user and group quotas)
    must(E.plan(shared/'g1',*base,'--max-tasks',10,check=False),1,'--max-tasks');must(E.plan(shared/'g2',*base,'--max-checkpoints',3,check=False),1,'--max-checkpoints')
    must(E.plan(shared/'g3',*base,'--max-files',10,check=False),1,'--max-files')
    # D.7/D.13 merge scratch (Stage 3a repair round 2): the projection is the campaign's peak, every group's raw rows x 2
    # (the sum of the per-group scratch_bytes), not the largest group's alone: a /scratch on which the largest group's
    # two copies fit but the campaign's peak does not is refused; one that holds the peak is accepted
    sc=manifest(shared/'k1')['scale'];sbs=[v['scratch_bytes']for v in sc['merge'].values()]
    assert sc['merge_scratch_bytes_peak']==sum(sbs)and len(sbs)>1 and all(v['scratch_bytes']==2*900*v['rows']for v in sc['merge'].values()),sc['merge']
    cap=int((max(sbs)+sum(sbs))/2/0.8)
    must(E.plan(shared/'g5',*base,check=False,C8_MERGE_SCRATCH_BYTES=cap),1,'of scratch','D.13');assert not (shared/'g5').exists()
    must(E.plan(shared/'g6',*base,seed=SEED+16,C8_MERGE_SCRATCH_BYTES=int(sum(sbs)/0.8)+1),0,'projected merge scratch')
    fb=td/'lfsbin';fb.mkdir()
    (fb/'lfs').write_text('#!/bin/sh\nif [ "$3" = "-g" ]; then echo "/expanse/lustre/scratch 60000000000* 0 53687091200 - 4000000 0 0 -"; else echo "/expanse/lustre/scratch 1000 0 9000000000 - $FAKE_FILES_USED 0 2000000 -"; fi\n')
    (fb/'lfs').chmod(0o755);path=f'{fb}:{os.environ["PATH"]}'
    def guard(used,projected,reserve=None):
        code=('import sys;sys.path.insert(0,sys.argv[1]);import production as p;from pathlib import Path\n'
              'try:\n    r=p.file_guard(int(sys.argv[2]),None,Path(sys.argv[3]));print("MAX",r["max_files"])\nexcept ValueError as e:print("REFUSED",e)\n')
        cp=subprocess.run([sys.executable,'-B','-c',code,str(E.pkg/'tools'),str(projected),str(td)],capture_output=True,text=True,
                          env=c8pkg.env(PATH=path,C8_SITE='expanse',FAKE_FILES_USED=used,C8_PARTNER_FILE_RESERVE=reserve))
        return cp.stdout+cp.stderr
    assert 'REFUSED'in guard(1950000,40000)
    out=guard(1104040,1000);assert 'MAX 300000'in out and 'OVER the group limit'in out and 'group kbytes'in out,out
    assert 'MAX 95960'in guard(1104040,1000,800000)
    cp=E.plan(shared/'g4',*base,check=False,PATH=path,C8_SITE='expanse',FAKE_FILES_USED=1104040)
    must(cp,0,'projected files','--max-files = min(300,000');pf=manifest(shared/'g4')['scale']
    assert pf['lustre']['max_files']==300000 and pf['projected_files']==2*len(manifest(shared/'g4')['jobs'])*3+pf['checkpoints']+12*24+32
    # EDQUOT at each publish point: 74, the quota named, the previous state intact. common.io_fault honours
    # C8_TEST_IO_FAULT only off Expanse (the tools' environment keeps SLURM_CLUSTER_NAME; c8pkg.env strips C8_SITE), so in
    # an Expanse job (J-VAL-1) this part is not run and the record says so; its evidence is the Mac run.
    faults=os.environ.get('SLURM_CLUSTER_NAME')!='expanse'
    if faults:
        must(E.plan(shared/'q1',*base,check=False,C8_TEST_IO_FAULT='plan_rename'),74,'quota');assert not (shared/'q1').exists()and not list(shared.glob('q1.tmp.*'))
        d=shared/'q2';E.plan(d,*base,seed=SEED+13);j=manifest(d)['jobs'][0]
        must(E.t('production.py','run',d,'--index',j['id'],'--threads',2,'--scratch',E.scr,check=False,C8_TEST_IO_FAULT='checkpoint_publish'),74,'quota')
        assert not list((d/'groups'/j['group']/'checkpoints').glob('*.json'))
        E.run_all(d);must(E.t('production.py','merge',d,'--scratch',E.scr,check=False,C8_TEST_IO_FAULT='merge_output'),74,'quota')
        assert not list(d.glob('groups/*/merged.json'))and not list(d.glob('groups/*/graph_replicates.csv'))
        E.merge(d,'--jobs',2);assert len(list(d.glob('groups/*/merged.json')))==24
        must(E.t('assemble.py',d,'--bootstrap',0,check=False,C8_TEST_IO_FAULT='result_publish'),74,'quota');assert not (d/'C8_test_result.json').exists()
    else:
        # the guard itself: with the fault requested, an Expanse environment publishes normally (the hook is inert)
        d=shared/'q2';E.plan(d,*base,seed=SEED+13,C8_TEST_IO_FAULT='plan_rename');assert manifest(d)['seed']==SEED+13
    ok('D.4/D.7/A-ORC-15: SQLite files are built only on the scratch (spy); a SIGKILLed plan leaves no target directory and no SQLite file on the '
       'shared path and a rerun succeeds; --max-tasks, --max-checkpoints and --max-files refuse; the merge scratch projection is the campaign\'s '
       'peak (sum over groups of rows x 900 x 2): a /scratch that holds the largest group\'s two copies but not the peak refuses; with a fake lfs quota 1,950,000 of 2,000,000 files '
       'refuses 40,000 projected, 1,104,040 used gives --max-files 300,000 (the session budget binds) and a partner reserve of 800,000 gives 95,960; '
       'the projection and the group quota are printed; '+
       ('EDQUOT at the plan rename, the checkpoint publish, the merge output and the result publication stops with the quota named and the '
        'previous state intact (ledger and intent files: tests/test_submit.py)'if faults else
        'EDQUOT injection NOT RUN on this host: C8_TEST_IO_FAULT is honoured only off Expanse (common.io_fault), and a requested fault is '
        'inert here (the plan publishes); the injection evidence is the Mac run'),edquot_injection='run'if faults else'not run on Expanse (inert hook checked)')

# =====================================================================================================================
# per-index task data, the bytes-per-claim spy, the platform contract (A-ORC-13), SQLite (A-ORC-14), staging (A-ORC-16)
def test_per_index_and_spies(E:Env,td:Path):
    import production as prod
    M=E.model();d=td/'pi';E.plan(d,'--pilot','--test-only','--replicates',2,'--threads',2,'--cost-model',M,'--index-hours',0.001)
    m=manifest(d)
    for g in m['groups']:
        db=sqlite3.connect((d/'groups'/g['name']/'tasks.sqlite').resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
        for j in (j for j in m['jobs']if j['group']==g['name']):
            want=''.join(prod._row_line(*r)for r in db.execute('SELECT uid,rep,gi,lo,hi,total,block FROM tasks WHERE shard=? ORDER BY pos',(j['shard'],))).encode()
            assert (d/j['tasks_file']).read_bytes()==want
        db.close()
    j0,j1=m['jobs'][0],m['jobs'][1];orig=flip(d/j0['tasks_file'],0)
    must(E.t('production.py','run',d,'--index',j0['id'],'--scratch',E.scr,check=False),1,'differs from the manifest pin')
    E.t('production.py','run',d,'--index',j1['id'],'--scratch',E.scr);(d/j0['tasks_file']).unlink();(d/j0['tasks_file']).write_bytes(orig)
    db=d/'groups'/j0['group']/'tasks.sqlite';db.chmod(0)
    try:
        cp,ev=spy(E.pkg,td,'production.py','run',d,'--index',j0['id'],'--threads',2,'--scratch',E.scr);assert cp.returncode==0,cp.stderr[-800:]
    finally:db.chmod(0o644)
    assert not [p for p in opened(ev,False)if p.endswith('tasks.sqlite')]and not [e for e in ev if e[0]=='sqlite']
    assert not [p for p in opened(ev,False)if '/vendor/'in p],'run opened vendor/'
    # the subprocess platform contract on macOS: the native worker (the fake here) and one probe, ldd (failed, recorded) and uname -p
    launches=[e[1]for e in ev if e[0]=='popen'];names=[os.path.basename(a[0])for a in launches]
    assert names.count('ldd')==1 and set(names)<={'ldd','uname','c8d3_gmp'}and names.count('c8d3_gmp')==j0['blocks'],names
    ck=json.loads(next((d/'groups'/j0['group']/'checkpoints').glob('*.json')).read_text())['runtime']
    assert ck['fingerprint']['ldd_error']and ck['fingerprint_bytes']>0 and ck['fingerprint']['cpu_model']
    # A-ORC-14: read-only SQLite opens use immutable=1 (status and merge), and no rollback/WAL/lock file appears
    E.run_all(d)
    for script,args in (('production.py',['status',d,'--fast']),('production.py',['merge',d,'--scratch',E.scr,'--serial'])):
        cp,ev=spy(E.pkg,td,script,*args);sq=[e[1]for e in ev if e[0]=='sqlite'and str(d.resolve())in e[1]]
        assert all('immutable=1'in x and 'mode=ro'in x for x in sq),sq
    assert not [p for p in d.rglob('*')if p.name.endswith(('-journal','-wal','-shm'))]
    # bytes per claim: the same claim in two campaigns whose OTHER indices hold 10^3 and 10^6 tasks
    inv=json.loads((E.pkg/'inputs/inventory.json').read_text());im=hashlib.sha256((E.pkg/'inputs/manifest.json').read_bytes()).hexdigest();sizes={}
    for name,P in (('small',4096),('large',1<<24)):
        f=td/f'sel_{name}.json';f.write_text(json.dumps(selection(inv,im,{'free:3':[{'id':0,'points':4096}],'power:8':[{'id':g,'points':P}for g in range(4)]},role='other')))
        dd=td/f'bpc_{name}';E.plan(dd,'--pilot','--graphs',f,'--test-only','--replicates',2,'--threads',2,'--plan-role','validation','--bootstrap-chunk',256,'--shards',2,
                                   seed=SEED+20,SLURM_JOB_ID='4242',SLURM_TMPDIR=E.scr)
        mm=manifest(dd);jc=next(j for j in mm['jobs']if j['group']=='a_free_L3')
        cp,ev=spy(E.pkg,td,'production.py','run',dd,'--index',jc['id'],'--threads',2,'--scratch',E.scr);assert cp.returncode==0,cp.stderr[-600:]
        rd=set(opened(ev));sizes[name]=(sum(os.path.getsize(p)for p in rd if p.startswith(str(dd.resolve()))and os.path.isfile(p)),sum(j['tasks']for j in mm['jobs']))
    (b1,t1),(b2,t2)=sizes['small'],sizes['large'];assert t1<2000 and t2>10**6 and abs(b1-b2)<=max(4096,0.01*b1),sizes
    # staging (D.15, A-ORC-16): only members of the index's blocks; --whole-pack above 1 GB refuses
    j=m['jobs'][0];st=td/'stage1';out=json.loads(subprocess.run([sys.executable,'-B','-c',f'import sys;sys.path.insert(0,{str(E.pkg/"tools")!r});import stage_runtime as s,json;print(json.dumps(s.stage(sys.argv[1],sys.argv[2],{j["id"]})))',str(d),str(st)],capture_output=True,text=True,env=c8pkg.env()).stdout)
    rows=prod.job_rows(d,j);assert out['members_staged']==len({r[2]for r in rows})
    big=Env(td,'bigpack');bd=td/'bp';big.plan(bd,'--pilot','--test-only','--replicates',2,'--threads',2,'--plan-role','validation','--bootstrap-chunk',512,'--shards',1)
    pack=big.pkg/'inputs/packs/free_L3.pack';data=pack.read_bytes();pack.unlink()
    with pack.open('wb')as f:f.write(data);f.truncate(2**30+10)
    jb=next(j for j in manifest(bd)['jobs']if j['group']=='a_free_L3')
    cp=subprocess.run([sys.executable,'-B',str(big.pkg/'tools/stage_runtime.py'),str(bd),str(td/'stage2'),'--index',str(jb['id']),'--whole-pack'],capture_output=True,text=True,env=c8pkg.env())
    assert cp.returncode!=0 and '1 GB'in cp.stderr,cp.stderr
    ok('A-ORC-13/14/16: per-index task files equal the SQLite rows; a one-byte change makes only that index refuse; run --index never opens '
       'tasks.sqlite (spy; it completes with tasks.sqlite unreadable) nor vendor/; the claim starts exactly the native worker per block and one probe '
       '(ldd, failed and recorded as ldd_error, then uname -p on macOS); bytes read per claim in the campaign-data class are independent of the '
       'other indices\' task counts (10^3 against 10^6); read-only SQLite opens of status and merge use mode=ro&immutable=1 and leave no rollback '
       'or WAL file; staging copies only the members of the index\'s blocks and a whole pack above 1 GB refuses',bytes_per_claim=sizes)

# =====================================================================================================================
# the parallel merge (A-ORC-6, Mac part) and the carried-over safety features (A-ORC-7)
RACE_DRIVER=r'''
import argparse,contextlib,io,json,sys
sys.path.insert(0,sys.argv[1]);import production as prod
pkg,run,group,scratch,variant=sys.argv[1:6];orig=prod.dump_point;raced=[]
def racing(path,obj,point):
    if point=='merge_output'and not raced:
        other=json.loads(json.dumps(obj));raced.append(str(path))
        if variant=='different':
            other['batches'][0][0]+=1.0;other.pop('payload_sha256');other['payload_sha256']=prod.object_hash(other)
        orig(path,other,point)   # the other publisher wins the race
    return orig(path,obj,point)
prod.dump_point=racing;out=io.StringIO();err=None
try:
    with contextlib.redirect_stdout(out):
        prod.merge(argparse.Namespace(directory=__import__('pathlib').Path(run),group=group,jobs=1,parse_jobs=1,fan_in=prod.MERGE_FAN_IN,serial=False,scratch=scratch,accept_tool_change=False))
except (RuntimeError,ValueError)as x:err=str(x)
print(json.dumps({'raced':raced,'stdout':out.getvalue(),'error':err}))
'''

def test_merge_and_safety(E:Env,td:Path):
    import production as prod
    inv=json.loads((E.pkg/'inputs/inventory.json').read_text());im=hashlib.sha256((E.pkg/'inputs/manifest.json').read_bytes()).hexdigest()
    f=td/'sel_m.json';f.write_text(json.dumps(selection(inv,im,{'free:8':[{'id':0,'points':8192,'nest':[2048,4096]},{'id':1,'points':2048}],'free:3':[{'id':0,'points':4096}],
                                                                  'power:6':[{'id':g,'points':1024}for g in range(3)]},role='other')))
    a=td/'m a#%?';E.plan(a,'--pilot','--graphs',f,'--test-only','--replicates',3,'--threads',2,'--plan-role','validation','--bootstrap-chunk',256,'--shards',5)
    E.run_all(a);b=td/'m_serial';shutil.copytree(a,b)
    E.merge(a,'--jobs',24,'--parse-jobs',16);E.merge(b,'--serial')
    names=('merged.json','graph_replicates.csv','graph_tails.csv','graph_promotions.csv','graph_costs.csv','graph_prefixes.csv')
    for g in manifest(a)['groups']:
        for n in names:
            pa,pb=a/'groups'/g['name']/n,b/'groups'/g['name']/n
            if n=='merged.json':
                x,y=json.loads(pa.read_text()),json.loads(pb.read_text());x.pop('payload_sha256');y.pop('payload_sha256');x.pop('manifest_sha256');y.pop('manifest_sha256')
                assert x==y,(g['name'],n)
            else:assert pa.exists()==pb.exists()and (not pa.exists()or pa.read_bytes()==pb.read_bytes()),(g['name'],n)
    assert (a/'groups/a_free_L8/graph_prefixes.csv').exists()and not (a/'groups/a_free_L3/graph_prefixes.csv').exists()
    # fan-in 2 (several passes) is byte-identical too; concurrent merges: the collision branch runs and keeps the identical file
    c=td/'m_fan';shutil.copytree(b,c);[p.unlink()for p in c.glob('groups/*/merged.json')];[p.unlink()for p in c.glob('groups/*/graph_*.csv')]
    E.merge(c,'--jobs',2,'--fan-in',2)
    for g in manifest(a)['groups']:
        for n in names[1:]:
            pa,pc=a/'groups'/g['name']/n,c/'groups'/g['name']/n
            assert pa.exists()==pc.exists()and(not pa.exists()or pa.read_bytes()==pc.read_bytes())
    e=td/'m_conc';shutil.copytree(b,e);[p.unlink()for p in e.glob('groups/*/merged.json')];[p.unlink()for p in e.glob('groups/*/graph_*.csv')]
    procs=[subprocess.Popen([sys.executable,'-B',str(E.pkg/'tools/production.py'),'merge',str(e),'--jobs','1','--scratch',str(E.scr),'--group','a_power_L6'],
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=c8pkg.env())for _ in range(6)]
    outs=[p.communicate()for p in procs];assert all(p.returncode==0 for p in procs),[o[1][-300:]for o in outs]
    assert any('identical merged.json published concurrently'in o[0]or 'already merged'in o[0]for o in outs)
    md=e/'groups/a_power_L6/merged.json';doc=json.loads(md.read_text());doc['batches'][0][0]+=1;md.unlink();md.write_text(json.dumps(doc))
    must(E.t('production.py','merge',e,'--group','a_power_L6','--scratch',E.scr,check=False),1,'payload checksum')   # an edited merged.json
    # The publish collision, forced (A-ORC-6 Mac part): a concurrent publisher's merged.json lands between this merge's
    # tables and its own publish (the scratch package's production.dump_point hooked in a driver process, --jobs 1
    # --parse-jobs 1, so phase 2 runs in that process). Identical content: the collision branch runs and keeps the file;
    # different content (another worker output, with a valid payload checksum): refused.
    drv=td/'race_driver.py';drv.write_text(RACE_DRIVER);coll={}
    for variant in ('identical','different'):
        f=td/f'm_coll_{variant}';shutil.copytree(b,f);[x.unlink()for x in f.glob('groups/*/merged.json')];[x.unlink()for x in f.glob('groups/*/graph_*.csv')]
        cp=subprocess.run([sys.executable,'-B',str(drv),str(E.pkg/'tools'),str(f),'a_power_L6',str(E.scr),variant],capture_output=True,text=True,env=c8pkg.env())
        assert cp.returncode==0,cp.stderr[-1500:];coll[variant]=json.loads(cp.stdout.splitlines()[-1])
    x=coll['identical']
    assert x['raced']and x['error']is None and 'a_power_L6: identical merged.json published concurrently; kept'in x['stdout'],x
    assert json.loads((td/'m_coll_identical/groups/a_power_L6/merged.json').read_text())['payload_sha256']==json.loads((a/'groups/a_power_L6/merged.json').read_text())['payload_sha256']
    x=coll['different']
    assert x['raced']and x['error']and 'a different merged.json was published concurrently'in x['error']and 'identical merged.json'not in x['stdout'],x
    # the signal-safe launch boundary: SIGTERM during run stops the native child, removes the runtime, keeps committed blocks, exits 143
    s=td/'sig';E.plan(s,'--pilot','--test-only','--points',1024,'--replicates',2,'--threads',2,'--plan-role','validation','--bootstrap-chunk',256,'--shards',1)
    j=manifest(s)['jobs'][0];rt=td/'sigscr';rt.mkdir()
    p=subprocess.Popen([sys.executable,'-B',str(E.pkg/'tools/production.py'),'run',str(s),'--index',str(j['id']),'--scratch',str(rt)],env=c8pkg.env(C8_FAKE_SLEEP='5'),
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    t0=time.time()
    while time.time()-t0<30 and not list(rt.glob('c8d3_runtime_*/block_*')):time.sleep(0.05)
    time.sleep(0.3);p.send_signal(signal.SIGTERM);o,err=p.communicate(timeout=60)
    assert p.returncode==143 and not list(rt.glob('c8d3_runtime_*')),(p.returncode,err[-300:])
    # records carry host and executable identity; time policy; the campaign path with '#', '%' and '?' merged above
    ck=json.loads(next((a/'groups/a_free_L3/checkpoints').glob('*.json')).read_text())
    assert ck['runtime']['executable_sha256']==manifest(a)['executable_sha256']and ck['runtime']['fingerprint']['host']
    import lanes
    assert lanes.parse_timeleft('UNLIMITED')==math.inf and lanes.parse_timeleft('1-02:03:04')==93784 and lanes.parse_timeleft('INVALID')is None
    ok('A-ORC-6 (Mac)/A-ORC-7: merge --jobs 24 --parse-jobs 16 equals the serial merge byte for byte (graph_replicates, graph_tails, '
       'graph_promotions, graph_costs and graph_prefixes of the nested graph; merged.json up to its manifest hash), so does --fan-in 2; six concurrent '
       'merges all succeed and an edited merged.json refuses (payload checksum); a forced publish collision (a racing publisher hooked in front of '
       'dump_point) runs the collision branch and keeps an identical merged.json, and refuses a different one ("a different merged.json was '
       'published concurrently"); SIGTERM during run stops the native child, '
       'removes the job-private runtime and exits 143; checkpoints carry host and executable identity; a campaign path with #, % and ? works')

def test_zero_task_groups(E:Env,td:Path):
    """A-ORC-7's zero-task group case: a test-only plan without L8 inputs (C8_ALLOW_NO_L8=1) keeps all 24 groups, the
    L8 groups with zero tasks and no index; run, merge (zero batches) and the test-only assemble complete."""
    Z=Env(td,'nol8',l8=False);d=td/'zt'
    Z.plan(d,'--pilot','--test-only','--points',512,'--replicates',2,'--plan-role','validation','--bootstrap-chunk',512,'--shards',1,'--threads',1,job=False,C8_ALLOW_NO_L8='1')
    m=manifest(d);assert len(m['groups'])==24 and all(config(d,f'{c}_{s}_L8')['tasks']==0 for c in 'ab'for s in ('free','power'))
    assert not [j for j in m['jobs']if j['group'].endswith('_L8')]
    Z.run_all(d,threads=1);Z.merge(d)
    z=json.loads((d/'groups/a_power_L8/merged.json').read_text());assert z['batches']==[[0.,0.],[0.,0.]]and z['complete']
    Z.t('assemble.py',d,'--bootstrap',0);r=json.loads((d/'C8_test_result.json').read_text());assert r['label']=='test'and r['C8_full']is None
    ok('A-ORC-7 zero-task groups: without L8 inputs a test-only plan keeps all 24 groups, the four L8 groups with zero tasks and no index; run, '
       'merge (zero batches, complete) and the test-only assemble complete')

# =====================================================================================================================
def test_seed_logs_two_sites(E:Env,td:Path):
    """Amendment A1 (two sites, two seed logs; HD6): add and merge refuse a missing log; on symmetry (C8_SITE=symmetry)
    init refuses without --from, and --from refuses a copy that is not a seed log or lacks a seed of the package mirror,
    and takes a byte copy of the mirror; merge appends the other site's new entries verbatim and in order, once, under
    the lock; a non-test plan on symmetry refuses a forbidden set that lacks a mirror seed (and a missing mirror), and
    passes with the mirror; a test-only plan and Expanse plans are unaffected."""
    pkg=E.pkg;(pkg/'designs').mkdir(exist_ok=True);mir=pkg/'designs/forbidden_seeds.json';shutil.copy2(ROOT/'designs/forbidden_seeds.json',mir)
    root=td/'root';root.mkdir();S=dict(C8_SITE='symmetry',C8_ROOT=root);F=dict(C8_SITE='fake',C8_ROOT=root)
    sym=td/'sym_seeds.json';exp=td/'exp_seeds.json'
    must(tool(pkg,'seeds.py','init','--log',sym,check=False,**S),64,'starts as a copy');assert not sym.exists()
    (td/'notalog.json').write_text('{"seeds": []}');must(tool(pkg,'seeds.py','init','--log',sym,'--from',td/'notalog.json',check=False,**S),64,'c8-d3-seeds-1')
    doc=json.loads(mir.read_text());short=td/'short.json';short.write_text(json.dumps({**doc,'seeds':doc['seeds'][:-1]},indent=1)+'\n')
    must(tool(pkg,'seeds.py','init','--log',sym,'--from',short,check=False,**S),64,'lacks 1 seed(s) of the package mirror');assert not sym.exists()
    must(tool(pkg,'seeds.py','init','--log',sym,'--from',mir,check=False,**S),0,'"state": "created"');assert sym.read_bytes()==mir.read_bytes()
    must(tool(pkg,'seeds.py','init','--log',sym,'--from',mir,check=False,**S),64,'exists')
    # Expanse's log moves on: two new entries; merge folds them into the symmetry log once, verbatim and in order
    shutil.copy2(mir,exp);tool(pkg,'seeds.py','add','--seed',31337,'--label','expanse later 1','--log',exp,**F);tool(pkg,'seeds.py','add','--seed',31338,'--label','expanse later 2','--log',exp,**F)
    tool(pkg,'seeds.py','add','--seed',4242424,'--label','symmetry own','--log',sym,**F)
    r=json.loads(must(tool(pkg,'seeds.py','merge',exp,'--log',sym,check=False,**F),0).stdout);assert r['added']==2,r
    got=json.loads(sym.read_text())['seeds'];want=json.loads(exp.read_text())['seeds']
    assert got[:len(doc['seeds'])]==doc['seeds']and got[-2:]==want[-2:]and got[-3]['seed']==4242424,got[-3:]
    r=json.loads(must(tool(pkg,'seeds.py','merge',exp,'--log',sym,check=False,**F),0).stdout);assert r['added']==0
    r=json.loads(must(tool(pkg,'seeds.py','merge',sym,'--log',exp,check=False,**F),0).stdout);assert r['added']==1   # the other direction
    assert {(e['seed'],e['source'])for e in json.loads(sym.read_text())['seeds']}=={(e['seed'],e['source'])for e in json.loads(exp.read_text())['seeds']}
    must(tool(pkg,'seeds.py','merge',exp,'--log',td/'missing.json',check=False,**F),64,'does not exist')
    must(tool(pkg,'seeds.py','merge',td/'notalog.json','--log',sym,check=False,**F),64,'not a c8-d3-seeds-1')
    # a non-test plan on symmetry: the forbidden set must cover the mirror. The plans run under c8pkg.INJECT's validator
    # (R2-S1-02); without it (inject=False; the environment's seam is the fakes' only) the same plan is test-only and skips
    # the mirror check
    model=E.model();base=('--pilot','--replicates',2,'--threads',2,'--cost-model',model)
    empty=td/'empty_seeds.json';empty.write_text(json.dumps({'schema':'c8-d3-seeds-1','seeds':[]})+'\n')   # a log without the mirror's seeds
    cp=E.plan(td/'p_gap0',*base,'--forbid-seeds-from',empty,check=False,C8_SITE='symmetry',seed=SEED+9,inject=False)
    assert 'test-only: synthetic'in cp.stderr and 'package mirror'not in cp.stderr,(cp.returncode,cp.stderr[-800:])
    must(E.plan(td/'p_gap',*base,'--forbid-seeds-from',empty,check=False,C8_SITE='symmetry'),1,'lack','seed(s) of the package mirror');assert not (td/'p_gap').exists()
    must(E.plan(td/'p_test','--pilot','--points',2048,'--test-graphs','all','--replicates',2,'--threads',2,'--cost-model',model,check=False,C8_SITE='symmetry',seed=SEED+10),0)   # test-only: no check
    must(E.plan(td/'p_exp',*base,'--forbid-seeds-from',empty,check=False,seed=SEED+11),0)   # off symmetry (the fakes emulate Expanse): unchanged
    # past the mirror check, a non-test plan reserves its seed (S2-002) under symmetry's session lock, whose NFS-home mount
    # check the Mac cannot pass (69): nothing is published, and no mirror refusal
    cp=must(E.plan(td/'p_ok',*base,'--forbid-seeds-from',sym,check=False,C8_SITE='symmetry',seed=SEED+12),69,'mount check')
    assert 'package mirror'not in cp.stderr and not (td/'p_ok').exists(),cp.stderr[-600:]
    mir.unlink()
    try:must(E.plan(td/'p_nomir',*base,'--forbid-seeds-from',sym,check=False,C8_SITE='symmetry',seed=SEED+13),1,'package mirror','missing')
    finally:shutil.copy2(ROOT/'designs/forbidden_seeds.json',mir)
    ok('A1 seed logs: add and merge refuse a missing log; on symmetry init needs --from a seed log holding every mirror seed (byte copy); merge folds '
       'the other site\'s new entries in once, verbatim and in order, both directions; a non-test plan on symmetry refuses a forbidden set that '
       'lacks a mirror seed or a missing mirror and passes the mirror check with the mirror (then stops at symmetry\'s seed-reservation lock, '
       'which the Mac cannot take); test-only and Expanse plans unaffected')

TESTS=['seeds_and_nets','seed_logs_two_sites','allocation','selection_files','chunking_synthetic','roles','first_sweep_bootstrap','blocks_plan_level','atomic_and_guards',
       'per_index_and_spies','merge_and_safety','zero_task_groups','lanes','lanes_submission','done_markers','recovery_merge','arrays_and_recovery']

def run(only=None,keep=False)->dict:
    td=Path(tempfile.mkdtemp(prefix='c8d3_uo_'));t0=time.time()
    try:
        E=Env(td,'pkg')
        import lanes_tests
        lanes_tests.ok=ok   # one RESULTS list (lanes_tests imported this file as a module of its own)
        for name in TESTS:
            if only and name not in only:continue
            fn=globals().get(f'test_{name}')or getattr(lanes_tests,f'test_{name}')
            sub=td/name;sub.mkdir();fn(E,sub)
        return {'status':'passed','tests':len(RESULTS),'seconds':round(time.time()-t0,1),'results':RESULTS}
    finally:
        if keep:print('kept',td)
        else:shutil.rmtree(td,ignore_errors=True)

# Stage 6, group A (tests/lanes_tests.py): S2-001, S2-002, S2-005, F7
TESTS+=['vendor_pin','seed_reservations','reserve_required','plan_staging','lane_sigterm']

if __name__=='__main__':
    only=set(sys.argv[sys.argv.index('--only')+1].split(','))if '--only'in sys.argv else None
    print(json.dumps(run(only,'--keep'in sys.argv),indent=1,default=str))
