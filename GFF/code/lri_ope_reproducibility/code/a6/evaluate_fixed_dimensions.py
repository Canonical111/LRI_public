from pathlib import Path
import json
import mpmath as mp
from calculate_a6 import coefficients,d1_inputs,serial
from spectral_masters import evaluate
mp.mp.dps=65

def primitives2():
 q=mp.mpf(1)/4
 fm=mp.hyper([q,q,2*q,2*q],[3*q,3*q,1],1);fp=mp.hyper([3*q,3*q,2*q,2*q],[5*q,5*q,1],1)
 bm=mp.gamma(q)**4*fm;bp=64*mp.pi**4/mp.gamma(q)**4*fp
 def Y(r):
  r=mp.mpf(r);a=(r+2)/8;b=(r+6)/8
  return r/8*(mp.gamma(a)/mp.gamma(b))**7*mp.hyper([1,1+r/8]+[a]*7,[r/8]+[b]*7,-1)
 c=mp.cos(mp.pi/8);s=mp.sin(mp.pi/8)
 x0=Y(2);xp=c**7*Y(3)-s**7*Y(5);xm=c**7*Y(1)+s**7*Y(7)
 T=(mp.gamma(q)/mp.gamma(3*q))**4;P4=(bm*bm-bp*bp)/(4*mp.pi**3)
 P5=8/mp.pi*(25*x0*x0-28*mp.sqrt(2)*x0*(xp+xm)+18*(xp*xp+xm*xm)+28*xp*xm)
 return T,P4,P5

def thermals(d,inp):
 q=mp.mpf(d)/4;A=mp.digamma(2*q)-2*mp.digamma(q)+mp.digamma(1);R=mp.polygamma(1,2*q)-mp.polygamma(1,1)
 U=mp.polygamma(2,q);V=mp.polygamma(2,1)+mp.polygamma(2,2*q);X=mp.polygamma(3,2*q)-mp.polygamma(3,1)
 T,P,P5,K,L,Z=[mp.mpf(inp[n]) for n in ('T','P4','P5','K','L','Z')]
 return {3:(A*A+R)/108-T/81,4:(16*P-A**3-mp.mpf(4)/3*A*T-3*A*R+mp.mpf(53)/2*U-3*V)/648,
 5:(-1536*(P5+K)+384*A*P-576*L-48*T*T+120*A*A*T+168*T*R+7152*Z-15*A**4-90*A*A*R+414*A*U-108*A*V-117*R*R-75*X)/46656}

out={}
r1=json.loads(Path('d1_results.json').read_text());out['1']=r1
for d in (2,3):
 if d==2:T,P,P5=primitives2()
 else:T=6*mp.mpf('5.01710256455385536959085484569018');P=mp.mpf('62.0583279434066724664633885840967');P5=mp.mpf('240.340317759083549816366546388004')
 checks=[]
 for n,nu,j in [(32,512,5),(64,1536,8),(96,2048,8)]:
  ev=evaluate(d,n,nu,j);ev['Q_reference']=str(T/6);ev['P4_reference']=str(P)
  inp={'T':T,'P4':P,'P5':P5,'K':mp.mpf(str(ev['K'])),'L':mp.mpf(str(ev['L'])),
       'Z':4*mp.catalan*T/6 if d==2 else mp.mpf(str(ev['Z']))}
  rr=coefficients(d,**inp);ev['a6']=str(rr['coefficients'][6]);ev['C5_check']=str(thermals(d,inp)[5])
  if d==2:ev['Z_reference']=str(inp['Z'])
  checks.append(ev);print('FIXED',d,n,nu,'a6',ev['a6'],'C5',ev['C5_check'],flush=True)
  out[str(d)]={**serial(rr),'spectral_convergence':checks}
  Path('fixed_dimension_results.json').write_text(json.dumps(out,indent=2))
 Path(f'd{d}_inputs.json').write_text(json.dumps(serial(inp),indent=2))
 out[str(d)]['thermal_checks']=serial(thermals(d,inp))
 out[str(d)]['numerical_qualification']='K,L,Z evaluated numerically with explicit asymptotic spin tails; Z2 uses its exact Gamma/Catalan formula. Repeated truncations and quadrature checks are diagnostics, not certified intervals.'
Path('fixed_dimension_results.json').write_text(json.dumps(out,indent=2))
