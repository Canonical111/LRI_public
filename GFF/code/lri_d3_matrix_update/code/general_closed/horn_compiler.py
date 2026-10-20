"""Finite, derivative-free conversion of the LRI master formulas to Horn arrays.

The output is a finite list of unweighted generalized Lauricella/Horn functions.
No graph integral, parameter derivative, or regulator-coefficient extraction is
used by the compiler. It is a formula compiler, not an analytic-continuation
numerical implementation. For K outside 0<q<1/2 the COMPLETE expression is
continued in q from its common convergence domain; terms are not independently
assigned endpoint values of divergent power series.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import Counter, defaultdict
from itertools import product
import math, json, gzip, argparse
from pathlib import Path
import sympy as sp
from sympy.functions.combinatorial.numbers import stirling

q=sp.Symbol('q',positive=True)
y=sp.Symbol('x') # x=pi*cot(pi*q), scalar
P=sp.Symbol('p') # p=pi^2, scalar, NOT spectral p
l,n=sp.symbols('ell n',integer=True,nonnegative=True)

@dataclass(frozen=True)
class Atom:
    kind: str
    order: int
    a: sp.Expr
    b: sp.Expr|None
    vec: tuple[int,int]

ATOMS={};SCALARS={'p':'pi**2','x':'pi*cot(pi*q)'}

def atom(kind,m,a,vec,b=None):
    a=sp.sympify(a);b=None if b is None else sp.sympify(b)
    obj=Atom(kind,m,a,b,tuple(vec))
    for key,value in ATOMS.items():
        if value==obj:return key
    key=sp.Symbol('v'+str(len(ATOMS)))
    ATOMS[key]=obj;return key

def diff(m,a,b,vec):return atom('D',m,a,vec,b)
def psi(m,a,vec):
    assert m>=1
    return atom('J',m,a,vec)
def harm(a,vec):return atom('H',0,a,vec)
def gauss(a,vec):return atom('B',0,a,vec)
def scalar(name,expr):
    SCALARS[name]=str(expr);return sp.Symbol(name)

def cm(m):
    return scalar('c'+str(m),(-1)**(m+1)*sp.polygamma(m-1,q)-sp.polygamma(m-1,1-q)+(1+(-1)**m)*sp.polygamma(m-1,1))

def delta(m):
    return diff(m-1,q,2*q,(1,1))+diff(m-1,1-q,1,(0,1))
def lam(m):return cm(m)+delta(m)

def ecoeff(ks,r):
    E=[sp.Integer(1)]
    for i in range(1,r+1):
        E.append(sp.expand(sum(ks[j-1]*E[i-j]/sp.factorial(j-1) for j in range(1,i+1))/i))
    return E[r]

@dataclass
class Master:
    name:str
    power:int
    polynomial:sp.Expr
    factor:sp.Expr=sp.Integer(1)
    theta:sp.Expr|None=None
    spin_polynomial:sp.Expr=sp.Integer(1)
    alternating:bool=False
    constant:sp.Expr=sp.Integer(0)


def masters():
    L=[lam(i) for i in range(1,5)]
    F3=(9*L[0]**2+3*L[1])/2
    F4=sp.Rational(32,3)*L[0]**3+8*L[0]*L[1]+sp.Rational(2,3)*L[2]
    E=[];TH=[]
    for m in range(1,4):
        c=scalar('e'+str(m),(((-1)**m)*sp.polygamma(m,q)-sp.polygamma(m,1-q))/2)
        E.append(c+(psi(m,q,(1,1))+psi(m,1-q,(0,1)))/2)
    for m in range(1,3):
        c=scalar('t'+str(m),-(((-1)**m)*sp.polygamma(m+1,q)+sp.polygamma(m+1,1-q))/4)
        TH.append(c+(psi(m+1,q,(1,1))+psi(m+1,1-q,(0,1)))/4)
    mu1=(harm(q,(1,1))+harm(1-q,(0,1)))/2
    muc=scalar('muc',-(sp.polygamma(1,q)+sp.polygamma(1,1-q))/4)
    mu2=muc+(psi(1,q,(1,1))+psi(1,1-q,(0,1)))/4
    F31=9*L[0]*E[0]+sp.Rational(3,2)*E[1]
    F32=9*E[0]**2+9*L[0]*TH[0]+sp.Rational(3,2)*TH[1]
    F41=32*L[0]**2*E[0]+8*E[0]*L[1]+8*L[0]*E[1]+sp.Rational(2,3)*E[2]
    ans=[Master('Q',3,F3,sp.Rational(1,3)),Master('P4',4,-F4),
         Master('L',4,-(4*mu1*F4+F41)),
         Master('Z',3,((9*mu1**2+3*mu2)*F3+6*mu1*F31+F32)/9)]
    D1,D2,D3,D4=[delta(i) for i in range(1,5)]
    J1,J2,J3=[psi(i,2*q,(1,1))+psi(i,1,(0,1)) for i in range(1,4)]
    H=harm(2*q,(1,1))+harm(1,(0,1))
    reg=(D1**4/6-2*D1**3*y/3+5*D1**2*D2/4+3*D1**2*J1/4+D1**2*(-13*P/12-y*y/4)
         -5*D1*D2*y/2+5*D1*D3/12-3*D1*J1*y/2-D1*J2/4+D1*(4*P*y/3+y**3)
         +D2**2/2+3*D2*J1/4+D2*(-11*P/12+y*y/4)-5*D3*y/12-D4/24
         +H*(D1**3/2-3*D1**2*y/2+3*D1*D2/2-D1*P-3*D2*y/2+D3/2)
         -J1*P/2+J2*y/4-J3/4)
    bm,bn=gauss(2*q,(1,1)),gauss(1,(0,1))
    gg=sp.expand((1+bm)**2*(1+bn)**2-1)
    A=scalar('A',sp.polygamma(0,2*q)+sp.polygamma(0,1)-2*sp.polygamma(0,q))
    U=scalar('U',sp.polygamma(2,q))
    ans.append(Master('K',2,(P+y*y)**2/2*gg-reg,sp.Rational(1,4),constant=-A*U/4))
    # Primitive P5: two Gamma-moment channels, with no remaining measure poles.
    for theta,name,pol in [(2*q,'P5a',sp.Integer(1)),(2*q-1,'P5b',l*(l+4*q-2))]:
        kap=[]
        for m in range(1,7):
            hconst=2**m*(-1)**m*(sp.polygamma(m-1,theta-q)-(-1)**(m-1)*sp.polygamma(m-1,1-theta+q)
                              -sp.polygamma(m-1,-q)+(-1)**(m-1)*sp.polygamma(m-1,1+q))
            c=scalar('k'+str(m),(7-2**(m+1) if m%2 else 7)*((-1)**(m+1)*sp.polygamma(m-1,q)-sp.polygamma(m-1,1-q)+(1+(-1)**m)*sp.polygamma(m-1,1)))
            kap.append(c+7*delta(m)+2**m*(diff(m-1,theta+q,q,(1,2))+diff(m-1,1+q,1+q-theta,(1,2))))
        ans.append(Master(name,7,ecoeff(kap,6),1/(2*sp.gamma(2*q)**2),theta,pol,True))
    return ans

# Array representation uses raw Pochhammer sums (no factorials). add_factorials()
# converts it to the conventional /prod n! notation by inserting unit uppers.
@dataclass
class Term:
    dim:int
    pref:sp.Expr
    upper:list=field(default_factory=list)
    lower:list=field(default_factory=list)
    z:list=field(default_factory=list)
    poly:sp.Expr=sp.Integer(1)
    def row(self,up,a,v,count=1):
        v=tuple(v)
        if not any(v):return
        (self.upper if up else self.lower).extend([(sp.expand(a),v)]*count)
    def append_index(self):
        self.upper=[(a,v+(0,)) for a,v in self.upper]
        self.lower=[(a,v+(0,)) for a,v in self.lower]
        self.z.append(1);self.dim+=1
        return self.dim-1
    def copy(self):return Term(self.dim,self.pref,list(self.upper),list(self.lower),list(self.z),self.poly)


def form(a,vec,block,dim):
    if block==0:return sp.expand(a),(vec[1],)+(0,)*(dim-1)
    return sp.expand(a+vec[0]),tuple(vec)+(0,)*(dim-2)

def base(master,block):
    r=master.power
    if block==0:
        t=Term(1,master.factor,z=[1]);vl=(1,);vn=(1,)
        t.row(True,q,vl,r);t.row(True,1-q,vn,r)
        t.row(False,2*q,vl,r);t.row(False,1,vn,r)
        t.poly=master.spin_polynomial.subs({l:0,n:sp.Symbol('N0')})
    else:
        t=Term(2,master.factor*4*q/sp.Integer(2)**r,z=[-1 if master.alternating else 1,1]);vl=(1,1);vn=(0,1);vj=(1,0)
        if master.alternating:t.pref=-t.pref
        t.row(True,q+1,vl,r);t.row(True,1-q,vn,r)
        t.row(False,2*q+1,vl,r);t.row(False,1,vn,r)
        for a in [2*q+1,4*q-1]:t.row(True,a,vj)
        for a in [2*q,2]:t.row(False,a,vj)
        t.poly=master.spin_polynomial.subs({l:sp.Symbol('N0')+1,n:sp.Symbol('N1')})
    if master.theta is not None:
        theta=master.theta;shift=block
        t.pref*=sp.gamma(theta+q+shift)*sp.gamma(theta-q-shift)/(sp.gamma(q+shift)*sp.gamma(-q-shift))
        v=(2,) if block==0 else (1,2)
        for a in [theta+q+shift,1+q+shift]:t.row(True,a,v)
        for a in [q+shift,1+q-theta+shift]:t.row(False,a,v)
    return t


def reciprocal(t,a,v,power):
    t.pref/=a**power;t.row(True,a,v,power);t.row(False,a+1,v,power)

def insert(t,at,choice,block):
    old=t.dim;i=t.append_index()
    a,va=form(at.a,at.vec,block,t.dim)
    va=list(va);va[i]+=1;va=tuple(va)
    if at.kind=='D':
        b,vb=form(at.b,at.vec,block,t.dim);vb=list(vb);vb[i]+=1;vb=tuple(vb)
        m=at.order;t.pref*=(-1)**(m+1)*sp.factorial(m)*(b-a)
        reciprocal(t,a,va,m+1-choice);reciprocal(t,b,vb,choice+1)
    elif at.kind=='J':
        m=at.order;t.pref*=(-1)**(m+1)*sp.factorial(m);reciprocal(t,a,va,m+1)
    elif at.kind=='H':
        # H_N(a) = N sum_k 1/((a+k)(a+N+k)).
        vk=[0]*t.dim;vk[i]=1
        reciprocal(t,at.a,tuple(vk),1);reciprocal(t,a,va,1)
        if block==0:N=at.vec[1]*sp.Symbol('N0')
        else:N=at.vec[0]*(1+sp.Symbol('N0'))+at.vec[1]*sp.Symbol('N1')
        t.poly*=N
    elif at.kind=='B':
        # delta(c) = -q^2 sum (1-q)_k(1+q)_k/((2)_k(c)_{k+1}).
        vk=[0]*t.dim;vk[i]=1;vk=tuple(vk)
        for z in [1-q,1+q]:t.row(True,z,vk)
        t.row(False,2,vk)
        vbase=list(va);vbase[i]-=1;vbase=tuple(vbase)
        t.pref*=-q*q/a;t.row(True,a,vbase);t.row(False,a+1,va)
    else:raise ValueError(at.kind)


def shifted(t,shift):
    out=t.copy()
    out.upper=[];out.lower=[]
    for up,rows in [(True,t.upper),(False,t.lower)]:
        for a,v in rows:
            j=sum(x*y for x,y in zip(v,shift))
            if j:out.pref*=sp.rf(a,j) if up else 1/sp.rf(a,j)
            out.row(up,a+j,v)
    for i,j in enumerate(shift):
        if j:
            out.pref*=sp.factorial(j)*t.z[i]**j
            v=[0]*t.dim;v[i]=1
            out.row(True,j+1,v);out.row(False,1,v)
    return out

def polynomial_terms(t,block):
    bdim=1 if block==0 else 2
    N=sp.symbols('N0:'+str(bdim))
    poly=sp.Poly(sp.expand(t.poly),*N)
    for powers,c in poly.terms():
        if c==0:continue
        for js in product(*(range(k+1) for k in powers)):
            coef=c*sp.prod(stirling(k,j,kind=2) for k,j in zip(powers,js))
            if coef==0:continue
            out=shifted(t,tuple(js)+(0,)*(t.dim-bdim));out.pref*=coef;out.poly=1
            yield out

def canonical(t):
    # Convert to conventional Horn /prod n! and cancel matching parameters.
    up=Counter((str(a),v) for a,v in t.upper);dn=Counter((str(a),v) for a,v in t.lower)
    for i in range(t.dim):
        v=tuple(1 if j==i else 0 for j in range(t.dim));up[('1',v)]+=1
    for row in set(up)&set(dn):
        z=min(up[row],dn[row]);up[row]-=z;dn[row]-=z
    u=tuple(sorted((a,v,k) for (a,v),k in up.items() if k))
    d=tuple(sorted((a,v,k) for (a,v),k in dn.items() if k))
    return t.dim,u,d,tuple(t.z)

def compile_master(master,emit=True):
    print('Expanding',master.name,flush=True)
    expr=sp.expand(master.polynomial)
    av=sorted(expr.free_symbols&set(ATOMS),key=str)
    pol=sp.Poly(expr,*av)
    results=defaultdict(list);count=0
    for block in [0,1]:
        bt=base(master,block)
        if sp.expand(bt.poly)==0:continue
        for powers,coef in pol.terms():
            ats=[]
            for a,k in zip(av,powers):ats.extend([ATOMS[a]]*k)
            ranges=[range(at.order+1) if at.kind=='D' else range(1) for at in ats]
            for choices in product(*ranges):
                t=bt.copy();t.pref*=coef
                for at,ch in zip(ats,choices):insert(t,at,ch,block)
                for out in polynomial_terms(t,block):
                    if emit:results[canonical(out)].append(out.pref)
                    count+=1
        print(master.name,'block',block,'raw terms',count,flush=True)
    entries=[]
    if emit:
        for key,prefs in results.items():
            dim,up,dn,z=key
            # Keeping a factored Add avoids huge unnecessary expression expansion.
            pref=sp.factor_terms(sp.Add(*prefs))
            if pref==0:continue
            entries.append(dict(prefactor=str(pref),dimension=dim,
                                upper=[[a,list(v),k] for a,v,k in up],lower=[[a,list(v),k] for a,v,k in dn],arguments=list(z)))
    return dict(name=master.name,constant=str(master.constant),raw_terms=count,terms=entries,
                scope='Finite Horn representation; joint dimensional continuation of the complete K expression is prescribed.')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--masters',default='Q,P4,L,Z,K,P5a,P5b');ap.add_argument('--out',required=True);ap.add_argument('--count-only',action='store_true');args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    ms=masters();names=args.masters.split(',');summary=[]
    for m in ms:
        if m.name not in names:continue
        v=compile_master(m,not args.count_only)
        if not args.count_only:
            with gzip.open(out/(m.name+'_horn.json.gz'),'wt') as f:json.dump(v,f,separators=(',',':'))
        summary.append(dict(name=m.name,raw_terms=v['raw_terms'],functions=len(v['terms']),max_variables=max((t['dimension'] for t in v['terms']),default=0)))
        print(summary[-1],flush=True)
    (out/'scalar_parameters.json').write_text(json.dumps(SCALARS,indent=2))
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    (out/'atom_dictionary.json').write_text(json.dumps({str(k):dict(kind=v.kind,order=v.order,a=str(v.a),b=str(v.b),vec=v.vec) for k,v in ATOMS.items()},indent=2))

if __name__=='__main__':main()
