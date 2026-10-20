"""Outward-rounded real intervals, implemented using integers only.

Every endpoint is an integer divided by 2**BITS.  Neither mpmath nor machine
floating point participates in constructing an interval.  Set precision before
creating any interval; do not mix objects from different precisions.
"""
from __future__ import annotations
from fractions import Fraction as F
from math import isqrt
from functools import lru_cache
import ast

BITS = 1024
SCALE = 1 << BITS

def set_precision(bits: int) -> None:
    global BITS, SCALE
    if bits < 64: raise ValueError('at least 64 bits required')
    BITS, SCALE = bits, 1 << bits
    log2.cache_clear()

def ceildiv(a: int, b: int) -> int:
    return -((-a)//b)

class I:
    __slots__ = ('lo', 'hi')
    def __init__(self, x=0):
        if isinstance(x,I): self.lo,self.hi=x.lo,x.hi; return
        x=F(x)
        self.lo=x.numerator*SCALE//x.denominator
        self.hi=ceildiv(x.numerator*SCALE,x.denominator)
    @classmethod
    def raw(cls,lo,hi):
        if lo>hi: raise ValueError('reversed interval')
        out=object.__new__(cls); out.lo,out.hi=int(lo),int(hi); return out
    @classmethod
    def bounds(cls,lo,hi):
        return cls.raw(I(lo).lo,I(hi).hi)
    def __add__(self,other):
        b=I(other);return I.raw(self.lo+b.lo,self.hi+b.hi)
    __radd__=__add__
    def __neg__(self):return I.raw(-self.hi,-self.lo)
    def __sub__(self,other):return self+-I(other)
    def __rsub__(self,other):return I(other)+-self
    def __mul__(self,other):
        b=I(other); p=(self.lo*b.lo,self.lo*b.hi,self.hi*b.lo,self.hi*b.hi)
        return I.raw(min(p)//SCALE,ceildiv(max(p),SCALE))
    __rmul__=__mul__
    def inv(self):
        if self.lo<=0<=self.hi:raise ZeroDivisionError('interval contains zero')
        return I.raw(SCALE*SCALE//self.hi,ceildiv(SCALE*SCALE,self.lo))
    def __truediv__(self,other):
        b=I(other)
        if b.lo<=0<=b.hi:raise ZeroDivisionError('interval contains zero')
        numerators=[self.lo*SCALE,self.hi*SCALE]
        floors=[a//d for a in numerators for d in [b.lo,b.hi]]
        ceils=[ceildiv(a,d) for a in numerators for d in [b.lo,b.hi]]
        return I.raw(min(floors),max(ceils))
    def __rtruediv__(self,other):return I(other)/self
    def __pow__(self,k):
        if isinstance(k,F) and k.denominator==2:
            return self.sqrt()**k.numerator
        if isinstance(k,F) and k.denominator==1:k=k.numerator
        if not isinstance(k,int):raise TypeError('only integer and half-integer powers')
        if k<0:return self.inv()**(-k)
        a=I(1);b=self
        while k:
            if k&1:a=a*b
            k>>=1
            if k:b=b*b
        return a
    def sqrt(self):
        if self.lo<0:raise ValueError('negative interval in sqrt')
        lo=isqrt(self.lo*SCALE); n=self.hi*SCALE; hi=isqrt(n)
        if hi*hi<n:hi+=1
        return I.raw(lo,hi)
    def absolute_upper(self):return F(max(abs(self.lo),abs(self.hi)),SCALE)
    def width(self):return F(self.hi-self.lo,SCALE)
    def lower(self):return F(self.lo,SCALE)
    def upper(self):return F(self.hi,SCALE)
    def inflate(self,error):
        ee=I(error).hi
        if ee<0:raise ValueError('negative radius')
        return I.raw(self.lo-ee,self.hi+ee)
    def contains(self,x):
        x=F(x);return self.lo*x.denominator<=x.numerator*SCALE<=self.hi*x.denominator
    def package(self,places=150):
        p=10**places
        ll=self.lo*p//SCALE;hh=ceildiv(self.hi*p,SCALE)
        def dec(n):
            sign='-' if n<0 else '';n=abs(n)
            a,b=divmod(n,p)
            return f'{sign}{a}.{b:0{places}d}'
        return {'lower_numerator':str(self.lo),'upper_numerator':str(self.hi),
                'denominator_power_of_two':BITS,'decimal_lower':dec(ll),
                'decimal_upper':dec(hh),'decimal_places':places,
                'width_numerator':str(self.hi-self.lo)}
    def __repr__(self):
        return str(self.package(20)['decimal_lower'])+'..'+str(self.package(20)['decimal_upper'])

def log_core(y: I) -> I:
    """log(y), for a positive interval close to [1,2], by atanh."""
    z=(y-1)/(y+1)
    q=z.absolute_upper()
    if q>=F(1,2):raise ValueError('insufficient log range reduction')
    zz=z*z;term=z;total=I(0)
    # q <= 1/3 normally; this count also safely handles all q<1/2.
    M=BITS//2+12
    for j in range(M):
        total+=term/(2*j+1)
        term*=zz
    error=2*q**(2*M+1)/((2*M+1)*(1-q*q))
    return (2*total).inflate(error)

@lru_cache(None)
def log2():return log_core(I(2))

def log(x) -> I:
    x=I(x)
    if x.lo<=0:raise ValueError('log needs strictly positive interval')
    k=x.lo.bit_length()-1-BITS
    if k>=0:y=x/(1<<k)
    else:y=x*(1<<(-k))
    return log_core(y)+k*log2()

def exp(x) -> I:
    x=I(x);k=0
    while x.absolute_upper()>F(1,2):x=x/2;k+=1
    q=x.absolute_upper();term=I(1);out=I(1);j=0
    # exp(q)<2 and the factorial Taylor bound controls the discarded tail.
    bound=F(1)
    target=F(1,1<<(BITS+16))
    while True:
        j+=1;term=term*x/j;out+=term
        bound=2*q**(j+1)
        import math
        bound/=math.factorial(j+1)
        if bound<target:break
    out=out.inflate(bound)
    for _ in range(k):out=out*out
    return out

def machin_pi(terms=None) -> I:
    if terms is None:terms=BITS//4+20
    def atan_inv(q):
        ss=I(0)
        for j in range(terms):ss+=F((-1)**j,(2*j+1)*q**(2*j+1))
        e=F(1,(2*terms+1)*q**(2*terms+1))
        return ss+I.bounds(0,e) if terms%2==0 else ss+I.bounds(-e,0)
    return 16*atan_inv(5)-4*atan_inv(239)

def evaluate(expression: str, env: dict) -> I:
    """Evaluate a small, explicitly whitelisted arithmetic grammar."""
    def const(node):
        if isinstance(node,ast.Constant) and isinstance(node.value,int):return F(node.value)
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.USub):return -const(node.operand)
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Div):return const(node.left)/const(node.right)
        raise ValueError('power must be an integer or rational literal')
    def go(t):
        if isinstance(t,ast.Constant) and isinstance(t.value,int):return I(t.value)
        if isinstance(t,ast.Name) and t.id in env:return I(env[t.id])
        if isinstance(t,ast.UnaryOp):
            if isinstance(t.op,ast.USub):return -go(t.operand)
            if isinstance(t.op,ast.UAdd):return go(t.operand)
        if isinstance(t,ast.BinOp):
            a=go(t.left)
            if isinstance(t.op,ast.Pow):return a**const(t.right)
            b=go(t.right)
            if isinstance(t.op,ast.Add):return a+b
            if isinstance(t.op,ast.Sub):return a-b
            if isinstance(t.op,ast.Mult):return a*b
            if isinstance(t.op,ast.Div):return a/b
        if isinstance(t,ast.Call) and isinstance(t.func,ast.Name) and len(t.args)==1:
            a=go(t.args[0])
            if t.func.id=='sqrt':return a.sqrt()
            if t.func.id=='log':return log(a)
        raise ValueError('unsupported arithmetic expression: '+ast.dump(t))
    return go(ast.parse(expression,mode='eval').body)
