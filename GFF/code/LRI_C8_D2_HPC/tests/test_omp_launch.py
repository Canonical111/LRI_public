#!/usr/bin/env python3
"""R1, R2 (Stage-6 residuals after fix round 2, 2026-10-06): the test harnesses launch their native programs in the
controlled OpenMP environment (tools/common.py omp_child_env), so an inherited OMP_THREAD_LIMIT=1, OMP_DYNAMIC=true or
any other OMP_*, GOMP_*, KMP_* control cannot run a multi-threaded check serially while its record says otherwise.
Mac-runnable: a Python stand-in for the worker (it logs the OpenMP controls it receives and the team a libgomp
runtime would give it) and a simulated /proc/<pid>/task (common.proc_task_count reads the stand-in's team).

  invariance       tests/validate.py invariance (A-RPL-6: 23-point chunks, layouts 0/1/2, 1 against 4 threads) with
                   OMP_THREAD_LIMIT=1, OMP_DYNAMIC=true, OMP_NUM_THREADS=64, GOMP_SPINCOUNT=0 and KMP_AFFINITY=none
                   inherited: every run gets exactly omp_child_env(threads)'s controls (OMP_NUM_THREADS = its own thread
                   count, OMP_DYNAMIC=FALSE, close binding on cores, nothing inherited); each run's team is observed
                   (common.TeamWatch) and each record carries teams_observed and team_sizes_verified
  invariance_team  a runtime that ignores the request (a team of 1 at 4 threads) fails the check, and so does a run
                   whose team cannot be observed (no /proc, e.g. macOS), instead of a record with thread_identical
  run_env          validate.run and fresh_output (every other native launch of validate.py, and forced_tiers.py's and
                   numerics_flags.py's precision tools, which use validate.run): harness_env, i.e. the controlled
                   environment with the requested OMP_NUM_THREADS (a native_cmd's own thread count by default) and no
                   binding (--jobs runs unpinned batches concurrently); forced_tiers.py and numerics_flags.py pass their
                   tools' thread count; validate.py's refusal runs (bad_inputs) and inspector runs (inspector_tempdir)
                   pass the controlled environment
  tools_env        tests/quad_differential.py run_json and tools/prepare_inputs.py inspect_pack: the controlled
                   environment with their thread count, unbound
  sanitize_env     tests/sanitize.py ENV (R2): omp_child_env(4) plus ASAN_OPTIONS and UBSAN_OPTIONS, nothing inherited
Usage: python3 -B tests/test_omp_launch.py [--output FILE] [--only NAME,...]"""
from __future__ import annotations
import argparse,ast,importlib,json,os,subprocess,sys,tempfile,textwrap
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];PY=sys.executable
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests')]
import common  # noqa: E402
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,'status':'passed',**info});print('PASS',name,flush=True)

OMP_PREFIXES=('OMP_','GOMP_','KMP_')
DIRTY={'OMP_THREAD_LIMIT':'1','OMP_DYNAMIC':'true','OMP_NUM_THREADS':'64','GOMP_SPINCOUNT':'0','KMP_AFFINITY':'none'}
def omp_of(env:dict)->dict:return {k:v for k,v in env.items()if k.startswith(OMP_PREFIXES)}
def bound(threads:int)->dict:return {'OMP_NUM_THREADS':str(threads),'OMP_DYNAMIC':'FALSE','OMP_PROC_BIND':'close','OMP_PLACES':'cores'}
def unbound(threads:int)->dict:return {'OMP_NUM_THREADS':str(threads),'OMP_DYNAMIC':'FALSE'}

