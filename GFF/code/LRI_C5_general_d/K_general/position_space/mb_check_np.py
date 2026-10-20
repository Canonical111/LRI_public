#!/usr/bin/env python3
"""Quick double-precision check of the 2-fold MB representation of J_t (symmetric-star form):
   J_t = N * (1/(2 pi i)^2) int int Phi(z1,z2),  N = Gamma(2q)^2/Gamma(q)^4,
   Phi = G(-z1)^2 G(-z2)^2 G(q+z1+z2)^2 G(q+z2)/G(q-z2) * G(t/2+z1) G(q-t/2-z1-z2)/(G(2q-t/2-z1) G(q+t/2+z1+z2)).
   Straight contours Re z1 = c1 in (-t/2,0), Re z2 = c2 in (-q,0), c1+c2 > -q.  Trapezoid rule (exponentially convergent)."""
import numpy as np
from scipy.special import loggamma as lg, gamma
import mpmath as mp
import sys

def J_mb(d, t, c1=None, c2=None, h=0.08, Y=14.0):
    q = d / 4.0
    if c1 is None: c1 = -t / 4.0
    if c2 is None: c2 = -q / 3.0
    y = np.arange(-Y, Y + h / 2, h)
    Y1, Y2 = np.meshgrid(y, y, indexing='ij')
    z1 = c1 + 1j * Y1; z2 = c2 + 1j * Y2
    L = (2 * lg(-z1) + 2 * lg(-z2) + 2 * lg(q + z1 + z2) + lg(q + z2) - lg(q - z2)
         + lg(t / 2 + z1) + lg(q - t / 2 - z1 - z2) - lg(2 * q - t / 2 - z1) - lg(q + t / 2 + z1 + z2))
    val = np.exp(L).sum() * h * h / (4 * np.pi ** 2)
    N = gamma(2 * q) ** 2 / gamma(q) ** 4
    return N * val

def J_d2(tau):   # note gc:K2master
    F = lambda x: mp.hyp3f2(0.5, 0.5, x, 1, 1, 1)
    return float(mp.pi ** 2 * (F(tau) ** 2 + F(1 - tau) ** 2))

def J_d1(t):     # note eq:Jhat / t^2
    t = mp.mpf(t)
    f = [mp.hyp3f2(t, t, 0.5, 0.5 + t, 0.5 + t, 1), mp.hyp3f2(t, t, t, 0.5 + t, 0.5 + t, 1),
         mp.hyp3f2(0.5, 0.5, t, 1, 0.5 + t, 1), mp.hyp3f2(0.5, 0.5, t, 1, 1, 1),
         mp.hyp3f2(0.5, 0.5, 0.5, 1, 1.5 - t, 1), mp.hyp3f2(0.5, 0.5, 1 - t, 1, 1.5 - t, 1)]
    G = mp.gamma
    Jh = 2 * mp.pi * (G(1 + t) ** 2 / G(0.5 + t) ** 2 * (f[0] + f[1]) + t * mp.sqrt(mp.pi) * G(1 + t) / G(0.5 + t) * f[2]
                      + t * G(1 + t) * G(1 - t) * f[3] + t ** 2 * mp.sqrt(mp.pi) * G(1 - t) / G(1.5 - t) * (f[4] + f[5]))
    return float(Jh / t ** 2)

if __name__ == '__main__':
    for tau in (0.3, 0.1, 0.23):
        print('d=2 tau=%g  MB=%.15g  exact=%.15g' % (tau, J_mb(2.0, 2 * tau).real, J_d2(tau)))
    for t in (0.3, 0.1):
        print('d=1 t=%g  MB=%.15g  exact=%.15g' % (t, J_mb(1.0, t).real, J_d1(t)))
