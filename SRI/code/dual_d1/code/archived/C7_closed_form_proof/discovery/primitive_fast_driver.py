"""Rebuild each primitive block; accept only an exact full-source application."""
from pathlib import Path
import subprocess,sys,json,time
from sympy import prevprime
base=Path(__file__).resolve().parent
primes=[2**61-1]
for _ in range(20):primes.append(int(prevprime(primes[-1])))
start=int(sys.argv[1]) if len(sys.argv)>1 else 10
end=int(sys.argv[2]) if len(sys.argv)>2 else 2
report=[]
for m in range(start,end-1,-1):
 now=time.time();target=base/f'after{m+1}.words';p0=base/f'mod{m}'
 if not Path(str(p0)+'.modcert.txt').exists():
  with open(str(p0)+'.log','w') as log:
   code=subprocess.call([str(base/'stage_fast'),'6',str(m),str(target),str(p0),str(primes[0])],stdout=log,stderr=subprocess.STDOUT)
  if code:raise RuntimeError(f'Discovery failed m={m}, code={code}')
 files=[str(p0)+'.modcert.txt'];passed=False
 for j in range(len(primes)):
  cert=base/f'stage{m}.candidate.cert';out=base/f'after{m}.words'
  code=subprocess.call([sys.executable,str(base/'reconstruct_stage.py'),str(cert),*files])
  if code==0:
   with open(base/f'apply{m}_p{j+1}.log','w') as log:
    code=subprocess.call([str(base/'check_apply'),str(target),str(cert),str(base/'D_endpoints.terms'),'6',str(m),str(out)],stdout=log,stderr=subprocess.STDOUT)
   if code==0:
    final=base/f'stage{m}.certificate.txt';final.write_bytes(cert.read_bytes());passed=True;break
  p=base/f'mod{m}_p{j+1}'
  if not Path(str(p)+'.modcert.txt').exists():
   with open(str(p)+'.log','w') as log:
    code=subprocess.call([str(base/'stage_fast'),'6',str(m),str(target),str(p),str(primes[j+1]),str(p0)+'.labels.txt'],stdout=log,stderr=subprocess.STDOUT)
   if code:raise RuntimeError(f'Selected solve failed m={m} prime={j+1} code={code}')
  files.append(str(p)+'.modcert.txt')
 if not passed:raise RuntimeError(f'Exact application did not pass m={m}')
 data=json.load(open(str(out)+'.report.json'));data.update(primes_used=len(files),wall_seconds=time.time()-now);report.append(data)
 (base/'primitive_rebuild_report.json').write_text(json.dumps(report,indent=2))
 print('EXACT STAGE COMPLETE',data,flush=True)
print('ALL REQUESTED PRIMITIVE BLOCKS COMPLETE',flush=True)
