"""Enumerate analytically specified sources; these are not fitted identities."""
from analytic_sources import *
from inverse_stage import fullrow
from lyndon import factor
import math,time
base=Path(__file__).resolve().parent
M=11

def moncode(words):
 out=0;used=0
 for w in sorted(words,key=lambda w:(len(w),w),reverse=True):
  n=len(w);raw=0
  for a in w:raw=16*raw+a
  token=(n<<(4*n))|raw;count=3+4*n;used+=count
  out|=token<<(64-used)
 return out

def wordcode(w):
 raw=0
 for a in w:raw=16*raw+a
 return (len(w)<<24)|raw

def contexts(n):
 if not n:return [()]
 if n==1:return [((a,),) for a in range(M+1)]
 if n==2:return [((a,b),) for a in range(M+1) for b in range(a+1,M+1)]+[((a,),(b,)) for a in range(M+1) for b in range(a+1)]
 raise ValueError(n)

def base_rows(n):
 if n==1:
  for a in (0,1):
   lab=('Z',1,0,0,a);yield lab,source(lab)
  for a in range(2,M+1):
   for b in range(a,M+1):
    if a*b<=M:
     lab=('L',1,0,0,a,b);yield lab,source(lab)
  return
 for bb in convergent(n):
  bs=sum(b<<(n-i-1) for i,b in enumerate(bb))
  for aa in product(*(range(b,M+1) for b in bb)):
   if max(a for a,b in zip(aa,bb) if b==0)+max(a for a,b in zip(aa,bb) if b==1)>M:continue
   st=tuple(zip(bb,aa));lab=('D',n,bs,0,*aa);r=fullrow(st)
   if r:yield lab,r
 for d in range(2,M+1):
  for aa in product(range(M//d+1),repeat=n):
   if not aa[-1]:continue
   lab=('S',n,0,d,*aa);r=source(lab)
   if r:yield lab,r
 for aa in product((0,1),repeat=n):
  if len(factor(aa))!=1:continue
  lab=('I',n,0,0,*aa);r=source(lab)
  if r:yield lab,r
for degree in (1,2,3):
 count=0;f=open(base/f'low{degree}.rows','w')
 for n in range(1,degree+1):
  cc=contexts(degree-n)
  for lab,r in base_rows(n):
   for ctx in cc:
    f.write(str(moncode(ctx))+' '+' '.join(map(str,lab))+'\n');f.write(str(len(r))+'\n')
    for w,c in sorted(r.items()):f.write(f'{wordcode(w)} {c}\n')
    count+=1
 f.close();print('LOW SOURCES',degree,count,flush=True)
