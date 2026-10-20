"""The estimator of Delta_E for one NRG item: settled value, plateau test and, where there is no plateau, extrapolation.

This rule replaces the quality-range midpoint used until 13 October 2026 (note Sec. 3.7; the old values are in note
App. E). It was written on 13 October 2026, after the review, and before the comparisons with the epsilon series and the
Monte Carlo study were recomputed. Its constants are fixed below and were not varied afterwards; note Sec. 3.7 reports how
the classification depends on TAU, on h and on the window width.

Input: one entry of data/summaries/<campaign>_details.json (written by summarize.py): the window audit of the record
(start, stop, Delta_E, log_response_residual, gap_relative_variation of every window) and the per-site
log|d_alpha Delta_n| of the derivative flow.

Settled value  The window with the smallest residual + variation: the stretch of the chain where the critical flow is
               closest to its fixed point. It is the 'selected' window of the original analyzer and of every record.
Plateau test   The windows whose start lies within h = ceil(w/4) sites of the settled window (w = window width). The
               plateau drift is the largest |Delta_E(window) - settled value| among them. There is a plateau if the
               drift is <= TAU. The plateau drift is then the chain-depth error.
Extrapolation  Only where there is no plateau. The per-site local exponent
                   Delta_loc(n) = 1 - [ln|d_alpha Delta_{n+1}| - ln|d_alpha Delta_{n-1}|] / (2 ln Lambda)
               at RG time l = n ln Lambda is fitted with Delta_inf + A exp(-omega (l - l_0)) (free Delta_inf, A, omega;
               unweighted least squares) on l_hi - S <= l <= l_hi, for S in SPANS, where l_hi is the RG time of the last
               site of the settled window and l_0 the first fitted point. A span with fewer than MIN_POINTS sites is
               skipped. Start values: Delta_inf = last point, A = first - last, omega = 0.2; Levenberg-Marquardt
               (scipy least_squares, method 'lm'). The extrapolated value is the median of the three Delta_inf. The
               chain-depth error is the larger of |extrapolated - settled| and the spread of the three fits.
               The extrapolation is *determined* only if every fit converged with omega > OMEGA_MIN. Where the fit range
               lies on a flat plateau (Delta_sigma = 0.001) omega is not determined, the fitted values depend on the last
               bits of the input, and the extrapolation is reported as not determined (None). A point that needs the
               extrapolation must have it determined for every item (build_tables.py stops otherwise).
"""
import math
import numpy as np
from scipy.optimize import least_squares

TAU=5e-5               # plateau threshold on the plateau drift
SPANS=(30.0,25.0,20.0)  # fit ranges in RG time l = n ln Lambda, ending at the settled window
MIN_POINTS=8            # fewest sites in a fit range
OMEGA_MIN=0.01          # an extrapolation with a fitted omega below this is not determined


def settled_window(detail):
    W=detail['windows']
    return min(W,key=lambda w:w['log_response_residual']+w['gap_relative_variation'])


def plateau_drift(detail,sel):
    W=detail['windows'];h=math.ceil((sel['stop']-sel['start'])/4)
    return max(abs(w['Delta_E']-sel['Delta_E']) for w in W if abs(w['start']-sel['start'])<=h),h


def local_exponent(detail,Lambda):
    """Sites n = 1 .. N-2, RG time l = n ln Lambda, Delta_loc(n)."""
    lg=np.array(detail['log_abs_d_alpha_odd_gap'],dtype=float);lnL=math.log(Lambda)
    n=np.arange(1,len(lg)-1);return n,n*lnL,1-(lg[2:]-lg[:-2])/(2*lnL)


def extrapolate(detail,Lambda,sel):
    n,l,d=local_exponent(detail,Lambda);lhi=(sel['stop']-1)*math.log(Lambda);fits=[]
    for S in SPANS:
        m=(l>=lhi-S-1e-9)&(l<=lhi+1e-9);x=l[m];y=d[m]
        if len(x)<MIN_POINTS:continue
        res=least_squares(lambda p:p[0]+p[1]*np.exp(-p[2]*(x-x[0]))-y,[y[-1],y[0]-y[-1],0.2],method='lm',max_nfev=20000)
        fits.append({'span':S,'Delta_inf':float(res.x[0]),'omega':float(res.x[2]),'max_abs_residual':float(np.max(np.abs(res.fun))),
                     'points':int(len(x)),'converged':bool(res.success)})
    if not fits or not all(f['converged'] and f['omega']>OMEGA_MIN for f in fits):
        return {'value':None,'spread':None,'l_hi':lhi,'fits':None,'status':'not determined'}
    v=sorted(f['Delta_inf'] for f in fits)
    return {'value':float(np.median(v)),'spread':v[-1]-v[0],'l_hi':lhi,'fits':fits,'status':'determined'}


def estimate(detail,Lambda):
    """Everything the budget needs from one item."""
    sel=settled_window(detail);drift,h=plateau_drift(detail,sel)
    W=detail['windows'];prev=[w for w in W if w['start']==sel['start']-1]
    out={'settled':sel['Delta_E'],'settled_start':sel['start'],'settled_stop':sel['stop'],'h':h,'plateau_drift':drift,
         'plateau':drift<=TAU,'drift_per_site':None if not prev else sel['Delta_E']-prev[0]['Delta_E'],
         'extrapolation':extrapolate(detail,Lambda,sel)}
    return out


def value(e,extrapolated):
    """The estimator of a point: the settled value, or the extrapolation where the point has no plateau."""
    if not extrapolated:return e['settled']
    if e['extrapolation']['value'] is None:raise ValueError('extrapolation needed but not determined')
    return e['extrapolation']['value']


def depth_error(e,extrapolated):
    if not extrapolated:return e['plateau_drift']
    x=e['extrapolation'];return max(abs(x['value']-e['settled']),x['spread'])
