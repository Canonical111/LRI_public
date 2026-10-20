"""Exact primitive, beta-moment, and finite-part algebra checks.
This script checks only the lower inputs; the full period identity is proved by the separate certificate.
"""
import contextlib,io
import sympy as s
from pathlib import Path
buf=io.StringIO()
with contextlib.redirect_stdout(buf):
    import endpoint3_exact as ep3
    import endpoint4_exact as ep4
r=s.symbols('r',positive=True)
z2,z3,z4=ep3.z2,ep3.z3,ep3.z4
assert s.expand(ep3.final-(-108+60*z2+22*z3-34*z4+16*s.log(2)))==0
assert s.expand(ep4.result-(6-12*z2-54*z3-25*z4))==0
l=s.log(r);m=s.log(1-r)
flog=-(l+1)/r+l/(1-r)-l+m+l*l-2*l*m-2*s.polylog(2,r)
res=s.diff(flog,r)-l/(r*r*(1-r)**2)
res=res.replace(lambda x:x.func==s.polylog and x.args[0]==1,lambda x:-s.log(1-x.args[1]))
assert s.simplify(s.expand_log(res,force=True))==0
F=r*(s.log(1+r)-l)-2*s.polylog(2,-r)-l*l+(l+1-s.log(1+r))/r+l
res=s.diff(F,r)-(1+2/r+1/r**2)*(s.log(1+r)-l)
res=res.replace(lambda x:x.func==s.polylog and x.args[0]==1,lambda x:-s.log(1-x.args[1]))
assert s.simplify(s.expand_log(res,force=True))==0
# The angular primitive for the current-weighted four-kink kernel.
y,t=s.symbols('y t',positive=True)
rr=1-y-t
kernel=(y+rr)*(y+t)**2*(t+rr)**2/(y*y*t*t*rr*rr)
e=s.symbols('e',positive=True)
A=(y+1)*(y*y+1)/(y*y*(1-y))
M=(1+1/y)*(1/e-1/(1-y-e))+A*s.log((1-y-e)/e)
# Leibniz differentiation of the exact angular integral fixes the lower/upper terms;
# it vanishes at coincident limits e=(1-y)/2.
assert s.simplify(s.diff(M,e)+kernel.subs(t,e)+kernel.subs(t,1-y-e))==0
assert s.simplify(M.subs(e,(1-y)/2))==0
print(buf.getvalue())
print('PASS: endpoint3 exact finite-part assembly')
print('PASS: endpoint4 exact finite-part assembly including radial log shift')
print('PASS: primitive derivatives for both endpoint3 inner integrals')
print('PASS: exact angular reduction of the current-weighted four-kink kernel')
print('The full D3 period identity is verified separately by verify_certificate.py.')
