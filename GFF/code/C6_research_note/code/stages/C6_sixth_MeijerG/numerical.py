"""Independent checks of a finite MeijerG reduction of the Pb block.
Barnes integrals are used only as numerical verification, not in the final
Wolfram expression. No Wolfram kernel execution is claimed.
"""
import json, sys, time
from pathlib import Path
from fractions import Fraction
import mpmath as mp
sys.path.insert(0, str(Path(__file__).resolve().parent/'legacy'))
from rational_tails import enclosure

ROOT = Path(__file__).resolve().parent

def mf(q):
    return mp.mpf(q.numerator)/q.denominator

def run(digits=70, N=160, order=50):
    mp.mp.dps=digits
    start=time.time()
    def kernel(u):
        return mp.exp(8*mp.re(mp.loggamma(mp.mpf('0.25')+1j*u))
                    -4*mp.re(mp.loggamma(mp.mpf('0.75')+1j*u)))
    segments=[0,mp.mpf('0.125'),mp.mpf('0.25'),mp.mpf('0.5'),1,2,4,8,16,mp.inf]
    g44=mp.quad(kernel,segments)/mp.pi
    g35=mp.quad(lambda u:kernel(u)/mp.cosh(2*mp.pi*u),segments)/mp.pi
    pb_new=8*mp.pi*(13*g35+11*g44)
    alpha=mp.atan(mp.mpf(11)/13)/mp.pi
    def alpha_kernel(u):
        s=mp.mpf('0.25')+1j*u
        z=(4*mp.loggamma(s)+5*mp.loggamma(mp.mpf('0.5')-s)
           -2*mp.loggamma(1-s)-mp.loggamma(mp.mpf('0.5')+s)
           -mp.loggamma(s+alpha)-mp.loggamma(1-s-alpha))
        return mp.re(mp.exp(z))
    galpha=mp.quad(alpha_kernel,segments)/mp.pi
    pb_single=8*mp.pi*mp.sqrt(290)*galpha
    params=[('Hminus',['1/4']*6,['3/4']*6),
            ('H0',['1/2']*6,['1']*6),
            ('Hplus',['3/4']*6,['5/4']*6)]
    hs={}; reports=[]
    for name,up,dn in params:
        iv,info=enclosure(tuple(up),tuple(dn),N,order)
        hs[name]=mf((iv[0]+iv[1])/2)
        reports.append({'name':name,'value':mp.nstr(hs[name],digits),
                        'exact_rational_interval_width':mp.nstr(mf(iv[1]-iv[0]),8)})
    Q=mp.gamma(mp.mpf('0.25'))**4/mp.pi
    pb_old=6*Q**3/mp.pi*(2*hs['Hminus']-1)-104*mp.pi**5*hs['H0']+2**18*mp.pi**5/Q**3*hs['Hplus']
    return {'working_digits':digits,'ordinary_cutoff':N,'ordinary_tail_order':order,
            'G35':mp.nstr(g35,digits),'G44':mp.nstr(g44,digits),
            'Galpha':mp.nstr(galpha,digits),'alpha':mp.nstr(alpha,digits),'Pb_single':mp.nstr(pb_single,digits),'single_vs_two_Pb_difference':mp.nstr(abs(pb_single-pb_new),8),'Pb_new':mp.nstr(pb_new,digits),'Pb_old':mp.nstr(pb_old,digits),
            'absolute_Pb_difference':mp.nstr(abs(pb_new-pb_old),8),
            'absolute_C6_change_due_to_substitution':mp.nstr(24*abs(pb_new-pb_old)/2187,8),
            'ordinary_values':reports,'seconds':time.time()-start,
            'new_full_C6_evaluation':False,'new_rigorous_MeijerG_interval':False,
            'method':'MeijerG values: separate inverse-Mellin integrals with exponentially decaying real gamma kernels; old values: rational-ratio interval evaluator. Floating point gamma factors and quadrature are not rigorous intervals.'}

if __name__=='__main__':
    d=int(sys.argv[1]) if len(sys.argv)>1 else 70
    n=int(sys.argv[2]) if len(sys.argv)>2 else 160
    m=int(sys.argv[3]) if len(sys.argv)>3 else 50
    report=run(d,n,m)
    (ROOT/'results').mkdir(exist_ok=True)
    (ROOT/'results'/f'numerical_{d}.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
