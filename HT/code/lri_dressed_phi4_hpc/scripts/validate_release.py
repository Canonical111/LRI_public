#!/usr/bin/env python3
"""Staged release validation; the receipt is written only after EVERY stage has run.

Stages: pytest, saved-seed regression, --window none equality against a frozen
baseline tree (if --baseline is given), and a calibration smoke run. passed is the
conjunction of all stages. A failing run never overwrites an existing receipt.
"""
import argparse,subprocess,sys,time,os,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lri_dressed.io import atomic_json,envelope,source_fingerprint,release_fingerprint,runtime
p=argparse.ArgumentParser();p.add_argument('--output',default='validation/receipt.json');p.add_argument('--threads',type=int,default=4)
p.add_argument('--workdir',help='directory for stage artifacts (default: next to the receipt)')
p.add_argument('--baseline',required=True,help='frozen e637dfd source tree for --window none equality (pinned fingerprint)')
p.add_argument('--skip',nargs='*',default=[],choices=['saved_seeds','baseline','calibration','window_baseline','optimized_basis'],help='local/test use only; recorded in the receipt')
a=p.parse_args()
sys.path.insert(0,str(ROOT/'scripts'))
from baseline_equality import check_baseline
a.baseline=str(Path(a.baseline).resolve());baseline_sha=check_baseline(a.baseline)        # before any expensive stage
out=Path(a.output);work=Path(a.workdir or out.parent/'stages');work.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMBA_NUM_THREADS=str(max(4,a.threads)),
         PYTHONPATH=str(ROOT/'src')+os.pathsep+os.environ.get('PYTHONPATH',''))
stages=[]

def sha(path):
    try:return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:return None

def stage(name,cmd,artifact=None):
    if name in a.skip:stages.append({'stage':name,'skipped':True,'passed':False});return
    t=time.perf_counter();proc=subprocess.run(cmd,env=env,cwd=ROOT,capture_output=True,text=True)
    stages.append({'stage':name,'returncode':proc.returncode,'passed':proc.returncode==0,'seconds':time.perf_counter()-t,
        'stdout':proc.stdout[-20000:],'stderr':proc.stderr[-20000:],'artifact':str(artifact) if artifact else None,
        'artifact_sha256':sha(artifact) if artifact else None})
    print(f'[{name}] rc={proc.returncode} {stages[-1]["seconds"]:.1f}s',flush=True);print(proc.stdout[-3000:]);print(proc.stderr[-3000:],file=sys.stderr)

t0=time.perf_counter()
stage('pytest',[sys.executable,'-m','pytest','-q','-p','no:cacheprovider',str(ROOT/'tests')])
stage('saved_seeds',[sys.executable,str(ROOT/'scripts/check_saved_seeds.py'),'--output',str(work/'saved_seed_regression.json'),'--threads',str(a.threads)],work/'saved_seed_regression.json')
stage('baseline',[sys.executable,str(ROOT/'scripts/baseline_equality.py'),'--baseline',a.baseline,'--output',str(work/'baseline_equality.json'),'--threads',str(a.threads),'--cores',str(a.threads)],work/'baseline_equality.json')
stage('calibration',[sys.executable,str(ROOT/'scripts/calibrate.py'),'--cuts','12','--windows','none','vacuum:consistent','--deltas','.1',
      '--concurrent','2','--workdir',str(work/'calibration_smoke'),'--output',str(work/'calibration_smoke.json')],work/'calibration_smoke.json')
stage('window_baseline',[sys.executable,str(ROOT/'scripts/window_baseline_equality.py'),
      '--output',str(work/'window_baseline.json'),'--threads',str(a.threads)],work/'window_baseline.json')
stage('optimized_basis',[sys.executable,str(ROOT/'scripts/validate_density.py'),
      '--output',str(work/'optimized_basis.json'),'--workdir',str(work/'optimized_basis'),
      '--threads',str(a.threads)],work/'optimized_basis.json')
passed=all(s['passed'] for s in stages)
payload={'passed':passed,'stages':stages,'source_sha256':source_fingerprint(),'release_sha256':release_fingerprint(),'runtime':runtime(),
         'baseline':a.baseline,'baseline_source_sha256':baseline_sha,
         'seconds':time.perf_counter()-t0,'host':os.uname().nodename,'skipped':[s['stage'] for s in stages if s.get('skipped')]}
if passed or not out.exists():atomic_json(out,envelope('validation',{},payload))
else:atomic_json(out.with_name(out.name+'.failed'),envelope('validation',{},payload))
print('RECEIPT',out if passed else 'not written (failed)','passed=',passed)
raise SystemExit(0 if passed else 1)
