"""Line and bundle series of the 1D LRI with two-ended eps-Taylor jets (PLAN.md sec. 3.2).

u_m(eps)^2 = ((1-eps)/2)_m / m!  (m >= 0, u_0 = 1).  log u_m(eps) = log u_m + sum_k phi_k(m) eps^k with
    phi_k(m) = -H_k(m) / (2k),   H_k(m) = sum_{t<m} (2t+1)^{-k}
(1D: x = (1-eps)/2 and a single factor; the 2D code has an extra 2^{-k}).  e_k(m) = [eps^k] exp(sum phi_j eps^j).
A chi line (m >= 1 only: the zero mode is NOT a line) joining a vertex at Taylor order alpha (left end) and one at
order beta (right end) has the jet  line(alpha, beta)[m] = u_m^2 e_alpha(m) e_beta(m);  a bundle of n lines has
U(n, alpha, beta) = [eps_i^alpha eps_j^beta] (sum_{m>=1} u_m(eps_i) u_m(eps_j) y^m)^n, all coefficients being Taylor
coefficients (not derivatives).  U(n, 0, 0) = S_n = (V_1 - 1)^n of C4P (positive)."""
import numpy as np


class Series5:
    def __init__(self, N, dmax=3, nmax=8):
        self.N = N
        self.dmax = dmax
        self.nmax = nmax
        u2 = np.empty(N + 1)
        u2[0] = 1.0
        for j in range(1, N + 1):
            u2[j] = u2[j - 1] * (j - 0.5) / j
        self.u2 = u2
        m = np.arange(N + 1)
        odd = 2.0 * m + 1.0                     # (2t+1) for t = 0..N
        phi = {}
        for k in range(1, dmax + 1):
            H = np.concatenate([[0.0], np.cumsum(odd[:N] ** (-k))])      # H_k(m) = sum_{t<m} (2t+1)^{-k}
            phi[k] = -H / (2.0 * k)
        self.phi = phi
        e = {0: np.ones(N + 1)}
        if dmax >= 1:
            e[1] = phi[1].copy()
        if dmax >= 2:
            e[2] = phi[2] + phi[1] ** 2 / 2.0
        if dmax >= 3:
            e[3] = phi[3] + phi[1] * phi[2] + phi[1] ** 3 / 6.0
        if dmax >= 4:
            raise ValueError("dmax <= 3 implemented (order 5 needs at most 3)")
        self.e = e
        self._line = {}
        self._U = {}

    def line(self, al, be):
        key = (al, be)
        if key not in self._line:
            v = self.u2 * self.e[al] * self.e[be]
            v[0] = 0.0                            # chi lines only
            self._line[key] = v
        return self._line[key]

    def U(self, n, al=0, be=0):
        """[eps_i^al eps_j^be] of the bundle series of n chi lines (length N+1)."""
        key = (n, al, be)
        if key in self._U:
            return self._U[key]
        N = self.N
        if n == 0:
            out = np.zeros(N + 1)
            if al == 0 and be == 0:
                out[0] = 1.0
        else:
            out = np.zeros(N + 1)
            for a1 in range(al + 1):
                for b1 in range(be + 1):
                    prev = self.U(n - 1, al - a1, be - b1)
                    if not prev.any():
                        continue
                    out += np.convolve(prev, self.line(a1, b1))[: N + 1]
        self._U[key] = out
        return out
