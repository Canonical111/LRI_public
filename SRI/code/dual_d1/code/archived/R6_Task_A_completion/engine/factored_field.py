"""Exact QQ multivariate fractions with factored denominators.

All denominator factors are checked by exact polynomial division. This adapter
avoids repeated general polynomial gcds in ordered hyperlog integration.
It does not evaluate or fit any integral numerically.
"""
from sympy.polys.rings import ring
from sympy.polys.domains import QQ
from functools import lru_cache
from math import comb

class Field:
    def __init__(self,names):
        vals=ring(names,QQ)
        self.ring=vals[0]; self.ngens=self.ring.ngens
        self.names=tuple(str(x) for x in self.ring.symbols)
        self.zero=Frac(self,self.ring.zero,{})
        self.one=Frac(self,self.ring.one,{})
        self.gens=tuple(Frac(self,x,{}) for x in vals[1:])
        self._factors={}
    def __call__(self,a):
        if isinstance(a,Frac):
            assert a.K is self
            return a
        if getattr(a,'ring',None) is self.ring:return Frac(self,a,{})
        if isinstance(a,str):return self.from_expr(a)
        return Frac(self,self.ring.ground_new(QQ.convert(a)),{})
    def from_expr(self,ex):
        # Restricted AST parser. Expanded numerators are collected termwise,
        # and factored denominators are inverted before any expansion.
        import ast
        if not isinstance(ex,str):ex=str(ex)
        tree=ast.parse(ex.replace('^','**'),mode='eval').body
        env=dict(zip(self.names,self.gens));ix={n:i for i,n in enumerate(self.names)}
        def integer(n):
            if isinstance(n,ast.Constant) and isinstance(n.value,int):return n.value
            if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub):return -integer(n.operand)
            if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.UAdd):return integer(n.operand)
            raise ValueError('not an integer literal')
        def monomial(n):
            coeff=QQ.one;mon=[0]*self.ngens;todo=[n]
            while todo:
                q=todo.pop()
                if isinstance(q,ast.Constant) and isinstance(q.value,int):coeff*=q.value
                elif isinstance(q,ast.Name):mon[ix[q.id]]+=1
                elif isinstance(q,ast.UnaryOp):
                    if isinstance(q.op,ast.USub):coeff=-coeff
                    elif not isinstance(q.op,ast.UAdd):return None
                    todo.append(q.operand)
                elif isinstance(q,ast.BinOp) and isinstance(q.op,ast.Mult):todo.extend((q.left,q.right))
                elif isinstance(q,ast.BinOp) and isinstance(q.op,ast.Pow) and isinstance(q.left,ast.Name):
                    nn=integer(q.right)
                    if nn<0:return None
                    mon[ix[q.left.id]]+=nn
                elif isinstance(q,ast.BinOp) and isinstance(q.op,ast.Div):
                    try:cc=integer(q.right)
                    except ValueError:return None
                    coeff/=cc;todo.append(q.left)
                else:return None
            return tuple(mon),coeff
        def polynomial(n):
            out={};todo=[(n,1)]
            while todo:
                q,sign=todo.pop()
                if isinstance(q,ast.BinOp) and isinstance(q.op,(ast.Add,ast.Sub)):
                    todo.append((q.left,sign));todo.append((q.right,sign if isinstance(q.op,ast.Add) else -sign))
                elif isinstance(q,ast.UnaryOp) and isinstance(q.op,(ast.USub,ast.UAdd)):
                    todo.append((q.operand,-sign if isinstance(q.op,ast.USub) else sign))
                else:
                    term=monomial(q)
                    if term is None:return None
                    m,c=term;out[m]=out.get(m,QQ.zero)+sign*c
            return self.ring.from_dict({m:c for m,c in out.items() if c})
        def inv_ev(n):
            if isinstance(n,ast.BinOp):
                if isinstance(n.op,ast.Mult):return inv_ev(n.left)*inv_ev(n.right)
                if isinstance(n.op,ast.Pow):return ev(n.left)**(-integer(n.right))
                if isinstance(n.op,ast.Div):return inv_ev(n.left)*ev(n.right)
            if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub):return -inv_ev(n.operand)
            return ev(n).inv()
        def ev(n):
            if isinstance(n,ast.Constant):return self(integer(n))
            if isinstance(n,ast.Name):return env[n.id]
            if isinstance(n,ast.UnaryOp):
                x=ev(n.operand)
                if isinstance(n.op,ast.USub):return -x
                if isinstance(n.op,ast.UAdd):return x
            if isinstance(n,ast.BinOp):
                if isinstance(n.op,(ast.Add,ast.Sub)):
                    p=polynomial(n)
                    if p is not None:return Frac(self,p,{})
                    a=ev(n.left);b=ev(n.right)
                    return a+b if isinstance(n.op,ast.Add) else a-b
                if isinstance(n.op,ast.Mult):return ev(n.left)*ev(n.right)
                if isinstance(n.op,ast.Div):return ev(n.left)*inv_ev(n.right)
                if isinstance(n.op,ast.Pow):return ev(n.left)**integer(n.right)
            raise ValueError(('unsupported expression',ast.dump(n)))
        return ev(tree)
    def factor(self,p):
        if not p:raise ZeroDivisionError
        key=tuple(p.items())
        if key in self._factors:return self._factors[key]
        # Linear polynomials and monomials need no general factorizer.
        if len(p)==1:
            (mon,c),=p.items();fac={}
            for i,n in enumerate(mon):
                if n:fac[self.ring.gens[i]]=n
            out=c,fac
        elif max(map(sum,p))<=1:
            lc=p.LC;out=lc,{p.quo_ground(lc):1}
        else:
            c,fs=p.factor_list();ds={}
            for f,m in fs:
                lc=f.LC;c*=lc**m;ds[f.quo_ground(lc)]=m
            out=c,ds
        if len(self._factors)>500:self._factors.clear()
        self._factors[key]=out
        return out

