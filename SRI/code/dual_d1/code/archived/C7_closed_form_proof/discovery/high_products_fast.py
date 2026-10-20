"""Exact products stage: primitive weight-five/four relations with retained contexts."""
from pathlib import Path
from collections import defaultdict,Counter
from fractions import Fraction as Q
from math import factorial, gcd, isqrt
import os,sys,json,time,subprocess
from sympy import prevprime
from analytic_sources import decode_multiplier
base=Path(__file__).resolve().parent
primes=[2**61-1]
for _ in range(24):primes.append(int(prevprime(primes[-1])))
def moncode(words):
 out=0;used=0
 for w in sorted(words,key=lambda w:(len(w),w),reverse=True):
  raw=0
  for a in w:raw=16*raw+a
  count=3+4*len(w);used+=count;out|=((len(w)<<(4*len(w)))|raw)<<(64-used)
 return out
def monfact(words):
 p=1
 for k in Counter(words).values():p*=factorial(k)
 return p
def contexts(poly,n):
 out=defaultdict(dict)
 for line in poly.read_text().splitlines():
  c,mc=line.split();ff=list(decode_multiplier(int(mc)))
  high=[w for w in ff if len(w)==n]
  if not high:continue
  assert len(high)==1
  w=high[0]
  if max(w)<2:continue
  ff.remove(w);code=moncode(ff);out[code][w]=Q(c)/monfact(ff)
 return out

def run(argv,log):
 with open(log,'w') as f:return subprocess.call(list(map(str,argv)),stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'FORCE_ALL':'1'})

class CRT:
 def __init__(self): self.M=1; self.values={}
 def add(self,file):
  lines=Path(file).read_text().splitlines();p=int(lines[0]);data={tuple(s.split()[1:]):int(s.split()[0]) for s in lines[1:]};inv=pow(self.M,-1,p)
  for label in set(self.values)|set(data):
   v=self.values.get(label,0);self.values[label]=v+self.M*((data.get(label,0)-v)*inv%p)
  self.M*=p
 def reconstruct(self,out):
  bound=isqrt(self.M//2);res={}
  for label,x in self.values.items():
   a,b=self.M,x;c,d=0,1
   while abs(b)>bound:
    q=a//b;a,b=b,a-q*b;c,d=d,c-q*d
   if not d or abs(d)>bound or gcd(b,d)!=1:return False
   res[label]=Q(b,d)
  Path(out).write_text(''.join(str(c)+' 0 '+' '.join(label)+'\n' for label,c in sorted(res.items()) if c))
  return True

def main():
 current=Path(sys.argv[1]).resolve();initial=int(sys.argv[2]) if len(sys.argv)>2 else 5
 baseprod=base/'product_stages';baseprod.mkdir(exist_ok=True); reportfile=baseprod/'stages_report.json'; records=json.loads(reportfile.read_text()) if reportfile.exists() else []
 for n in range(initial,3,-1):
  groups=sorted(contexts(current,n));print('FACTOR WEIGHT',n,'contexts',len(groups),flush=True)
  for gi,ctx in enumerate(groups):
   for m in range(11,1,-1):
    vals={w:c for w,c in contexts(current,n).get(ctx,{}).items() if max(w)==m}
    if not vals:continue
    pref=baseprod/f'w{n}_c{ctx}_m{m}';target=Path(str(pref)+'.target.words')
    target.write_text(''.join(f'{c} {n} '+' '.join(map(str,w))+'\n' for w,c in sorted(vals.items())))
    p0=Path(str(pref)+'_p0');shared=baseprod/f'shared_w{n}_m{m}.rowcache';cache=Path(str(p0)+'.rowcache')
    if shared.exists() and not cache.exists():os.link(shared,cache)
    code=run([base/'stage_fast',n,m,target,p0,primes[0]],str(p0)+'.log')
    if code:raise RuntimeError(f'Unsolved product projection n={n} ctx={ctx} m={m}, see {p0}.log')
    if cache.exists() and not shared.exists():os.link(cache,shared)
    files=[str(p0)+'.modcert.txt']; crt=CRT();crt.add(files[0]);passed=False;start=time.time()
    for j in range(len(primes)-1):
     cert=Path(str(pref)+'.candidate.cert');out=Path(str(pref)+'.poly')
     if crt.reconstruct(cert):
      code=run([base/'apply_poly_stage',current,cert,base/'D_endpoints.terms',n,m,ctx,pref,out],str(pref)+f'.apply{j}.log')
      if code==0:passed=True;break
     pp=Path(str(pref)+f'_p{j+1}')
     code=run([base/'stage_fast',n,m,target,pp,primes[j+1],str(p0)+'.labels.txt'],str(pp)+'.log')
     if code:raise RuntimeError(f'Selected product solve failed {pp}')
     files.append(str(pp)+'.modcert.txt');crt.add(files[-1])
    if not passed:raise RuntimeError('No exact product certificate obtained')
    current=out;record=json.load(open(str(pref)+'.report.json'));record['primes_used']=len(files);records.append(record)
    (baseprod/'stages_report.json').write_text(json.dumps(records,indent=2));(baseprod/'current_state.txt').write_text(str(current)+'\n')
    print('EXACT PRODUCT STAGE',record,'elapsed',time.time()-start,flush=True)
  normpref=baseprod/f'after_weight{n}'
  code=run([base/'normalize_products',current,base,normpref],str(normpref)+'.log')
  if code:raise RuntimeError('Low-product normalization failed')
  current=Path(str(normpref)+'.poly');(baseprod/'current_state.txt').write_text(str(current)+'\n')
  print('NORMALIZED',n,json.load(open(str(normpref)+'.report.json')),flush=True)
 print('HIGH PRODUCT REDUCTION COMPLETE',current,flush=True)
if __name__=='__main__':main()
