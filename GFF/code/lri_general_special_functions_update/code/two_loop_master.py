#!/usr/bin/env python3
"""All-regulator two-loop master in two ordinary 3F2(1/4) functions.
The bubble-normalized amplitude is S(d,z)=[4F1(d,z)-2W(d,z)F2(d,z)]/z^2.
A2=3/z^2+3S, B2=1/z^2+S/2.  Cauchy coefficients are used only to
verify and tabulate Laurent data, not to assert a derivative-free C4/C5.
Requires mpmath.
"""
from pathlib import Path
import argparse,json
import mpmath as mp

def regularized_master(d,z):
    z=mp.mpc(z);d=mp.mpf(d);a=(d+z)/4;b=(d+3*z)/4
    r=mp.gamma((d+z)/2)/mp.gamma(1+z/2)
    f1=mp.hyper([d/2,z/2,a],[1-z/2,a+mp.mpf('.5')],mp.mpf('.25'))
    f2=mp.hyper([z,(d+z)/2,b],[1+z/2,b+mp.mpf('.5')],mp.mpf('.25'))
    w=r*r*mp.gamma(1+z)*mp.gamma(1-z/2)*mp.gamma(b)**2/(mp.gamma(a)**2*mp.gamma(d/2)*mp.gamma(2*b))
    return 4*f1-2*w*f2

def euler_master(d,z):
    d=mp.mpf(d);z=mp.mpf(z);a=(d+z)/4
    r=mp.gamma((d+z)/2)/mp.gamma(1+z/2)
    pref=r*r*mp.gamma(z)/mp.gamma(a)**4*mp.beta(a,a)*mp.beta(2*a,z/2)
    def integrand(t):
        if not t:return mp.mpf(0)
        v=t**4/2
        return 4*t**3*(v*(1-v))**(a-1)*mp.hyp2f1(d/2,z/2,d/2+z,1-v+v*v)
    return pref*mp.quad(integrand,[0,mp.mpf('.25'),mp.mpf('.5'),mp.mpf('.75'),1])

def coeffs(d,radius=mp.mpf('.025'),nodes=72,order=4):
    angles=[2*mp.pi*k/nodes for k in range(nodes)]
    vals=[regularized_master(d,radius*mp.exp(1j*t)) for t in angles]
    out=[]
    for j in range(order+1):
        out.append(mp.fsum(v*mp.exp(-1j*j*t) for t,v in zip(angles,vals))/(nodes*radius**j))
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('two_loop_checks.json'));args=p.parse_args()
    mp.mp.dps=75;checks=[];tab={}
    for d,z in [(1,mp.mpf('.4')),(2,mp.mpf('.3')),(3,mp.mpf('.35'))]:
        h=regularized_master(d,z)/z**2;e=euler_master(d,z)
        checks.append(dict(d=d,z=str(z),S_hyper=mp.nstr(h,60),S_Euler=mp.nstr(e,60),residual=mp.nstr(h-e,8)))
        print(checks[-1],flush=True)
    for d in [1,2,3]:
        cc=coeffs(d);cc2=coeffs(d,mp.mpf('.02'),80)
        a2={};b2={}
        for j,c in enumerate(cc):
            a2[j-2]=3*c.real+(3 if j==0 else 0)
            b2[j-2]=c.real/2+(1 if j==0 else 0)
        A=mp.digamma(mp.mpf(d)/2)+mp.digamma(1)-2*mp.digamma(mp.mpf(d)/4)
        tab[d]=dict(A2={str(k):mp.nstr(v,62) for k,v in a2.items()},B2={str(k):mp.nstr(v,62) for k,v in b2.items()},
                    S_pole_minus_A=mp.nstr(cc[1]-A,8),coefficient_settings_difference=mp.nstr(max(abs(x-y) for x,y in zip(cc,cc2)),8))
        print('Laurent',d,tab[d],flush=True)
    out=dict(normalization='massive-Schwinger IR prescription with bubble-normalized bare coupling; do not mix its finite parts with the d=1 ordered-span prescription',
             working_digits=75,checks=checks,laurent=tab,scope='Euler-integral identity and two-loop Laurent coefficients only; numerical residuals not rigorous bounds')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
