"""Check the complete map from archived exact RG inputs to the certificate.

Requires SymPy. This script verifies the trace assembly and the exact
conversion to period words. It does not reintegrate the original kink kernels.
The preceding raw integration archive is supplied separately in the bundle.
"""
from __future__ import annotations
from pathlib import Path
from fractions import Fraction as Q
from collections import defaultdict,Counter
from functools import lru_cache
import re,json,hashlib,time
import sympy as s
from verify_certificate_core import shuffle
root=Path(__file__).resolve().parent
src=root.parent/'input_expressions'
start=time.time()
read=lambda name:s.sympify((src/name).read_text())
a,p,A,E,c,f,q,b,G,k=[read(n+'_check_symbolic.expr') for n in ['a','p','A','E','c','f','q','b','G','k']]
V,R,J,L,M,N=[read(n+'_symbolic.expr') for n in ['V','R','J','L','M','N']]
B=A/8-E/2-G/4+(a*a-a*b)/8+a*c/16-a*p/2-b*c/8+c*c/64-c*f/32-c*p/8-f/32-k/32-q/8
assembled=s.expand_log(B+2*V+R+3*J/8-L/8+M/4+N/16,force=True).expand()
assert s.expand(assembled-read('C6_symbolic.expr'))==0, 'Archived trace assembly does not match'
Z2,Z3,Z4,Z5=s.symbols('Z2 Z3 Z4 Z5')
candidate=26-38*Z2+104*Z3-80*Z4-272*Z5+112*Z2*Z3
assert s.expand(candidate-read('C6_candidate.expr'))==0
expr=s.expand(assembled-candidate)
assert s.expand(expr-read('C6_difference_symbolic.expr'))==0
expr=s.expand(expr.subs({s.pi**6:216*Z2**3,s.pi**4:36*Z2**2,s.pi**2:6*Z2}))

def multiply(left:dict,right:dict)->dict:
    out=defaultdict(Q)
    for a,c in left.items():
        for b,d in right.items():
            for word,count in shuffle(a,b).items():out[word]+=c*d*count
    return {w:c for w,c in out.items() if c}

@lru_cache(None)
def lift(ex)->dict:
    if ex.is_Rational:return {():Q(int(ex.p),int(ex.q))} if ex else {}
    if ex.is_Add:
        out=defaultdict(Q)
        for term in ex.args:
            for word,coef in lift(term).items():out[word]+=coef
        return {w:c for w,c in out.items() if c}
    if ex.is_Mul:
        out={():Q(1)}
        for factor in ex.args:out=multiply(out,lift(factor))
        return out
    if ex.is_Pow and ex.exp.is_Integer and ex.exp>=0:
        out={():Q(1)}
        for _ in range(int(ex.exp)):out=multiply(out,lift(ex.base))
        return out
    if ex.is_Symbol:
        name=str(ex)
        if name.startswith('R_'):
            tokens=name.split('_')[1:]
            if not tokens or any(not re.fullmatch(r'(?:0|m[1-9][0-9]*)',token) for token in tokens):
                raise ValueError(f'Invalid period name: {name}')
            return {tuple(0 if z=='0' else int(z[1:]) for z in tokens):Q(1)}
        if name in ('Z2','Z3','Z4','Z5'):
            n=int(name[1:])
            return {(2,)+(1,)*(n-1):-Q(2**(n-1),2**(n-1)-1)}
    if ex.func==s.log and ex.args[0].is_Rational and ex.args[0]>0:
        arg=ex.args[0];out=defaultdict(Q)
        for prime,power in s.factorint(int(arg.p)).items():out[(int(prime),)]-=int(power)
        for prime,power in s.factorint(int(arg.q)).items():out[(int(prime),)]+=int(power)
        return {w:c for w,c in out.items() if c}
    if ex.func==s.polylog:
        n,arg=ex.args;ratio=1-arg
        if n.is_Integer and n>=2 and ratio.is_Rational and ratio>0:
            a,b=int(ratio.p),int(ratio.q);out=defaultdict(Q)
            out[(a,)+(b,)*(int(n)-1)]+=1
            out[(b,)*int(n)]-=1
            return {w:c for w,c in out.items() if c}
    raise ValueError(f'Unsupported exact expression: {ex}')

words=lift(expr)
assert all(len(w) in (2,3,4,5) and all(0<=a<=10 for a in w) for w in words)
expected={tuple(w):Q(c) for w,c in json.loads((root/'C6_linear_words.json').read_text())}
assert words==expected, 'The canonical word vector differs'
for n in range(2,6):
    cert=json.loads((root/f'C6_certificate_w{n}.json').read_text())
    target={tuple(w):Q(c) for w,c in cert['target']}
    assert target=={w:c for w,c in words.items() if len(w)==n}
report={'status':'exact RG assembly and complete period-target map verified',
        'weight_counts':dict(sorted(Counter(map(len,words)).items())),
        'target_words':len(words),'reintegrated_raw_kinks':False,
        'inputs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(src.glob('*.expr'))},
        'seconds':time.time()-start}
(root/'target_rebuild_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
