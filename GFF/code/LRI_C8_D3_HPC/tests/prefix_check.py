#!/usr/bin/env python3
"""A-DES-8 (a)-(d) on fakes (Mac): prefix outputs (R06). --real (A-DES-8 (e)) is the J-VAL-3 part with the real worker.

(a) Normalization in closed form (the fake worker divides each point's contribution by the task total, as
    c7d3_integrate.cpp:56): a graph at 32,768 points with nest [4096] and the integrand const: the prefix jets equal the
    full-stream jets (w = (1e-4, 2e-4) at L8), not 1/8 of them; step:4096: prefix w, full stream w/8; nest
    [4096, 8192, 16384] under step:4096: w, w/2, w/4 and w/8 at 32,768.
(b) Prefix tails with ramp (|t| = point index + 1): at 4,096 the top 16 are 4,096..4,081, tail_sum 4,096 x 4,097/2 and
    argmax 4,095; the full stream 32,768..32,753, 32,768 x 32,769/2 and 32,767; a pilot_report run monkeypatched to read
    full-stream tails at n = 4,096 fails the length-rule assert.
(c) tools/prefix_verify.py (its own parser, Fraction sums, its own top-16 union; no import from production.py) equals
    every graph_prefixes.csv row on fake campaigns chunked at 256, 1,024 and 4,096 points; the CSV is byte-identical
    for merge --jobs 1, --jobs 8 and --fan-in 2; a tampered row (one jet divided by 8; one top-16 entry from the full
    stream) makes prefix_verify and `pilot_report.py subset-check` fail. S3-012: the expected rows come from the pinned
    configuration: a group whose nested graphs' checkpoints and graph_prefixes.csv are both gone, a config.json that
    differs from the manifest's pin (replicates 3), a missing replicate's checkpoint rows and an overlapping (duplicated)
    task each fail prefix_verify (none passes with zero rows checked).
(d) Statistics on synthetic nested data: iid per-point values give V(32,768)/V(4,096) = 1 and alpha_hat = 1/2 within
    their Monte Carlo errors; replicate values built with alpha = 0.534 give alpha_hat = 0.534 +- 0.01; the share fall,
    the variance ratio and the (excess) Hill index equal tail_calib.py's functions (stats and stats4, extracted from
    reference/c8d3_recon/tail_calib.py by its AST, without running the module) on the same arrays.
(e) --real (J-VAL-3, Stage 3b): the real worker on two L8 graphs, the 32,768-point nested prefix against a 4,096-point
    campaign of the same seed (see real()).
Usage: python3 -B tests/prefix_check.py [--keep] [--output FILE] | --real [--threads N] [--output FILE]"""
from __future__ import annotations
import argparse,ast,hashlib,json,math,shutil,sys,tempfile
from fractions import Fraction
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'tools')]
import c8pkg  # noqa: E402
from c8pkg import manifest,config  # noqa: E402
from unit_orchestration import Env,selection,must  # noqa: E402
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,**info});print('PASS',name,flush=True)
W=(1e-4,2e-4)

def read_rows(path:Path,key=('replicate','graph','points'))->dict:
    lines=path.read_text().splitlines();head=lines[0].split(',');out={}
    for l in lines[1:]:
        d=dict(zip(head,l.split(',')));out[tuple(int(d[k])for k in key if k in d)]=d
    return out

def plan_run_merge(E:Env,td:Path,name:str,groups:dict,task_s:float,integrand:str,*merge_args)->Path:
    inv=json.loads((E.pkg/'inputs/inventory.json').read_text());im=hashlib.sha256((E.pkg/'inputs/manifest.json').read_bytes()).hexdigest()
    f=td/f'sel_{name}.json';f.write_text(json.dumps(selection(inv,im,groups)));d=td/name
    E.plan(d,'--graphs',f,'--pilot','--replicates',2,'--threads',2,'--cost-model',E.model(),'--forbid-seeds-from',E.seeds,'--task-seconds',task_s)
    E.run_all(d,C8_FAKE_INTEGRAND=integrand);E.merge(d,*merge_args);return d

