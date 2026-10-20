"""Convergent one-dimensional evaluation of [delta^2 g^2](beta_g/g).
The parameter delta is expanded in the Gaussian pair kernel before integration.
This computes a scheme-dependent input, NOT the final invariant C6.
"""
import json
from pathlib import Path
import mpmath as m

def compute(dps=65):
    m.mp.dps=dps
    half=m.mpf(1)/2
    def integrand(t):
        a=m.log(t); b=m.log1p(-t)
        # P is coefficient of delta^2 in W3 at the minimal-gap shell,
        # after setting the explicit shell log to zero.
        P=-a*a*b+a*b*b-b**3/3+2*a*a*b*b-2*a*b**3+b**4/2
        K=1/(t*t*(1-t)**2)
        return K*P-a*a/t
    # Exponential coordinate makes the subtraction numerically stable.
    def stable(w):
        t=m.exp(-w);a=-w;b=m.log1p(-t)
        # Compute P/t - a^2 without subtraction of close leading terms.
        if t < m.mpf('0.001'):
            bplus = -sum(t**j/m.mpf(j) for j in range(2,max(25,dps//3+12)))
            # -b/t -1 = -(b+t)/t
            remainder = -a*a*bplus/t+(a*b*b-b**3/3+2*a*a*b*b-2*a*b**3+b**4/2)/t
            return (remainder+a*a*(2*t-t*t))/(1-t)**2
        return integrand(t)*t
    integral=m.quad(stable,[m.log(2),2,5,15,40,m.inf])
    V=2*m.log(2)**3/3-2*integral
    return {'dps':dps,'convergent_integral':m.nstr(integral,dps-5),'V':m.nstr(V,dps-5)}

if __name__=='__main__':
    results=[compute(50),compute(85)]
    for result in results:print(json.dumps(result,indent=2),flush=True)
    (Path(__file__).resolve().parent/'three_tail_second.json').write_text(json.dumps(results,indent=2)+'\n')
