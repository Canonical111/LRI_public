"""Kite jets through degree two using the uploaded note, squared-distance exponents."""
from fractions import Fraction as F
from itertools import permutations
from functools import lru_cache
import mpmath as mp
from jet_engine import X,D,HALF,Engine
from polar_reconstruction import edge,ZERO,completion_star_value,PolarEngine

class QuadraticEngine(Engine):
    def __init__(self,d,T,K=0,Z=0,N=7):
        super().__init__(d,T,N=N);self.K=mp.mpf(K);self.Z=mp.mpf(Z)
    @lru_cache(None)
    def kite(self,*es):
        direct=self.direct_kite(es)
        if direct is not None:return direct
        comp=self.completion(es)
        for (i,j),x in comp.items():
            if not x:
                try:return completion_star_value(self,comp,i,j)
                except (ValueError,ZeroDivisionError):pass
        if all(x.a==1 for x in comp.values()):
            return {0:self.T/2,1:mp.mpf(0),2:self.Z*sum(self.m(x.b)**2 for x in comp.values())}
        for perm in permutations(range(5)):
            new=tuple(edge(comp,perm[i],perm[j]) for i,j in ((0,2),(1,2),(0,3),(1,3),(2,3)))
            base=tuple(x.a for x in new)
            if base not in ((1,1,1,1,2),(1,1,1,2,1)):continue
            try:
                out=self.patternA(new) if base==(1,1,1,1,2) else self.patternB(new)
                return {k:v for k,v in out.items() if k<=2}
            except (ValueError,ZeroDivisionError):continue
        raise ValueError(('unhandled kite pattern',es,comp))
    def patternA(self,es):
        a,b,c,f,r=es;A,R,U,V=self.A,self.R,self.U,self.V
        t=HALF-r;p0=D-a-c-r;p1=D-b-f-r;sig=p0+p1
        ts,ps0,ps1,ss=(self.m(x.b) for x in (t,p0,p1,sig))
        if any(x.a for x in (t,p0,p1)):raise ValueError('wrong patternA')
        if not ts or not ps0 or not ps1:raise ZeroDivisionError('A critical pole direction')
        P=self.add(self.shift(self.conv((HALF+t-a+c)/2,HALF-t),-1,1/ps0),
                   self.shift(self.conv((HALF+t-b+f)/2,HALF-t),-1,1/ps1),
                   self.shift(self.conv(HALF-p0,HALF-p1),-1,1/ts),
                   {-2:-(1/ps0+1/ps1)/ts})
        return self.add(P,{1:ss*(A*R+U/4),2:ts*ss*(A*A*R/2+A*U/4-R*R/2)-A*V*ss*ss/2})
    def patternB(self,es):
        a,b,c,f,r=es;p1=HALF-f;p2=D-b-f-r;z1=3*HALF-a-b-c-f-r;z2=D-c-f-r
        if p1.a or p2.a or z1.a or z2.a:raise ValueError('wrong B')
        if not p1.b:raise ZeroDivisionError('B critical pole')
        G2=self.mul(self.conv(HALF+p1-r,HALF-p1),self.conv(r+p2-z1,HALF-p2))
        G1=self.mul(self.conv(r-p1+p2+z2,HALF+p1-r-z2),self.conv(HALF+p1-r-p2,HALF-p1))
        G0=self.mul(self.conv(HALF+p1-r,HALF-p1),self.conv(r+p2,HALF-p2))
        db=self.add(self.conv(r+p2+z2-z1,HALF-p2),self.scale(self.conv(r+p2-z1,HALF-p2),-1),
                    self.scale(self.conv(r+p2+z2,HALF-p2),-1),self.conv(r+p2,HALF-p2))
        return self.add(G2,G1,self.scale(G0,-1),self.shift(db,-1,1/self.m(p1.b)),
                        {2:4*self.K*self.m(z1.b)*self.m(z2.b)})

if __name__=='__main__':
    import random
    mp.mp.dps=45
    E=QuadraticEngine(1,6*mp.gamma(mp.mpf(1)/4)**4/mp.pi,N=6)
    O=PolarEngine(1,E.T,N=6)
    for base in ((1,1,1,1,2),(1,1,1,2,1),(1,2,2,1,1)):
        for k in range(3):
            rng=random.Random(88+k)
            es=tuple(X(n,F(rng.randint(1,15),11)) for n in base)
            o=O.kite(*es);a=E.kite(*es)
            print(base,k,{j:mp.nstr(a.get(j,0)-o.get(j,0),8) for j in (-2,-1,0,1)})
