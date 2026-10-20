#!/usr/bin/env python3
"""Exercise safe side-run verification and numerical guards, including Python -O."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
    principal=[ROOT/'outputs/reproduced/run_receipt.json',ROOT/'outputs/reproduced/verification/regression_checks.json']
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in principal}
    checks=[]
    code=f'''import sys
sys.path.insert(0,{str(ROOT/'code/c1_refinement')!r})
from runtime_config import ratio_interval
for args in [(0.27,12.,0.01,0.02,0.1),(0.27,12.,-0.01,0.02,12.),(0.27,12.,float("nan"),0.02,0.1)]:
    try:
        ratio_interval(*args)
    except ValueError:
        pass
    else:
        raise RuntimeError("Scientific guard disabled")
print("three explicit guards passed")
'''
    result=subprocess.run([sys.executable,'-O','-c',code],env=env,capture_output=True,text=True)
    checks.append(dict(name='explicit_ratio_guards_under_python_O',passed=result.returncode==0,stdout=result.stdout,stderr=result.stderr))
    with tempfile.TemporaryDirectory(prefix='c1-side-run-check-') as tmp:
        out=Path(tmp)/'smoke'
        run=subprocess.run([sys.executable,str(ROOT/'code/workflow/reproduce.py'),'smoke','--from-scratch','--output',str(out)],env=env,capture_output=True,text=True)
        checks.append(dict(name='isolated_smoke_profile',passed=run.returncode==0,stdout_tail=run.stdout[-700:],stderr_tail=run.stderr[-700:]))
        verify=subprocess.run([sys.executable,str(ROOT/'code/workflow/verify.py'),'results','--results',str(out)],env=env,capture_output=True,text=True)
        report=out/'verification/regression_checks.json'
        checks.append(dict(name='partial_run_reported_cleanly_as_incomplete',passed=verify.returncode==1 and report.is_file() and 'Traceback' not in verify.stderr,returncode=verify.returncode,report_written=report.is_file(),stderr=verify.stderr))
    after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in principal}
    checks.append(dict(name='principal_receipt_and_report_unchanged',passed=before==after))
    report={'status':'passed' if all(c['passed'] for c in checks) else 'failed','scope':'Workflow and guard regression checks, not scientific uncertainty certification','checks':checks}
    out=ROOT/'outputs/verification/revision_guard_checks.json';out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if report['status']!='passed':raise SystemExit(1)
if __name__=='__main__':main()
