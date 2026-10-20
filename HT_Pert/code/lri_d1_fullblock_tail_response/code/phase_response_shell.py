"""Complete V--J_phase--V thermal response, all low bath modes included.
This is one insertion class, not the entire thermal coefficient. Its high
phase support is generated before summing: no thermal target enters.
"""
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict
from itertools import product
from functools import lru_cache
import math,json,argparse,time
import numpy as np
from scipy.signal import fftconvolve
ROOT=Path(__file__).resolve().parents[1]
LD=np.longdouble

def comp(n,k):
    if k==1:yield (n,);return
    for x in range(n+1):
        for z in comp(n-x,k-1):yield (x,)+z

def delta(m):return 2-2*((m+7)//8)

@lru_cache(None)
def weights():
    out=defaultdict(F);diag={};fact=math.factorial
    for p,thermal in [(0,F(1,3)),(1,F(-1)),(2,F(1)),(3,F(-1,3))]:
        one=defaultdict(F)
        for spectators in range(p+1):
            n=p-spectators
            for l in comp(n,3):
             for r in comp(n,3):
                left=[degree-a-b for degree,a,b in zip([4,2,4],l,r)]
                if min(left)<0 or sum(left)%2:continue
                a=F(left[0]+left[1]-left[2],2)
                b=F(left[0]+left[2]-left[1],2)
                c=F(left[1]+left[2]-left[0],2)
                if any(v<0 or v.denominator!=1 for v in [a,b,c]):continue
                a,b,c=map(int,[a,b,c])
                P1=spectators+l[1]+l[2]+r[0]+a+b
                P2=spectators+l[2]+r[0]+r[1]+b+c
                create=a+l[1]
                jfac=(delta(P2+2) if create==0 else (F(delta(P2+2)+delta(P2+4),2) if create==1 else delta(P2+4)))
                if not jfac:continue
                v=F(fact(p)*fact(4)*fact(2)*fact(4),fact(spectators)*144)
                for k in l+r+(a,b,c):v/=fact(k)
                v*=jfac
                if v:
                    assert P1<=7 and P2<=7 and P1>=5 and P2>=5
                    one[a,b,c,F(P1-p,4),F(P2-p,4)]+=v
        diag[p]=dict(one)
        for key,v in one.items():out[key]+=thermal*v/81
    return {k:v for k,v in out.items() if v},diag

class Engine:
 def __init__(self,L,direct=False):
    if L<2 or L%2:raise ValueError('Positive even low cutoff required')
    if np.finfo(LD).nmant<63:raise RuntimeError('Extended longdouble required')
    self.L=L;self.N=L-2;self.direct=direct;self.ws={};self.gs={};self.cache={}
    for k in range(6):
        w=np.zeros(self.N+1,dtype=LD);w[0]=1
        for n in range(1,len(w)):w[n]=w[n-1]*(LD(k)/2+n-1)/n
        self.ws[k]=w
 def G(self,a,d):
    key=a,d
    if key in self.gs:return self.gs[key]
    n=np.arange(self.N+1,dtype=LD);den=n+LD(d.numerator)/d.denominator
    w=np.divide(1,den,out=np.zeros_like(den),where=(den!=0)&(n%2==0))
    if a==0:g=w
    elif self.direct:
        g=np.array([np.dot(self.ws[a][:self.N+1-k],w[k:]) for k in range(self.N+1)],dtype=LD)
    else:
        z=fftconvolve(self.ws[a],w[::-1]);g=z[self.N-np.arange(self.N+1)]
    self.gs[key]=g;return g
 def T(self,a,b,c,d,e):return np.dot(self.ws[b],self.G(a,d)*self.G(c,e))
 def calc(self):
    rows=[];val=LD(0)
    terms,_=weights()
    for (a,b,c,d,e),v in terms.items():
        raw=self.T(a,b,c,d,e);value=raw*LD(v.numerator)/v.denominator
        val+=value;rows.append(dict(edges=[a,b,c],left_shift=str(d),right_shift=str(e),coefficient=str(v),value=float(value),raw_kernel=float(raw)))
    return dict(cutoff=self.L,response4=float(val),rows=rows)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cutoffs',type=int,nargs='+',default=[2,4,8,16,32,64,128,256,512,1024,4096,16384]);p.add_argument('--direct',action='store_true');a=p.parse_args();rows=[]
 for L in a.cutoffs:
    t=time.perf_counter();o=Engine(L,a.direct).calc();o['seconds']=time.perf_counter()-t;rows.append(o)
    print(L,o['response4'],o['seconds'],flush=True)
 (ROOT/'results/phase_response_shells.json').write_text(json.dumps(rows,indent=2)+'\n')
 terms,_=weights();print('terms',len(terms))
 for key,v in terms.items():print(key,v)