def part_a_b(E:Env,td:Path):
    groups={'free:8':[{'id':0,'points':32768,'nest':[4096],'label':'p1c'},{'id':1,'points':32768,'nest':[4096,8192,16384],'label':'p1c'}]}
    res={}
    for integ in ('const','step:4096','ramp'):
        d=plan_run_merge(E,td,f'a_{integ.replace(":","_")}',groups,1.0245,integ,'--jobs',2);res[integ]=d
        for c in 'ab':
            p=d/'groups'/f'{c}_free_L8';pre=read_rows(p/'graph_prefixes.csv');full=read_rows(p/'graph_replicates.csv',('replicate','graph'))
            tails=read_rows(p/'graph_tails.csv',('replicate','graph'))
            for rep in range(2):
                fj=[float(full[(rep,0)][f'jet_{i}'])for i in range(2)]
                if integ=='const':
                    pj=[float(pre[(rep,0,4096)][f'jet_{i}'])for i in range(2)]
                    assert all(abs(x-w)<=1e-12*w for x,w in zip(pj,W))and all(abs(x-w)<=1e-12*w for x,w in zip(fj,W)),(pj,fj)
                elif integ=='step:4096':
                    pj=[float(pre[(rep,0,4096)][f'jet_{i}'])for i in range(2)]
                    assert all(abs(x-w)<=1e-12*w for x,w in zip(pj,W))and all(abs(x-w/8)<=1e-12*w for x,w in zip(fj,W)),(pj,fj)
                    for P,fac in ((4096,1),(8192,2),(16384,4)):
                        q=[float(pre[(rep,1,P)][f'jet_{i}'])for i in range(2)];assert all(abs(x-w/fac)<=1e-12*w for x,w in zip(q,W)),(P,q)
                    f1=[float(full[(rep,1)][f'jet_{i}'])for i in range(2)];assert all(abs(x-w/8)<=1e-12*w for x,w in zip(f1,W))
                else:
                    r=pre[(rep,0,4096)];top=[float(r[f'tail_top_{i+1}'])for i in range(16)]
                    assert top==[float(4096-i)for i in range(16)]and float(r['tail_sum'])==4096*4097/2 and int(r['tail_argmax'])==4095,(top[:3],r['tail_sum'],r['tail_argmax'])
                    t=tails[(rep,0)];top=[float(t[f'tail_top_{i+1}'])for i in range(16)]
                    assert top==[float(32768-i)for i in range(16)]and float(t['tail_sum'])==32768*32769/2 and int(t['tail_argmax'])==32767
    # the length rule: a Camp monkeypatched to read full-stream tails at n = 4096 fails the assert (in the scratch package's tools)
    code=f'''
import sys;sys.path.insert(0,{str(E.pkg/'tools')!r})
import pilot_report as pr
c=pr.Camp({str(res['ramp'])!r});good=pr.screen_graph(c,'free',0,4096)
assert good['campaigns']['a']['share_max']==4096/(4096*4097/2),good
orig=pr.Camp.at
pr.Camp.at=lambda self,key,g,n:orig(self,key,g,self.g[key]['total'][g])
for f in (lambda:pr.screen_graph(c,'free',0,4096),lambda:pr.confirm_graph(c,'free',0)):
    try:f();raise SystemExit('full-stream tails read at n = 4096 passed')
    except AssertionError as e:assert 'length rule' in str(e),e
print('length rule enforced')
'''
    import subprocess
    cp=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True,env=c8pkg.env());assert cp.returncode==0 and 'length rule enforced'in cp.stdout,cp.stderr[-800:]
    ok('A-DES-8 (a): const: the 4,096-prefix jets equal the full-stream jets (1e-4, 2e-4), not 1/8; step:4096: prefix w and full stream w/8; nest '
       '[4096, 8192, 16384]: w, w/2, w/4, w/8; (b) ramp: prefix top 16 = 4096..4081, tail_sum 4096*4097/2, argmax 4095; full stream 32768..32753, '
       '32768*32769/2, 32767; a pilot_report Camp monkeypatched to read full-stream tails at 4,096 points fails the length-rule assert (screen and confirm)')
    return res

