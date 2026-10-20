#!/usr/bin/env python3
"""Finite-order conversion between LRI thermal and bulk one-point coefficients.

Conventions: epsilon=2s-d; Delta_E=sum C_n epsilon**n;
<:Phi^2:>=a_phi2/|y|**(2 Delta_phi), a_phi2=sum_{n>=2} a_n epsilon**n.

Uses the a2,...,a6 formula derived in the accompanying project note as INPUT.
This script verifies algebraic conversion, not the underlying loop calculation.

Dependencies: mpmath; sympy only for --verify.
Example:
 python relations.py --dimension 2 --C3 -0.874850012653 --C4 5.048868431 \
     --C5 -38.833645896
For generic d add --omega (13 Z_d - L_d - 12 K_d), or omit --C5 to
compute only a2,...,a5. At d=2 omega is inferred using the archive's
closed master identities. No numerical truncation/remainder bound is supplied.
"""
from __future__ import annotations
import argparse
import json
from typing import Any
import mpmath as mp


def number(x: Any) -> mp.mpf:
    if isinstance(x, str) and '/' in x:
        p, q = x.split('/')
        return mp.mpf(p) / mp.mpf(q)
    return mp.mpf(x)


def omega_two(C3: Any, C4: Any) -> mp.mpf:
    """Exact d=2 elimination using K2,L2,Z2 identities from GFF.zip."""
    c3, c4 = number(C3), number(C4)
    ell, G = mp.log(2), mp.catalan
    Q = 2*ell**2 - mp.mpf(27)/2*c3
    P4 = mp.mpf(81)/2*c4 + 8*ell**3 - 27*ell*c3 + mp.mpf(359)/16*mp.zeta(3)
    return 52*G*Q + 2*ell*P4 - 384*G**2 + 336*ell*mp.zeta(3)


def from_thermal(d: Any, C3: Any, C4: Any,
                 C5: Any | None = None, omega: Any | None = None) -> dict:
    d = number(d)
    if not mp.isfinite(d) or not (0 < d < 4):
        raise ValueError('Require fixed 0<d<4.')
    c3, c4 = number(C3), number(C4)
    q = d/4
    A = mp.digamma(2*q)-2*mp.digamma(q)+mp.digamma(1)
    R = mp.polygamma(1,2*q)-mp.polygamma(1,1)
    U = mp.polygamma(2,q)
    V = mp.polygamma(2,1)+mp.polygamma(2,2*q)
    X = mp.polygamma(3,2*q)-mp.polygamma(3,1)
    B = [mp.polygamma(j,1-q)-mp.polygamma(j,q)+mp.factorial(j)/q**(j+1)
         for j in range(4)]
    a2 = -mp.gamma(1-q)*mp.gamma(2*q)**3/(54*mp.gamma(1+q)*mp.gamma(4*q))
    logs = [4*A/3-B[0]/4,
            6*c3-A*A/4+R/9+B[1]/32,
            6*c4-3*A*c3+19*A**3/324-A*R/12+U/12-B[2]/384]
    if C5 is not None:
        c5 = number(C5)
        if omega is None:
            if d != 2:
                raise ValueError('a6 requires omega=13 Z-L-12 K at generic d.')
            om = omega_two(c3, c4)
        else:
            om = number(omega)
        logs.append(6*c5-3*A*c4+(A*A-5*R/6)*c3-9*c3*c3
                    -11*A**4/576+37*A*A*R/864-53*A*U/2592-5*A*V/432
                    -53*R*R/5184-47*X/7776+om/81+B[3]/6144)
    else:
        om = None
    # If exp(sum ell_j x^j)=sum r_n x^n then n*r_n=sum j*ell_j*r_{n-j}.
    normalized = [mp.mpf(1)]
    for n in range(1,len(logs)+1):
        normalized.append(sum(j*logs[j-1]*normalized[n-j] for j in range(1,n+1))/n)
    return {'dimension':d,'C2':A/9,'omega':om,
            'log_coefficients':{j+1:v for j,v in enumerate(logs)},
            'a_coefficients':{j+2:a2*v for j,v in enumerate(normalized)},
            'qualification':'Conditional on the earlier one-point calculation; algebraic conversion only. '
                            'Not a resummation or an uncertainty bound.'}