@lru_cache(maxsize=300)
def lininfo(f):
    # f is immutable in this module (PolyElement hashes its sorted monomials).
    ng=f.ring.ngens
    for mon,c in f.items():
        if sum(mon)>1:return None
    candidates=[i for i in range(ng) if any(mon[i] for mon in f)]
    if not candidates:return None
    # Choose the variable with least possible downstream expansion: lex first.
    idx=min(candidates)
    m=[0]*ng;m[idx]=1;b=f.get(tuple(m),QQ.zero)
    rest=f-f.ring.gens[idx]*b
    return idx,b,rest

@lru_cache(maxsize=150)
def modular_coeffs(p,idx):
    prime=1000000007
    values=[37,101,211,307,419,509,613,701,809,907,1009,1103,1201,1301,1409,1511]
    degs=[0]*p.ring.ngens
    for mon in p:
        for j,n in enumerate(mon):degs[j]=max(degs[j],n)
    pw=[[pow(values[j],n,prime) for n in range(degs[j]+1)] for j in range(p.ring.ngens)]
    cs=[0]*(degs[idx]+1)
    for mon,c in p.items():
        dd=int(c.denominator)%prime
        if not dd:return None
        val=int(c.numerator)%prime*pow(dd,-1,prime)%prime
        for j,n in enumerate(mon):
            if j!=idx and n:val=val*pw[j][n]%prime
        cs[mon[idx]]=(cs[mon[idx]]+val)%prime
    return cs,values,prime

def cannot_divide(p,f,info):
    if len(p)<12:return False
    idx,b,rest=info;spec=modular_coeffs(p,idx)
    if spec is None:return False
    cs,values,prime=spec
    bb=int(b.numerator)%prime*pow(int(b.denominator),-1,prime)%prime
    if not bb:return False
    rv=0
    for mon,c in rest.items():
        val=int(c.numerator)%prime*pow(int(c.denominator),-1,prime)%prime
        for j,n in enumerate(mon):
            if n:val=val*pow(values[j],n,prime)%prime
        rv=(rv+val)%prime
    root=-rv*pow(bb,-1,prime)%prime;out=0
    for c in reversed(cs):out=(out*root+c)%prime
    return out!=0

@lru_cache(maxsize=300)
def divide_linear_cached(p,f):
    info=lininfo(f)
    if info is None:
        q,r=p.div(f);return q,r
    idx,b,rest=info
    if cannot_divide(p,f,info):return p.ring.zero,p
    cs={}
    for mon,c in p.items():
        n=mon[idx];m=list(mon);m[idx]=0
        cs.setdefault(n,{})[tuple(m)]=c
    if not cs:return p,p
    dd=max(cs)
    if dd==0:return p.ring.zero,p
    co={n:p.ring.from_dict(d) for n,d in cs.items()}
    root=-rest.quo_ground(b)
    val=co.get(dd,p.ring.zero);qdict={}
    for n in range(dd,0,-1):
        for mon,c in val.items():
            mm=list(mon);mm[idx]+=n-1;qdict[tuple(mm)]=c/b
        val=val*root+co.get(n-1,p.ring.zero)
    return p.ring.from_dict(qdict),val

