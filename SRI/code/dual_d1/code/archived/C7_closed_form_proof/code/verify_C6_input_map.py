#!/usr/bin/env python3
"""Exact independent map from archived RG coefficients to the C6 certificate.

Standard-library only. Expressions are parsed as a restricted AST, never eval'd.
Every log, polylog and product is lifted directly into the rational shuffle
algebra. No numerical periods, fitted coefficients, or symbolic simplifier are
used. This verifies the period/input layer, not the original kink integrations.
"""
from __future__ import annotations
import argparse, ast, hashlib, json, re, time, sys
sys.setrecursionlimit(max(sys.getrecursionlimit(), 20000))
from collections import defaultdict
from fractions import Fraction as Q
from functools import lru_cache
from pathlib import Path

Word=tuple[int,...]
Vec=dict[Word,Q]

def clean(a:Vec)->Vec: return {w:c for w,c in a.items() if c}
def add(a:Vec,b:Vec,scale:Q=Q(1))->Vec:
    out=defaultdict(Q,a)
    for w,c in b.items():out[w]+=scale*c
    return clean(out)
def scale(a:Vec,c:Q)->Vec:return clean({w:x*c for w,x in a.items()})
@lru_cache(None)
def shuffle(a:Word,b:Word)->tuple[tuple[Word,int],...]:
    if not a:return ((b,1),)
    if not b:return ((a,1),)
    d=defaultdict(int)
    for w,c in shuffle(a[1:],b):d[(a[0],)+w]+=c
    for w,c in shuffle(a,b[1:]):d[(b[0],)+w]+=c
    return tuple(d.items())
def mul(a:Vec,b:Vec)->Vec:
    out=defaultdict(Q)
    for x,c in a.items():
        for y,d in b.items():
            for w,n in shuffle(x,y):out[w]+=c*d*n
    return clean(out)
def power(a:Vec,n:int)->Vec:
    if n<0:raise ValueError('Negative nonconstant power')
    v={():Q(1)}
    for _ in range(n):v=mul(v,a)
    return v

def rational(n:ast.AST)->Q:
    if isinstance(n,ast.Constant) and type(n.value) is int:return Q(n.value)
    if isinstance(n,ast.UnaryOp):
        if isinstance(n.op,ast.USub):return -rational(n.operand)
        if isinstance(n.op,ast.UAdd):return rational(n.operand)
    if isinstance(n,ast.BinOp):
        a,b=rational(n.left),rational(n.right)
        if isinstance(n.op,ast.Add):return a+b
        if isinstance(n.op,ast.Sub):return a-b
        if isinstance(n.op,ast.Mult):return a*b
        if isinstance(n.op,ast.Div):return a/b
        if isinstance(n.op,ast.Pow) and b.denominator==1:return a**int(b)
    raise ValueError('Expected exact rational: '+ast.dump(n))

def primes(n:int)->dict[int,int]:
    ans={};p=2
    while p*p<=n:
        while n%p==0:ans[p]=ans.get(p,0)+1;n//=p
        p+=1
    if n>1:ans[n]=ans.get(n,0)+1
    return ans

def zeta(n:int)->Vec:
    if n<2:raise ValueError('Divergent zeta')
    return {(2,)+(1,)*(n-1):-Q(2**(n-1),2**(n-1)-1)}

