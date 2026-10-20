#!/usr/bin/env python3
"""Exact, generic-d RG algebra through epsilon^5, plus d=1 substitution.
This checks algebra, not the evaluation of the general-d four/five-loop
projective integrals.  Requirements: sympy.
"""
from pathlib import Path
import argparse,json
import sympy as s
r=s.Rational
A,R,M,Q,J,t1,tq,t2=s.symbols('A R M Q J t1 tq t2')
b4,c4,D4,D5=s.symbols('b4 c4 D4 D5')
b3=6*Q+r(87,4)*A**2-r(9,4)*R+M
c3=r(7,2)*A**2-R/2+M/3
# The corrected three-loop zero-momentum alpha coefficients.
aU=-t1-tq+2*t2+J
aT=A**2/2+t1/2+tq-3*t2/2-J
aI1=3*A**2/2+(t1-t2)/2
aI3=M/3
s1=A**2/4+3*t1/4+tq-7*t2/4-J
b3_zm=3*aT+12*aU+12*aI1+3*aI3+6*Q
c3_zm=aT+2*aI1+aU+aI3
checks={
'b3_MS_from_ZM':s.expand(b3_zm+9*s1-b3.subs(R,t2-t1)),
'c3_MS_from_ZM':s.expand(c3_zm-c3.subs(R,t2-t1)),
'cancel_auxiliary_J':s.diff(s.expand(b3_zm+9*s1+c3_zm),J),
}
g=s.symbols('g')
x3,x4,x5,y3,y4,y5=s.symbols('b3 b4 b5 c3 c4 c5')
B=3-6*A*g+x3*g**2+x4*g**3+x5*g**4
Gam=g-A*g**2+y3*g**3+y4*g**4+y5*g**5
Cs={}
for n in range(1,6):
    Cs[n]=s.expand(s.series(s.diff(Gam,g)/B**n,g,0,n).removeO()).coeff(g,n-1)/n-(r(1,2) if n==1 else 0)
checks['C1']=s.simplify(Cs[1]+r(1,6));checks['C2']=s.simplify(Cs[2]-A/9)
checks['C3']=s.simplify(Cs[3].subs({x3:b3,y3:c3})-(A*A+R-8*Q)/108)
C4=(60*A**3-8*A*x3+18*A*y3+3*y4-x4)/243
C5=(336*A**4-60*A*A*x3+108*A*A*y3+x3*x3-3*x3*y3-10*A*x4+24*A*y4+3*y5-x5)/729
checks['Lagrange_C4']=s.simplify(Cs[4]-C4)
checks['Lagrange_C5']=s.simplify(Cs[5]-C5)
C4d=(D4-51*A**3+9*A*R-48*A*Q-2*A*M)/243
C5d=(D5+10*A*D4-6*A*c4-r(5541,16)*A**4-r(51,4)*A*A*M-162*A*A*Q+r(315,8)*A*A*R+6*M*Q-r(3,4)*M*R+36*Q*Q-18*Q*R+r(27,16)*R*R)/729
checks['generic_d_C4_collected']=s.expand(C4.subs({x3:b3,y3:c3,x4:3*c4-D4,y4:c4})-C4d)
checks['generic_d_C5_collected']=s.expand(C5.subs({x3:b3,y3:c3,x4:3*c4-D4,y4:c4,x5:3*y5-D5})-C5d)
# An independent coefficient-by-coefficient d=1 algebra specialization.
p,Z,P4,P5,K,L,Catalan=s.symbols('pi zeta3 P4 P5 K L Catalan')
b41=-6*P4-r(393,4)*A**3-54*A*Q+r(39,4)*A*p*p+16*A*p+r(165,4)*p**3+12*p*p+24*p+1119*Z
c41=-r(127,8)*A**3-3*A*Q+r(17,8)*A*p*p+r(8,3)*A*p+r(57,8)*p**3+4*p*p+8*p+r(387,2)*Z
rem=-r(16347,64)*A**4+A*A*(-r(1179,4)*Q+r(1053,32)*p*p+45*p)+A*(r(3657,16)*p**3+24*p*p+48*p+r(24843,4)*Z)-24*K+Q*(894*Catalan+r(343,4)*p*p+24*p)-r(95,64)*p**4-p**3
D51=-24*P5-63*Q*Q-54*A*P4-9*L+rem
H=2*p*p/3+8*Catalan
C41=(16*P4-A**3-A*p*p-53*p**3-1436*Z-8*A*Q)/648
C51=(-1536*(P5+K)+384*A*P4-576*L-1728*Q*Q+48*Q*(15*A*A+149*H+7*p*p)-15*A**4-30*A*A*p*p-828*A*p**3-21456*A*Z-83*p**4)/46656
sub={R:p*p/3,M:-4*p,D4:3*c41-b41,c4:c41,D5:D51}
checks['d1_C4_algebra']=s.expand(C4d.subs(sub)-C41)
checks['d1_C5_algebra']=s.expand(C5d.subs(sub)-C51)
# Double complex Selberg product at sigma=tau=1/2, theta=-1/4.
v=s.symbols('v',positive=True)
# gamma_C(1/2)=1; gamma_C(1/4)=v; gamma_C(3/4)=1/v;
# gamma_C(-1/2)=-4, gamma_C(-1/4)=-16/v.
selberg=2*p*p*(1**2/(1/v))*(v*v*(-4)/(-16/v))
checks['complex_Selberg_d2']=s.expand(selberg-p*p*v**4/2)

