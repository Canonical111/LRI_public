#!/usr/bin/env python3
"""Exact algebra certificates and independent quadratures for the closed form.

Run: python verify_closed_forms.py --dps 80
Dependencies: sympy, mpmath. No PSLQ/integer-relation fitting is used.

The analytic proof is in the LaTeX note. This program checks its symbolic
reductions, derivatives of the displayed primitives, and independent
convergent integral representations. Decimal agreement is not used as proof.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sympy as s
import mpmath as mp


def exact_zero(expr: s.Expr, label: str) -> None:
    if s.simplify(s.expand(expr)) != 0:
        raise AssertionError(label + ': symbolic residual ' + str(expr))
    print(label + ': PASS')


def symbolic_checks() -> None:
    L,H,Z2,Z3=s.symbols('L H Z2 Z3',real=True)
    D=s.symbols('D',real=True)  # Li_2(1/3)
    T4,T3,T23,T34,Tn3,Tn2,Th=s.symbols('T4 T3 T23 T34 Tn3 Tn2 Th',real=True)
    Dh=Z2/2-L**2/2
    Dn=-D-(H-L)**2/2
    D4=2*(Dh+Dn)
    D34=Z2-D4+2*L*(H-2*L)
    # Real primitives for F(a)=integral_0^a log^2(1-t)/t dt.
    F4=(-2*L)*(H-2*L)**2+2*(H-2*L)*D34-2*T34+2*Z3
    Fh=-L**3-2*L*Dh-2*Th+2*Z3
    Fn=L*(H-L)**2-2*Z2*(H-L)-2*(H-L)*Dn-2*T23+(H-L)**3/3+2*Z3
    JL=s.expand(F4/4-Fh/2-Fn/2-L*D4/2-T4/4-L**3/3)
    def landen(lz,l1):
        return Z3+Z2*l1-lz*l1**2/2+l1**3/6
    rhs3=landen(-H,L-H)
    rhs4=landen(-2*L,H-2*L)
    rhsK=s.Rational(2,3)*(L-H)**3-2*Z2*(L-H)
    lhsK=2*T3+T34-4*Th-2*Tn3-4*T23+s.Rational(7,2)*Z3
    half3=s.Rational(7,8)*Z3-Z2*L/2+L**3/6
    eq=s.expand((lhsK-rhsK).subs(T3,rhs3-T23-Tn2)
                .subs(Tn3,rhs4-T4-T34).subs(T4,4*(Th+Tn2)).subs(Th,half3))
    sol=s.solve(eq,T23)[0]
    Pi=H**3-3*H**2*L+6*H*L**2-5*L**3-6*H*Z2+6*L*Z2
    exact_zero(sol-(T34/2+Tn2+s.Rational(7,6)*Z3+Pi/6),
               'Kummer + Landen + duplication reduction')
    JL=s.expand(JL.subs(T4,4*(Th+Tn2)).subs(T23,sol).subs(Th,half3))
    exact_zero(JL+Z3/3,'Key finite-part integral J_L = -zeta(3)/3')

    # P primitive: introduce J(z) with explicitly known derivative.
    z=s.symbols('z',positive=True)
    J=s.Function('J')
    ell=s.log(1-z)-s.log(z)
    Klo=2*((s.log(2)-s.log(z))*s.log(1+z)-s.polylog(2,(1+z)/2)-s.polylog(2,-z))
    Klo+=-2*ell*(1/z+1/(1+z))+1/z+3/(1+z)+6*s.polylog(2,z)+3*s.log(z)**2-6*s.log(z)+3*s.log(1-z*z)
    Khi=s.Rational(4,3)*s.log(z)**3-4*s.log(z)**2*s.log(1+z)
    Khi+=-8*s.log(z)*s.polylog(2,-z)+8*s.polylog(3,-z)+8*s.polylog(3,z)
    Khi+=-8*s.polylog(2,z)*s.log(1+z)-8*J(z)-4*Z2*s.log(z/(1+z))
    A=2/(1+z)+2/(1+z)**2-6/z+2/z**2
    B=2/(1+z)-3/(1+z)**2-2/z+1/z**2
    target=A*ell+B+(4*s.log(z)**2-4*Z2+8*s.polylog(2,z))/(z*(1+z))
    derivative=s.diff(Klo+Khi,z).subs(s.diff(J(z),z),s.log(1-z)*s.log(1+z)/z)
    derivative=derivative.replace(lambda t:t.func==s.polylog and t.args[0]==1,
                                  lambda t:-s.log(1-t.args[1]))
    derivative=s.expand_log(derivative,force=True)
    exact_zero(s.together(derivative-target),'Explicit primitive for P')

    # Evaluate the primitive at z=1/2 symbolically. Logs and polylogs are
    # reduced by exact elementary relations, leaving the already-proved JL.
    jhalf=JL+L*D4/2+T4/4+L**3/3
    kp=(Klo+Khi).subs(z,s.Rational(1,2)).subs({J(s.Rational(1,2)):jhalf,
          s.polylog(2,s.Rational(3,4)):D34,
          s.polylog(2,s.Rational(1,2)):Dh,
          s.polylog(2,s.Rational(-1,2)):Dn,
          s.polylog(3,s.Rational(-1,2)):Tn2,
          s.polylog(3,s.Rational(1,2)):Th,
          s.pi**2:6*Z2})
    kp=s.expand_log(kp,force=True).subs({s.log(2):L,s.log(3):H})
    kp=s.expand(kp.subs(T4,4*(Th+Tn2))-6+2*Dh)
    P=4*Z2+s.Rational(8,3)*Z3-2+3*H+L**2+2*Dn
    exact_zero(kp-P,'Closed form for P from its primitive')

    # Exact finite-part tables for the four- and five-insertion regions.
    Rbulk=12-12*Z2-16*Z3
    Rlower=s.Integer(4)
    Rupper=8-8*Z2-14*Z3-16*L
    R=24-20*Z2-30*Z3-16*L
    exact_zero(Rbulk+Rlower+Rupper-R,'R4 region sum')
    Sbulk=48*Z3+26*Z2-19
    Slower=-8*JL+12*Z2+12*H+4*L**2+8*Dn
    Supper=16+6*Z2
    S=44*Z2+s.Rational(152,3)*Z3-3+12*H+4*L**2+8*Dn
    exact_zero(Sbulk+Slower+Supper-S,'S region sum')
    exact_zero(S-4*P-(5+28*Z2+40*Z3),'Exact identity S - 4P')

    a=-4*Z2; c=-16; p=8-2*Z2-7*Z3-8*L
    b=-21+38*Z2+60*Z3+32*L-S
    f=16*P+4*R-32+16*Z2+32*Z3
    D2=s.Rational(1,2)-a/2-s.Rational(c,8)
    T2=-a/8+b/4-s.Rational(c,32)+f/16+p/2
    exact_zero(D2-(s.Rational(5,2)+2*Z2),'D2 invariant')
    exact_zero(T2-(2-2*Z2-4*Z3),'T2 invariant')

    # Rational decomposition of the five-insertion middle-vertex integral.
    aa,w,t=s.symbols('aa w t',positive=True)
    P0=lambda q:q*q*(1-q)**2
    P0p=lambda q:2*q*(1-q)*(1-2*q)
    C=P0(aa)/w**2; DD=P0(aa+w)/w**2
    AA=P0p(aa)/w**2+2*P0(aa)/w**3
    BB=-P0p(aa+w)/w**2+2*P0(aa+w)/w**3
    exact_zero(s.together(P0(aa+t)/(t*t*(w-t)**2)-(1+AA/t+BB/(w-t)+C/t**2+DD/(w-t)**2)),
               'Middle-vertex rational decomposition')
    # Upper five-vertex boundary primitive.
    U=(4-12/t-8/t**2)*s.log(t-1)-6+10/(t-1)-8/t
    prim=(4*t-2)*s.log(t-1)-10*t+4-6*s.log(t)**2-12*s.polylog(2,1/t)+8*s.log(t-1)/t
    der=s.diff(prim,t).replace(lambda q:q.func==s.polylog and q.args[0]==1,
                             lambda q:-s.log(1-q.args[1]))
    der=s.expand_log(der,force=True).subs(s.log(1-1/t),s.log(t-1)-s.log(t))
    exact_zero(s.together(der-U),'Upper five-vertex boundary primitive')


def numerical_checks(dps:int) -> dict[str,str]:
    mp.mp.dps=dps
    one=mp.mpf(1); h=one/2; Z2=mp.zeta(2);Z3=mp.zeta(3)
    L=mp.log(2); H=mp.log(3); DN=mp.polylog(2,-h)
    J=mp.quad(lambda t:mp.log1p(-t)*mp.log1p(t)/t,[0,h])
    JL=J-L*mp.polylog(2,h*h)/2-mp.polylog(3,h*h)/4-L**3/3
    P=4*Z2+8*Z3/3-2+3*H+L*L+2*DN
    R=24-20*Z2-30*Z3-16*L
    S=44*Z2+152*Z3/3-3+12*H+4*L*L+8*DN
    # Direct, convergent independent P integral with explicit boundary subtraction.
    def HQ(e):
        le=mp.log((1-2*e)/e); z=e/(1-e)
        return (2*le+1)/e-4*le/(1-e)-2*(1-e)*le-2-3*e+4*mp.log(z)**2-4*Z2+8*mp.polylog(2,z)
    eps=mp.power(10,-dps//3)
    pquad=mp.quad(lambda e:HQ(e)/e,[eps,mp.sqrt(eps),mp.mpf('.01'),one/3])
    l=mp.log(eps)
    pquad+=(2*l+1)/eps+4*l**3/3+3*l*l+(-6-4*Z2)*l
    # Kummer relation on the real principal branches used in the proof.
    q=one/3
    kleft=2*mp.polylog(3,q)+mp.polylog(3,3*one/4)-4*mp.polylog(3,h)-2*mp.polylog(3,-q)-4*mp.polylog(3,2*q)+7*Z3/2
    kright=2*mp.log(2*q)**3/3-2*Z2*mp.log(2*q)
    result={
      'P':mp.nstr(P,dps),'R4':mp.nstr(R,dps),'S':mp.nstr(S,dps),
      'J_L':mp.nstr(JL,dps),'J_L_integral_residual':mp.nstr(JL+Z3/3,8),
      'Kummer_specialization_residual':mp.nstr(kleft-kright,8),
      'P_independent_cutoff_integral':mp.nstr(pquad,dps//2),
      'P_cutoff_integral_residual':mp.nstr(pquad-P,8),
      'D2':mp.nstr(mp.mpf('2.5')+2*Z2,dps),
      'T2':mp.nstr(2-2*Z2-4*Z3,dps),
      'x_3_over_2_coefficient':mp.nstr(mp.mpf(39)/16+2*Z2,dps),
      'x_2_coefficient':mp.nstr(4-4*Z2-8*Z3,dps),
      'a1':mp.nstr(-4*Z2,dps),
      'b1':mp.nstr(-21+38*Z2+60*Z3+32*L-S,dps),
      'c1':'-16',
      'f1':mp.nstr(16*P+4*R-32+16*Z2+32*Z3,dps),
      'p':mp.nstr(8-2*Z2-7*Z3-8*L,dps)}
    if abs(JL+Z3/3)>mp.power(10,-dps+8):
        raise AssertionError('Direct J_L integral check failed')
    if abs(kleft-kright)>mp.power(10,-dps+8):
        raise AssertionError('Kummer branch check failed')
    # O(eps log^2 eps) is present in the finite-cutoff P check.
    if abs(pquad-P)>1000*eps*(1+abs(mp.log(eps))**2):
        raise AssertionError('Independent P integral check failed')
    return result


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dps',type=int,default=80)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'closed_form_values.json')
    args=parser.parse_args()
    if not 40<=args.dps<=250:
        parser.error('--dps must be between 40 and 250')
    symbolic_checks()
    values=numerical_checks(args.dps)
    print(json.dumps(values,indent=2))
    args.output.write_text(json.dumps(values,indent=2)+'\n')
    print('All checks passed. See the note for the analytic argument and RG assumptions.')

if __name__=='__main__':
    main()
