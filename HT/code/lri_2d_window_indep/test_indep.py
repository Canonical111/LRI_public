"""Self-tests of indep_ht2d (independent of the ht2d package)."""
import cmath
import math
from math import comb

import numpy as np

from indep_ht2d import Bath, ZeroMode, Sector, solve_spectrum, couplings


def fock_full(L):
    modes = [(a, n - a) for n in range(1, L + 1) for a in range(n + 1)]
    states = []

    def rec(i, N, occ):
        if i == len(modes):
            states.append(tuple(occ))
            return
        lev = sum(modes[i])
        k = 0
        while N + k * lev <= L:
            rec(i + 1, N + k * lev, occ + [k])
            k += 1
    rec(0, 0, [])
    return modes, states


def test_vertices_bruteforce(L=5, x=0.3, Js=(0, 1, 2)):
    """W_k vs explicit theta average of normal-ordered :phi_b^k: in the full N<=L Fock space."""
    modes, states = fock_full(L)
    idx = {s: i for i, s in enumerate(states)}
    n = len(states)
    u = [math.sqrt(np.prod([x + i for i in range(a)]) * np.prod([x + i for i in range(b)])
                   / (math.factorial(a) * math.factorial(b))) for a, b in modes]
    T = 4 * L + 3
    Wavg = {k: np.zeros((n, n), complex) for k in range(1, 5)}
    for t in range(T):
        th = 2 * math.pi * t / T
        Pp = np.zeros((n, n), complex)  # phi^+ (annihilation part)
        for j, s in enumerate(states):
            for m, (a, b) in enumerate(modes):
                if s[m]:
                    s2 = list(s); s2[m] -= 1
                    Pp[idx[tuple(s2)], j] += u[m] * math.sqrt(s[m]) * cmath.exp(-1j * (a - b) * th)
        Pm = Pp.conj().T
        for k in range(1, 5):
            op = sum(comb(k, p) * np.linalg.matrix_power(Pm, p) @ np.linalg.matrix_power(Pp, k - p)
                     for p in range(k + 1))
            Wavg[k] += op / T
    Jof = np.array([sum((a - b) * s[m] for m, (a, b) in enumerate(modes)) for s in states])
    worst = 0.0
    for J in Js:
        bath = Bath(L, x, J=J, reflect_even=False)
        # map bath external states to full-state indices
        sel = []
        for s in bath.ext:
            occ = [0] * len(modes)
            for m, k in s:
                occ[modes.index(bath.modes[m])] = k
            sel.append(idx[tuple(occ)])
        assert sorted(sel) == sorted(np.nonzero(Jof == J)[0].tolist())
        for k in range(1, 5):
            ref = Wavg[k][np.ix_(sel, sel)]
            assert np.abs(ref.imag).max() < 1e-12
            d = np.abs(bath.Wfull[k].toarray() - ref.real).max()
            worst = max(worst, d)
    print(f"vertex brute force (L={L}, J={Js}): max |diff| = {worst:.2e}")
    assert worst < 1e-12


def test_reflection():
    b = Bath(6, 0.27)
    for k in range(1, 5):
        W = b.W[k].toarray()
        assert np.abs(W - W.T).max() < 1e-13
    # reflection-odd complement must decouple: Q Q^T W = W Q Q^T on the J=0 space
    Q = b.Q.toarray()
    Pe = Q @ Q.T
    for k in range(1, 5):
        Wf = b.Wfull[k].toarray()
        assert np.abs(Pe @ Wf - Wf @ Pe).max() < 1e-13
    print("reflection projector commutes with W_k; W_k symmetric")


def test_two_point(x=0.37):
    q, th = 0.43, 0.9
    b = Bath(40, x, J=0, reflect_even=False) if False else None
    s = sum(math.prod([x + i for i in range(a)]) * math.prod([x + i for i in range(c)])
            / (math.factorial(a) * math.factorial(c)) * q ** (a + c) * cmath.exp(1j * (a - c) * th)
            for a in range(80) for c in range(80))
    ref = (1 - q * cmath.exp(1j * th)) ** (-x) * (1 - q * cmath.exp(-1j * th)) ** (-x)
    print(f"two-point weights: |sum - closed form| = {abs(s - ref):.1e}")
    assert abs(s - ref) < 1e-12


def test_free_limit(x=0.3, L=8):
    zm = ZeroMode(x, x / 4, 0.0, M=60, Ke=6, Ko=6, lam=1.0)
    # zero-mode energies x(n+1/2) - shifted => x n
    assert np.allclose(np.sort(zm.energies - zm.E0), x * np.sort(np.r_[np.arange(0, 12, 2), np.arange(1, 12, 2)]))
    bath = Bath(L, x)
    # g=0 and A=x/4: L_j = (x/4 - x/4)... L1=(x/2-x/2)q=0, L2=0, L3=0, L4=0
    for k in range(1, 5):
        assert np.abs(zm.Lop[k]).max() < 1e-14
    sec = Sector(zm, bath, L, 1)
    w, _ = sec.lowest(np.zeros(sec.nb), 4)
    print("free odd levels", w)
    assert abs(w[0] - x) < 1e-12


def test_dense_vs_lanczos(x=0.3, L=8):
    theta = (-0.2, -1.5)
    A, g, r = couplings(theta, x)
    zm = ZeroMode(x, A, g, M=200, Ke=24, Ko=24)
    bath = Bath(L, x)
    sec = Sector(zm, bath, L, 0)
    D = np.linspace(0, -0.5, sec.nb) * (sec.N > 0)
    w1, _ = sec.lowest(D, 4)
    sec.dim_save = sec.dim
    # force Lanczos
    import indep_ht2d as m
    old = Sector.lowest

    def lanczos(self, D, nev=1, v0=None, tol=1e-14):
        import scipy.sparse.linalg as sla
        mask = self.mask

        def mv(v):
            V = np.zeros((self.K, self.nb)); V[mask] = v
            return self.matvec_full(V, D)[mask]
        op = sla.LinearOperator((self.dim, self.dim), matvec=mv, dtype=float)
        w, U = sla.eigsh(op, k=nev, which="SA", tol=tol)
        return np.sort(w), U
    w2, _ = lanczos(sec, D, 4)
    print(f"dense vs Lanczos: {np.abs(w1 - w2).max():.1e}")
    assert np.abs(w1 - w2).max() < 1e-11


if __name__ == "__main__":
    test_two_point()
    test_vertices_bruteforce(L=5, Js=(0, 1, 2))
    test_reflection()
    test_free_limit()
    test_dense_vs_lanczos()
    print("ALL PASS")
