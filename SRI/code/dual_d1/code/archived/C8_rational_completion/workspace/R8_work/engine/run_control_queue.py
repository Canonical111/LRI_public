import subprocess,json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parent.parent
for kind,deriv,n in [('Z','base',6),('Z','v',6),('Z','d',4),('A','d',5)]:
 logfile=root/f'controls_{kind}{n}_{deriv}.log'
 with logfile.open('w') as f:
  r=subprocess.run([sys.executable,str(root/'engine/run_tail_queue.py'),kind,deriv,str(n),'1'],stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,OPENBLAS_NUM_THREADS='1'))
 print(kind,n,deriv,r.returncode,flush=True)