def lift(n:ast.AST)->Vec:
    if isinstance(n,ast.Constant):return {():rational(n)} if rational(n) else {}
    if isinstance(n,ast.Name):
        if re.fullmatch(r'Z[2-9][0-9]*',n.id):return zeta(int(n.id[1:]))
        if n.id.startswith('R_'):
            tokens=n.id.split('_')[1:]
            if any(not re.fullmatch(r'(0|m[1-9][0-9]*)',x) for x in tokens):raise ValueError(n.id)
            return {tuple(0 if x=='0' else int(x[1:]) for x in tokens):Q(1)}
        raise ValueError('Unexpected name '+n.id)
    if isinstance(n,ast.UnaryOp):
        return scale(lift(n.operand),Q(-1) if isinstance(n.op,ast.USub) else Q(1))
    if isinstance(n,ast.BinOp):
        if isinstance(n.op,ast.Add):return add(lift(n.left),lift(n.right))
        if isinstance(n.op,ast.Sub):return add(lift(n.left),lift(n.right),Q(-1))
        if isinstance(n.op,ast.Mult):return mul(lift(n.left),lift(n.right))
        if isinstance(n.op,ast.Div):return scale(lift(n.left),1/rational(n.right))
        if isinstance(n.op,ast.Pow):
            p=rational(n.right)
            if p.denominator!=1:raise ValueError('Noninteger power')
            k=int(p)
            if isinstance(n.left,ast.Name) and n.left.id=='pi':
                if k%2:raise ValueError('Odd power of pi')
                return power(scale(zeta(2),Q(6)),k//2)
            return power(lift(n.left),k)
    if isinstance(n,ast.Call) and isinstance(n.func,ast.Name):
        if n.func.id=='log' and len(n.args)==1:
            x=rational(n.args[0]);out=defaultdict(Q)
            if x<=0:raise ValueError('Nonpositive logarithm')
            for p,k in primes(x.numerator).items():out[(p,)]-=k
            for p,k in primes(x.denominator).items():out[(p,)]+=k
            return clean(out)
        if n.func.id=='polylog' and len(n.args)==2:
            k=rational(n.args[0]);r=rational(n.args[1]);v=1-r
            if k.denominator!=1 or k<2 or v<=0:raise ValueError('Unsupported polylogarithm')
            k=int(k);a,b=v.numerator,v.denominator
            return add({(a,)+(b,)*(k-1):Q(1)},{(b,)*k:Q(1)},Q(-1))
    raise ValueError('Unsupported expression '+ast.dump(n))

def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--report',type=Path)
    args=p.parse_args();start=time.perf_counter();root=args.root.resolve();stage=root/'stages/C6_exact';src=stage/'input_expressions'
    def read(name:str)->Vec:return lift(ast.parse((src/name).read_text(),mode='eval').body)
    co={n:read(n+'_check_symbolic.expr') for n in ['a','p','A','E','c','f','q','b','G','k']}
    co.update({n:read(n+'_symbolic.expr') for n in ['V','R','J','L','M','N']})
    # Parse the rational trace polynomial and evaluate it in the lifted algebra.
    formula='A/8-E/2-G/4+(a*a-a*b)/8+a*c/16-a*p/2-b*c/8+c*c/64-c*f/32-c*p/8-f/32-k/32-q/8+2*V+R+3*J/8-L/8+M/4+N/16'
    def assemble(n:ast.AST)->Vec:
        if isinstance(n,ast.Name):return co[n.id]
        if isinstance(n,ast.Constant):return {():rational(n)}
        if isinstance(n,ast.BinOp):
            if isinstance(n.op,ast.Add):return add(assemble(n.left),assemble(n.right))
            if isinstance(n.op,ast.Sub):return add(assemble(n.left),assemble(n.right),Q(-1))
            if isinstance(n.op,ast.Mult):return mul(assemble(n.left),assemble(n.right))
            if isinstance(n.op,ast.Div):return scale(assemble(n.left),1/rational(n.right))
        raise ValueError(ast.dump(n))
    assembled=assemble(ast.parse(formula,mode='eval').body)
    assert assembled==read('C6_symbolic.expr'),'Trace does not map to archived C6'
    difference=add(assembled,read('C6_candidate.expr'),Q(-1))
    assert difference==read('C6_difference_symbolic.expr'),'Difference archive mismatch'
    target={tuple(w):Q(c) for w,c in json.loads((stage/'proof/C6_linear_words.json').read_text())}
    assert difference==target,'Canonical word target mismatch'
    counts={n:sum(len(w)==n for w in target) for n in range(2,6)}
    for n in range(2,6):
        cert=json.loads((stage/f'proof/C6_certificate_w{n}.json').read_text())
        assert {tuple(w):Q(c) for w,c in cert['target']}=={w:c for w,c in target.items() if len(w)==n}
    report={'status':'PASS','method':'restricted AST directly to exact rational shuffle algebra','weight_counts':counts,'target_words':len(target),'raw_integrals_reintegrated':False,'numerical_periods_used':False,'seconds':time.perf_counter()-start,'input_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(src.glob('*.expr'))}}
    text=json.dumps(report,indent=2);print(text)
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(text+'\n')
if __name__=='__main__':main()