def part_c(E:Env,td:Path):
    import prefix_verify as pv
    groups={'free:8':[{'id':0,'points':32768,'nest':[4096],'label':'p1c'},{'id':1,'points':8192,'nest':[1024,4096],'label':'p1c'},{'id':2,'points':4096,'label':'stratified'}],
            'power:8':[{'id':1,'points':32768,'nest':[4096],'label':'p1c'}]}
    rec={}
    for task_s,want in ((0.2565,256),(1.0245,1024),(4.0965,4096)):
        d=plan_run_merge(E,td,f'c_{want}',groups,task_s,'hash','--jobs',1)
        ch=config(d,'a_free_L8')['chunks'];assert int(ch['0'])==want and int(config(d,'b_power_L8')['chunks']['1'])==want,(want,ch)
        v=pv.verify(d);assert v['verified']and v['rows_checked']>0,v;rec[want]=v['rows_checked']
        if want==1024:
            base=d;copies={}
            for tag,args in (('jobs8',('--jobs',8)),('fan2',('--jobs',2,'--fan-in',2))):
                x=td/f'c_1024_{tag}';shutil.copytree(base,x);[p.unlink()for p in x.glob('groups/*/merged.json')];[p.unlink()for p in x.glob('groups/*/graph_*.csv')]
                E.merge(x,*args);copies[tag]=x
            for g in manifest(base)['groups']:
                a=(base/'groups'/g['name']/'graph_prefixes.csv').read_bytes()
                for x in copies.values():assert (x/'groups'/g['name']/'graph_prefixes.csv').read_bytes()==a,(g['name'],x)
            sc=E.t('pilot_report.py','subset-check',base,check=False);assert sc.returncode==0,sc.stderr[-500:]
            # tampered rows: one jet divided by 8; one top-16 entry from the full stream
            for tag,edit in (('jet8',lambda h,c:c.__setitem__(h.index('jet_0'),str(Fraction(c[h.index('jet_0')])/8 if '/'in c[h.index('jet_0')]else float(c[h.index('jet_0')])/8))),
                             ('top',lambda h,c:c.__setitem__(h.index('tail_top_1'),'32768.0'))):
                x=td/f'c_tamper_{tag}';shutil.copytree(base,x);p=x/'groups/a_free_L8/graph_prefixes.csv';lines=p.read_text().splitlines();h=lines[0].split(',')
                cells=lines[1].split(',');edit(h,cells);lines[1]=','.join(cells);p.unlink();p.write_text('\n'.join(lines)+'\n')
                vv=pv.verify(x);assert not vv['verified'],tag
                # subset-check reads the merged files under their recorded digests: the edit is caught
                cp=E.t('pilot_report.py','subset-check',x,check=False);assert cp.returncode!=0,(tag,cp.stdout[-300:])
            # S3-012: the expected keys come from the pinned configuration, never from the checkpoints that exist
            def s312(tag,edit,want):
                x=td/f'c_s312_{tag}';shutil.copytree(base,x);edit(x);vv=pv.verify(x,'a_free_L8')
                assert not vv['verified']and any(want in q for q in vv['problems']),(tag,vv);return vv
            def gone(x):
                for f in (x/'groups/a_free_L8/checkpoints').glob('*.json'):f.unlink()
                (x/'groups/a_free_L8/graph_prefixes.csv').unlink()
            def reps3(x):
                f=x/'groups/a_free_L8/config.json';c=json.loads(f.read_text());c['replicates']=3;f.write_text(json.dumps(c))
            def drop_rep(x):   # every checkpoint row of replicate 1 of nested graph 0 removed (payload digests recomputed)
                for f in (x/'groups/a_free_L8/checkpoints').glob('*.json'):
                    d=json.loads(f.read_text());d['native']['rows']=[r for r in d['native']['rows']if not (r['graph']==0 and r['rep']==1)];d['payload_sha256']=pv.canon_hash(d['native']);f.write_text(json.dumps(d))
            def dup(x):   # one task of nested graph 0 counted twice: a copy of its checkpoint under another name
                f=next(f for f in sorted((x/'groups/a_free_L8/checkpoints').glob('*.json'))if any(r['graph']==0 for r in json.loads(f.read_text())['native']['rows']))
                shutil.copy2(f,f.with_name('zz_copy.json'))
            s312('no_checkpoints',gone,'no checkpoint rows');s312('config',reps3,'pin');s312('replicate',drop_rep,'no checkpoint rows');s312('duplicate',dup,'overlap')
    ok('A-DES-8 (c): prefix_verify (own parser, Fraction sums, own top-16 union) equals every graph_prefixes.csv row on fake campaigns chunked at '
       '256, 1,024 and 4,096 points; graph_prefixes.csv is byte-identical for merge --jobs 1, --jobs 8 and --fan-in 2; subset-check passes the '
       'untouched campaign; a jet divided by 8 and a full-stream top-16 entry each fail prefix_verify and subset-check; S3-012: a group with its '
       'nested graphs\' checkpoints and graph_prefixes.csv gone, a config.json off its pin, a replicate without checkpoint rows and a duplicated task '
       'each fail prefix_verify (expected rows from the pinned configuration, contiguous non-overlapping coverage)',rows=rec)

