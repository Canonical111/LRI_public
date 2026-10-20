from pathlib import Path
import subprocess,sys,os,time,json
ROOT=Path(__file__).resolve().parents[1]
def main():
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1')
    records=[]
    for name in ['tests/check_annulus.py','code/mixing_asymptotics.py','tests/validate.py','tests/check_finite_response.py']:
        start=time.perf_counter();p=subprocess.run([sys.executable,str(ROOT/name)],cwd=ROOT,env=env,text=True,capture_output=True)
        records.append(dict(script=name,status='pass' if p.returncode==0 else 'fail',seconds=time.perf_counter()-start,stdout=p.stdout,stderr=p.stderr))
        (ROOT/'results/test_run.json').write_text(json.dumps(records,indent=2)+'\n');print(name,records[-1]['status'],flush=True)
        if p.returncode:raise RuntimeError(p.stderr or p.stdout)
if __name__=='__main__':main()
