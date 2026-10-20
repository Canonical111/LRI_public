#!/usr/bin/env python3
"""Verify the thermal/invariant algebra and record provenance-labelled numbers.

This does NOT perform new kink integrations or determine Omega. Exact symbolic
identities are distinguished from comparisons with archived numerical outputs.
"""
from __future__ import annotations
import argparse,json,platform
from pathlib import Path
import sympy as s
import mpmath as mp

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();root=args.root.resolve();mp.mp.dps=100
    z2,z3,z4,z5,z6=s.symbols('Z2 Z3 Z4 Z5 Z6')
    q=s.Rational
    C={1:s.Integer(-2),2:q(1,2),3:q(39,16)+2*z2,
       4:4-4*z2-8*z3,
       5:q(11249,1024)-q(361,16)*z2+24*z3+q(49,2)*z4,
       6:26-38*z2+104*z3-80*z4-272*z5+112*z2*z3}
    T2=2-2*z2-4*z3;T3=C[6]/4
    D2=q(5,2)+2*z2;D3=q(21,4)-13*z2+11*z3+11*z4
    even={z2:s.pi**2/6,z4:s.pi**4/90,z6:s.pi**6/945}
    def zero(expr):
        return s.expand(expr.subs(even))==0
    assert zero(C[3]-(D2-q(1,16)))
    assert zero(C[4]-2*T2)
    assert zero(C[5]-(2*D3-T2/2+(D2-q(1,16))**2/4))
    assert zero(C[6]-4*T3)
    known=(q(94647,32768)+q(1011,1024)*z2+q(77,4)*z3-q(1059,64)*z4
           +68*z5-20*z2*z3+q(343,8)*z6-16*z3**2)
    assert zero(known-(-T3-T2*T2+C[3]*C[5]/2))
    # Independent binomial expansion of the two eigenvalues through t^7.
    t=s.Symbol('t');d=2*t*t;D4=s.Symbol('D4')
    T=d/2+T2*d**2+T3*d**3
    D=-2*d+D2*d**2+D3*d**3+D4*d**4
    Q=s.series((T*T/4-D)/(2*d),t,0,7).removeO()
    h=s.expand(Q-1)
    sq=s.series(1+h/2-h*h/8+h**3/16,t,0,7).removeO()
    f=s.Poly(s.series(1+T/2-2*t*sq,t,0,8).removeO(),t)
    for n in range(1,7):assert zero(f.nth(n)-C[n]),n
    assert zero(f.nth(7)-(4*D4+known))
    plus=s.Poly(s.series(1+T/2+2*t*sq,t,0,8).removeO(),t)
    for n in range(1,8):assert zero(plus.nth(n)-(-1)**n*f.nth(n)),n
    def numeric(expr,digits=82):
        return str(s.N(expr.subs({z2:s.zeta(2),z3:s.zeta(3),z4:s.zeta(4),z5:s.zeta(5),z6:s.zeta(6)}),digits))
    coefficients={str(n):{'power_of_x':str(q(n,2)),
                 'expression_zeta':str(C[n]),'expression_even_zeta_evaluated':str(s.expand(C[n].subs(even))),
                 'decimal':numeric(C[n]),'status':'Published baseline' if n<=2 else 'Specified matched RG result with archived exact integral reduction; not independently rederived physically in this consolidation'} for n in C}
    out={'convention':'Delta_epsilon(x)=1+sum(C_n*x**(n/2)); x=(1-s)/2',
         'C':coefficients,'invariants':{n:{'expression':str(e),'decimal':numeric(e)} for n,e in {'T2':T2,'T3':T3,'D2':D2,'D3':D3}.items()},
         'C7':{'expression':'4*D4 + '+str(known),'numerical_value':None,'status':'Uncomputed; Omega remains unknown'},
         'qualification':'Decimal strings evaluate the expressions. They are not rigorous interval error estimates for original integrals or finite-x remainder bounds.'}
    (root/'data/thermal_coefficients.json').write_text(json.dumps(out,indent=2)+'\n')
    archived=root/'stages/C6_integrals/reproducibility/final_evaluation_run2.json'
    c=json.loads(archived.read_text())['coefficients']
    exact_c6=mp.mpf(26)-38*mp.zeta(2)+104*mp.zeta(3)-80*mp.zeta(4)-272*mp.zeta(5)+112*mp.zeta(2)*mp.zeta(3)
    residual=exact_c6-mp.mpf(c['C6']);assert abs(residual)<mp.mpf('1e-75')
    # Numerical recombination of the old D4 piece uses saved evaluated beta inputs.
    oldpath=root/'stages/C7_partial/old_D4_symbolic.expr'
    env={n:s.Float(c[n+'_check'],95) for n in ['a','b','c','f','p','A','E','G','q','k']}
    env.update({n:s.Float(c[n],95) for n in ['V','R','J','L','M','N']})
    old=s.sympify(oldpath.read_text(),locals=env);assert not old.free_symbols
    partial=json.loads((root/'data/C7_reported_inputs.json').read_text())
    r={n:mp.mpf(v['value']) for n,v in partial['reported_inputs'].items()}
    r['K']=mp.mpf(partial['K']['value']);oldnum=mp.mpf(str(s.N(old,90)))
    B4=(oldnum-3*r['alpha']/32+r['beta']/4-r['gamma']/2+r['Phi']/16-r['Psi']/8-r['Q']/8-r['P']/16-3*r['K']/128)
    C7constant=4*B4+mp.mpf(numeric(known,95))
    diagnostics={'C6_archived_decimal_residual':mp.nstr(residual,16),
                 'C7_old_piece_recombined_from_archived_C6_beta_numbers':mp.nstr(oldnum,60),
                 'C7_partial_B4_using_transcript_only_new_inputs':mp.nstr(B4,18),
                 'C7_partial_constant_using_transcript_only_new_inputs':mp.nstr(C7constant,18),
                 'Omega':None,'C7':None,
                 'warning':'The C7 partial recombination is a consistency diagnostic using reported rounded inputs, not a fresh evaluation of their defining integrals, not a C7 estimate, and not an interval bound.'}
    (root/'verification/C7_partial_diagnostic.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
    result={'status':'PASS','exact_checks':['Invariant conversion for C3,C4,C5,C6','Known part of C7 including even-zeta reductions','Independent binomial eigenvalue expansion through t^7','Branch exchange t -> -t through t^7'],
            'numerical_diagnostics':diagnostics,'python':platform.python_version(),'sympy':s.__version__,'mpmath':mp.__version__}
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
