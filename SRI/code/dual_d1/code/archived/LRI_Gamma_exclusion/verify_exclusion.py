#!/usr/bin/env python3
"""Exact rational interval certificate for the Gamma-family exclusion.
Uses only Python standard library. The optional SymPy script regenerates
endpoint_exact_expressions.json from the explicit Gamma model.
"""
from fractions import Fraction as Q
from dataclasses import dataclass
import ast, json
from pathlib import Path
from decimal import Decimal,localcontext

@dataclass(frozen=True)
class I:
    lo: Q
    hi: Q
    def __init__(self,lo,hi=None):
        object.__setattr__(self,'lo',Q(lo));object.__setattr__(self,'hi',Q(lo if hi is None else hi))
        assert self.lo<=self.hi
    @staticmethod
    def co(x):return x if isinstance(x,I) else I(x)
    def __add__(self,b):
        b=self.co(b);return I(self.lo+b.lo,self.hi+b.hi)
    __radd__=__add__
    def __neg__(self):return I(-self.hi,-self.lo)
    def __sub__(self,b):return self+-self.co(b)
    def __rsub__(self,b):return self.co(b)+-self
    def __mul__(self,b):
        b=self.co(b);v=[self.lo*b.lo,self.lo*b.hi,self.hi*b.lo,self.hi*b.hi];return I(min(v),max(v))
    __rmul__=__mul__
    def __truediv__(self,b):
        b=self.co(b);assert not b.lo<=0<=b.hi
        return self*I(1/b.hi,1/b.lo)
    def __rtruediv__(self,b):return self.co(b)/self
    def __pow__(self,n):
        assert isinstance(n,int)
        if n<0:return 1/self**(-n)
        out=I(1)
        for _ in range(n):out=out*self
        return out

def atan_bounds(r,N):
    val=sum(((-1)**k*r**(2*k+1)/Q(2*k+1) for k in range(N)),Q(0))
    nxt=(-1)**N*r**(2*N+1)/Q(2*N+1)
    return I(min(val,val+nxt),max(val,val+nxt))
p=16*atan_bounds(Q(1,5),24)-4*atan_bounds(Q(1,239),8)
r=Q(1,3);N=30
l0=2*sum((r**(2*k+1)/Q(2*k+1) for k in range(N)),Q(0))
l=I(l0,l0+2*r**(2*N+1)/(Q(2*N+1)*(1-r*r)))
N=1000
z0=sum((Q(1,k**3) for k in range(1,N+1)),Q(0))
z=I(z0+Q(1,2*(N+1)**2),z0+Q(1,2*N*N))

root=Path(__file__).resolve().parent
expr=json.loads((root/'endpoint_exact_expressions.json').read_text())
def calc(node):
    if isinstance(node,ast.Constant):
        assert isinstance(node.value,int);return I(node.value)
    if isinstance(node,ast.Name):return {'p':p,'l':l,'z':z}[node.id]
    if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.USub):return -calc(node.operand)
    if isinstance(node,ast.BinOp):
        a=calc(node.left)
        if isinstance(node.op,ast.Pow):
            n=ast.literal_eval(node.right);return a**n
        b=calc(node.right)
        if isinstance(node.op,ast.Add):return a+b
        if isinstance(node.op,ast.Sub):return a-b
        if isinstance(node.op,ast.Mult):return a*b
        if isinstance(node.op,ast.Div):return a/b
    raise ValueError(ast.dump(node))
vals={k:calc(ast.parse(v,mode='eval').body) for k,v in expr.items()}
A=p+4*l
curv=I(Q(4,3))+Q(32,9)*A
D,B0,B1,E0,E1,C0,C1=(vals[k] for k in ['D','B0','B1','E0','E1','C0','C1'])
assert D.lo>0 and B1.lo>0
T=(curv*D-B0)/B1
third=(C0+C1*T-3*curv*(E0+E1*T))/D
b_req=(third-Q(64,3)*A)/384
alpha_req=81*(b_req+(A*A+p*p/3)/108)
alpha_min=3*p**3+12*p**2
b_min=alpha_min/81-(A*A+p*p/3)/108
third_min=Q(64,3)*A+384*b_min
assert vals['base_endpoint'].hi < -1
assert alpha_req.lo>197 and alpha_req.hi<198
assert alpha_min.lo>211
assert third.hi<927
assert third_min.lo>992
assert third.hi<third_min.lo
assert T.lo>2122 and T.hi<2123

def dec(q):
    with localcontext() as c:
        c.prec=28
        return str(Decimal(q.numerator)/Decimal(q.denominator))
def rec(v):return {'lower_display':dec(v.lo),'upper_display':dec(v.hi)}
report={
 'scope':'Proof by exact rational interval arithmetic; displayed endpoints rounded only for readability. Strict assertions used exact fractions.',
 'constant_constructions':{'pi':'Machin alternating sums, 24 and 8 terms','log2':'atanh(1/3) positive series, 30 terms and geometric remainder','zeta3':'1000-term rational sum and integral remainder bounds'},
 'bounds':{k:rec(v) for k,v in {'pi':p,'log2':l,'zeta3':z,'unmodified_endpoint':vals['base_endpoint'],'Sy':D,'B1':B1,'tau_curvature':T,'trial_third':third,'required_alphaI4':alpha_req,'physical_alphaI4_lower_bound':alpha_min,'physical_third_lower_bound':third_min}.items()},
 'exact_assertions':{'unmodified_nonzero':True,'unique_real_tau':True,'required_alpha_between_197_and_198':True,'physical_alpha_greater_than_211':True,'trial_third_less_than_927':True,'physical_third_greater_than_992':True,'disjoint_intervals':True},
 'qualification':'Excludes a globally exact C3 thermal branch satisfying the published GFF beta-function coefficients. Does not alone refute equality of all coefficients of an SRI asymptotic series with beyond-all-orders corrections.'}
(root/'interval_certificate.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
