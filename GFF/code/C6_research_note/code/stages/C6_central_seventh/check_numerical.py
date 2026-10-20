"""Independent floating-point checks of the finite-Fourier periodization.

Evaluates paired, shifted gamma-ratio sums at nonzero deformation parameters.
The new central harmonic summand is not used in these tests. Results are checks,
not certified bounds; certify.py constructs the separate rational intervals.
"""
from pathlib import Path
import json,math,time
import mpmath as mp
ROOT=Path(__file__).resolve().parent

def phi(x,t,N):
    def Z(t):
        a=t+mp.mpf(1)/4+x;b=t+mp.mpf(3)/4-x
        seq=mp.mpf(1);total=mp.mpf(0);bs=0
        for n in range(N):
            bs+=math.comb(N,n);w=1-mp.mpf(bs)/2**N
            total+=(-1)**n*w*(n+t)*seq
            seq*=((n+a)/(n+b))**7
        return (mp.gamma(a)/mp.gamma(b))**7*total
    den=(mp.gamma(mp.mpf(1)/2+x)/mp.gamma(1-x)*mp.cos(mp.pi*x))**7
    return (mp.sin(mp.pi*(mp.mpf(1)/4+t+x))**7*Z(t)+mp.sin(mp.pi*(mp.mpf(1)/4-t+x))**7*Z(1-t))/den

def main():
    out=[];st=time.time()
    for digits,N in [(60,260),(90,400)]:
        mp.mp.dps=digits
        for x in [mp.mpf(0),mp.mpf(1)/100,-mp.mpf(1)/100+1j*mp.mpf(1)/250]:
            f1=phi(x,mp.mpf(1)/8,N);f2=phi(x,mp.mpf(1)/4,N);f3=phi(x,mp.mpf(3)/8,N)
            a1=((f1+f3)/mp.sqrt(2)+f2)/2;a2=(f1-f3)/2;a3=((f1+f3)/mp.sqrt(2)-f2)/2
            for t in [mp.mpf(1)/7,mp.mpf(1)/3,mp.mpf(1)/5+1j*mp.mpf(1)/100]:
                pred=a1*mp.sin(2*mp.pi*t)+a2*mp.sin(4*mp.pi*t)+a3*mp.sin(6*mp.pi*t)
                err=abs(phi(x,t,N)-pred)
                assert err<mp.mpf(10)**(-digits+12)
                out.append({'digits':digits,'N':N,'x':str(x),'t':str(t),'absolute_difference':mp.nstr(err,12)})
    result={'scope':'Floating-point checks at nonzero parameters, not interval certificates. No central harmonic series is inserted into the compared functions.','checks':out,'count':len(out),'seconds':time.time()-st}
    (ROOT/'results/numerical_checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(len(out),'numerical Fourier checks passed in',time.time()-st,'seconds')
    for d in [60,90]:print(d,'digits max error',max(float(x['absolute_difference']) for x in out if x['digits']==d))
    return result
if __name__=='__main__':main()