# The worker stand-in. `--env`: print the OpenMP controls it received (and exit 0). Otherwise the native command line
# (root gamma net tasks out seed layout rate threads mode -): it logs its controls and the team libgomp would give
# num_threads(threads) under them (OMP_THREAD_LIMIT caps it; OMP_DYNAMIC=true may shrink it: the stand-in takes 1;
# FAKE_IGNORE_REQUEST: a runtime that ignores the request), publishes that team for the simulated /proc, and writes
# rows whose values, tails, argmax and max_abs merge exactly over chunks (each point i of graph g, replicate r has
# t = 1000 g + 100 r + i + 1, distinct and increasing; every field a worker row has, as validate.chunk_merge compares
# them: Stage-6 fix round 4).
FAKE=r'''import json,os,sys,time
a=sys.argv[1:]
omp={k:v for k,v in os.environ.items()if k.startswith(('OMP_','GOMP_','KMP_'))}
if a[:1]==['--env']:print(json.dumps(omp));sys.exit(0)
root,gamma,net,tasks,out,seed,layout,rate,threads,mode,dash=a
threads=int(threads);team=threads
if os.environ.get('FAKE_IGNORE_REQUEST'):team=1
if omp.get('OMP_THREAD_LIMIT'):team=min(team,int(omp['OMP_THREAD_LIMIT']))
if omp.get('OMP_DYNAMIC','').lower()in('true','1'):team=1
with open(os.environ['FAKE_LOG'],'a')as f:f.write(json.dumps({'threads':threads,'omp':omp,'team':team})+'\n')
open(os.path.join(os.environ['FAKE_TEAM_DIR'],str(os.getpid())),'w').write(str(team))
lines=open(tasks).read().split('\n');rows=[]
for line in lines[1:]:
    if not line.strip():continue
    uid,rep,g,b,e,n=map(int,line.split())
    t=[1000*g+100*rep+i+1 for i in range(b,e)]
    rows.append({'uid':uid,'rep':rep,'graph':g,'begin':b,'end':e,'total':n,'values':[str(sum(t)),str(2*sum(t))],
                 'tail_top':[str(v)for v in sorted(t,reverse=True)[:16]],'tail_sum':str(sum(t)),'tail_argmax':e-1,'quad':0,'mp':0,'max_abs':str(3*max(t)),'seconds':0.01})
time.sleep(float(os.environ.get('FAKE_SLEEP','0.25')))
json.dump({'rows':rows},open(out,'w'))
'''

class World:
    """A package root in td for validate.py: bin/c8d2_{decimal,gmp} (the stand-in), empty L8 packs (invariance only
    checks that they exist), the team directory and the launch log."""
    def __init__(self,td:Path):
        self.td=td.resolve();(self.td/'bin').mkdir();(self.td/'inputs/packs').mkdir(parents=True);self.teams=self.td/'teams';self.teams.mkdir()
        self.log=self.td/'launches.jsonl';self.log.write_text('')
        for b in ('decimal','gmp'):
            w=self.td/'bin'/f'c8d2_{b}';w.write_text(f'#!{PY}\n'+FAKE);w.chmod(0o755)
        for s in ('free','power'):(self.td/f'inputs/packs/{s}_L8.pack').write_bytes(b'')
        self.worker=self.td/'bin/c8d2_decimal'
    def env(self,**extra)->dict:return {**DIRTY,'FAKE_LOG':str(self.log),'FAKE_TEAM_DIR':str(self.teams),**extra}
    def launches(self)->list:return [json.loads(x)for x in self.log.read_text().splitlines()]
    def task_count(self,pid:int):
        """the simulated /proc/<pid>/task: the stand-in's published team, 1 before it is published"""
        try:return int((self.teams/str(pid)).read_text())
        except (OSError,ValueError):return 1

def validate_module():
    import validate as V
    return importlib.reload(V)

def run_invariance(W:World,observable:bool=True,**extra):
    """validate.invariance on the stand-in (one backend), the simulated /proc when observable."""
    V=validate_module()
    with mock.patch.dict(os.environ,W.env(**extra)),mock.patch.object(V,'ROOT',W.td),\
         mock.patch.object(V,'by_cost',lambda sector,L:[11,12,13]),\
         mock.patch.object(V,'stage',lambda root,sector,L,ids:(root.mkdir(parents=True,exist_ok=True),root)[1]),\
         mock.patch.object(V,'make_net',lambda path,*a,**k:Path(path).write_bytes(b'net')),\
         mock.patch.object(common,'team_observable',lambda:observable),mock.patch.object(common,'proc_task_count',W.task_count):
        work=W.td/f'work{len(list(W.td.glob("work*")))}';work.mkdir()
        return V.invariance(work,['decimal'])

