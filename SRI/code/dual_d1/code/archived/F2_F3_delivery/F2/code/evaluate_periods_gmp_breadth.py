"""Independent GMP implementation of the same Taylor/asymptotic period recurrences."""
from pathlib import Path
from decimal import Decimal
import subprocess,tempfile,math,os
import mpmath as mp
ROOT=Path(__file__).resolve().parent

def evaluate(words,dps=80,R=90,ntaylor=230,nasym=120,stepfrac='.35',guard=12):
 words=set(map(tuple,words));assert all(w and w[-1]!=0 and all(a>=0 for a in w) for w in words)
 closure={()}
 for w in words:
  for j in range(len(w)+1):closure.add(w[j:])
 ws=sorted(closure,key=lambda w:(len(w),w));ix={w:i for i,w in enumerate(ws)};needed={w[1:] for w in ws[1:]}
 with mp.workdps(dps+50):lr=mp.nstr(mp.log(R),dps+40)
 with tempfile.TemporaryDirectory(prefix='gmp_period_') as td:
  inp=Path(td)/'input.txt';out=Path(td)/'output.txt'
  with inp.open('w') as f:
   f.write(f'{len(ws)} {dps} {ntaylor} {nasym} {R} {stepfrac} {lr}\n')
   for w in ws:
    f.write(' '.join(map(str,[w[0] if w else 1,ix[w[1:]] if w else 0,len(w),int(w in needed),*(ix[w[j:]] for j in range(1,len(w)+1))]))+'\n')
  env=os.environ.copy();env.setdefault('OMP_NUM_THREADS','3')
  subprocess.run([str(ROOT/'periods_gmp'),str(inp),str(out)],check=True,env=env)
  vals={}
  for line in out.read_text().splitlines():
   i,value=line.split();w=ws[int(i)]
   if w in words:vals[w]=Decimal(value)
  assert set(vals)==words
  return vals
