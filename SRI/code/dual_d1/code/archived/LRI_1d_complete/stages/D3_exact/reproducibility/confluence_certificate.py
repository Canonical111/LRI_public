"""Find a rational confluence certificate using modular linear algebra.
Discovery is modular; the delivered certificate is accepted ONLY after an
exact rational verification of every coefficient of every period word.
"""
from confluence_relations import *
from math import isqrt,gcd
P=2**61-1

def modq(c,p=P):return int(c.numerator)*pow(int(c.denominator),-1,p)%p
class CertifiedModular:
 def __init__(self,p=P):self.p=p;self.basis=[];self.leads={};self.defs=[]
 def add(self,row,source):
  p=self.p;r={w:modq(c,p) for w,c in row.items() if c};parents={}
  while r:
   lead=max(r)
   if lead not in self.leads:
    inv=pow(r[lead],-1,p);idx=len(self.basis)
    self.leads[lead]=idx
    self.basis.append({w:c*inv%p for w,c in r.items()})
    self.defs.append((source,inv,{j:-c*inv%p for j,c in parents.items()}))
    return
   j=self.leads[lead];fac=r[lead];parents[j]=(parents.get(j,0)+fac)%p
   for w,c in self.basis[j].items():
    a=(r.get(w,0)-fac*c)%p
    if a:r[w]=a
    elif w in r:del r[w]
 def certificate(self,row):
  p=self.p;r={w:modq(c,p) for w,c in row.items() if c};weights=Counter()
  while r:
   lead=max(r)
   if lead not in self.leads:raise ValueError(('unreduced',lead,len(r)))
   j=self.leads[lead];fac=r[lead];weights[j]=(weights[j]+fac)%p
   for w,c in self.basis[j].items():
    a=(r.get(w,0)-fac*c)%p
    if a:r[w]=a
    elif w in r:del r[w]
  sources=Counter()
  for j in range(len(self.basis)-1,-1,-1):
   fac=weights[j]%p
   if not fac:continue
   src,sc,parents=self.defs[j];sources[src]=(sources[src]+fac*sc)%p
   for k,c in parents.items():weights[k]=(weights[k]+fac*c)%p
  return {i:c for i,c in sources.items() if c}

def ratrec(x,m):
 bound=isqrt(m//2);u1,u2,u3=1,0,m;v1,v2,v3=0,1,x%m
 while abs(v3)>bound:
  q=u3//v3;u1,u2,u3,v1,v2,v3=v1,v2,v3,u1-q*v1,u2-q*v2,u3-q*v3
 if not v2:return None
 num,den=v3,v2
 if den<0:num,den=-num,-den
 if den<=bound and abs(num)<=bound and gcd(num,den)==1 and (num-x*den)%m==0:return Q(num,den)
 return None

def run(n):
 start=time.time();tar={tuple(w):Q(c) for w,c in json.loads((ROOT/'D3_linear_words.json').read_text()) if len(w)==n}
 sources=list(relations(n))+list(scaling_relations(n));A=CertifiedModular()
 for i,(desc,row) in enumerate(sources):
  A.add(row,i)
  if i and i%1000==0:print('weight',n,'row',i,'rank',len(A.basis),'sec',time.time()-start,flush=True)
 modular=A.certificate(tar);cert=[];res=Counter(tar)
 for idx,cmod in sorted(modular.items()):
  c=ratrec(cmod,P)
  if c is None:raise ValueError(('rational reconstruction failed',n,idx,cmod))
  desc,row=sources[idx];cert.append(dict(coefficient=str(c),relation=desc))
  for w,v in row.items():res[w]-=c*v
 res={w:c for w,c in res.items() if c}
 if res:raise AssertionError(('EXACT VERIFICATION FAILED',n,len(res),list(res.items())[:3]))
 out=dict(weight=n,status='exact rational identity verified',period_convention='R_w = constant as T -> infinity of G(-w;T)',certificate=cert,source_count=len(sources),rank_mod_prime=len(A.basis),discovery_prime=str(P),target=[[list(w),str(c)] for w,c in sorted(tar.items())])
 (ROOT/f'confluence_certificate_w{n}.json').write_text(json.dumps(out,indent=2))
 print('EXACT CERTIFICATE PASS weight',n,'used',len(cert),'relations; seconds',time.time()-start,flush=True)
 print('largest coefficient numerator',max(abs(Q(e['coefficient']).numerator) for e in cert),'denominator',max(Q(e['coefficient']).denominator for e in cert),flush=True)
 return out
if __name__=='__main__':
 for n in (2,3,4):run(n)
