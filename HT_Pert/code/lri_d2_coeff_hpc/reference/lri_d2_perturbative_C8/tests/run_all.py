"""Independent small checks; does not silently repeat the largest coefficient runs."""
from pathlib import Path
import sys,subprocess,os,json,time
ROOT=Path(__file__).resolve().parents[1]
def main():
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1',NUMBA_NUM_THREADS='1')
    commands=[['code/exact_circle.py','--cutoffs','0','2','4','6','--schemes','raw','consistent'],['tests/test_coefficients.py'],['tests/test_finite_uploaded.py'],['tests/test_local_algebra.py']]
    records=[]
    for cmd in commands:
        t=time.perf_counter();p=subprocess.run([sys.executable]+cmd,cwd=ROOT,env=env,text=True,capture_output=True)
        records.append(dict(command=cmd,returncode=p.returncode,seconds=time.perf_counter()-t,stdout=p.stdout,stderr=p.stderr))
        (ROOT/'results/test_run.json').write_text(json.dumps(records,indent=2)+'\n')
        print('PASS' if p.returncode==0 else 'FAIL',cmd,flush=True)
        if p.returncode:raise RuntimeError(p.stderr or p.stdout)
if __name__=='__main__':main()
