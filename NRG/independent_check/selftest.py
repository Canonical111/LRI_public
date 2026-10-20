#!/usr/bin/env python3
"""
selftest.py -- fast checks (seconds) of indep_nrg.py.  Exit status 0 iff every check passes.

  (a) Lanczos chain reproduces the star (eigenvalues = xi_m, first components^2 |gamma|^2 = gamma_m^2),
      plus: finite-M norm, and chain convergence in M and in mp precision at a realistic N.
  (b) Untruncated NRG spectrum (unshifted, divided by Lambda^n) = exact diagonalization of the full
      chain Hamiltonian built from Kronecker products, sector by sector.
  (c) Parity structure of B_n: the kept states (composed back into the full Hilbert space) are
      parity eigenstates with the assigned labels, the true matrix elements of b_n between equal
      parities vanish, and B_n equals <kept| b_n |kept> computed in the full space.  Done with and
      without truncation.
  (d) Finite-difference derivative consistent between two h at the critical coupling of a small
      system (also exercises the critical search end to end).
  (e) Determinism: two identical flows are bitwise identical (needed for tiny-h differences).
  (f) Window audit on synthetic data with a known slope, and the SPEC 6 window geometry.
  (g) Bracket/bisection logic on analytic residual functions, including bracket expansion/failure.
"""

import math
import os
import sys
import time
from functools import reduce

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mpmath                       # noqa: E402
import numpy as np                  # noqa: E402

import indep_nrg as nrg             # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print("[%s] %s %s" % ("PASS" if ok else "FAIL", name, detail), flush=True)
    if not ok:
        FAILS.append(name)


# -------------------------------------------------------------------------------------------
# (a) Lanczos vs star
# -------------------------------------------------------------------------------------------
def test_a():
    # Full tridiagonalization (N = M) of small stars.  M = 30 at the production precision rule
    # is a case where the plain three-term recurrence fails completely, so this also guards
    # the reorthogonalization.
    cases = [(Ls, ss, 10, 60) for Ls, ss in (("3", "0.8"), ("2.5", "0.502"), ("2", "0.998"))]
    cases += [("3", "0.8", 30, nrg.default_dps(30, 3.0)), ("2", "0.6", 30, nrg.default_dps(30, 2.0))]
    for Ls, ss, M, dps in cases:
        tol = 10.0 ** (-(dps - M * math.log10(float(Ls)) - 15))
        with mpmath.workdps(dps):
            Lam, s = mpmath.mpf(Ls), mpmath.mpf(ss)
            xi, w = nrg.star_unit(Lam, s, M)
            a, b, norm2 = nrg.lanczos(xi, w, M)          # full tridiagonalization, M x M
            T = mpmath.zeros(M, M)
            for i in range(M):
                T[i, i] = a[i]
            for i in range(M - 1):
                T[i, i + 1] = T[i + 1, i] = b[i]
            E, Q = mpmath.eigsy(T)
            order = sorted(range(M), key=lambda k: E[k])
            # xi_m decreases with m, so ascending eigenvalue k <-> bin m = M-1-k
            err_e = max(abs(E[order[k]] - xi[M - 1 - k]) / xi[M - 1 - k] for k in range(M))
            # weights: Q[0,k]^2 |gamma|^2 = gamma_m^2  <=>  Q[0,k]^2 norm2 = w_m  (alpha cancels)
            err_w = max(abs(Q[0, order[k]] ** 2 * norm2 - w[M - 1 - k]) / w[M - 1 - k]
                        for k in range(M))
            norm_exact = (1 - Lam ** (-M * (s + 1))) / (s + 1)
            err_n = abs(norm2 - norm_exact) / norm_exact
        tag = "Lambda=%s s=%s M=%d dps=%d" % (Ls, ss, M, dps)
        check("(a) star<->chain eigenvalues  " + tag, err_e < tol,
              "max rel err %.2e (tol %.0e)" % (float(err_e), tol))
        check("(a) star<->chain weights      " + tag, err_w < tol,
              "max rel err %.2e (tol %.0e)" % (float(err_w), tol))
        check("(a) |gamma|^2 = 2a(1-L^{-M(s+1)})/(s+1)  " + tag, err_n < 10.0 ** (10 - dps),
              "rel err %.2e" % float(err_n))
    # convergence of the rescaled coefficients at a realistic length, in M and in precision
    for Ls, ss, N in (("3", "0.8", 40), ("2", "0.8", 40)):
        ch = nrg.wilson_chain(Ls, ss, N)
        conv = nrg.chain_convergence(ch)
        worst = max(conv.values())
        check("(a) chain converged in M and dps  Lambda=%s s=%s N=%d" % (Ls, ss, N), worst < 1e-15,
              "%s; eps_r[N-1]=%.6f t_r[N-1]=%.6f" % (conv, ch.eps_r[-1], ch.t_r[-1]))