# Derive the needed simple-pole combinations from the RG pole recursions.
z=s.symbols('z')
beta=[None,3,-6*A,x3,x4,x5];gamma=[None,1,-A,y3,y4,y5]
G={1:s.Integer(1)};Zct={0:s.Integer(1)}
for k in range(2,6):
    G[k]=s.expand(sum(beta[j]*(k-j)*G[k-j] for j in range(1,k))/((k-1)*z))
for k in range(1,5):
    Zct[k]=s.expand(sum(((k-j)*beta[j]+gamma[j])*Zct[k-j] for j in range(1,k+1))/(k*z))
a20,a21,a22,a30,a31,a40,a4m,a5m=s.symbols('a20 a21 a22 a30 a31 a40 a4m a5m')
e20,e21,e22,e30,e31,e40,e4m,e5m=s.symbols('e20 e21 e22 e30 e31 e40 e4m e5m')
AA={2:a20+a21*z+a22*z*z,3:a30+a31*z,4:a4m/z+a40,5:a5m/z}
EE={2:e20+e21*z+e22*z*z,3:e30+e31*z,4:e4m/z+e40,5:e5m/z}
GP=sum(G[k]*g**k for k in G);ZP=sum(Zct[k]*g**k for k in Zct)
# Dictionary polynomial multiplication in g avoids huge intermediate expansion.
def mul(p,q,cap):
    out={}
    for i,v in p.items():
        for j,w in q.items():
            if i+j<=cap:out[i+j]=out.get(i+j,0)+v*w
    return {i:s.expand(v) for i,v in out.items()}
def power(p,n,cap):
    out={0:s.Integer(1)}
    for j in range(n):out=mul(out,p,cap)
    return out
b_derived={};c_derived={}
for order in [4,5]:
    temp=0;temp2=0
    for loop in range(2,order+1):
        temp+=(-1)**loop*AA[loop]*power(G,loop+1,order+1).get(order+1,0)
        temp2+=(-1)**loop*EE[loop]*mul(Zct,power(G,loop,order),order).get(order,0)
    b_derived[order]=-order*s.expand(temp).coeff(z,-1)
    c_derived[order]=-order*s.expand(temp2).coeff(z,-1)
b4_expected=36*A*a20-216*a21+48*a30-4*a4m
c4_expected=26*A*e20-140*e21+40*e30-4*e4m
b5_expected=5*a5m-75*a40+450*a31-60*A*a30-1350*a22+585*A*a21-5*x3*a20
c5_expected=5*e5m-65*e40+325*e31-s.Rational(95,2)*A*e30-s.Rational(2275,3)*e22+s.Rational(725,2)*A*e21-(10*x3+5*y3)*e20/3
checks['generic_b4_simple_pole']=s.expand(b_derived[4]-b4_expected)
checks['generic_c4_simple_pole']=s.expand(c_derived[4]-c4_expected)
checks['generic_b5_simple_pole']=s.expand(b_derived[5]-b5_expected)
checks['generic_c5_simple_pole']=s.expand(c_derived[5]-c5_expected)
checks['general_d_combined_sensitivity']=s.diff((3*c5_expected-b5_expected)/729,e5m)-s.Rational(5,243)
assert all(s.simplify(v)==0 for v in checks.values()),checks

out=dict(checks={k:str(s.simplify(v)) for k,v in checks.items()},all_exact=True,
    scope='generic RG identities and d=1 formula substitutions; not a numerical evaluation of general-d four- or five-loop integrals',
    b3=str(b3),c3=str(c3),C4=str(C4d),C5=str(C5d),
    latex=dict(b3=s.latex(b3),c3=s.latex(c3),C4=s.latex(C4d),C5=s.latex(C5d)))
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=Path('symbolic_checks.json'));args=parser.parse_args()
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
