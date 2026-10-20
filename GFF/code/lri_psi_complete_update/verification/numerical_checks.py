#!/usr/bin/env python3
"""Reproducible consistency checks for the analytic Kappa proof.
These are numerical tests, not interval bounds and not the proof itself.
Requires mpmath. The endpoint master is recomputed; graph integrals are not.
"""
from pathlib import Path
import json, time, argparse
import mpmath as m
from kappa_endpoint import integral_kappa
from hyp3_asym import hyp3
import K_pfq

def run(digits=110):
    st=time.perf_counter(); m.mp.dps=digits
    fmt=lambda x:m.nstr(x,digits)
    A=m.digamma(m.mpf('.5'))+m.digamma(1)-2*m.digamma(m.mpf('.25'))
    T=m.polygamma(1,m.mpf('.25')); Tb=m.polygamma(1,m.mpf('.75'))
    U=m.polygamma(2,m.mpf('.25'))
    Kpsi=(T*(3*T-Tb)+A*U)/2
    Knum,I,j2,g2=integral_kappa()
    ell=m.log(2)
    u=-(16/m.pi)*m.quad(lambda x:m.log(m.cos(x)),[0,m.pi/8,m.pi/4])
    sigma=4*m.quad(lambda x:x*x/m.sin(x) if x else 0,[0,m.pi/4,m.pi/2])
    rec={'master_working_digits':digits,'Kappa_psi':fmt(Kpsi),'Kappa_endpoint':fmt(Knum),
         'Kappa_endpoint_minus_psi':fmt(Knum-Kpsi),
         'lower_u_residual':fmt(u-(4*ell-8*m.catalan/m.pi)),
         'lower_sigma_residual':fmt(sigma-(8*m.pi*m.catalan-14*m.zeta(3))),
         'scope':'Fresh endpoint master, elementary integral coefficients and finite-parameter hypergeometric tests. No interval enclosure; no graph recomputation.'}
    print('endpoint master residual',m.nstr(Knum-Kpsi,15),flush=True)
    m.mp.dps=75
    rec['finite_parameter_working_digits']=75
    rec['tail_controls']={'base':{'N':120,'order':52},'stronger':{'N':180,'order':64}}
    tests=[]
    for t in [m.mpf('.2'),m.mpf('.37'),m.mpc('.12','.07')]:
        vals=[]
        for N,order in [(120,52),(180,64)]:
            F=lambda z:hyp3([m.mpf('.5'),m.mpf('.5'),z],[1,1],N=N,order=order)
            G=lambda z:hyp3([z,z,z],[m.mpf('.5')+z]*2,N=N,order=order)
            f,fn,g,gn=F(t),F(-t),G(t),G(-t)
            bil=m.cos(m.pi*t)**2*g*gn+m.pi**2*t*t*f*fn-1
            J2=2*m.pi*(1+m.cos(m.pi*t)+2*m.sin(m.pi*t))*m.gamma(t)**2/m.gamma(m.mpf('.5')+t)**2*g+2*m.pi**2*(2+m.tan(m.pi*t/2))*f
            K_pfq.h3=lambda a,b:hyp3(a,b,N=N,order=order)
            J6=K_pfq.jhat(t)/(t*t)
            vals.append((bil,J6-J2,J2))
        test={'t':[m.nstr(t.real,20),m.nstr(t.imag,20)],
              'bilinear_residual_base':m.nstr(vals[0][0],30),
              'bilinear_residual_stronger':m.nstr(vals[1][0],30),
              'six_minus_two_base':m.nstr(vals[0][1],30),
              'six_minus_two_stronger':m.nstr(vals[1][1],30),
              'J2_stronger_minus_base':m.nstr(vals[1][2]-vals[0][2],30)}
        tests.append(test);print('finite point',test,flush=True)
    rec['finite_parameter_checks']=tests
    m.mp.dps=50; t=m.mpf('.2')
    F=lambda z:m.hyper([m.mpf('.5'),m.mpf('.5'),z],[1,1],1)
    G=lambda z:m.hyper([z,z,z],[m.mpf('.5')+z]*2,1)
    res=m.cos(m.pi*t)**2*G(t)*G(-t)+m.pi**2*t*t*F(t)*F(-t)-1
    rec['mpmath_direct_bilinear']={'working_digits':50,'t':'.2','residual':m.nstr(res,40)}
    rec['elapsed_seconds']=time.perf_counter()-st
    return rec

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--digits',type=int,default=110)
    args=parser.parse_args()
    if args.digits<30:parser.error('use at least 30 working digits')
    result=run(args.digits)
    output=Path(__file__).with_name('numerical_checks.json')
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
