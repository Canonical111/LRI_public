"""Independent floating-point checks of the new wheel-H representation.

The H value is evaluated using its proved inner Barnes integral, not by
substitution of its known wheel value.  Old rational component enclosures
are used only after integration as independent comparison data.
These floating-point checks are NOT interval certificates.
"""
from pathlib import Path
import argparse, json, time
import mpmath as mp
ROOT = Path(__file__).resolve().parent

def rational(rec):
    return mp.mpf(rec['numerator']) / mp.mpf(rec['denominator'])

def old_midpoints():
    rec = json.loads((ROOT/'inputs/C6_standard_even_intervals.json').read_text())['high_accuracy'][-1]
    return [(rational(rec[k]['lower']) + rational(rec[k]['upper']))/2 for k in ('F4','F6')]

def alpha():
    return mp.atan(mp.mpf(5)/8)/mp.pi

def d(s):
    return mp.polygamma(1,mp.mpf('0.5')-s)-mp.polygamma(1,1-s)

def N(s):
    a=alpha()
    return (mp.gamma(s)**2 * mp.gamma(mp.mpf('.5')-s)**3 /
        (mp.gamma(1-s)**2 * mp.gamma(mp.mpf('.5')+s) *
         mp.gamma(s+a) * mp.gamma(1-s-a)))

def M1(s):
    return mp.gamma(s)*mp.gamma(mp.mpf('.5')-s)**3/(mp.gamma(1-s)**3*mp.gamma(mp.mpf('.5')+s))

def M2(s):
    return mp.gamma(s)**2*mp.gamma(mp.mpf('.5')-s)**2/(mp.gamma(1-s)**2*mp.gamma(mp.mpf('.5')+s)**2)

def gamma_t(t):
    return mp.gamma(t)*mp.gamma(t+mp.mpf('.5'))*mp.gamma(mp.mpf('.5')-t)*mp.gamma(1-t)

def inner(s):
    """The actual second Barnes integral, upward at Re(t)=1/8."""
    ct=mp.mpf(1)/8
    def kernel(v):
        t=ct+1j*v
        return gamma_t(t)/(mp.mpf('.5')-s-t)**2/(2*mp.pi)
    # The kernel is exponentially decaying, with a possible peak at -Im(s).
    knots=sorted(set([-mp.inf,-4,-1,-mp.im(s),0,1,4,mp.inf]))
    return mp.quad(kernel,knots)

def wheel_H():
    # I(s)=pi*d(s). Combining upper/lower outer halves gives this real integral.
    return mp.quad(lambda u: mp.re(N(mp.mpf(1)/4+1j*u)*d(mp.mpf(1)/4+1j*u)),
                   [0,mp.mpf(1)/4,mp.mpf(1)/2,1,2,4,8,16,mp.inf])

def run(digits, do_inner):
    mp.mp.dps=digits
    start=time.time()
    packing=[]
    for u in [0,mp.mpf(1)/7,mp.mpf(2)/3,2]:
        s=mp.mpf(1)/4+1j*u
        packing.append(abs(mp.sqrt(89)*N(s)-8*M1(s)-5*M2(s)))
    inner_checks=[]
    if do_inner:
        for imag in [0,mp.mpf(1)/5,mp.mpf(2)/3]:
            s=mp.mpf(1)/4+1j*imag
            got=inner(s)
            inner_checks.append({'s':str(s),'value':mp.nstr(got,digits),
                 'absolute_error':mp.nstr(abs(got-mp.pi*d(s)),8)})
    H=wheel_H()
    f4,f6=old_midpoints()
    Wold=24*f4+15*mp.pi*f6
    Wnew=mp.sqrt(89)*H/mp.pi**2
    Bnew=-393*mp.pi*mp.sqrt(89)*H
    Bold=-9432*mp.pi**3*f4-5895*mp.pi**4*f6
    rec={'working_digits':digits,'Hwheel':mp.nstr(H,digits),
         'alphaW':mp.nstr(alpha(),digits),
         'W0_from_new_H':mp.nstr(Wnew,digits),
         'W0_from_inherited_KdF_midpoints':mp.nstr(Wold,digits),
         'W0_absolute_difference':mp.nstr(abs(Wnew-Wold),10),
         'wheel_block_in_r6':mp.nstr(Bnew,digits),
         'wheel_block_absolute_difference':mp.nstr(abs(Bnew-Bold),10),
         'packing_max_error':mp.nstr(max(packing),10),
         'inner_Barnes_checks':inner_checks,
         'method':'Outer gamma-product Barnes kernel, with analytically evaluated inner Barnes integral; separately tested direct inner integration.',
         'reference_use':'Existing fine rational F4,F6 interval midpoints used only for comparison AFTER integration.',
         'new_rigorous_interval_certificate':False,
         'new_full_C6_evaluation':False,
         'elapsed_seconds':time.time()-start}
    out=ROOT/'results'/f'numerical_{digits}.json'
    out.write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('digits',type=int,nargs='?',default=40)
    p.add_argument('--inner',action='store_true')
    args=p.parse_args()
    if not 20 <= args.digits <= 120:
        p.error('digits must be between 20 and 120')
    run(args.digits,args.inner)