def tail_calib_functions()->dict:
    """stats and stats4 of reference/c8d3_recon/tail_calib.py, compiled from the module's AST (the module itself runs
    the whole calibration at import)."""
    src=(ROOT/'reference/c8d3_recon/tail_calib.py').read_text();tree=ast.parse(src)
    fns=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in('stats','stats4')]
    assert {f.name for f in fns}=={'stats','stats4'}
    ns={'np':np,'N1':4096,'N2':32768,'K':16};exec(compile(ast.Module(body=fns,type_ignores=[]),'tail_calib.py','exec'),ns)
    return ns

def part_d():
    import pilot_report as pr
    rng=np.random.default_rng(8);G,R=400,8
    # iid per-point values: V(32768)/V(4096) = 1 and alpha_hat = 1/2; replicate means at alpha = 0.534
    V1=[];V2=[]
    for _ in range(G):
        # per replicate the 4,096-point mean and the 32,768-point mean (nested: the first 4,096 points are shared)
        S1=rng.normal(0,math.sqrt(4096),R);S2=rng.normal(0,math.sqrt(28672),R)   # sums of unit-variance iid points over [0,4096) and [4096,32768)
        y1=S1/4096;y2=(S1+S2)/32768
        V1.append(4096*float(np.var(y1,ddof=1)));V2.append(32768*float(np.var(y2,ddof=1)))
    ratio=sum(V2)/sum(V1);al=pr.alpha_hat(V2,V1)
    se=math.sqrt(2/(G*(R-1)))*math.sqrt(2)   # Var of ln(sum V2/sum V1) ~ 2 x 2/(G (R-1)) (two independent chi-square sums)
    assert abs(math.log(ratio))<=3*se and abs(al-.5)<=3*se/(2*math.log(8)),(ratio,al,se)
    alpha=0.534;V1=[];V2=[]
    for _ in range(4000):
        s1=4096**-alpha;s2=32768**-alpha
        V1.append(4096*float(np.var(rng.normal(0,s1,R),ddof=1)));V2.append(32768*float(np.var(rng.normal(0,s2,R),ddof=1)))
    a2=pr.alpha_hat(V2,V1);assert abs(a2-alpha)<=0.01,a2
    # share fall, variance ratio and (excess) Hill against tail_calib's stats/stats4 on the same arrays
    ns=tail_calib_functions();X=np.abs(rng.standard_t(3,size=(6,8,32768)))+1e-12
    ref=ns['stats'](X);ref4=ns['stats4'](X)
    for g in range(6):
        tl={}
        for n in (4096,32768):
            Y=X[g][:,:n];top=-np.sort(-np.partition(Y,n-16,axis=1)[:,n-16:],axis=1)
            tl[n]=[(float(Y[r].sum()),[float(v)for v in top[r]],n)for r in range(8)]
        s1,s2=pr.tail_stats(tl[4096]),pr.tail_stats(tl[32768])
        assert abs(s1['xi']-ref['hill1'][g])<=1e-12 and abs(s2['xi']-ref['hill2'][g])<=1e-12,(g,s1['xi'],ref['hill1'][g])
        assert abs(s1['share_max']-ref['smax1'][g])<=1e-12*ref['smax1'][g]
        assert abs(pr.share_fall(s1['shares'],s2['shares'])-ref['fall'][g])<=1e-10*ref['fall'][g]
        V1=4096*float(np.var(X[g][:,:4096].mean(1),ddof=1));V2=32768*float(np.var(X[g].mean(1),ddof=1));assert abs(V2/V1-ref['vrat'][g])<=1e-10*ref['vrat'][g]
        assert abs(s1['xi_excess']-ref4['e1'][g])<=1e-9 and abs(s2['xi_excess']-ref4['e2'][g])<=1e-9,(g,s2['xi_excess'],ref4['e2'][g])
    ok('A-DES-8 (d): iid nested values give V(32,768)/V(4,096) = 1 and alpha_hat = 1/2 within 3 SE (400 graphs x 8 replicates); alpha = 0.534 '
       'replicates give alpha_hat %.4f (within 0.01); Hill, largest share, share fall, variance ratio and the excess Hill index equal tail_calib.py\'s '
       'stats/stats4 on the same arrays'%a2)

