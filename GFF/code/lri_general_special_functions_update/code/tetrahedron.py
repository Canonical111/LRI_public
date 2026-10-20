#!/usr/bin/env python3
"""General-d tetrahedron: double Mellin--Barnes quadrature and exact tests.
The quadrature uses double precision; convergence checks are not interval bounds.
Requirements: numpy, scipy, mpmath.  No saved period value is used as an input.
"""
import argparse,json,time
from pathlib import Path
import numpy as np
from scipy.special import loggamma,gammaln,digamma,polygamma
import mpmath as mp

def tetrahedron(d:float,step:float=.015,cutoff:float=9.,block:int=128)->tuple[float,float]:
    if d<=0 or step<=0 or cutoff<=0:raise ValueError('d, step and cutoff must be positive')
    q=d/4.; c=-q/3; n=int(np.ceil(cutoff/step)); y=np.arange(-n,n+1)*step
    v=c+1j*y[None,:]; lv=2*loggamma(-v)+loggamma(q+v)-loggamma(q-v)
    total=0j
    for start in range(0,len(y),block):
        u=c+1j*y[start:start+block,None]
        lu=2*loggamma(-u)+loggamma(q+u)-loggamma(q-u)
        w=u+v
        total+=np.exp(lu+lv+2*loggamma(q+w)+loggamma(-w)-loggamma(2*q+w)).sum()
    ans=2*np.exp(2*gammaln(2*q)-4*gammaln(q))*total*step**2/(2*np.pi)**2
    return float(ans.real),float(ans.imag)

def exact_tetra(d):
    mp.mp.dps=70
    if d==1:return 6*mp.gamma(mp.mpf(1)/4)**4/mp.pi
    if d==2:return (mp.gamma(mp.mpf(1)/4)/mp.gamma(mp.mpf(3)/4))**4
    if d==4:return 12*mp.zeta(3)
    return None

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('tetrahedron_checks.json'))
    args=p.parse_args();rows=[]
    for d in [1.,1.5,2.,2.5,3.,3.5,4.]:
        for h,T in [(.015,8.),(.01,10.)]:
            st=time.time();val,imag=tetrahedron(d,h,T)
            A=digamma(d/2)+digamma(1)-2*digamma(d/4)
            R=polygamma(1,d/2)-polygamma(1,1)
            row=dict(d=d,step=h,cutoff=T,Tetra=val,imaginary_residual=imag,
                     C2=A/9,C3=(A*A+R)/108-val/81,seconds=time.time()-st)
            ex=exact_tetra(d)
            if ex is not None:row.update(exact_tetrahedron=mp.nstr(ex,65),error_vs_exact=float(mp.mpf(val)-ex))
            rows.append(row);print(row,flush=True)
    q=mp.mpf(1)/4
    exact2=dict(Tetra=mp.nstr(exact_tetra(2),65),
                C2=mp.nstr(4*mp.log(2)/9,65),
                C3=mp.nstr(4*mp.log(2)**2/27-exact_tetra(2)/81,65))
    out=dict(method='blockwise tensor trapezoidal quadrature of the double MB contour',
             numerical_precision='IEEE double; settings comparison only, not interval certification',
             rows=rows,dimension_two_exact=exact2)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
