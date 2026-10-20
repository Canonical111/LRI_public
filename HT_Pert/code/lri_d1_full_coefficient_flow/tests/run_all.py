"""Run independent validation in separate one-thread processes."""
from pathlib import Path
import sys,json,subprocess,os,time
ROOT=Path(__file__).resolve().parents[1]
def main():
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1')
    records=[]
    for script in ['exact_stationarity.py','independent_coefficients.py','forecast_replay.py','validate_saved.py']:
        t=time.perf_counter()
        p=subprocess.run([sys.executable,str(ROOT/'tests'/script)],cwd=ROOT,env=env,capture_output=True,text=True)
        records.append(dict(driver=script,returncode=p.returncode,seconds=time.perf_counter()-t,stdout=p.stdout,stderr=p.stderr))
        (ROOT/'results/test_run.json').write_text(json.dumps(records,indent=2)+'\n')
        print(script,'PASS' if not p.returncode else 'FAIL',flush=True)
        if p.returncode:raise RuntimeError(p.stdout+'\n'+p.stderr)
if __name__=='__main__':main()
