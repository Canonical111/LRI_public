"""Portable exact algebra; archived C1,...,C7 are inputs, not recomputed RG data."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sympy as s
import mpmath as mp

Y = s.Symbol('y')

def z(n: int):
    return s.Symbol(f'Z{n}')

def even_ratio(k: int):
    return (-1)**(k+1)*s.bernoulli(2*k)*2**(2*k-1)*6**k/s.factorial(2*k)

def canonical(expr):
    expr = s.sympify(expr)
    repl = {v: even_ratio(int(str(v)[1:])//2)*z(2)**(int(str(v)[1:])//2)
            for v in expr.free_symbols
            if str(v).startswith('Z') and str(v)[1:].isdigit()
            and int(str(v)[1:]) > 2 and int(str(v)[1:]) % 2 == 0}
    expr = s.expand(expr.subs(repl))
    p = s.Poly(expr, z(2))
    return s.expand(sum(co*(z(2)**i if i < 2 else z(2*i)/even_ratio(i))
                        for (i,), co in p.terms()))

def truncate(expr, n: int):
    p = s.Poly(s.expand(expr), Y)
    return s.Add(*(co*Y**i for (i,), co in p.terms() if i < n))

def mul(a, b, n: int):
    out = [s.Integer(0)]*n
    for i, ai in enumerate(a[:n]):
        if ai == 0:
            continue
        for j, bj in enumerate(b[:n-i]):
            if bj != 0:
                out[i+j] += ai*bj
    return [canonical(v) for v in out]

def binomial_power(a, exponent, n: int):
    assert a[0] == 1
    v = list(a[:n]); v[0] = s.Integer(0)
    out = [s.Integer(1)] + [s.Integer(0)]*(n-1)
    p = list(out)
    for k in range(1, n):
        p = mul(p, v, n)
        if all(q == 0 for q in p):
            break
        co = s.binomial(exponent, k)
        out = [canonical(aa + co*bb) for aa, bb in zip(out, p)]
    return out

def known_coefficients():
    return {1:s.Integer(-2), 2:s.Rational(1,2),
        3:s.Rational(39,16)+2*z(2),
        4:4-4*z(2)-8*z(3),
        5:s.Rational(11249,1024)-s.Rational(361,16)*z(2)+24*z(3)+s.Rational(49,2)*z(4),
        6:26-38*z(2)+104*z(3)-80*z(4)-272*z(5)+112*z(2)*z(3)}


KNOWN = known_coefficients()
KNOWN[7]=(s.Rational(1798583,32768)-s.Rational(90637,1024)*z(2)
          +s.Rational(453,4)*z(3)-s.Rational(16835,64)*z(4)
          +1224*z(5)-540*z(2)*z(3)+s.Rational(4335,8)*z(6)-320*z(3)**2)
c=KNOWN
z2,z3,z4,z5,z6,z7,z8=map(z,range(2,9))

def weight(expr,w):
    out=0
    for term in s.Add.make_args(canonical(expr)):
        wt=sum(int(str(q)[1:])*int(ex) for q,ex in term.as_powers_dict().items() if str(q).startswith('Z'))
        if wt==w: out+=term
    return s.expand(out)

def numerical(expr,digits=30):
    vals={v:s.zeta(int(str(v)[1:])) for v in expr.free_symbols
          if str(v).startswith('Z') and str(v)[1:].isdigit()}
    return str(s.N(expr.subs(vals),digits))

def inverse_coefficients():
    phi=[s.Integer(1)]+[-c[j+1]/2 for j in range(1,7)]
    return [canonical(s.Rational(8,m*2**m)*binomial_power(phi,-m,m-1)[m-2]) for m in range(2,9)]
g=inverse_coefficients()
