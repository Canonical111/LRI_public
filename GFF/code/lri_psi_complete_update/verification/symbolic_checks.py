#!/usr/bin/env python3
"""Exact algebra checks for the psi revision and the Kappa proof; no numeric fitting."""
from pathlib import Path
import json
import sympy as s
n,t=s.symbols('n t')
# Divide the contiguous identity by a_n(t), using exact term ratios.
r=(n+s.Rational(1,2))**2*(n+t)/(n+1)**3
left=t*(n+t)-(2*t*t-2*t+s.Rational(3,4))+(t-1)**3/(n+t-1)
right=(n+1)**3/(n+t)*r-n**3/(n+t-1)
checks={'contiguous_telescoping_certificate':s.cancel(left-right)==0}
l,p,z,g,S,T,u,v=s.symbols('l p z g S T u v')
lg=4*l*t-p*p*t*t/3+4*z*t**3-7*p**4*t**4/90
h=s.series(s.exp(lg),t,0,5).removeO()
c=1-p*p*t*t/2+p**4*t**4/24
sn=p*t-p**3*t**3/6
j2=s.expand(2*(1+c+2*sn)*h*(1+S*t**3+T*t**4)).coeff(t,4)
j2+=s.expand(2*p*p*(2+p*t/2)*(1+u*t+v*t*t)).coeff(t,2)
A=p+4*l
g2=A**4/6-A*A*p*p/6-A*p**3/3-12*A*z-p**4/180
K=s.expand(j2-g2)
Ktarget=128*g*g+24*p*p*g-4*p**3*l-28*A*z
Kreduce=s.expand(K.subs(T,p*p*u*u/2-p**4/6-p*p*v).subs({S:8*p*g-14*z,u:4*l-8*g/p}))
checks['Kappa_from_bilinear_and_elementary_sums']=s.expand(Kreduce-Ktarget)==0
Q,P4,P5,B=s.symbols('Q P4 P5 B')
D,R,PsiT,U,V=s.symbols('D R PsiT U V')
H=2*p*p/3+8*g
Kpsi=2*PsiT**2-3*R*PsiT+A*U/2
Lpsi=-(3*A-D)*P4/6-2*D*B/3
subs={D:p,R:p*p/3,PsiT:p*p+8*g,U:-2*p**3-56*z,V:-2*z}
checks['Kappa_psi_special_values']=s.expand(Kpsi.subs(subs)-Ktarget)==0
old=[s.Rational(1,2),-s.Rational(1,6),A/9,(A*A+p*p/3-8*Q)/108,
     (16*P4-A**3-A*p*p-53*p**3-1436*z-8*A*Q)/648]
new=[s.Rational(1,2),-s.Rational(1,6),A/9,(A*A+R-8*Q)/108,
     (16*P4-A**3-3*A*R-8*A*Q+s.Rational(53,2)*U-24*V)/648]
Lold=-(p+6*l)*P4/3-2*p*B/3
old.append((-1536*(P5+Ktarget)+384*A*P4-576*Lold-1728*Q**2+48*Q*(15*A**2+149*H+7*p**2)-15*A**4-30*A*A*p*p-828*A*p**3-21456*A*z-83*p**4)/46656)
new.append((-1536*P5+96*(7*A-D)*P4+384*D*B-1728*Q**2+48*Q*(15*A**2+149*PsiT-128*R)-3072*PsiT**2+4608*R*PsiT-15*A**4-90*A*A*R-354*A*U-864*A*V-747*R**2)/46656)
for i,(x,y) in enumerate(zip(old,new)):
    checks[f'C{i}_original_vs_psi']=s.expand(x-y.subs(subs))==0
checks['L_original_vs_psi']=s.expand(Lold-Lpsi.subs(subs))==0
# Coefficient t^4 in the bilinear identity.
bil=s.expand((1-p*p*t*t+p**4*t**4/3)*(1+S*t**3+T*t**4)*(1-S*t**3+T*t**4)+p*p*t*t*(1+u*t+v*t*t)*(1-u*t+v*t*t)-1).coeff(t,4)
checks['bilinear_fourth_coefficient']=s.expand(bil-(2*T+p**4/3+p*p*(2*v-u*u)))==0
# Reflected-quarter forms are exact rewritings of the sparse basis.
Tb,Ub=s.symbols('Tb Ub')
reflected=-1536*P5+96*(7*A-D)*P4+384*D*B-1728*Q**2+16*Q*(45*A**2+383*PsiT-64*Tb)-768*PsiT*(3*PsiT-Tb)-15*A**4-15*A**2*(PsiT+Tb)-s.Rational(6,7)*A*(431*U+18*Ub)-s.Rational(83,4)*(PsiT+Tb)**2
checks['C5_reflected_vs_sparse']=s.expand(46656*new[5].subs({R:(PsiT+Tb)/6,V:(U+Ub)/56})-reflected)==0
reflected4=16*P4-A**3-A*(PsiT+Tb)/2-8*A*Q+(365*U-6*Ub)/14
checks['C4_reflected_vs_sparse']=s.expand(648*new[4].subs({R:(PsiT+Tb)/6,V:(U+Ub)/56})-reflected4)==0
checks['Kappa_reflected_vs_sparse']=s.expand(Kpsi.subs(R,(PsiT+Tb)/6)-(PsiT*(3*PsiT-Tb)+A*U)/2)==0
result={'checks':checks,'all_passed':all(checks.values()),'method':'exact SymPy rational symbolic algebra; not a substitute for the analytic proof'}
output=Path(__file__).with_name('symbolic_checks.json')
output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
assert result['all_passed']
