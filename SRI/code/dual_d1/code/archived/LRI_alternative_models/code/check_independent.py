#!/usr/bin/env python3
"""Independent finite-power and direct-function checks of the trial generators.

These verify calculations about the trial formulas, not new physical C_n.
"""
import math,json,argparse
from pathlib import Path
import sympy as s
import mpmath as mp
from sympy.functions.combinatorial.numbers import stirling
import alternative_models as a


def explicit_power_exp(ell,n):
    # Direct finite exponential, independent of h'=ell' h recurrence.
    out=a.zero(n);out[0]=s.Integer(1)
    power=a.zero(n);power[0]=s.Integer(1)
    for j in range(1,n+1):
        power=a.mul(power,ell,n)
        out=[s.expand(u+v/s.factorial(j)) for u,v in zip(out,power)]
    return out


def explicit_power_log(H,n):
    x=list(H);x[0]=0
    out=a.zero(n);power=a.zero(n);power[0]=s.Integer(1)
    for j in range(1,n+1):
        power=a.mul(power,x,n)
        out=[s.expand(u+(-1)**(j+1)*v/s.Integer(j)) for u,v in zip(out,power)]
    return out


def mpr(q):
    return mp.mpf(int(s.numer(q)))/int(s.denom(q))


def kernel_callable(fit):
    terms=[(k,d,r,mpr(c)) for k,d,r,c in fit['terms']]
    poly=[mpr(v) for v in fit['rational']]
    def K(t):
        if not t:return mp.mpf(0)
        L=mp.loggamma(1+t)+mp.euler*t
        v=[L]
        for j in range(1,5):
            v.append(sum(int(stirling(j,k,kind=2))*t**k*(mp.digamma(1+t)+mp.euler if k==1 else mp.polygamma(k-1,1+t)) for k in range(1,j+1)))
        ans=mp.fsum(c*t**j for j,c in enumerate(poly))
        for kind,d,r,c in terms:
            if kind=='Theta':w=v[r]
            elif kind=='LL':w=L*L
            elif kind=='Dsq':w=2*L*v[1]
            else:raise ValueError('This check uses the default theta dictionary')
            ans+=c*t**d*w
        return ans
    return K


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path('independent_checks.json'));p.add_argument('--numerical',action='store_true');args=p.parse_args()
    inp=a.input_coeffs();H=[s.Integer(1)]+[-inp[j+1]/2 for j in range(1,7)]
    assert explicit_power_log(H,6)==a.logarithm(H,6)
    out={'input_logarithm_direct_finite_powers':True,'models':{}}
    for borel in [False,True]:
        print('checking model',borel,flush=True)
        fit=a.fit_kernel(7,borel)
        v=a.kernel_series(fit,8)
        ell=[s.expand(e*(s.factorial(k) if borel else 1)) for k,e in enumerate(v)]
        assert explicit_power_exp(ell,8)==a.exponential(ell,8)
        name='borel' if borel else 'convergent'
        out['models'][name]={'finite_power_exponential_vs_recurrence_through_C9':True}
        if args.numerical:
            mp.mp.dps=60;K=kernel_callable(fit);coeff=a.model_coeffs(fit,9)
            if borel:
                nodes,weights=mp.gauss_quadrature(36,'laguerre')
            c={k:mp.mpf(a.num(v,70)) for k,v in coeff.items()}
            rows=[]
            for t in [mp.mpf('0.001'),mp.mpf('0.0005')]:
                exponent=mp.fsum(weights[j]*K(nodes[j]*t) for j in range(len(nodes))) if borel else K(t)
                direct=1-2*t*mp.exp(exponent)
                approx=1+mp.fsum(v*t**k for k,v in c.items())
                err=direct-approx
                assert abs(err)<mp.mpf('1e-22')
                rows.append({'t':str(t),'direct':mp.nstr(direct,50),'series_through_C9':mp.nstr(approx,50),'difference':mp.nstr(err,25),'difference_over_t10':mp.nstr(err/t**10,25)})
            ratio=mp.mpf(rows[0]['difference'])/mp.mpf(rows[1]['difference'])
            assert 900<ratio<1150
            out['models'][name]['direct_function_checks']=rows
            out['models'][name]['remainder_ratio_t_to_half_t']=mp.nstr(ratio,25)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
