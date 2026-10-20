"""Cross-check fits of the local exponent that include the departure from the fixed point (the "detuning" term).
They are NOT the estimator (estimator.py) and no published value is taken from them. They come from the review of
13 October 2026 (REVIEWS.md) and test the estimator from outside; note Sec. 3.8 defines them.

Both fit Delta_loc(l) (estimator.local_exponent) with an approach term plus a detuning term B exp(y (l - l_end)), where
y = 1 - D_inf is the growth rate of the residual detuning and l_end the last fitted RG time, on several ranges ending at
l_end = l_N - k / y_t (l_N = N ln Lambda, y_t = 1 - settled value): the last k / y_t of RG time, where the detuning
dominates, is left out. Levenberg-Marquardt (scipy least_squares, method 'lm'). The result is the median over the
accepted fits, with their range and count.

late      approach A exp(-omega (l - l_0)); ranges l_0 in (20, 25, 30, 35) (40, 50, 60, 70 at Delta_sigma = 0.001),
          k in (8, 10, 12); fits accepted if the largest residual is below 2e-6 (2e-5 if none is). A test of the
          settled and extrapolated values at every point.
crossover approach A / (exp(omega (l - l_0)) - 1) (the one-loop crossover form near s = 1/2) or A exp(-omega (l - l_0));
          ranges l_0 in (13, 18, 22), k in (12, 15); fits accepted if the largest residual is below 2e-5 and
          0 < omega < 2. A cross-check at the points not converged in chain depth.
"""
import math
import numpy as np
from scipy.optimize import least_squares
from estimator import local_exponent


def _summary(vals):
    if not vals:return None
    D=np.array([v[0] for v in vals]);om=np.array([v[1] for v in vals])
    return {'value':float(np.median(D)),'min':float(D.min()),'max':float(D.max()),'n':int(len(D)),'omega':float(np.median(om))}


def late(detail,Lambda,nsites,settled,ds):
    n,l,d=local_exponent(detail,Lambda);lN=nsites*math.log(Lambda);yt=1-settled;fits=[]
    for llo in ((40.,50.,60.,70.) if ds<0.005 else (20.,25.,30.,35.)):
        for k in (8.,10.,12.):
            m=(l>=llo)&(l<=lN-k/yt)
            if m.sum()<10:continue
            x=l[m];v=d[m];xe=x[-1]
            g=lambda p:p[0]+p[1]*np.exp(-p[2]*(x-x[0]))+p[3]*np.exp((1-p[0])*(x-xe))-v
            r=least_squares(g,[v[len(v)//2],v[0]-v[len(v)//2],.2,-1e-5],method='lm',max_nfev=50000,x_scale='jac')
            fits.append((float(r.x[0]),float(r.x[2]),float(np.max(np.abs(r.fun)))))
    good=[f for f in fits if f[2]<2e-6] or [f for f in fits if f[2]<2e-5]
    s=_summary(good)
    if s:s['tried']=len(fits);s['residual_cut']=2e-6 if any(f[2]<2e-6 for f in fits) else 2e-5
    return s


def crossover(detail,Lambda,nsites,settled):
    n,l,d=local_exponent(detail,Lambda);lN=nsites*math.log(Lambda);yt=1-settled;fits=[]
    for llo in (13.,18.,22.):
        for k in (12.,15.):
            m=(l>=llo)&(l<=lN-k/yt)
            if m.sum()<8:continue
            x=l[m];v=d[m];xe=x[-1]
            for form in ('crossover','exp'):
                if form=='crossover':
                    g=lambda p:p[0]+p[1]/np.expm1(np.clip(p[2]*(x-p[4]),1e-9,700))+p[3]*np.exp((1-p[0])*(x-xe))-v
                    p0=[v[-1],(v[0]-v[-1])*0.5,0.1,0.0,0.0]
                else:
                    g=lambda p:p[0]+p[1]*np.exp(-p[2]*(x-x[0]))+p[3]*np.exp((1-p[0])*(x-xe))-v
                    p0=[v[-1],v[0]-v[-1],0.1,0.0]
                try:r=least_squares(g,p0,method='lm',max_nfev=50000,x_scale='jac')
                except Exception:continue
                mr=float(np.max(np.abs(r.fun)))
                if mr<2e-5 and 0<r.x[2]<2:fits.append((float(r.x[0]),float(r.x[2]),mr))
    s=_summary(fits)
    if s:s['tried']=None
    return s