# -------------------------------------------------------------------------------------------
# helpers: full-space operators for (b), (c)
# -------------------------------------------------------------------------------------------
def kron_all(mats):
    return reduce(np.kron, mats)


def full_op(single, where, nb, nsites):
    """Operator `single` on factor `where` (0 = spin, 1+j = chain site j) of spin (x) sites."""
    mats = [np.eye(2)] + [np.eye(nb)] * nsites
    mats[where] = single
    return kron_all(mats)


def full_hamiltonian(chain, alpha, nb, nsites, Delta=nrg.DELTA_DEFAULT):
    """Exact (boson-truncated) chain Hamiltonian, physical units, from the same rescaled chain."""
    Lam = chain.Lambda
    eps = [chain.eps_r[n] / Lam ** n for n in range(nsites)]
    hop = [chain.t_r[n + 1] / Lam ** (n + 1) for n in range(nsites - 1)]     # t_n
    sx = np.diag([1.0, -1.0])                       # sigma_x in its eigenbasis
    sz = nrg.SIGMA_Z_XBASIS
    b, num, _ = nrg.boson_ops(nb)
    H = -(Delta / 2) * full_op(sx, 0, nb, nsites)
    H += 0.5 * chain.lam_tot(alpha) * full_op(sz, 0, nb, nsites) @ full_op(b + b.T, 1, nb, nsites)
    for n in range(nsites):
        H += eps[n] * full_op(np.diag(num), 1 + n, nb, nsites)
    for n in range(nsites - 1):
        hopn = full_op(b.T, 1 + n, nb, nsites) @ full_op(b, 2 + n, nb, nsites)
        H += hop[n] * (hopn + hopn.T)
    return H


def full_parity(nb, nsites):
    _, _, p = nrg.boson_ops(nb)
    return kron_all([np.array([1, -1])] + [p.astype(float)] * nsites)


# -------------------------------------------------------------------------------------------
# (b) NRG (no truncation) vs exact diagonalization
# -------------------------------------------------------------------------------------------
def test_b():
    for Ls, ss, alpha, nb, N in (("3", "0.8", 0.3, 4, 3), ("2.5", "0.502", 0.07, 3, 4),
                                 ("2", "0.998", 0.0, 3, 4)):
        ch = nrg.wilson_chain(Ls, ss, N, M=40)
        fl = nrg.nrg_flow(ch, alpha, nb, K=10 ** 6, N=N, check_parity=True)
        n = N - 1
        re, ro = fl.last_raw
        phys_e = (re - fl.raw_min[n]) / ch.Lambda ** n + fl.offset[n]
        phys_o = (ro - fl.raw_min[n]) / ch.Lambda ** n + fl.offset[n]
        H = full_hamiltonian(ch, alpha, nb, N)
        P = full_parity(nb, N)
        ev = np.linalg.eigvalsh(H[np.ix_(P > 0, P > 0)])
        od = np.linalg.eigvalsh(H[np.ix_(P < 0, P < 0)])
        cross = np.max(np.abs(H[np.ix_(P > 0, P < 0)]))
        ok_dim = (ev.size == phys_e.size) and (od.size == phys_o.size)
        err = max(np.max(np.abs(np.sort(phys_e) - ev)), np.max(np.abs(np.sort(phys_o) - od))) \
            if ok_dim else np.inf
        gap_ed = (od[0] - ev[0]) * ch.Lambda ** n
        check("(b) NRG == ED  Lambda=%s s=%s alpha=%g nb=%d N=%d (dim %d)"
              % (Ls, ss, alpha, nb, N, H.shape[0]), ok_dim and err < 1e-12 and cross == 0,
              "max |dE| = %.2e, g_N-1 NRG %.12f vs ED %.12f" % (err, fl.g[-1], gap_ed))