def real(a)->dict:
    """A-DES-8 (e) (J-VAL-3, Stage 3b): the real worker (bin/c8d3_gmp of this package, the L8 packs present). One free and
    one power L8 graph (the median-cost kernel of each sector) x both campaigns x 2 replicates, planned test-only twice
    with the same fresh seed, basis and chunk options (--plan-role validation on the bootstrap basis, D.5; chunk 512,
    2 shards): once at 32,768 points with nest [4096], once at 4,096 points. Both campaigns are run in-process
    (production.py run --index) and merged (production.py merge; their role is pilot_subset). Then every
    graph_prefixes.csv row (replicate, graph, 4096) equals the 4,096-point campaign's graph_replicates.csv row to
    1e-19 relative in every jet (the same long double; the factor 8 is exact), and its tail_top, tail_sum and
    tail_argmax equal that campaign's graph_tails.csv row (string-identical). The seed is registered in $C8_SEEDS
    after both plans (seeds.py add on each campaign; HD6)."""
    import os,secrets,subprocess
    from decimal import Decimal as D
    seeds_log=os.environ.get('C8_SEEDS')
    if not seeds_log or not Path(seeds_log).exists():raise SystemExit('prefix_check --real needs C8_SEEDS (the forbidden-seed log; Expanse env.sh)')
    inv=json.loads((ROOT/'inputs/inventory.json').read_text());im=hashlib.sha256((ROOT/'inputs/manifest.json').read_bytes()).hexdigest()
    if '8' not in inv['free']or not (ROOT/'inputs/packs/free_L8.pack').exists():raise SystemExit('prefix_check --real needs the L8 packs (make link-l8 STORE=$C8_STORE)')
    picks={s:sorted(inv[s]['8'],key=lambda r:(r['cost'],r['id']))[len(inv[s]['8'])//2]['id']for s in('free','power')}
    base=Path(tempfile.mkdtemp(prefix='c8d3_prefix_real_',dir=os.environ.get('TMPDIR')));scratch=base/'scratch';scratch.mkdir()
    env={k:v for k,v in os.environ.items()if not k.startswith(('SLURM_','SBATCH_','SQUEUE_','C8_FAKE_'))and k!='C8_SITE'}
    env.update(OPENBLAS_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')   # test-only plans in node-local scratch, as tests/workflow.py
    def call(script,*args,e=env):
        cp=subprocess.run([sys.executable,'-B',str(ROOT/'tools'/script),*map(str,args)],capture_output=True,text=True,env=e)
        if cp.returncode:raise RuntimeError(f'{script} {args}: exit {cp.returncode}\n{cp.stderr[-3000:]}')
        return cp
    import production as prod
    forb=prod.read_seed_file(Path(seeds_log))
    while True:
        seed=secrets.randbits(63)
        if not prod.seed_refusal(seed,forb):break
    threads=a.threads or max(1,min(32,len(os.sched_getaffinity(0))if hasattr(os,'sched_getaffinity')else os.cpu_count()or 1))
    runs={}
    try:
        for name,P,nest in(('n32768',32768,[4096]),('n4096',4096,[])):
            groups={f'{s}:8':[{'id':g,'points':P,**({'nest':nest}if nest else{}),'label':'prefix_check'}]for s,g in picks.items()}
            f=base/f'sel_{name}.json';f.write_text(json.dumps(selection(inv,im,groups,role='prefix_check',seed=seed)));d=base/name
            call('production.py','plan',d,'--seed',seed,'--pilot','--graphs',f,'--replicates',2,'--test-only','--plan-role','validation','--bootstrap-chunk',512,
                 '--shards',2,'--threads',threads,'--backend','gmp','--mp-check','on','--scratch',scratch)
            runs[name]=d
        for d in runs.values():call('seeds.py','add',d,'--log',seeds_log,e=dict(os.environ))   # HD6: after both plans
        for d in runs.values():
            m=json.loads((d/'manifest.json').read_text())
            assert m['test_only']and m['plan_role']=='validation'and m['cost_basis']=='bootstrap'and m['campaign_role']=='pilot_subset'and m['seed']==seed,m.get('campaign_role')
            for j in m['jobs']:call('production.py','run',d,'--index',j['id'],'--threads',threads,'--scratch',scratch)
            call('production.py','merge',d,'--jobs',4,'--scratch',scratch)
        rows=0;worst=D(0);detail={}
        for c in'ab':
            for s,g in picks.items():
                grp=f'{c}_{s}_L8';pre=read_rows(runs['n32768']/'groups'/grp/'graph_prefixes.csv');full=read_rows(runs['n4096']/'groups'/grp/'graph_replicates.csv',('replicate','graph'))
                tails=read_rows(runs['n4096']/'groups'/grp/'graph_tails.csv',('replicate','graph'))
                for rep in range(2):
                    x=pre[(rep,g,4096)];y=full[(rep,g)];z=tails[(rep,g)]
                    jets=[k for k in y if k.startswith('jet_')];assert jets and all(k in x for k in jets),(grp,sorted(x))
                    for k in jets:
                        u,v=D(x[k]),D(y[k]);rel=abs(u-v)/abs(v)if v else abs(u)
                        worst=max(worst,rel)
                        if rel>D('1e-19'):raise AssertionError(f'A-DES-8 (e) {grp} rep {rep} graph {g} {k}: prefix {u} vs 4,096-point {v} (relative {rel:.3e} > 1e-19)')
                    tk=['tail_sum','tail_argmax']+[f'tail_top_{i}'for i in range(1,17)]
                    diff=[k for k in tk if x.get(k)!=z.get(k)]
                    if diff:raise AssertionError(f'A-DES-8 (e) {grp} rep {rep} graph {g}: tail fields {diff} differ ({[(x.get(k),z.get(k))for k in diff[:2]]})')
                    rows+=1
                detail[grp]=g
        ok('A-DES-8 (e) real worker: %d prefix rows (2 L8 graphs x 2 campaigns x 2 replicates) equal the 4,096-point rows: jets to %.2e relative (<= 1e-19), '
           'tail_top, tail_sum and tail_argmax identical'%(rows,worst),seed=seed,graphs=picks,groups=detail,max_relative=f'{worst:.3e}',threads=threads,
           manifests={k:hashlib.sha256((d/'manifest.json').read_bytes()).hexdigest()for k,d in runs.items()})
        return {'seed':seed,'rows':rows,'max_relative':f'{worst:.3e}'}
    finally:
        if a.keep:print('kept',base,file=sys.stderr)
        else:shutil.rmtree(base,ignore_errors=True)

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--keep',action='store_true');ap.add_argument('--output',type=Path);ap.add_argument('--real',action='store_true')
    ap.add_argument('--threads',type=int,help='--real: worker threads (default: the job\'s CPUs, at most 32)')
    a=ap.parse_args()
    if a.real:
        x=real(a);r={'status':'passed','part':'A-DES-8 (e) real worker','tests':len(RESULTS),'results':RESULTS,**x}
        if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=1)+'\n')
        print(json.dumps({k:v for k,v in r.items()if k!='results'}));return 0
    td=Path(tempfile.mkdtemp(prefix='c8d3_prefix_'))
    try:
        part_d();E=Env(td,'pkg');part_a_b(E,td);part_c(E,td)
    finally:
        if a.keep:print('kept',td,file=sys.stderr)
        else:shutil.rmtree(td,ignore_errors=True)
    r={'status':'passed','tests':len(RESULTS),'results':RESULTS}
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=1)+'\n')
    print(json.dumps({'status':'passed','tests':len(RESULTS)}));return 0
if __name__=='__main__':sys.exit(main())
