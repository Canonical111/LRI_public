"""Completed big-cutoff control calculations, one subprocess at a time."""
from pathlib import Path
import subprocess,sys,os,json,time
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1')
 runs=[]
 for args in [('--cutoffs','44','--scheme','raw','--degree','8'),('--cutoffs','44','--scheme','dconn','--degree','7')]:
  t=time.monotonic();p=subprocess.run([sys.executable,str(ROOT/'code/ragged_quotient.py'),*args,'--batch','1'],env=env,capture_output=True,text=True)
  runs.append(dict(args=args,returncode=p.returncode,seconds=time.monotonic()-t,stdout=p.stdout,stderr=p.stderr))
  (ROOT/'results/large_checks.json').write_text(json.dumps(runs,indent=2)+'\n')
  if p.returncode:raise RuntimeError(p.stderr)
 print('Large control calculations completed')
