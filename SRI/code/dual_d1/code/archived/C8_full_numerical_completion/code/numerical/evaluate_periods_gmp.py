"""Independent GMP implementation of the same Taylor/asymptotic period recurrences."""
from pathlib import Path
from decimal import Decimal
import subprocess,tempfile,math,os,shutil
import mpmath as mp
ROOT=Path(__file__).resolve().parent

def evaluate(words,dps=80,R=90,ntaylor=230,nasym=120,stepfrac='.35',guard=12):
 binary=ROOT/'periods_gmp';source=ROOT/'periods_gmp.cpp'
 if not binary.exists() or binary.stat().st_mtime<source.stat().st_mtime:
  compiler=shutil.which('g++') or shutil.which('c++')
  if compiler is None:raise RuntimeError('A C++17 compiler and GMP development libraries are required for this backend.')
  subprocess.run([compiler,'-O3','-std=c++17','-fopenmp',str(source),'-lgmpxx','-lgmp','-o',str(binary)],check=True)
 words=set(map(tuple,words));assert all(w and w[-1]!=0 and all(a>=0 for a in w) for w in words)
 closure={()}
 for w in words:
  for j in range(len(w)+1):closure.add(w[j:])
 # Depth-first suffix-tree ordering: reversed suffixes are prefixes.
 # Every suffix is available before its parent word, but expanded polynomials
 # need remain live only along the active tree path, not a whole weight layer.
 ws=sorted(closure,key=lambda w:tuple(reversed(w)));ix={w:i for i,w in enumerate(ws)};needed={w[1:] for w in ws[1:]}
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
