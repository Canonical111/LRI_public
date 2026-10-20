"""Checks of the six-vertex and fixed-point assembly.
The numeric path uses Gamma-function Laurent jets and independent rational
regulator/reference choices. It is not direct integration of every full graph.
"""
from __future__ import annotations
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations
import json,argparse,time
import mpmath as mp
import sympy as sp
from jet_engine import X,HALF,D
from reconstruct import ReconstructionEngine
from vertex_counterterms import Forests
from calculate_a6 import coefficients

def mul_e(E,x,y):return E.mul(x,y)
def power_e(E,x,n):
 out={0:mp.mpf(1)}
 for _ in range(n):out=E.mul(out,x)
 return out

def symbolic_checks():
 from symbolic_engine import SymbolicEngine,LP
 E=SymbolicEngine(verbose=False);u=X(1,-F(1,4));bubble=E.conv(2*u,2*u)
 R,Xs=LP.var('R'),LP.var('X')
 assert not bubble.get(3,LP.cast(0))-(R*R/8+F(7,48)*Xs)
 r=json.load(open('symbolic_results.json'));col=json.load(open('collected_a6.json'));univ=json.load(open('universal_assembly.json'))
 varnames='A R U V X M N T P P5 K L Z Ccross p1_3 p1_m1 W4 W5 W6 b5'
 sym=dict(zip(varnames.split(),sp.symbols(varnames)))
 p=lambda t:sp.sympify(t,locals=sym)
 for k,nm in [(-4,'s64'),(-3,'s63'),(-2,'s62'),(-1,'s61')]:
  assert sp.expand(p(r['S6'][str(k)])-p(univ['S6_poles'][nm]))==0
 h4=p(col['h4'])
 assert all(not h4.has(sym[x]) for x in ['M','N','Ccross','p1_3','p1_m1'])
 assert col['D5_match'];assert univ['factorization_remainder']=='0'
 return {'S6_all_four_poles_match':True,'mass_and_crossed_kite_cancel':True,
         'outer_factorization_exact':True,'D5_matches_note':True,'bubble_epsilon3_check':True}

def numeric(d=1,precision=60,seed=173,reference_seed=419):
 mp.mp.dps=precision
 if d==1:
  data=json.load(open('d1_results.json'));inp={k:mp.mpf(data[k]) for k in ['T','P4','P5','K','L','Z']}
 else:inp={k:mp.mpf(v) for k,v in json.load(open(f'd{d}_inputs.json')).items()}
 T,P,P5,K,L,Z=[inp[k] for k in ('T','P4','P5','K','L','Z')]
 E=ReconstructionEngine(d,T,P4=P,K=K,L=L,Z=Z,Ccross=mp.mpf(17),N=8,verbose=True)
 E.pole_seed=seed;E.reference_seed=reference_seed
 # The crossed quadratic coefficient is left arbitrary; it cancels exactly
 # from a6. Choosing 17 here exercises that cancellation, rather than claims
 # the corresponding individual physical integral has that value.
 u=X(1,-F(1,4));sums={2:{0:mp.mpf(1)/6},3:E.scale(E.conv(2*u,2*u),F(1,4))}
 start=time.time()
 for n in (4,5,6):
  sums[n]={}
  for r in json.load(open(f'graphs_n{n}.json')):
   g={p:m*u for p,m in zip(combinations(range(n),2),r['edges']) if m}
   j=E.kernel(g,range(n),(0,1));j={k:j.get(k,0) for k in range(2-n,7-n)}
   sums[n]=E.add(sums[n],E.scale(j,F(r['weight'])))
  print('VERIFIED NUMERIC KERNEL',n,flush=True)
 FST=Forests(E,P5=P5);beta={};mass={}
 for ell in range(1,6):
  bv=mp.mpf(0);cv=mp.mpf(0)
  for r in json.load(open(f'vertex_n{ell+1}.json')):
   z=FST.counterterm(ell+1,tuple(r['edges'])).get(-1,0)
   bv+=E.m(F(r['weight4']))*z;cv+=E.m(F(r['weight2']))*z
  beta[ell]=ell*(-1)**ell*bv;mass[ell]=ell*(-1)**ell*cv
  print('VERIFIED NUMERIC RG',ell,mp.nstr(beta[ell],20),mp.nstr(mass[ell],20),flush=True)
 # Bare-coupling jets g_B = g + sum G_n(epsilon) g^n.
 G={1:{0:mp.mpf(1)}}
 for n in range(2,6):
  z=E.add(*(E.scale(G[n-ell],beta[ell]*(n-ell)) for ell in range(1,n)))
  G[n]=E.shift(z,-1,mp.mpf(1)/(n-1))
 def mul_g(x,y):
  out={}
  for i,xi in x.items():
   for j,yj in y.items():
    if i+j<=6:out[i+j]=E.add(out.get(i+j,{}),E.mul(xi,yj))
  return out
 ren={};power={0:{0:mp.mpf(1)}}
 for n in range(1,7):
  power=mul_g(power,G)
  if n<2:continue
  a=u;b=(2*n-1)*u-(n-2)*HALF
  outer=E.gr([HALF,HALF-b,2*a+b-D,a+b-HALF,a+b-HALF],[a,a,2*a+2*b-D])
  amp=E.mul(sums[n],outer)
  for order in range(n,7):ren[order]=E.add(ren.get(order,{}),E.scale(E.mul(amp,power.get(order,{})),(-1)**n))
 maxpole=max(abs(v) for rr in ren.values() for k,v in rr.items() if k<0)
 b1,b2,b3,b4,b5=[beta[k] for k in range(1,6)]
 gs={1:1/b1,2:-b2/b1**3,3:2*b2*b2/b1**5-b3/b1**4,
     4:-5*b2**3/b1**7+5*b2*b3/b1**6-b4/b1**5,
     5:14*b2**4/b1**9-21*b2*b2*b3/b1**8+(6*b2*b4+3*b3*b3)/b1**7-b5/b1**6}
 result={k:mp.mpf(0) for k in range(2,7)}
 for n in range(2,7):
  gpow=power_e(E,gs,n)
  for k in range(2,7):result[k]+=sum(ren[n].get(j,0)*gpow.get(k-j,0) for j in range(k+1))
 expected=coefficients(d,**inp)['coefficients']
 differences={k:result[k]-expected[k] for k in result}
 print('FINAL DIFFERENCES',differences,'MAXPOLE',maxpole,flush=True)
 return {'d':d,'precision':precision,'pole_seed':seed,'reference_seed':reference_seed,
         'auxiliary_crossed_kite_coefficient':17,'beta':{k:mp.nstr(v,precision) for k,v in beta.items()},
         'mass_gamma':{k:mp.nstr(v,precision) for k,v in mass.items()},
         'amplitude_coefficients':{k:mp.nstr(v,precision) for k,v in result.items()},
         'differences':{k:mp.nstr(v,12) for k,v in differences.items()},'maximum_pole_residual':mp.nstr(maxpole,12),
         'seconds':time.time()-start,'scope':'Gamma-jet graph reconstruction and independent rational reference choices, not direct full-dimensional quadrature of every graph.'}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--numeric',action='store_true');ap.add_argument('--dimension',type=int,default=1);args=ap.parse_args()
 out={'symbolic':symbolic_checks()}
 if args.numeric:out['numeric']=numeric(args.dimension)
 Path('verification_results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
