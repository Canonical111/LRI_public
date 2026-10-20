#!/usr/bin/env python3
"""Fifth epsilon coefficient of the LRI bulk one-point function a_phi2.

Conventions: physical dimension 0<d<4, epsilon=2s-d,
Delta_phi=(d-epsilon)/4, and < :Phi^2: > = a_phi2/|y|^(2 Delta_phi).
This is a fixed-d perturbative coefficient, not a finite-epsilon error bound.

The new diagrammatic amplitude was derived in this project. Its four-loop
beta-function input and the primitive-period conventions are from the supplied
long_range_ising_condensed.tex. This does not independently validate that input.

Requirements: mpmath. Examples:
  python calculate_a5.py --d 1 2 3 --json results.json
  python calculate_a5.py --d 2.5 --tetra T_VALUE --wheel P4_VALUE
  python calculate_a5.py --d 2.5 --thermal-c3 C3_VALUE --thermal-c4 C4_VALUE

T = alpha_I4 = 6 Q_d; P4 is the normalized primitive four-wheel, NOT C4.
At d=1,2, the default periods use Gamma/hypergeometric formulas from the note.
At d=3, default period inputs are the note's displayed 33-digit evaluations.
For other dimensions supply either both periods or both thermal coefficients.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any
import mpmath as mp


def number(x:Any)->mp.mpf:
    return x if isinstance(x,mp.mpf) else mp.mpf(str(x))


def fixed_periods(d:mp.mpf)->tuple[mp.mpf,mp.mpf,dict]:
    q0=mp.mpf(1)/4
    if d in (1,2):
        fm=mp.hyper([q0,q0,2*q0,2*q0],[3*q0,3*q0,1],1)
        fp=mp.hyper([3*q0,3*q0,2*q0,2*q0],[5*q0,5*q0,1],1)
        bm=mp.gamma(q0)**4*fm
        bp=64*mp.pi**4/mp.gamma(q0)**4*fp
        if d==1:
            T=6*mp.gamma(q0)**4/mp.pi;P4=13*bm-3*bp
        else:
            T=(mp.gamma(q0)/mp.gamma(3*q0))**4
            P4=(bm**2-bp**2)/(4*mp.pi**3)
        return T,P4,{'method':'Gamma / fixed-argument 4F3(1) formulas from the supplied note'}
    if d==3:
        return (6*mp.mpf('5.01710256455385536959085484569018'),
                mp.mpf('62.0583279434066724664633885840967'),
                {'method':'displayed primitive-period evaluations from the supplied note',
                 'warning':'Finite-precision inputs, not certified error intervals; extra output digits are not new physical accuracy.'})
    raise ValueError('For general d supply T and P4, or thermal C3 and C4.')


def coefficients(d:Any,*,tetra:Any=None,wheel:Any=None,
                 thermal_c3:Any=None,thermal_c4:Any=None)->dict:
    d=number(d)
    if not mp.isfinite(d) or not 0<d<4:
        raise ValueError('The expansion is at fixed 0<d<4.')
    q=d/4
    A=mp.digamma(2*q)-2*mp.digamma(q)+mp.digamma(1)
    R=mp.polygamma(1,2*q)-mp.polygamma(1,1)
    U=mp.polygamma(2,q);V=mp.polygamma(2,1)+mp.polygamma(2,2*q)
    B=mp.pi*mp.cot(mp.pi*q)+1/q
    S=mp.polygamma(1,1-q)-mp.polygamma(1,q)+1/q**2
    D2=mp.polygamma(2,1-q)-mp.polygamma(2,q)+2/q**3
    K=mp.gamma(1-q)*mp.gamma(2*q)**3/(54*mp.gamma(1+q)*mp.gamma(4*q))
    use_periods=(tetra is not None or wheel is not None)
    use_thermal=(thermal_c3 is not None or thermal_c4 is not None)
    if use_periods and use_thermal:
        raise ValueError('Supply periods OR thermal coefficients, not both.')
    if use_periods:
        if tetra is None or wheel is None:raise ValueError('Both T and P4 are required.')
        T=number(tetra);P4=number(wheel);meta={'method':'user-supplied primitive periods'}
    elif use_thermal:
        if thermal_c3 is None or thermal_c4 is None:raise ValueError('Both C3 and C4 are required.')
        C3=number(thermal_c3);C4=number(thermal_c4)
        T=mp.mpf(3)/4*(A*A+R)-81*C3
        P4=(648*C4+A**3+mp.mpf(4)/3*A*T+3*A*R-mp.mpf(53)/2*U+3*V)/16
        meta={'method':'primitive periods inferred algebraically from user-supplied thermal C3,C4',
              'warning':'This is a hybrid calculation, not an independent check of the thermal coefficients.'}
    else:
        T,P4,meta=fixed_periods(d)
    if not (mp.isfinite(T) and mp.isfinite(P4)):
        raise ValueError('Period inputs must be finite.')
    h1=4*A/3
    h2=mp.mpf(25)/36*A*A+R/6-2*T/27
    h3=(mp.mpf(17)/108*A**3+A*R/12-2*A*T/27+4*P4/27
        +mp.mpf(71)/216*U-V/36)
    a2=-K
    a3=a2*(h1-B/4)
    a4=a2*(h2-B*h1/4+(B*B+S)/32)
    a5=a2*(h3-B*h2/4+A*(B*B+S)/24-(B**3+3*B*S+D2)/384)
    C3=(A*A+R)/108-T/81
    C4=(16*P4-A**3-mp.mpf(4)/3*A*T-3*A*R+mp.mpf(53)/2*U-3*V)/648
    from_thermal=a2*(6*C4+(5*A-mp.mpf(3)/2*B)*C3+mp.mpf(13)/108*A**3
        +mp.mpf(7)/108*A*R-mp.mpf(23)/144*A*A*B-B*R/36
        +A*(B*B+S)/24+U/12-(B**3+3*B*S+D2)/384)
    residual=from_thermal-a5
    if not mp.almosteq(from_thermal,a5):raise ArithmeticError('Thermal-coefficient conversion check failed.')
    result=dict(d=d,q=q,A=A,R=R,U=U,V=V,B=B,S=S,D2=D2,K=K,
                T=T,P4=P4,h1=h1,h2=h2,h3=h3,a2=a2,a3=a3,a4=a4,a5=a5,
                thermal_C3=C3,thermal_C4=C4,conversion_residual=residual,
                period_input=meta)
    if d==2:
        ell=mp.log(2)
        explicit=(-4*P4/729+(8*ell-1)*T/729-mp.mpf(272)/729*ell**3
                  +mp.mpf(50)/243*ell**2-4*ell/81+mp.mpf(485)/2916*mp.zeta(3)
                  +mp.mpf(1)/216)
        if not mp.almosteq(a5,explicit):raise ArithmeticError('Explicit d=2 formula check failed.')
        result['d2_explicit_residual']=explicit-a5
    return result


def serialize(obj:Any)->Any:
    if isinstance(obj,mp.mpf):return mp.nstr(obj,45)
    if isinstance(obj,dict):return {k:serialize(v) for k,v in obj.items()}
    if isinstance(obj,(tuple,list)):return [serialize(v) for v in obj]
    return obj


def main()->None:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--d',nargs='+',default=['1','2','3'])
    p.add_argument('--tetra');p.add_argument('--wheel')
    p.add_argument('--thermal-c3');p.add_argument('--thermal-c4')
    p.add_argument('--dps',type=int,default=70);p.add_argument('--json',type=Path)
    args=p.parse_args()
    if args.dps<35:p.error('--dps must be at least 35.')
    if len(args.d)>1 and any(x is not None for x in (args.tetra,args.wheel,args.thermal_c3,args.thermal_c4)):
        p.error('Custom inputs require exactly one dimension.')
    mp.mp.dps=args.dps
    try:
        rows=[coefficients(d,tetra=args.tetra,wheel=args.wheel,
                          thermal_c3=args.thermal_c3,thermal_c4=args.thermal_c4) for d in args.d]
    except (ValueError,ArithmeticError) as exc:p.error(str(exc))
    for row in rows:
        print('d =',row['d'])
        for key in ('a2','a3','a4','a5'):print(f'  {key} = {mp.nstr(row[key],27)}')
    examples=[]
    for row in rows:
        if row['d']==2:e=mp.mpf('.3')
        elif row['d']==3:e=mp.mpf('.18548')
        else:continue
        through4=sum(row[f'a{k}']*e**k for k in (2,3,4))
        term=row['a5']*e**5
        examples.append(dict(d=row['d'],epsilon=e,through_epsilon4=through4,
                             fifth_order_term=term,through_epsilon5=through4+term,
                             warning='Successive truncations, not uncertainty intervals.'))
    result={'scope':'New diagrammatic a5 calculation with four-loop RG and primitive-period input from the supplied note.',
            'normalization':'< :Phi^2: > = a_phi2 / |y|^(2 Delta_phi); epsilon=2s-d, Delta_phi=(d-epsilon)/4.',
            'formula':'a5=-K*(h3-B*h2/4+A*(B^2+S)/24-(B^3+3*B*S+D2)/384)',
            'rows':rows,'finite_epsilon_truncations':examples,
            'limitation':'Internal algebraic/integral-reduction checks; not external validation of the four-loop beta function, not a new bootstrap calculation, and not a resummation error estimate.'}
    if args.json:
        args.json.parent.mkdir(parents=True,exist_ok=True)
        args.json.write_text(json.dumps(serialize(result),indent=2)+'\n')
        print('Saved',args.json)

if __name__=='__main__':main()