def test_invariance():
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td));recs=run_invariance(W);seen=W.launches()
        assert len(recs)==12 and len(seen)==36,(len(recs),len(seen))
        bad=[x for x in seen if x['omp']!=bound(x['threads'])]
        assert not bad,f'runs with an uncontrolled OpenMP environment (inherited {DIRTY}): {bad[:3]}'
        assert sorted(x['threads']for x in seen)==[1]*24+[4]*12 and all(x['team']==x['threads']for x in seen),seen[:4]
        for r in recs:
            assert r['thread_identical']is True and r.get('team_sizes_verified')is True,r
            assert r.get('teams_observed')=={'whole_1':1,'chunks_4':4,'chunks_1':1},r
            assert 'omp_child_env'in r.get('omp_environment',''),r
    ok('invariance_runs_in_the_controlled_environment_with_observed_teams',runs=len(seen),records=len(recs))

def test_invariance_team():
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td))
        for label,kw,needle in (('a runtime that ignores the request',dict(extra={'FAKE_IGNORE_REQUEST':'1'}),'4 OpenMP threads requested'),
                                ('no /proc: the team cannot be observed',dict(observable=False),'cannot be observed')):
            try:recs=run_invariance(W,observable=kw.get('observable',True),**kw.get('extra',{}))
            except AssertionError as e:
                assert needle in str(e),(label,str(e))
                continue
            raise AssertionError(f'{label}: invariance passed ({len(recs)} records, e.g. {recs[0]})')
    ok('invariance_fails_on_a_smaller_or_unobservable_team')

def test_run_env():
    V=validate_module()
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td))
        with mock.patch.dict(os.environ,W.env()):
            got=json.loads(V.run([W.worker,'--env'],threads=3).stdout)
            assert got==unbound(3),got
            assert json.loads(V.run([W.worker,'--env']).stdout)==unbound(1)
            tasks=W.td/'tasks';tasks.write_text('C8D2TASKS1 8 3 1\n0 0 5 0 4 4\n');out=W.td/'out.json'
            cmd=V.native_cmd(W.worker,W.td,W.td/'gamma',W.td/'net',tasks,out,threads=6)
            assert V.native_threads(cmd)==6 and V.native_threads([W.worker,'--env'])==1
            d=V.fresh_output(cmd,out);assert len(d['rows'])==1
            last=W.launches()[-1];assert last['omp']==unbound(6)and last['team']==6,last
    # the precision tools that launch through validate.run pass their thread count; validate's direct launches pass env
    def calls(path:Path,pred):
        tree=ast.parse(path.read_text());return [n for n in ast.walk(tree)if isinstance(n,ast.Call)and pred(n.func)]
    for f,pred,what in ((ROOT/'tests/forced_tiers.py',lambda fn:isinstance(fn,ast.Name)and fn.id=='run','run'),
                        (ROOT/'tests/numerics_flags.py',lambda fn:isinstance(fn,ast.Attribute)and fn.attr=='run'and isinstance(fn.value,ast.Name)and fn.value.id=='V','V.run')):
        cs=calls(f,pred);assert cs,(f,what)
        miss=[c.lineno for c in cs if 'threads'not in{k.arg for k in c.keywords}]
        assert not miss,f'{f.name}: {what}(...) without threads= at lines {miss}'
    tree=ast.parse((ROOT/'tests/validate.py').read_text())
    for fn in [n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in('bad_inputs','inspector_tempdir')]:
        launches=[c for c in ast.walk(fn)if isinstance(c,ast.Call)and isinstance(c.func,ast.Attribute)and c.func.attr in('run','Popen')
                  and isinstance(c.func.value,ast.Name)and c.func.value.id=='subprocess']
        miss=[c.lineno for c in launches if 'env'not in{k.arg for k in c.keywords}]
        assert launches and not miss,f'validate.py {fn.name}: subprocess launches without env= at lines {miss}'
    ok('validate_run_and_the_precision_tools_use_the_controlled_environment')

