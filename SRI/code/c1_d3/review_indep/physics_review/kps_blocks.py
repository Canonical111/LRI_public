"""Independent d=3 scalar-4pt conformal blocks via the Zamolodchikov-like recursion of
Kos, Poland, Simmons-Duffin (arXiv:1406.4858, eqs. for h-tilde and c_1,c_2,c_3), d=3 (nu=1/2).
KPS normalization: g_KPS = r^Delta h, h -> (l!/(2nu)_l) (-1)^l C^nu_l(eta) = (-1)^l P_l(eta) as r->0,
(r, eta) radial rho-coordinates.  Polynomials in eta are stored as values on Gauss-Legendre nodes."""
import numpy as np
from functools import lru_cache
from scipy.special import poch, factorial, eval_legendre, gegenbauer, binom
from numpy.polynomial import legendre as L

NU = 0.5
M = 128                       # eta nodes (degree up to ~M-1 represented exactly)
XN, WN = L.leggauss(M)

def _pch(a, n):
    return float(poch(a, n))

def c1(k, l, d12, d34):
    return -(4**k*k*(-1)**k/factorial(k)**2)*_pch(l+2*NU, k)*_pch(0.5*(1-k+d12), k)*_pch(0.5*(1-k+d34), k)/_pch(l+NU, k)

def c2(k, l, d12, d34):
    return (-(4**(2*k)*k*(-1)**k/factorial(k)**2)*_pch(NU-k, 2*k)/(_pch(l+NU-k, 2*k)*_pch(l+NU+1-k, 2*k))
            * _pch(0.5*(1-k+l-d12+NU), k)*_pch(0.5*(1-k+l+d12+NU), k)
            * _pch(0.5*(1-k+l-d34+NU), k)*_pch(0.5*(1-k+l+d34+NU), k))

def c3(k, l, d12, d34):
    return -(4**k*k*(-1)**k/factorial(k)**2)*_pch(l+1-k, k)*_pch(0.5*(1-k+d12), k)*_pch(0.5*(1-k+d34), k)/_pch(l+NU+1-k, k)

def geg_series(lam, x, N):
    # coefficients of (1-2 x t + t^2)^{-lam} = sum_n C_n^{(lam)}(x) t^n, valid for any lam
    C = np.zeros((N+1, len(x)))
    C[0] = 1.0
    if N >= 1: C[1] = 2*lam*x
    for n in range(2, N+1):
        C[n] = (2*x*(n+lam-1)*C[n-1] - (n+2*lam-2)*C[n-2])/n
    return C

class KPS:
    def __init__(self, d12, d34, N):
        self.d12 = d12; self.d34 = d34; self.N = N
        self.memo = {}; self._PL = {}; self._poles = {}
        al = 0.5*(1+d12-d34); be = 0.5*(1-d12+d34)
        # series of 1/((1-r^2)^{1/2}(1+r^2+2r eta)^al (1+r^2-2r eta)^be) in r: coefficient arrays on nodes
        A = geg_series(al, -XN, N)
        B = geg_series(be, XN, N)
        C = np.zeros(N+1)
        for k in range(0, N//2+1):
            C[2*k] = binom(-0.5, k)*(-1)**k
        AB = np.zeros((N+1, M))
        for n in range(N+1):
            AB[n] = sum(A[i]*B[n-i] for i in range(n+1))
        self.base = np.zeros((N+1, M))
        for n in range(N+1):
            self.base[n] = sum(C[k]*AB[n-k] for k in range(n+1))
        # guard for al==0 or be==0 (C^(0) is degenerate): not needed for our parameters

    def htilde_n(self, l, n):
        return (-1)**l*self.PL(l)*self.base[n]

    def PL(self, l):
        if l not in self._PL: self._PL[l] = eval_legendre(l, XN)
        return self._PL[l]

    def poles(self, l):
        if l in self._poles: return self._poles[l]
        out = []
        for k in range(1, self.N+1):
            out.append((k, 1-l-k, l+k, c1(k, l, self.d12, self.d34)))
        for k in range(1, self.N//2+1):
            out.append((2*k, 1+NU-k, l, c2(k, l, self.d12, self.d34)))
        for k in range(1, l+1):
            if k <= self.N:
                out.append((k, 1+l+2*NU-k, l-k, c3(k, l, self.d12, self.d34)))
        self._poles[l] = out
        return out

    def Hm(self, Dp, l, m):
        """order-m coefficient (vector on eta nodes) of h_{Dp,l}; Dp is a fixed (pole-shifted) dimension"""
        key = (round(Dp, 12), l, m)
        v = self.memo.get(key)
        if v is not None: return v
        v = self.htilde_n(l, m).copy()
        for ni, Di, li, ci in self.poles(l):
            if ni > m or ci == 0.0: continue
            v += ci/(Dp-Di)*self.Hm(Di+ni, li, m-ni)
        self.memo[key] = v
        return v

    def h(self, Delta, l, nmax):
        return np.array([self.Hm(Delta, l, m) for m in range(nmax+1)])

    def legcoefs(self, Delta, l):
        H = self.h(Delta, l, self.N)
        # project onto Legendre P_j, j<=l+N
        J = l+self.N
        P = np.array([eval_legendre(j, XN) for j in range(J+1)])
        return np.array([[(2*j+1)/2*np.sum(WN*Hn*P[j]) for j in range(J+1)] for Hn in H])

    def block_code_norm(self, Delta, l):
        """returns callable g(z) normalized as (-1)^l 4^Delta g_KPS -> r^Delta P_l(eta) at small z"""
        cf = self.legcoefs(Delta, l)
        sgn = (-1)**l
        def g(z):
            z = np.asarray(z, dtype=complex)
            rho = z/(1+np.sqrt(1-z))**2
            r = np.abs(rho); xi = np.real(rho)/r
            val = np.zeros_like(r)
            for n in range(cf.shape[0]-1, -1, -1):
                val = val*r + L.legval(xi, cf[n], tensor=False)
            return sgn*(4*r)**Delta*val
        return g
