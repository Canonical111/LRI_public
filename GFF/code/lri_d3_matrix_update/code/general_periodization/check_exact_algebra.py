"""Exact algebra only: no numerical period values are used."""
import sympy as s,json
from pathlib import Path
p=s.pi;K,L,Z,P=s.symbols('K L Z P')
comb=s.expand(-1536*(P+K+s.Rational(3,8)*L-s.Rational(149,32)*Z)-(-1536*(P+K)-576*L+7152*Z))
bm,bp=s.symbols('Bm Bp')
ell=s.expand(512*((bm+bp)/64)*((bm-bp)/32)-(bm*bm-bp*bp)/4)

def weights(r):
 u=[]
 for h in range(1,r):
  lh=(-1)**(h+1)*s.polygamma(h-1,s.Rational(1,2))-s.polygamma(h-1,s.Rational(1,2))
  u.append(s.simplify(r*((1+(-1)**h)*s.polygamma(h-1,1)-lh)))
 def en(xx):
  e=[s.S.One]
  for n in range(1,len(xx)+1):
   e.append(s.expand(sum(xx[h-1]*e[n-h]/s.factorial(h-1) for h in range(1,n+1))/n))
  return e[-1]
 return [s.simplify((s.exp(s.I*p*k/2)*en([u[0]+2*s.I*p*k]+u[1:])+s.exp(-s.I*p*k/2)*en([u[0]-2*s.I*p*k]+u[1:]))/2) for k in range(r)]
b4=weights(4);b7=weights(7)
a=s.symbols('a1:4');cs=[s.S.Zero]*7
for i in range(1,4):
 for j in range(1,4):
  cs[abs(i-j)]+=a[i-1]*a[j-1]/2;cs[i+j]-=a[i-1]*a[j-1]/2
quad=s.simplify(-sum(c*b for c,b in zip(cs,b7))/(2*p**7)-2/p*(a[0]**2+14*a[0]*a[2]+8*a[1]**2+113*a[2]**2))
out={'C5_nonprimitive_collection_zero':comb==0,'P4_elliptic_normalization_zero':ell==0,
'B4_over_pi3':[str(s.simplify(v/p**3)) for v in b4],
'B7_over_pi6':[str(s.simplify(v/p**6)) for v in b7],
'P5_square_residue_zero':quad==0,'scope':'Exact SymPy algebra; independent of all period numerical values.'}
print(out)
Path(__file__).resolve().parents[2].joinpath('verification/general_periodization/exact_algebra.json').write_text(json.dumps(out,indent=2))
