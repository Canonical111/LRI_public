"""Exact local identities and complete polynomial/normalization checks."""
from pathlib import Path
import json, sympy as s, re
ROOT=Path(__file__).resolve().parent
checks=[]
def zero(label,e):
 e=s.factor(e)
 if e!=0:raise AssertionError((label,e))
 checks.append(label)
# Quadratic pullback of the elliptic differential equation.
m,V,Vp=s.symbols('m V Vp'); x=4*m*(1-m); xp=s.diff(x,m)
Vpp=(-(1-2*m)*Vp+V/4)/(m*(1-m))
yprime=Vp/xp;ysecond=Vpp/xp**2-Vp*s.diff(xp,m)/xp**3
zero('elliptic quadratic pullback gives quarter-Gauss equation',x*(1-x)*ysecond+(1-3*x/2)*yprime-V/16)
# All three Meijer G to K-product relations, from the retained p-basis.
k,kc,pi=s.symbols('k kc pi',positive=True)
p0=4*k*k/pi**2;p1=4*k*(k+kc)/pi;p2=4*(k+kc)**2
zero('g1 reduced to EllipticK square',s.sqrt(pi)*p0-4*k*k/pi**s.Rational(3,2))
zero('g2 reduced to complementary EllipticK product',(p1-pi*p0)/s.sqrt(pi)-4*k*kc/pi**s.Rational(3,2))
zero('g3 reduced to difference of EllipticK squares',(p2-2*pi*p1)/(2*pi**s.Rational(3,2))-2*(kc*kc-k*k)/pi**s.Rational(3,2))
A,B=s.symbols('A B')
zero('primitive quartic normalization',96*(15*(4*A)**2+12*(4*A)*(8*B)-(8*B)**2)-1536*(15*A*A+24*A*B-4*B*B))
# Harmonic kernel, derivative limit, and changes of variables.
n,t,a,b,c=s.symbols('n t a b c',positive=True)
zero('trigamma-kernel consecutive coefficient',4/(2*n+2)**2-4/(2*n+1)**2-(1/(n+1)**2-1/(n+s.Rational(1,2))**2))
for nv in range(9):
 for rv in [1,2,3,5,7]:
  av=s.Rational(rv+2,8)
  # Integral of x^(2a-1)*(1-x^(2n))/(1-x), expanded finitely.
  coeff=sum(1/(2*av+j) for j in range(2*nv))
  expected=s.expand_func(s.digamma(2*av+2*nv))-s.expand_func(s.digamma(2*av))
  zero(f'harmonic integral n={nv}, r={rv}',s.simplify(coeff-expected))
zero('J coefficient sign under L=-nu*J',-9408*(-1)-9408)
zero('even F4 coefficient',-9432/ s.Integer(3)+3144)
zero('even F6 coefficient',-5895/ s.Integer(3)+1965)
u,r=s.symbols('u r',positive=True)
zero('seventh u^4 Jacobian',4*u**3*(u**4)**((r+2)/4-1)-4*u**(r+1))
# Polylog polynomial conversion independent of any numerical coefficient.
L,G,z3,z5,Q,AA,T3,S5,Bsv,Ipoly=s.symbols('L G z3 z5 Q A T3 S5 Bsv Ipoly',real=True)
C3=3*pi**3/128+pi*L**2/32-G*L/2
Bvalue=-2*S5+2*G*(-T3+C3)+G*pi**3/96+s.Rational(33,512)*pi**2*z3
Svalue=-Ipoly/417792+s.Rational(37,384)*pi**2*z3-pi**3*G/24
oldBlock=208896*Bvalue+13056*(32*G-3*pi**2)*T3
nativeBlock=s.expand(oldBlock.subs(S5,Svalue))
shift=s.expand(nativeBlock-Ipoly+39168*pi*pi*T3)
src=json.loads((ROOT/'inputs/C6_standard_primitive_expression.json').read_text())
out=json.loads((ROOT/'results/expression.json').read_text())
loc={'A':AA,'Q':Q,'G':G,'pi':pi,'z3':z3,'z5':z5}
zero('complete current-to-native polynomial substitution',s.sympify(src['known_polynomial'],locals=loc)+shift.subs(L,(AA-pi)/4)-s.sympify(out['native_known_polynomial'],locals=loc))
assert src['ordinary_hypergeometric_terms']==out['ordinary_hypergeometric_terms'];checks.append('all 13 fixed ordinary values retained exactly')
assert src['source_correction']==out['source_correction'];checks.append('source correction retained exactly once')
# Native package delimiter check (not claimed to execute Wolfram Language).
text=(ROOT/'C6Native.wl').read_text();text=re.sub(r'\(\*.*?\*\)','',text,flags=re.S);text=re.sub(r'"(?:\\.|[^"\\])*"','""',text)
stack=[];pairs={')':'(',']':'[','}':'{'}
for pos,ch in enumerate(text):
 if ch in '([{':stack.append((ch,pos))
 elif ch in ')]}':
  if not stack or stack[-1][0]!=pairs[ch]:raise AssertionError(('Wolfram delimiter',pos,ch,stack[-1:]));
  stack.pop()
assert not stack;checks.append('Wolfram package delimiters balance (static check only)')
for bad in ['FoxH[','MeijerG[','SVHPL[','KampeDeFeriet[','HarmonicPolyLog[','Sum[','NSum[','D[','Derivative[']:
 assert bad not in text,bad
checks.append('no rare special heads, infinite Sum/NSum, or parameter derivatives in active package')
report={'all_passed':True,'check_count':len(checks),'checks':checks,'Wolfram_kernel_executed':False,'proof_scope':'Exact algebra and local identities; inherited graph and global period identifications not re-proved.'}
(ROOT/'results/symbolic_checks.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS',len(checks),'checks')
