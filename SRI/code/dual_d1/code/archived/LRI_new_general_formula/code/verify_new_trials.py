#!/usr/bin/env python3
"""Reproduce fitted trial functions, tests and a formal Euler-kernel exclusion.

This program does NOT compute a new physical LRI coefficient. The existing
C1,...,C7 are inputs; all n>=8 outputs refer solely to trial functions.
Requires SymPy, mpmath, and the companion modules in code/.
Run from any directory; no external data or original RG archives are required.
"""
from pathlib import Path
import argparse,json
from formal_series import *
from spectral_model import *
from endpoint_model import *
from euler_kernel import ks,ds,e,cert


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--order',type=int,default=9)
    ap.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'verification/results.json')
    opts=ap.parse_args()
    if not 8<=opts.order<=14:ap.error('--order must be between 8 and 14; higher orders can be computationally costly')
    report={'status':'EXACT CHECKS OF TRIALS; NO NEW PHYSICAL COEFFICIENT', 'checks':{}}
    g6= -s.Rational(27,16)*z2*z3-s.Rational(2201,512)*z2-s.Rational(11,4)*z3**2+s.Rational(147,32)*z3-s.Rational(793,128)*z4+s.Rational(153,16)*z5+s.Rational(1059,64)*z6+s.Rational(33655,4096)
    assert canonical(g[6]-g6)==0
    report['checks']['inverse_C7']=True
    report['inverse']={str(i):str(v) for i,v in enumerate(g)}

    coeffs=fit(7)
    assert coeffs is not None and len(coeffs)==24
    report['trial_polynomials']=[[list(k),str(v)] for k,v in coeffs.items()]
    report['checks']['seven_order_symbolic_fit']=True
    print('Exact C1,...,C7 fit: PASS (24 rational parameters fitted).',flush=True)
    predictions={};cc=c.copy()
    for m in range(8,opts.order+1):
        n=m+2;ys=[s.Integer(0)]+[-cc[i] for i in range(1,m)]+[s.Integer(0)]*2
        ef=evaluate_F(coeffs,ys,n)
        assert all(q==0 for q in ef[:m+1])
        cm=canonical(ef[m+1]/4);cc[m]=cm
        assert sum(weight(cm,w) for w in range(m))==cm
        predictions[str(m)]={'exact':str(cm),'numeric':numerical(cm,40),'highest_weight':str(weight(cm,m-1))}
        print('TRIAL C%d ='%m,numerical(cm,22),flush=True)
    report['trial_predictions']=predictions
    report['checks']['implicit_recurrence_and_weight_bound_through_order']=opts.order

    lower=fit(6)
    ys=[s.Integer(0)]+[-c[j] for j in range(1,7)]+[s.Integer(0)]*2
    cv=canonical(evaluate_F(lower,ys,9)[8]/4)
    assert canonical(cv-c[7])!=0
    report['retrospective_test']={'input_orders':'1,...,6','predicted_C7':str(cv),'numeric':numerical(cv,40),'actual_C7':numerical(c[7],40),'passed':False}
    print('Retrospective fitting-rule test: FAIL; predicted',numerical(cv,22),flush=True)

    ep=exact_endpoint(coeffs)
    expected=-s.Rational(43294985,3538944)-s.Rational(3407,6144)*PI+s.Rational(8222701,207360)/PI
    assert s.expand(ep[0]-expected)==0
    epc=exact_endpoint(coeffs,True)
    assert epc[0]==0 and s.expand(3*epc[2]-2*epc[1])==0
    ys=[s.Integer(0)]+[-c[j] for j in range(1,8)]+[s.Integer(0)]*2
    ec=completed_F(coeffs,ys,10)
    assert all(q==0 for q in ec[:9])
    cv8=canonical(ec[9]/4)
    shift_expected=(z2-4)/12
    assert canonical(s.diff(cv8,TAU)-shift_expected)==0
    expected0=canonical(cc[8]+s.Rational(2443757,960)*z2-s.Rational(158684509,46080))
    assert canonical(cv8.subs(TAU,0)-expected0)==0
    report['endpoint_family']={'raw_residual':str(ep[0]),'completed_F':str(epc[0]),'completed_gradient_condition':str(s.expand(3*epc[2]-2*epc[1])),'C8':str(cv8),'C8_tau0_numeric':numerical(cv8.subs(TAU,0),40),'dC8_dtau':str(shift_expected)}
    report['checks']['endpoint_value_slope_and_free_parameter_exact']=True

    # Numerical checks use Gamma functions directly, not their Taylor series.
    mp.mp.dps=60
    fn=numeric_function(coeffs,True,0);v=mp.mpf('.5')
    fy=mp.diff(lambda y:fn(y,v),v);ft=mp.diff(lambda t:fn(v,t),v)
    assert abs(fn(v,v))<mp.mpf('1e-53') and abs(3*ft-2*fy)<mp.mpf('1e-52')
    fyy=mp.diff(lambda y:fn(y,v),v,2);ftt=mp.diff(lambda t:fn(v,t),v,2)
    fyt=mp.diff(lambda y:mp.diff(lambda t:fn(y,t),v),v)
    yp=-mp.mpf(2)/3
    curvature=(ftt+2*fyt*yp+fyy*yp**2)/fy
    gff=mp.mpf(4)/3+mp.mpf(32)/9*(mp.pi+4*mp.log(2))
    report['GFF_curvature_holdout']={'trial_tau0':mp.nstr(curvature,45),'GFF':mp.nstr(gff,45),'passed':False}
    assert abs(curvature-gff)>1
    # Independently verify exact endpoint kernel values and first derivatives.
    for (a,b),row in ENDPOINT_KERNELS.items():
        fun=lambda yy,tt:numeric_kernel(a,b,yy,tt)
        actual=[fun(v,v),mp.diff(lambda yy:fun(yy,v),v),mp.diff(lambda tt:fun(v,tt),v)]
        for ex,num in zip(row,actual):
            val=s.sympify(ex).subs({PI:s.pi,LOG2:s.log(2)})
            assert abs(mp.mpf(str(s.N(val,55)))-num)<mp.mpf('1e-50')
    report['checks']['endpoint_kernel_derivatives_independent']=True
    print('Endpoint value/slope: PASS; withheld curvature: FAIL.',flush=True)

    # Universal single-product Euler kernel: arbitrary analytic rho.
    targets=[z2,-2*z3,s.Rational(21,4)*z4,-17*z5+3*z2*z3,s.Rational(1059,32)*z6-s.Rational(11,2)*z3*z3]
    sol={}
    for n in range(1,5):
        eq=s.expand(ks[n]-targets[n]).coeff(z(n+2))
        roots=s.solve(eq.subs(sol),ds[n-1]);assert len(roots)==1
        sol[ds[n-1]]=s.factor(roots[0])
    res5=s.factor((ks[3]-targets[3]).coeff(z2).coeff(z3).subs(sol))
    res6=s.factor((ks[4]-targets[4]).coeff(z3,2).subs(sol))
    p=8*e**2-16*e+23
    q=864*e**4-4176*e**3+16504*e**2-21884*e+14095
    assert s.factor(res5+p/27)==0 and s.factor(res6-q/5400)==0
    resultant=s.resultant(p,q,e)
    assert resultant==401375222784
    assert s.rem(q,p,e)==3402*e-s.Rational(24273,2)
    report['euler_exclusion']={'scope':'Formal/MZV coefficient matching; arbitrary analytic rho with rho(0)=1. Not an exclusion of sums or nonlinear systems.', 'moments':{str(k):str(v) for k,v in sol.items()},'kernel_coefficients':[str(v) for v in ks],'polynomials':[str(p),str(q)],'resultant':str(resultant),'remainder':str(s.rem(q,p,e)),'endpoint_MZV_derivations':cert.MZV_REPORT}
    report['checks']['single_product_Euler_kernel_formally_excluded']=True
    print('General scalar Euler-product kernel exclusion: PASS.',flush=True)

    # Exact characteristic-polynomial conversion for the next even order.
    # T/2 is the only integer-power part; delta=2t^2, so [t^8]T/2=8T4.
    d=s.Symbol('delta');T4=s.Symbol('T4')
    assert s.expand(T4*(2*Y**2)**4/2).coeff(Y,8)==8*T4
    report['checks']['physical_C8_requires_8T4']=True
    report['scope']='Existing C1,...,C7 are archived inputs. No raw kink integral, RG beta coefficient or new thermal coefficient was computed in this study.'
    opts.output.parent.mkdir(parents=True,exist_ok=True)
    opts.output.write_text(json.dumps(report,indent=2)+'\n')
    print('Wrote',opts.output,flush=True)
if __name__=='__main__':main()
