"""Independent quadratures of the old, branch-averaged, and unit-slope inner kernels."""
import json, sys, time
from pathlib import Path
import mpmath as mp

def run(dps=40):
    mp.mp.dps=dps
    pi=mp.pi; half=mp.mpf(1)/2
    cuts=[-mp.inf,-16,-4,-1,0,1,4,16,mp.inf]
    out=[]
    for s in [mp.mpf(1)/4,mp.mpf(1)/4+mp.mpf(3)/10*1j,mp.mpf(1)/4-mp.mpf(7)/10*1j]:
        def old(v,sign):
            t=mp.mpf(1)/8+1j*v
            # Gamma(t)Gamma(1-t) exp(sign i pi t), evaluated stably.
            if sign==-1:
                pair=2j*pi/mp.expm1(2j*pi*t)
            else:
                pair=-2j*pi/mp.expm1(-2j*pi*t)
            return pair/((1-t)*(1-2*s-t))/(2*pi)
        def new(v):
            t=mp.mpf(1)/16+1j*v
            return mp.cot(2*pi*t)/((half-t)*(half-s-t))/(2*pi)
        minus=mp.quad(lambda v:old(v,-1),cuts)
        plus=mp.quad(lambda v:old(v,1),cuts)
        unit=mp.quad(new,cuts)
        expected=(mp.digamma(1-2*s)+mp.euler)/(-2*s)
        row={'s':str(s),'old_minus':str(minus),'old_plus':str(plus),'unit_slope_inner':str(unit),
             'old_expected':str(expected),'branch_difference':str(abs(minus-plus)),
             'unit_identity_error':str(abs(pi*unit/2-expected)),
             'minus_identity_error':str(abs(minus-expected)),
             'plus_identity_error':str(abs(plus-expected))}
        print(json.dumps(row),flush=True);out.append(row)
    qerrs=[]
    for t in [mp.mpf(1)/16+mp.mpf(j)/7*1j for j in (0,1,3,10)]:
        ratio=(mp.gamma(t)*mp.gamma(half+t)*mp.gamma(1-t)*mp.gamma(half-t)**2*
               mp.rgamma(mp.mpf(3)/2-t)*mp.rgamma(mp.mpf(1)/4+t)*mp.rgamma(mp.mpf(3)/4+t)*
               mp.rgamma(mp.mpf(1)/4-t)*mp.rgamma(mp.mpf(3)/4-t))
        elementary=mp.cot(2*pi*t)/(half-t)
        qerrs.append(abs(ratio-elementary)/(1+abs(elementary)))
    data={'working_digits':dps,'rows':out,'local_gamma_quotient_max_relative_error':str(max(qerrs)),
          'rigorous_interval':False,'method':'independent one-dimensional complex quadratures; no outer integral here'}
    (Path(__file__).parent/'results'/f'inner_{dps}.json').write_text(json.dumps(data,indent=2))
    return data
if __name__=='__main__':run(int(sys.argv[1]) if len(sys.argv)>1 else 40)
