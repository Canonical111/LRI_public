"""Rational symbolic shadow of the Laurent reconstruction.
Numeric shadows choose regular deformation/reference directions; symbolic
coefficients are computed from Gamma-function jets, not fitted to values.
"""
import sympy as sp
import mpmath as mp
from fractions import Fraction as F
from collections import Counter
from itertools import combinations
import json
from jet_engine import X,Engine
from polar_reconstruction import PolarEngine
from assemble import four_sum
from five_vertex import evaluate

M,T,H=sp.symbols('M T H')
P={(k,n):sp.Symbol(('p','t','u')[k]+('m' if n==-1 else str(n))) for k in range(3) for n in (-1,0,1,2,3,4)}

class Dual:
    __slots__=('s','v')
    def __init__(self,s,v):self.s=sp.expand(s);self.v=mp.mpf(v)
    @staticmethod
    def cast(x):
        if isinstance(x,Dual):return x
        if isinstance(x,F):return Dual(sp.Rational(x.numerator,x.denominator),mp.mpf(x.numerator)/x.denominator)
        if isinstance(x,int):return Dual(sp.Integer(x),x)
        return Dual(sp.Rational(str(x)),x)
    def __add__(self,o):
        o=self.cast(o);return Dual(self.s+o.s,self.v+o.v)
    __radd__=__add__
    def __neg__(self):return Dual(-self.s,-self.v)
    def __sub__(self,o):return self+-self.cast(o)
    def __rsub__(self,o):return self.cast(o)+-self
    def __mul__(self,o):
        o=self.cast(o);return Dual(self.s*o.s,self.v*o.v)
    __rmul__=__mul__
    def __truediv__(self,o):
        o=self.cast(o);return Dual(sp.cancel(self.s/o.s),self.v/o.v)
    def __rtruediv__(self,o):return self.cast(o)/self
    def __pow__(self,n):return Dual(self.s**n,self.v**n)
    def __abs__(self):return abs(self.v)
    def __repr__(self):return 'Dual('+str(self.s)+', '+str(self.v)+')'

class SymbolicEngine(PolarEngine):
    def __init__(self):
        tv=6*mp.gamma(mp.mpf(1)/4)**4/mp.pi
        super().__init__(1,tv,N=3)
        self.num=Engine(1,tv,N=3)
        self.T=Dual(T,tv)
    def m(self,x):return Dual.cast(x)
    def gr(self,nums,dens=()):
        counts=Counter(nums);counts.subtract(dens);counts={x:c for x,c in counts.items() if c}
        zeros=[c for x,c in counts.items() if x.a==0 and x.b==0]
        if any(c>0 for c in zeros):raise ZeroDivisionError('identical gamma pole')
        if zeros:return {}
        pref=sp.S.One;pole=0;lg=[sp.S.Zero]*4;gbase=Counter()
        for x,c in counts.items():
            slope=sp.Rational(x.b.numerator,x.b.denominator)
            if x.a==0:
                pole-=c;pref*=slope**(-c);n=0
            else:n=int(x.a);assert x.a==n;gbase[n]+=c
            for k in range(1,4):lg[k]+=c*P[k-1,n]*slope**k/sp.factorial(k)
        gb=tuple(sorted((k,v) for k,v in gbase.items() if v))
        if gb==((-1,1),(2,2),(3,-1)):pref*=M
        elif gb==((-1,1),(1,-1),(2,3),(4,-1)):pref*=H
        elif gb:raise ValueError(('unexpected Gamma prefactor',gb))
        v=[sp.S.One]
        for k in range(1,min(3,2-pole)+1):v.append(sp.expand(sum(j*lg[j]*v[k-j] for j in range(1,k+1))/k))
        num=self.num.gr(nums,dens)
        return {pole+k:Dual(pref*x,num[pole+k]) for k,x in enumerate(v)}

def expr(x):return x.s if isinstance(x,Dual) else sp.Rational(str(x))
def compact(x):
    A,R,U,V,N=sp.symbols('A R U V N')
    s=expr(x)
    s=s.subs(P[0,-1],N-P[0,3]+P[0,0]+P[0,2])
    s=s.subs(P[0,2],A-P[0,0]+2*P[0,1])
    s=s.subs(P[1,2],R+P[1,0]).subs(P[2,1],U).subs(P[2,2],V-P[2,0])
    return sp.expand(s)

if __name__=='__main__':
    mp.mp.dps=60
    E=SymbolicEngine()
    S4,details=four_sum(E)
    print('S4_1:',compact(S4[1]),flush=True)
    rows=json.load(open('graphs_n5.json'));S5={};report=[]
    for row in rows:
        val,meta=evaluate(E,row)
        print(row['index'], 'finite:',compact(val[0]),flush=True)
        S5=E.add(S5,E.scale(val,F(row['weight'])))
        report.append(dict(index=row['index'],finite=str(compact(val[0]))))
    print('S5_0:',compact(S5[0]),flush=True)
    out={'S4_1':str(compact(S4[1])),'S5_0':str(compact(S5[0])),'graph_finite_parts':report,
         'gamma_jet_symbols':{str(v):str(k) for k,v in P.items()}}
    json.dump(out,open('symbolic_kernels.json','w'),indent=2)