def symbolic_checks() -> dict:
    import sympy as s
    A,R,U,V,X,T,P4,P5,K,L,Z = s.symbols('A R U V X T P4 P5 K L Z')
    C3,C4,C5 = s.symbols('C3 C4 C5')
    B0,B1,B2,B3 = s.symbols('B0 B1 B2 B3')
    # GFF/note/long_range_ising_condensed.tex, labels gs:C0C4 and gs:C5.
    thermal = {
        C3:(A*A+R)/108-T/81,
        C4:(16*P4-A**3-s.Rational(4,3)*A*T-3*A*R+s.Rational(53,2)*U-3*V)/648,
        C5:(-1536*(P5+K)+384*A*P4-576*L-48*T*T+120*A*A*T+168*T*R+7152*Z
             -15*A**4-90*A*A*R+414*A*U-108*A*V-117*R*R-75*X)/46656}
    h = [4*A/3,
         s.Rational(25,36)*A*A+R/6-s.Rational(2,27)*T,
         s.Rational(17,108)*A**3+A*R/12-s.Rational(2,27)*A*T
         +s.Rational(4,27)*P4+s.Rational(71,216)*U-V/36,
         -7*A**4/5184-7*A*A*R/288-7*A*A*T/972+14*A*P4/81+301*A*U/864-7*A*V/144
         -28*K/81-7*L/81-16*P5/81-103*R*R/5184+7*R*T/324-7*T*T/1458-61*X/3888+175*Z/162]
    log_h = [h[0],h[1]-h[0]**2/2,h[2]-h[0]*h[1]+h[0]**3/3,
             h[3]-h[0]*h[2]-h[1]**2/2+h[0]**2*h[1]-h[0]**4/4]
    proposal = [4*A/3,
                6*C3-A*A/4+R/9,
                6*C4-3*A*C3+19*A**3/324-A*R/12+U/12,
                6*C5-3*A*C4+(A*A-5*R/6)*C3-9*C3*C3
                -11*A**4/576+37*A*A*R/864-53*A*U/2592-5*A*V/432
                -53*R*R/5184-47*X/7776+(13*Z-L-12*K)/81]
    residuals = {f'log_H_order_{i+1}':str(s.expand(log_h[i]-proposal[i].subs(thermal)))
                 for i in range(4)}
    external = [1,-B0/4,(B0*B0+B1)/32,-(B0**3+3*B0*B1+B2)/384,
                (B0**4+6*B0*B0*B1+3*B1*B1+4*B0*B2+B3)/6144]
    logs = [log_h[i]+(-1)**(i+1)*[B0,B1,B2,B3][i]/(4**(i+1)*s.factorial(i+1))
            for i in range(4)]
    normalized=[s.Integer(1)]
    for n in range(1,5):
        normalized.append(s.expand(sum(j*logs[j-1]*normalized[n-j] for j in range(1,n+1))/n))
        expected=sum(([s.Integer(1)]+h)[j]*external[n-j] for j in range(n+1))
        residuals[f'a{n+2}_reconstruction']=str(s.expand(normalized[n]-expected))
    ell,G,z3=s.symbols('log2 Catalan zeta3')
    q2=2*ell**2-s.Rational(27,2)*C3
    p4=s.Rational(81,2)*C4+8*ell**3-27*ell*C3+s.Rational(359,16)*z3
    omega2=52*G*q2+2*ell*p4-384*G**2+336*ell*z3
    # Directly verify the compact d=2 LOG coefficient, not a numerical fit.
    log4two=proposal[3].subs({A:4*ell,R:0,U:-14*z3,V:-4*z3,X:0,
                            K:32*G**2-28*z3*ell,L:-2*ell*p4,Z:4*G*q2})+s.Rational(1,64)
    compact2=6*C5-11*ell*C4+(46*ell**2-26*G)*C3/3-9*C3**2-380*ell**4/81 \
             +104*G*ell**2/81-128*G**2/27+1303*ell*z3/216+s.Rational(1,64)
    residuals['dimension_2_log_order_4']=str(s.expand(log4two-compact2))
    if any(v!='0' for v in residuals.values()):
        raise AssertionError(residuals)
    return {'status':'PASS','exact_residuals':residuals,
            'scope':'Checks substitutions, logarithmic simplification, and reconstruction; '
                    'does not rederive one-point loop integrals or prove master identities.'}


def serial(obj:Any)->Any:
    if isinstance(obj,dict): return {str(k):serial(v) for k,v in obj.items()}
    if isinstance(obj,(list,tuple)): return [serial(v) for v in obj]
    if isinstance(obj,mp.mpf): return mp.nstr(obj,mp.mp.dps)
    return obj


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify',action='store_true')
    p.add_argument('--dimension');p.add_argument('--C3');p.add_argument('--C4')
    p.add_argument('--C5');p.add_argument('--omega');p.add_argument('--precision',type=int,default=50)
    args=p.parse_args()
    if args.verify:
        result=symbolic_checks()
    else:
        if any(x is None for x in (args.dimension,args.C3,args.C4)):
            p.error('Supply --dimension, --C3 and --C4, or use --verify.')
        if args.precision<20:p.error('Working precision must be at least 20.')
        with mp.workdps(args.precision):
            result=serial(from_thermal(args.dimension,args.C3,args.C4,args.C5,args.omega))
    print(json.dumps(result,indent=2))
