"""Independent floating-point checks; no new interval certificate is claimed."""
from __future__ import annotations
import argparse,json,time
from pathlib import Path
from functools import lru_cache
import mpmath as mp
from coefficients import Cquad,Cbarnes
ROOT=Path(__file__).resolve().parent

def old_primitive(digits:int):
    q=mp.mpf(1)/4;half=mp.mpf(1)/2;p=mp.pi
    ell=mp.log(2);Q=mp.gamma(q)**4/p;sqrtQ=mp.sqrt(Q)
    @lru_cache(None)
    def kernels(y):
        if not y:return [mp.mpf(0)]*3,[mp.mpf(0)]*3
        t=y*y
        h=mp.hyp2f1(q,q,half,t);v=mp.hyp2f1(q,q,1,t)
        vb=sqrtQ*h/(2*p)-2*y*mp.hyp2f1(3*q,3*q,3*half,t)/sqrtQ
        if t>mp.mpf('1e-10'):hb=mp.hyp2f1(q,q,half,1-t)
        else:
            coeff=power=mp.mpf(1);d=p+6*ell;hb=mp.mpf(0);lt=mp.log(t)
            for n in range((digits+30)//10+5):
                hb+=coeff*power*(d-lt)
                coeff*=(n+q)**2/(n+1)**2
                d+=2/mp.mpf(n+1)-2/(n+q)
                power*=t
            hb/=sqrtQ
        return ([v*v,sqrtQ/p*v*hb,Q/p**2*hb*hb],
                [vb*vb,sqrtQ/p*vb*h,Q/p**2*h*h])
    def fun(y):
        f,g=kernels(y)
        return 4*p**4*(15*f[2]*g[2]+24*f[1]*g[1]-4*f[0]*g[0])/mp.sqrt(1-y*y)
    end=1/mp.sqrt(2)
    return mp.quad(fun,[0,end/4,end/2,end])

def run(digits=50,cutoff=2048):
    if digits<30:raise ValueError('Use at least 30 decimal working digits.')
    start=time.time()
    with mp.workdps(digits):
        checks=[];cache={}
        for n in [0,1,2,3,8]:
            for j in [1,2,3]:
                B=Cbarnes(j,n);Q=Cquad(j,n);cache[j,n]=B
                checks.append({'j':j,'n':n,'barnes':mp.nstr(B,digits),
                               'chebyshev_quadrature':mp.nstr(Q,digits),
                               'absolute_difference':mp.nstr(abs(B-Q),10)})
        rows=[[cache[j,n] for j in [1,2,3]] for n in [0,1]]
        for n in range(1,cutoff-1):
            rows.append([(4*n*(4*n*n+1)*rows[n][j-1]-(2*n-1)**3*rows[n-1][j-1]
                          +32*(j-2)*n*(-1)**n/mp.pi)/(2*n+1)**3 for j in [1,2,3]])
        recerrors=[]
        for n in [2,3,8]:
            for j in [1,2,3]:recerrors.append(abs(rows[n][j-1]-cache[j,n]))
        pa=old_primitive(digits)
        inherited=mp.mpf('334926.045248051837883222001240077786613085905253136679683127457050582775321995132565614807357126170234753534116133150495')
        S=mp.mpf(0);partials=[]
        for n,(a,b,c) in enumerate(rows):
            phi=10*a*a+21*a*b+18*b*b+15*b*c
            S+=(1 if n==0 else 2)*(-1)**n*phi
            if n+1 in [1,16,32,128,512,2048,cutoff]:
                v=8*mp.pi**3*S
                partials.append({'modes':n+1,'Pa_partial':mp.nstr(v,digits),
                                 'signed_error_vs_Gauss_quadrature':mp.nstr(v-pa,15)})
        mx=max(mp.mpf(c['absolute_difference']) for c in checks)
        tolerance=mp.power(10,-digits+10)
        if max(mx,max(recerrors),abs(pa-inherited))>tolerance:
            raise ArithmeticError('Independent numerical comparison exceeded its working-precision tolerance.')
        return {'working_decimal_digits':digits,'new_rigorous_interval':False,
                'Wolfram_kernel_executed':False,'all_C6_sectors_recomputed':False,
                'coefficient_comparisons':checks,'max_coefficient_difference':mp.nstr(mx,12),
                'max_recurrence_vs_independent_barnes_difference':mp.nstr(max(recerrors),12),
                'Gauss_quartic_primitive':mp.nstr(pa,digits),
                'difference_from_inherited_reference':mp.nstr(abs(pa-inherited),12),
                'literal_spectral_partial_sums':partials,
                'scope':'Partial sums are not assigned the exact primitive value. Parseval proves the infinite identity; these are independent coefficient and implementation checks.',
                'elapsed_seconds':time.time()-start}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--digits',type=int,default=50);ap.add_argument('--cutoff',type=int,default=2048)
    a=ap.parse_args();r=run(a.digits,a.cutoff)
    dest=ROOT/f'results/numerical_{a.digits}.json';dest.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='coefficient_comparisons'},indent=2))
