from pathlib import Path
import subprocess,json,time,os,sys
root=Path(__file__).resolve().parent.parent;logs=root/'finite_logs';logs.mkdir(exist_ok=True);script=root/'engine/finite_lower.py'
jobs=[('EA',3,'base'),('Q',4,'base'),('EZ',4,'base'),('EA',5,'d'),('EZ',4,'d'),('EZ',6,'base'),('EQ',4,'vd'),('Q',4,'vvd'),('Q',6,'vv'),('EQ',6,'v')]
for kind,n,d in jobs:
 tag=f'{kind}{n}_{d}';manifest=root/'finite_lower'/tag/'manifest.json'
 if not manifest.exists():
  with (logs/f'{tag}_sources.log').open('w') as f:subprocess.run([sys.executable,str(script),'--n',str(n),'--kind',kind,'--deriv',d,'--sources'],stdout=f,stderr=subprocess.STDOUT,check=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1'))
 for b in json.loads(manifest.read_text())['blocks']:
  if (manifest.parent/b['id']/'result.json').exists():continue
  st=time.time()
  with (logs/f'{tag}_{b["id"]}.log').open('w') as f:subprocess.run([sys.executable,str(script),'--tag',tag,'--block',b['id']],stdout=f,stderr=subprocess.STDOUT,check=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1'))
  print('FINITE_FINISHED',tag,b['id'],time.time()-st,flush=True)
 from fractions import Fraction as F
 val=sum((F(json.loads((manifest.parent/b['id']/'result.json').read_text())['finite']) for b in json.loads(manifest.read_text())['blocks']),F(0))
 result={'status':'complete_finite_integral','raw':tag,'finite':str(val),'blocks':len(json.loads(manifest.read_text())['blocks'])}
 (manifest.parent/'total.json').write_text(json.dumps(result,indent=2));print('FINITE_TOTAL',result,flush=True)
print('ALL_LOWER_FINITE_DONE',flush=True)