def test_tools_env():
    import prepare_inputs as PI
    QD=importlib.import_module('quad_differential')
    with tempfile.TemporaryDirectory()as td:
        W=World(Path(td))
        with mock.patch.dict(os.environ,W.env()):
            d,_,_=QD.run_json([W.worker,'--env'],timeout=60,threads=5);assert d==unbound(5),d
            # the inspector stand-in: the rows it is asked for, with the header's sizes; it logs its controls
            insp=W.td/'inspect';insp.write_text(f'#!{PY}\n'+textwrap.dedent('''\
                import json,os,sys
                omp={k:v for k,v in os.environ.items()if k.startswith(('OMP_','GOMP_','KMP_'))}
                open(os.environ['FAKE_LOG'],'a').write(json.dumps({'threads':int(sys.argv[3]),'omp':omp,'team':None})+'\\n')
                for line in open(sys.argv[2]):
                    g,L,off,n=map(int,line.split())
                    print(json.dumps({'id':g,'L':L,'masks':2,'terms':3,'products':1,'segments':1,'addends':1,'numerators':1,'kernel_bytes':8}))
                '''));insp.chmod(0o755)
            pack=W.td/'p.pack';pack.write_bytes(b'x')
            rows=[{'id':7,'offset':0,'length':1,'monomials':2,'terms':3}]
            PI.inspect_pack(insp,pack,5,rows,2)
            last=W.launches()[-1];assert last['omp']==unbound(2),last
            assert rows[0]['kernel_bytes']==8
    ok('quad_differential_and_prepare_inputs_use_the_controlled_environment')

def test_sanitize_env():
    code='import json,sys;sys.path[:0]=[sys.argv[1],sys.argv[2]];import sanitize;print(json.dumps(sanitize.ENV))'
    cp=subprocess.run([PY,'-B','-c',code,str(ROOT/'tools'),str(ROOT/'tests')],capture_output=True,text=True,env={**os.environ,**DIRTY},timeout=120)
    assert cp.returncode==0,cp.stderr[-2000:]
    env=json.loads(cp.stdout)
    assert omp_of(env)==bound(4),omp_of(env)
    assert env['ASAN_OPTIONS']=='detect_leaks=0:abort_on_error=1'and env['UBSAN_OPTIONS']=='halt_on_error=1:print_stacktrace=1',env
    assert {k:v for k,v in env.items()if not k.startswith(OMP_PREFIXES)and k not in('ASAN_OPTIONS','UBSAN_OPTIONS')}==\
           {k:v for k,v in common.omp_child_env(4,{**os.environ}).items()if not k.startswith(OMP_PREFIXES)}
    ok('sanitize_env_is_omp_child_env_4_plus_the_sanitizer_options')

TESTS=[('invariance',test_invariance),('invariance_team',test_invariance_team),('run_env',test_run_env),('tools_env',test_tools_env),
       ('sanitize_env',test_sanitize_env)]

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path);ap.add_argument('--only')
    a=ap.parse_args();names=[n for n,_ in TESTS]
    sel=names if a.only is None else[s.strip()for s in a.only.split(',')if s.strip()]
    bad=[s for s in sel if s not in names]
    if not sel or bad:ap.error(f'--only: unknown test(s) {bad}; the tests are {", ".join(names)}'if bad else'--only: no test named')
    failed=[]
    for n,fn in TESTS:
        if n not in sel:continue
        try:fn()
        except Exception as e:
            import traceback;traceback.print_exc();failed.append(n);RESULTS.append({'test':n,'status':'failed','error':f'{type(e).__name__}: {e}'[:2000]})
    rec={'passed':not failed,'tests':len(RESULTS),'failed':failed,'requested':sel,'results':RESULTS}
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps({k:rec[k]for k in ('passed','tests','failed')}));return 0 if not failed else 1

if __name__=='__main__':sys.exit(main())
