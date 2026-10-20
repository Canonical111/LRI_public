"""Supplementary floating-point checks; never inputs to interval construction."""
from fractions import Fraction as F
from pathlib import Path
import json,time,sys
import mpmath as mp
ROOT=Path(__file__).resolve().parent

def original_primitive(dps=80):
    mp.mp.dps=dps
    q=mp.mpf(1)/4;h=mp.mpf(1)/2;pi=mp.pi
    ga=mp.gamma(q);gb=mp.gamma(3*q);eta=ga**2/(2*pi**mp.mpf('1.5'))
    def reflected(a,b,x,initial,pref):
        if x>mp.mpf('1e-20'):return mp.hyp2f1(a,b,a+b,1-x)
        c=mp.mpf(1);d=initial;p=mp.mpf(1);value=mp.mpf(0);lx=mp.log(x)
        for n in range(8):
            value+=c*p*(d-lx)
            c*=(n+a)*(n+b)/(n+1)**2
            d+=2/mp.mpf(n+1)-1/(n+a)-1/(n+b);p*=x
        return pref*value
    def integrand(y):
        if not y:return mp.mpf(0)
        x=y**4;om=1-x
        u=mp.hyp2f1(q,3*q,1,x)
        ub=reflected(q,3*q,x,6*mp.log(2),1/(ga*gb))
        hh=mp.hyp2f1(q,q,h,x)
        hb=reflected(q,q,x,pi+6*mp.log(2),mp.sqrt(pi)/ga**2)
        v=mp.hyp2f1(q,q,1,x)
        vb=mp.sqrt(pi)/gb**2*hh-2*mp.sqrt(pi)/ga**2*mp.sqrt(x)*mp.hyp2f1(3*q,3*q,3*h,x)
        B=2*eta**2*hb**2+eta*v*hb
        Bb=2*eta**2*hh**2+eta*vb*hh
        M=u*u+ub*ub+3/mp.sqrt(2)*u*ub
        return 128*pi**4*y**3*(M*(Bb/mp.sqrt(x)+B/mp.sqrt(om))+B*Bb/mp.sqrt(x*om))
    end=mp.root(mp.mpf('.5'),4)
    return mp.quad(integrand,[0,end/4,end/2,end])

def midpoint(rec):
    return (mp.mpf(rec['lower_numerator'])+mp.mpf(rec['upper_numerator']))/mp.power(2,rec['denominator_power_of_two']+1)

def main(dps=80):
    st=time.time();value=original_primitive(dps)
    data=json.loads((ROOT/'results/complete_refined.json').read_text())
    ref=midpoint(data['values']['Pa'])
    out={'scope':'Floating-point quadrature of the original folded Gauss-kernel primitive; no recurrence or new tail bound is inserted into the integrand.',
         'working_decimal_digits':dps,'Pa_original_kernel':mp.nstr(value,dps),
         'difference_from_certified_interval_midpoint':mp.nstr(value-ref,30),
         'interval_certificate':False,'seconds':time.time()-st}
    path=ROOT/'results'/f'quadrature_{dps}.json';path.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__':main(int(sys.argv[1]) if len(sys.argv)>1 else 80)
