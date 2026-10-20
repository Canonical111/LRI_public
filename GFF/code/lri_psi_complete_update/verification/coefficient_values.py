#!/usr/bin/env python3
"""Compare original and psi C0-C5 numerically: reused wheel periods, fresh P5 gamma moment."""
from pathlib import Path
import json,time
import mpmath as m
ROOT=Path(__file__).resolve().parent
m.mp.dps=70;start=time.perf_counter()
w=json.loads((ROOT/'wheel_inputs.json').read_text()); Fm=m.mpf(w['Fminus']); Fp=m.mpf(w['Fplus'])
q=m.mpf('.25');A=m.digamma(2*q)+m.digamma(1)-2*m.digamma(q)
D=m.digamma(1-q)-m.digamma(q);T=m.polygamma(1,q);Tb=m.polygamma(1,1-q);U=m.polygamma(2,q);Ub=m.polygamma(2,1-q)
Q=m.gamma(q)**4/m.pi;Bm=m.gamma(q)**4*Fm;Bp=64*m.pi**4/m.gamma(q)**4*Fp;P4=13*Bm-3*Bp

def gamma_moment(y):
    if not y:return m.mpf(0)
    return y*abs(m.gamma(q+1j*y))**14*(m.sinh(6*m.pi*y)+13*m.sinh(4*m.pi*y)+29*m.sinh(2*m.pi*y))
P5=m.quad(gamma_moment,[0,m.mpf('.125'),m.mpf('.5'),1,2,4,8,m.inf])/m.pi**(m.mpf(11)/2)
K=(T*(3*T-Tb)+A*U)/2;L=-(3*A-D)*P4/6-2*D*Bm/3
C=[m.mpf('.5'),-m.mpf(1)/6,A/9,(A*A+(T+Tb)/6-8*Q)/108,
   (16*P4-A**3-A*(T+Tb)/2-8*A*Q+(365*U-6*Ub)/14)/648,
   (-1536*P5+96*(7*A-D)*P4+384*D*Bm-1728*Q**2+16*Q*(45*A*A+383*T-64*Tb)-768*T*(3*T-Tb)-15*A**4-15*A*A*(T+Tb)-6*A*(431*U+18*Ub)/7-83*(T+Tb)**2/4)/46656]
l=m.log(2);Ao=m.pi+4*l;H=2*m.pi**2/3+8*m.catalan
Ko=128*m.catalan**2+24*m.pi**2*m.catalan-4*m.pi**3*l-28*Ao*m.zeta(3)
Lo=-(5*m.pi+26*l)*Bm+(m.pi+6*l)*Bp
O=[m.mpf('.5'),-m.mpf(1)/6,Ao/9,(Ao**2+m.pi**2/3-8*Q)/108,
   (16*P4-Ao**3-Ao*m.pi**2-53*m.pi**3-1436*m.zeta(3)-8*Ao*Q)/648,
   (-1536*(P5+Ko)+384*Ao*P4-576*Lo-1728*Q**2+48*Q*(15*Ao**2+149*H+7*m.pi**2)-15*Ao**4-30*Ao**2*m.pi**2-828*Ao*m.pi**3-21456*Ao*m.zeta(3)-83*m.pi**4)/46656]
rec={'working_digits':70,'C_psi':{f'C{i}':m.nstr(x,65)for i,x in enumerate(C)},
     'original_minus_psi':{f'C{i}':m.nstr(a-b,30)for i,(a,b)in enumerate(zip(O,C))},
     'Kappa':m.nstr(K,65),'L':m.nstr(L,65),'P4':m.nstr(P4,65),'P5_fresh_gamma_moment':m.nstr(P5,65),
     'wheel_periods_reused':True,'P5_recomputed':True,'rigorous_error_enclosure':False,'graph_integrals_recomputed':False,
     'elapsed_seconds':time.perf_counter()-start}
(ROOT/'coefficient_values.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2))