# -------------------------------------------------------------------------------------------
# (c) B_n parity structure
# -------------------------------------------------------------------------------------------
def test_c():
    for Ls, ss, alpha, nb, N, K in (("3", "0.8", 0.3, 4, 3, 10 ** 6), ("3", "0.8", 0.2, 3, 5, 5),
                                    ("2.5", "0.6", 0.15, 4, 4, 7)):
        ch = nrg.wilson_chain(Ls, ss, N, M=40)
        fl = nrg.nrg_flow(ch, alpha, nb, K=K, N=N, keep_vectors=True, check_parity=True)
        Phi = None
        worst_B = worst_same = worst_par = worst_orth = 0.0
        stored_zero = True
        for n in range(N):
            U = fl.Ufull[n]
            Phi = U if n == 0 else np.kron(Phi, np.eye(nb)) @ U   # kept states in full space
            dim_prev = Phi.shape[0] // nb
            b, _, _ = nrg.boson_ops(nb)
            b_full = np.kron(np.eye(dim_prev), b)                 # b of site n (last factor)
            B_true = Phi.T @ b_full @ Phi
            par = fl.par[n].astype(float)
            same = np.equal.outer(par, par)
            worst_B = max(worst_B, np.max(np.abs(B_true - fl.B[n])))
            worst_same = max(worst_same, np.max(np.abs(B_true[same])))
            P = full_parity(nb, n + 1)
            worst_par = max(worst_par, np.max(np.abs(P[:, None] * Phi - Phi * par[None, :])))
            worst_orth = max(worst_orth, np.max(np.abs(Phi.T @ Phi - np.eye(Phi.shape[1]))))
            stored_zero &= bool(np.all(fl.B[n][same] == 0.0))
        ok = worst_B < 1e-12 and worst_same < 1e-12 and worst_par < 1e-12 and worst_orth < 1e-12 \
            and stored_zero
        check("(c) B_n parity structure  Lambda=%s s=%s nb=%d N=%d K=%s" % (Ls, ss, nb, N, K), ok,
              "|B-<b>|=%.1e  |<b>_same-parity|=%.1e  |P phi - p phi|=%.1e  orth=%.1e  zeros=%s"
              % (worst_B, worst_same, worst_par, worst_orth, stored_zero))


# -------------------------------------------------------------------------------------------
# (d) finite differences at the critical coupling of a small system; (e) determinism
# -------------------------------------------------------------------------------------------
def test_d_e():
    Ls, ss, nb, K, N = "3", "0.8", 4, 8, 16
    ch = nrg.wilson_chain(Ls, ss, N)
    free = nrg.nrg_flow(ch, 0.0, nb, K)
    target = 0.3 * free.g[-1]
    crit = nrg.find_alpha_c(lambda a: float(nrg.nrg_flow(ch, a, nb, K).g[-1] - target))
    ok = crit["status"] == "ok"
    check("(d) critical search converges (tiny system)", ok,
          "alpha_c=%.15g, it=%d, bracket width %.1e" % (
              crit["alpha_c"] or float("nan"), crit["iterations"],
              crit["bracket"][1] - crit["bracket"][0]))
    if not ok:
        return
    ac = crit["alpha_c"]
    cf = nrg.nrg_flow(ch, ac, nb, K)
    res = cf.g[-1] - target
    check("(d) terminal residual small", abs(res) < 1e-8, "f(alpha_c) = %.2e" % res)
    D = {}
    for h in (1e-6, 1e-7):
        ap, am = nrg.fd_alphas(ac, h)
        D[h] = nrg.fd_derivative(nrg.nrg_flow(ch, ap, nb, K).g, nrg.nrg_flow(ch, am, nb, K).g, ac, h)
    big = np.abs(D[1e-6]) > 1e-3 * np.max(np.abs(D[1e-6]))
    rel = np.abs(D[1e-6] - D[1e-7]) / np.maximum(np.abs(D[1e-6]), np.abs(D[1e-7]))
    check("(d) D_n(h=1e-6) == D_n(h=1e-7) to 1e-4 rel", bool(np.all(rel[big] < 1e-4)),
          "max rel diff %.2e over %d sites; D_N-1 = %.4g" % (np.max(rel[big]), big.sum(), D[1e-6][-1]))
    # relevant direction: |D_n| should grow along the flow at the critical point
    check("(d) |D_n| grows along the critical flow", abs(D[1e-6][-1]) > abs(D[1e-6][2]),
          "|D_2|=%.3g |D_N-1|=%.3g" % (abs(D[1e-6][2]), abs(D[1e-6][-1])))
    # (e) determinism
    f1 = nrg.nrg_flow(ch, ac, nb, K)
    f2 = nrg.nrg_flow(ch, ac, nb, K)
    check("(e) two identical flows are bitwise identical", bool(np.array_equal(f1.g, f2.g)))