def cancel_factors(n,ds):
    ds=ds.copy()
    if not n:return n,{}
    for f,m in tuple(ds.items()):
        while m:
            if n==f:q,r=n.ring.one,n.ring.zero
            else:q,r=divide_linear_cached(n,f)
            if r:break
            n=q;m-=1
        if m:ds[f]=m
        else:del ds[f]
    return n,ds

class Frac:
    __slots__=('K','numer','denf','_den','_hash')
    def __init__(self,K,n,ds):
        self.K=K;self.numer=n;self.denf=ds;self._den=None;self._hash=None
    @property
    def denom(self):
        if self._den is None:
            d=self.K.ring.one
            for f,m in self.denf.items():d*=f**m
            self._den=d
        return self._den
    def __bool__(self):return bool(self.numer)
    def __neg__(self):return Frac(self.K,-self.numer,self.denf.copy())
    def __add__(self,other):
        other=self.K(other)
        if not self:return other
        if not other:return self
        ds=self.denf.copy();mul1=self.K.ring.one;mul2=self.K.ring.one
        common={}
        for f,m in other.denf.items():
            prev=ds.get(f,0)
            if m>prev:mul1*=f**(m-prev);ds[f]=m
            if prev:common[f]=min(m,prev)
        for f,m in self.denf.items():
            prev=other.denf.get(f,0)
            if m>prev:mul2*=f**(m-prev)
        n=self.numer*mul1+other.numer*mul2
        if not n:return self.K.zero
        if common:
            n,rem=cancel_factors(n,common)
            for f,m in common.items():
                ds[f]-=m-rem.get(f,0)
                if not ds[f]:del ds[f]
        return Frac(self.K,n,ds)
    __radd__=__add__
    def __sub__(self,other):return self+-self.K(other)
    def __rsub__(self,other):return self.K(other)+-self
    def __mul__(self,other):
        other=self.K(other)
        if not self or not other:return self.K.zero
        n1,d2=cancel_factors(self.numer,other.denf)
        n2,d1=cancel_factors(other.numer,self.denf)
        ds=d1.copy()
        for f,m in d2.items():ds[f]=ds.get(f,0)+m
        return Frac(self.K,n1*n2,ds)
    __rmul__=__mul__
    def inv(self):
        if not self:raise ZeroDivisionError
        c,ds=self.K.factor(self.numer)
        return Frac(self.K,self.denom.quo_ground(c),ds.copy())
    def __truediv__(self,other):return self*self.K(other).inv()
    def __rtruediv__(self,other):return self.K(other)*self.inv()
    def __pow__(self,n):
        n=int(n)
        if n<0:return self.inv()**(-n)
        if n==0:return self.K.one
        return Frac(self.K,self.numer**n,{f:m*n for f,m in self.denf.items()})
    def __eq__(self,other):
        try:other=self.K(other)
        except (ValueError,TypeError):return False
        return self.numer==other.numer and self.denf==other.denf
    def __hash__(self):
        if self._hash is None:self._hash=hash((self.numer,frozenset(self.denf.items())))
        return self._hash
    def __int__(self):
        if self.denf or not self.numer.is_ground:raise ValueError(self)
        c=self.numer.get((0,)*self.K.ngens,QQ.zero)
        if c.denominator!=1:raise ValueError(self)
        return int(c)
    def diff(self,x):
        i=self.K.gens.index(x);g=self.K.ring.gens[i]
        out=Frac(self.K,self.numer.diff(g),self.denf.copy())
        for f,m in self.denf.items():
            df=f.diff(g)
            if df:out-=self*self.K(df)*m/self.K(f)
        n,ds=cancel_factors(out.numer,out.denf)
        return Frac(self.K,n,ds)
    def to_poly(self):
        if self.denf:raise ValueError('not polynomial')
        return self.numer
    def as_expr(self):
        return self.numer.as_expr()/self.denom.as_expr()
    def __str__(self):
        if not self.denf:return str(self.numer)
        den='*'.join(f'({f})'+(f'**{m}' if m!=1 else '') for f,m in sorted(self.denf.items(),key=lambda x:str(x[0])))
        return f'({self.numer})/({den})'
    __repr__=__str__

def field(names,domain):
    K=Field(names);return (K,)+K.gens
