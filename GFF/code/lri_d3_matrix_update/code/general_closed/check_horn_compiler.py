"""Structural audit of the finite Horn parameter arrays and polynomial shifts.
Checks normalized coefficients as exact rational numbers, not a truncated
high-dimensional analytic continuation. Scalar Bell/master identities are
checked separately at high precision.
"""
from pathlib import Path
from itertools import product
import json,random
from fractions import Fraction
import sympy as sp
import mpmath as mp
import horn_compiler as h
mp.mp.dps=50
random.seed(73)
counts={'coefficients':0,'sampled_rows':0,'shifts':0};maxshift=mp.mpf(0)
QV=sp.Rational(3,10)
def val(a):
 z=sp.cancel(sp.sympify(a,locals={'q':h.q}).subs(h.q,QV));return Fraction(int(z.p),int(z.q))
def rf(a,k):
 a=val(a);r=Fraction(1)
 for j in range(k):r*=a+j
 return r

def check_array(t):
 key=h.canonical(t);dim,up,dn,z=key
 for k in [tuple(0 for _ in range(dim)),tuple((j+counts['sampled_rows'])%3 for j in range(dim))]:
  raw=Fraction(1)
  for a,v in t.upper:raw*=rf(a,sum(x*y for x,y in zip(v,k)))
  for a,v in t.lower:raw/=rf(a,sum(x*y for x,y in zip(v,k)))
  arr=Fraction(1)
  for a,v,p in up:arr*=rf(a,sum(x*y for x,y in zip(v,k)))**p
  for a,v,p in dn:arr/=rf(a,sum(x*y for x,y in zip(v,k)))**p
  for j in k:arr/=int(sp.factorial(j))
  assert raw==arr
  counts['coefficients']+=1
 counts['sampled_rows']+=1

def mpval(expr):
 return mp.mpf(str(sp.N(sp.sympify(expr,locals={'q':h.q}).subs(h.q,QV),55)))
def rawcoeff(t,k):
 v=mpval(t.pref)
 for a,w in t.upper:v*=mp.rf(mpval(a),sum(x*y for x,y in zip(w,k)))
 for a,w in t.lower:v/=mp.rf(mpval(a),sum(x*y for x,y in zip(w,k)))
 for z,n in zip(t.z,k):v*=z**n
 return v
# Finite falling-factorial shifts, including alternating spin variables.
for block in [0,1]:
 m=h.Master('test',3,sp.Integer(1),alternating=True)
 t=h.base(m,block)
 for at in [h.Atom('H',0,h.q,None,(1,1)),h.Atom('H',0,1-h.q,None,(0,1))]:h.insert(t,at,0,block)
 bd=1 if block==0 else 2
 for shift0 in product(range(3),repeat=bd):
  shift=tuple(shift0)+(0,)*(t.dim-bd);u=h.shifted(t,shift)
  k=tuple((i+1)%3 for i in range(t.dim));old=tuple(x+y for x,y in zip(k,shift))
  direct=rawcoeff(t,old)
  for ni,ji in zip(old,shift):direct*=mp.factorial(ni)/mp.factorial(ni-ji)
  compiled=rawcoeff(u,k)
  res=abs(direct-compiled)/max(1,abs(direct));maxshift=max(maxshift,res);counts['shifts']+=1
  assert res<mp.mpf('1e-45')
# Sample the complete compilation before prefactor merging, covering all seven masters.
masters=h.masters();nrows=0
for master in masters:
 expr=sp.expand(master.polynomial);av=sorted(expr.free_symbols&set(h.ATOMS),key=str);pol=sp.Poly(expr,*av)
 for block in [0,1]:
  bt=h.base(master,block)
  if sp.expand(bt.poly)==0:continue
  for powers,coef in pol.terms():
   ats=[]
   for a,k in zip(av,powers):ats.extend([h.ATOMS[a]]*k)
   ranges=[range(at.order+1) if at.kind=='D' else range(1) for at in ats]
   for choices in product(*ranges):
    t=bt.copy()
    for at,ch in zip(ats,choices):h.insert(t,at,ch,block)
    for out in h.polynomial_terms(t,block):
     nrows+=1
     if nrows%43==0 or master.name in ['Q','P4']:check_array(out)
 print(master.name,'audited',nrows,flush=True)
# Reduction of the primitive's fixed polygamma constants by reflection.
rc=[]
for q in [mp.mpf('.25'),mp.mpf('.3'),mp.mpf('.5'),mp.mpf('.75')]:
 for theta in [2*q,2*q-1]:
  for j in range(1,7):
   m=j-1;c=(-1)**(j+1)*mp.polygamma(m,q)-mp.polygamma(m,1-q)+(1+(-1)**j)*mp.polygamma(m,1)
   orig=7*c+2**j*(-1)**j*(mp.polygamma(m,theta-q)-(-1)**m*mp.polygamma(m,1-theta+q)-mp.polygamma(m,-q)+(-1)**m*mp.polygamma(m,1+q))
   target=(7-2**(j+1) if j%2 else 7)*c
   rc.append(abs(orig-target)/max(1,abs(orig),abs(target)))
assert max(rc)<mp.mpf('1e-45')
record=dict(scope='Exact normalized Horn coefficient tests and finite-shift identities; this is not a full numerical evaluation of every multivariate endpoint function.',counts=counts,generated_rows=nrows,max_shift_relative_residual=mp.nstr(maxshift,40),max_primitive_constant_relative_residual=mp.nstr(max(rc),40))
(Path(__file__).resolve().parents[2]/'verification/general_closed/horn_compiler_checks.json').write_text(json.dumps(record,indent=2));print(record)