# -------------------------------------------------------------------------------------------
# (f) window audit on synthetic data
# -------------------------------------------------------------------------------------------
def test_f():
    w, starts = nrg.window_geometry(65)
    check("(f) window geometry N=65: w=12, starts 8..36", w == 12 and list(starts) == list(range(8, 37)))
    w, starts = nrg.window_geometry(250)
    check("(f) window geometry N=250: w=32, starts 32..157", w == 32 and list(starts) == list(range(32, 158)))
    N, Lam, yt = 65, 3.0, 0.7
    n = np.arange(N)
    D = 3.0 * Lam ** (yt * n)
    g = np.ones(N)
    a = nrg.window_audit(D, g, Lam)
    s = a["summary"]
    ok = s["n_quality"] == s["n_windows"] == 29 and abs(s["delta_E_mid"] - 0.3) < 1e-12
    check("(f) synthetic exact power law -> Delta_E = 0.3 in all windows", ok,
          "n_quality=%d, mid=%.15f" % (s["n_quality"], s["delta_E_mid"]))
    g2 = g.copy()
    g2[20] = -1.0
    a2 = nrg.window_audit(D, g2, Lam)
    skipped = [r["start"] for r in a2["windows"] if r["skipped"]]
    check("(f) windows containing g_n <= 0 are skipped", skipped == list(range(9, 21)), str(skipped))
    g3 = g * (1 + 0.01 * (n == 30))                  # 1% bump -> variation > 0.005
    a3 = nrg.window_audit(D, g3, Lam)
    bad = [r["start"] for r in a3["windows"] if not r["quality"]]
    check("(f) variation criterion flags windows containing a 1% bump", bad == list(range(19, 31)), str(bad))


# -------------------------------------------------------------------------------------------
# (g) bracket / bisection logic
# -------------------------------------------------------------------------------------------
def test_g():
    for root in (0.3, 0.003, 5.0, 37.3):
        r = nrg.find_alpha_c(lambda a: root - a)
        ok = r["status"] == "ok" and abs(r["alpha_c"] - root) < 5e-14 * max(1, root)
        check("(g) bisection finds root %g" % root, ok,
              "alpha_c=%.17g it=%d" % (r["alpha_c"], r["iterations"]))
    r = nrg.find_alpha_c(lambda a: 1000.0 - a)
    check("(g) root beyond hi=100 -> bracket_failed", r["status"] == "bracket_failed")


if __name__ == "__main__":
    t0 = time.perf_counter()
    for t in (test_a, test_b, test_c, test_d_e, test_f, test_g):
        t()
    dt = time.perf_counter() - t0
    if FAILS:
        print("SELFTEST FAILED (%d): %s   [%.1fs]" % (len(FAILS), FAILS, dt), flush=True)
        sys.exit(1)
    print("SELFTEST PASSED  [%.1fs]" % dt, flush=True)
