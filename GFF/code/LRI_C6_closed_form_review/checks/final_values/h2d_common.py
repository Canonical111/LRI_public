# Double-precision kernels (numpy/scipy) for the three bivariate H values, in log form.
import numpy as np
from scipy.special import loggamma as lg
import mpmath as mp
from params import setup

P = setup(30)
def c(x): return complex(x)
alphaW = float(P['alphaW']); beta7 = c(P['beta7']); betap = c(P['betap']); betam = c(P['betam'])
PI = np.pi

def logsin_pi(z):
    """log sin(pi z), any branch (only exp() of sums is used); overflow-safe."""
    z = np.asarray(z, dtype=complex)
    out = np.empty_like(z)
    up = z.imag >= 0
    zu = z[up]; E = np.exp(2j*PI*zu)
    out[up] = -1j*PI*zu + np.log1p(-E) + np.log(0.5j)
    zd = z[~up]; E = np.exp(-2j*PI*zd)
    out[~up] = 1j*PI*zd + np.log1p(-E) + np.log(-0.5j)
    return out

def logN_alpha(s, al):
    # Gamma(s)^2 Gamma(1/2-s)^3 / (Gamma(1-s)^2 Gamma(1/2+s) Gamma(s+al) Gamma(1-s-al))
    return 2*lg(s) + 3*lg(0.5 - s) - 2*lg(1 - s) - lg(0.5 + s) - lg(s + al) - lg(1 - s - al)

def logP_t(t):
    return lg(t) + lg(t + 0.5) + lg(0.5 - t) + lg(1 - t)

def logA7(s, b):
    bb = np.conj(b)
    return (3*lg(s) + 7*lg(0.5 - s) + lg(1.25 - s) - 3*lg(1 - s) - lg(-s) - lg(0.25 - s)
            - lg(s + b) - lg(1 - s - b) - lg(s + bb) - lg(1 - s - bb))

def logPsi(s, b):
    # Gamma(s)^3 Gamma(1/2-s)^3 / (Gamma(1/2+s) prod_b Gamma(s+b)Gamma(1-s-b)),  1/(G(z)G(1-z)) = sin(pi z)/pi
    bb = np.conj(b)
    return (3*lg(s) + 3*lg(0.5 - s) - lg(0.5 + s)
            + logsin_pi(s + b) + logsin_pi(s + bb) - 2*np.log(PI))

def cot2pi(t):
    return 1/np.tan(2*PI*t)
