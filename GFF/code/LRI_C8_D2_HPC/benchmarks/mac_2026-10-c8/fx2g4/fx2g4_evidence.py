#!/usr/bin/env python3
"""Stage-6 fix round 2, group G4 (Y14, Y15): the before/after evidence, from a git checkout of the package.

1. Y14: every self-test probe of the current tests/ast_scan.py, counted by the current analyser and by the one at BASE
   (2ae3db7, the inspected tree): a probe the old analyser miscounts is a test that fails before the fix.
2. Y15: tests/unit_orchestration.py test_atomic_plan at BASE and the current one, each run in an isolated package copy
   (tests/pkgcopy.py, as the suite does) against tools/production.py and three mutants of its plan that only affect
   the `--test-graphs all` plan the test interrupts:
   - dies_before_staging: the plan raises before it creates its staging directory (S6E-R2-03's case: the BASE test
     polls for 120 s, signals a dead process and certifies atomicity with a different, smaller plan);
   - fails_in_write_phase: the plan creates its staging directory and a group, lives 1 s, then fails (and removes its
     staging): the BASE test kills it in the write phase but reruns a different plan, so a plan that can never
     succeed with the interrupted arguments passes;
   - hangs_before_staging: the plan sleeps (an hour) before its staging directory: the BASE test kills it after 120 s
     and passes with the smaller plan; the current test fails after 120 s and must kill the stopped child itself;
   - publishes_in_place (control): the plan builds in the target directory itself (no staging, no rename).
   The current test must pass the unmodified tool and fail every mutant; the BASE test passes the first three mutants.
   After every run no process of that run's plan may be left (`ps`; the child's command line names its directory).
Usage: python3 -B benchmarks/mac_2026-10-c8/fx2g4/fx2g4_evidence.py [--output FILE] [--skip-atomic]"""
from __future__ import annotations
import argparse,ast,importlib.util,json,os,subprocess,sys,tempfile,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BASE='2ae3db7'

def at_base(rel:str)->str:
    return subprocess.run(['git','-C',str(ROOT),'show',f'{BASE}:{rel}'],capture_output=True,text=True,check=True).stdout

def module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def probes(tmp:Path)->dict:
    old_path=tmp/'ast_scan_base.py';old_path.write_text(at_base('tests/ast_scan.py'))
    new,old=module(ROOT/'tests/ast_scan.py','ast_scan_now'),module(old_path,'ast_scan_base')
    fn=next(n for n in ast.walk(ast.parse((ROOT/'tests/ast_scan.py').read_text()))if isinstance(n,ast.FunctionDef)and n.name=='selftest')
    lit=next(n.value for n in ast.walk(fn)if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Name)and n.targets[0].id=='probes')
    table={}
    for name,(src,want) in ast.literal_eval(lit).items():
        t=ast.parse(src)
        table[name]=dict(expected=want,current=len(new.unreachable(t,name)+new.unbound(t,name)),base=len(old.unreachable(t,name)+old.unbound(t,name)))
    return dict(probes=table,current_failures=[k for k,v in table.items()if v['current']!=v['expected']],
                base_failures=[k for k,v in table.items()if v['base']!=v['expected']])

STAGE_LINE="    stage=out.with_name(out.name+f'.tmp.{os.environ.get(\"SLURM_JOB_ID\")or os.getpid()}')\n"
MKDIR_LINE="        stage.mkdir(parents=True);(stage/'groups').mkdir()\n"
MUTANTS={
    'unmodified':lambda s:s,
    'dies_before_staging':lambda s:s.replace(STAGE_LINE,"    if a.test_graphs=='all':raise ValueError('mutant: dies before staging')\n"+STAGE_LINE),
    'fails_in_write_phase':lambda s:s.replace(MKDIR_LINE,MKDIR_LINE+"        if a.test_graphs=='all':(stage/'groups'/'g0').mkdir();__import__('time').sleep(1.0);raise RuntimeError('mutant: fails in the write phase')\n"),
    'hangs_before_staging':lambda s:s.replace(STAGE_LINE,"    if a.test_graphs=='all':__import__('time').sleep(3600)\n"+STAGE_LINE),
    'publishes_in_place':lambda s:s.replace(STAGE_LINE,"    stage=out\n"),
}
BASE_PASSES=('dies_before_staging','fails_in_write_phase','hangs_before_staging')

