"""An additional nonoverlapping/lock-protected face worker, bounded concurrency."""
from pathlib import Path
import sys,json,subprocess,os,time
root=Path(__file__).resolve().parent.parent;kind,d,n,face=sys.argv[1:5];n=int(n);face=int(face)
folder=root/'tail_blocks'/f'{kind}_{d}';manifest=json.loads((folder/f'n{n}_face{face}_manifest.json').read_text());logs=root/'tail_logs'/f'{kind}{n}_{d}'
for b in manifest['blocks']:
 p=folder/b['id']
 if (p/'result.json').exists():continue
 st=time.time()
 with (logs/(b['id']+'_extra.log')).open('w') as f:
  run=subprocess.run([sys.executable,str(root/'engine/tail_boundary.py'),'--kind',kind,'--deriv',d,'--block',b['id']],stdout=f,stderr=subprocess.STDOUT,check=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1'))
 print('FACE_EXTRA_DONE',b['id'],time.time()-st,flush=True)
print('FACE_EXTRA_COMPLETE',face,flush=True)
