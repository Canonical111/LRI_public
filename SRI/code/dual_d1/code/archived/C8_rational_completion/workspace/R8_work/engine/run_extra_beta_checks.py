"""Fresh low-order controls for the five inherited C8 inputs.
Does not read any conjectured C8 coefficient. Serial optional control queue.
"""
from pathlib import Path
import sys,subprocess,json,time,os
from fractions import Fraction as F
r=Path(__file__).resolve().parent.parent;e=r/'engine';logs=r/'extra_beta_logs';logs.mkdir(exist_ok=True)
env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
def call(args,log):
 t=time.time()
 with (logs/log).open('w') as f:p=subprocess.run([sys.executable]+list(map(str,args)),cwd=e,env=env,stdout=f,stderr=subprocess.STDOUT)
 print('EXTRA',str(args),p.returncode,time.time()-t,flush=True);assert p.returncode==0,log
for kind,n,d in [('Q',4,'base'),('A',5,'dd'),('Z',4,'dd'),('Q',4,'vvv'),('Q',4,'vvd'),('Q',4,'vdd'),('Q',6,'vv')]:
 call([e/'run_tail_queue.py',kind,n and d,str(n),'1'],f'{kind}{n}_{d}_boundary.log')
for kind,n,d in [('EA',3,'dd'),('EZ',2,'dd'),('EQ',2,'vvv'),('EQ',2,'vvd'),('EQ',2,'vdd'),('EQ',4,'vv'),('Q',4,'vvv')]:
 tag=f'{kind}{n}_{d}';p=r/'finite_lower'/tag;m=p/'manifest.json'
 if not m.exists():call([e/'finite_lower.py','--n',str(n),'--kind',kind,'--deriv',d,'--sources'],f'{tag}_sources.log')
 for b in json.loads(m.read_text())['blocks']:
  if not(p/b['id']/'result.json').exists():call([e/'finite_lower.py','--tag',tag,'--block',b['id']],f'{tag}_{b["id"]}.log')
 val=sum((F(json.loads((p/b['id']/'result.json').read_text())['finite']) for b in json.loads(m.read_text())['blocks']),F(0))
 (p/'total.json').write_text(json.dumps({'status':'complete_finite_integral','raw':tag,'finite':str(val),'blocks':len(json.loads(m.read_text())['blocks'])},indent=2));print('EXTRA_FINITE_TOTAL',tag,val,flush=True)
print('EXTRA_ALL_INPUTS_COMPLETE',flush=True)