def live_plans(d:Path)->list[str]:
    """Processes whose command line names the run's campaign directory (an exited, unreaped child shows no arguments)."""
    ps=subprocess.run(['ps','-axww','-o','pid=,command='],capture_output=True,text=True,check=True).stdout
    return [l.strip()for l in ps.splitlines()if str(d)+' 'in l+' ']

def atomic(tmp:Path)->dict:
    sys.path.insert(0,str(ROOT/'tests'))
    U=module(ROOT/'tests/unit_orchestration.py','unit_orchestration_now')
    base_src=at_base('tests/unit_orchestration.py')
    node=next(n for n in ast.parse(base_src).body if isinstance(n,ast.FunctionDef)and n.name=='test_atomic_plan')
    ns=dict(vars(U));exec(compile(ast.Module(body=[node],type_ignores=[]),f'{BASE}:tests/unit_orchestration.py','exec'),ns)
    tests={'base_test':ns['test_atomic_plan'],'current_test':U.test_atomic_plan}
    td=tmp/'orch';td.mkdir();pkg=U.make_package(td)
    c7cal=(ROOT/'reference/c7d2_hpc_a55958f/tools/calibration.json').read_bytes()
    if (pkg/'tools/calibration.json').read_bytes()!=c7cal:U.replace_bytes(pkg/'tools/calibration.json',c7cal)
    os.environ['C8_INPUTS']=str(pkg/'tests/fixtures/inputs_mini')
    src=(pkg/'tools/production.py').read_text();out={}
    for mname,mut in MUTANTS.items():
        code=mut(src)
        if mname!='unmodified'and code==src:raise SystemExit(f'tools/production.py changed: mutant {mname} no longer applies')
        U.replace_bytes(pkg/'tools/production.py',code.encode())  # a new inode: never written through a hard link
        M=U.load_modules(pkg)  # the in-process plan (the BASE test's rerun) sees the mutant too
        for tname,fn in tests.items():
            run_td=tmp/f'{mname}_{tname}';run_td.mkdir();E=U.Env(pkg,M,run_td);t0=time.monotonic()
            try:fn(E);res=dict(passed=True)
            except Exception as e:res=dict(passed=False,error=f'{type(e).__name__}: {str(e).splitlines()[0]if str(e)else""}'[:200],where=traceback.extract_tb(e.__traceback__)[-1].line)
            time.sleep(0.5);res['seconds']=round(time.monotonic()-t0-0.5,1);res['plans_left']=live_plans(run_td/'atomic')
            out[f'{mname} | {tname}']=res
            print(mname,tname,res,flush=True)
    U.replace_bytes(pkg/'tools/production.py',src.encode())
    return out

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path);ap.add_argument('--skip-atomic',action='store_true');a=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='c8d2_fx2g4_') as t:
        t=Path(t);rec=dict(schema='c8-d2-fx2g4-evidence-1',base=BASE,python=sys.version.split()[0],platform=sys.platform,ast_scan=probes(t))
        if not a.skip_atomic:rec['atomic_plan']=atomic(t)
    ok=not rec['ast_scan']['current_failures']and bool(rec['ast_scan']['base_failures'])
    if 'atomic_plan'in rec:
        r=rec['atomic_plan']
        ok=ok and r['unmodified | base_test']['passed']and r['unmodified | current_test']['passed']\
           and all(r[f'{m} | base_test']['passed']for m in BASE_PASSES)\
           and not any(v['passed']for k,v in r.items()if k.endswith('current_test')and not k.startswith('unmodified'))\
           and not any(v['plans_left']for k,v in r.items()if k.endswith('current_test'))
    rec['passed']=ok
    s=json.dumps(rec,indent=1)+'\n'
    if a.output:a.output.write_text(s)
    print(json.dumps({'passed':ok,'base_failures':len(rec['ast_scan']['base_failures']),'current_failures':rec['ast_scan']['current_failures']}))
    return 0 if ok else 1

if __name__=='__main__':sys.exit(main())
