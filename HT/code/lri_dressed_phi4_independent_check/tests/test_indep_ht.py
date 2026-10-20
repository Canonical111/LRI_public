#!/usr/bin/env python3
"""Unit tests for indep_ht.py (pure logic / tiny sizes; run with python3 test_indep_ht.py)."""
import itertools
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import indep_ht as ih  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + ("  " + detail if detail else ""))


# ---------------------------------------------------------------------------
def test_u_coeffs():
    # u_n^2 are the Taylor coefficients of (1-z)^(-2 delta)
    for d in (0.01, 0.1, 0.25):
        u2 = ih.u2_coeffs(d, 30)
        z = 0.3
        s = np.sum(u2 * z ** np.arange(31))
        check("u_n^2 = taylor (1-z)^(-2d), d=%g" % d, abs(s - (1 - z) ** (-2 * d)) < 1e-12, "%.2e" % abs(s - (1 - z) ** (-2 * d)))
        # GFF two-point check: <phi(x) phi(y)> = sum u_n^2 (x/y)^n y^{-2d} -> |x-y|^{-2d}
        x, y = 0.2, 1.0
        val = np.sum(u2 * (x / y) ** np.arange(31))
        check("GFF 2pt from modes, d=%g" % d, abs(val - (y - x) ** (-2 * d)) < 1e-12)


def test_partitions():
    p = [1, 1, 2, 3, 5, 7, 11, 15, 22, 30, 42, 56, 77]
    st = ih.partitions_upto(12)
    cnt = np.bincount([sum((n + 1) * k for n, k in enumerate(s)) for s in st])
    check("partition counts p(n), n<=12", list(cnt) == p)


def test_projection_claim():
    d = 0.17
    for cut in (4, 6, 8):
        small = ih.FullBath(d, cut)
        big = ih.FullBath(d, cut + 4)
        idx_big = {s: i for i, s in enumerate(big.states)}
        sel = np.array([idx_big[s + (0,) * 4] for s in small.states])
        err = 0.0
        for k in range(1, 5):
            Wb = big.W[k][sel][:, sel].toarray()
            Ws = small.W[k].toarray()
            err = max(err, np.max(np.abs(Wb - Ws)))
        check("normal-ordered :X^k: on truncated space == projection of exact (cut=%d)" % cut, err < 1e-13, "max diff %.1e" % err)
        # counterexample: anti-normal-ordered B B^+ is NOT truncation-safe
        Bs = small.B
        Bb = big.B
        AN_s = (Bs @ Bs.T).toarray()
        AN_b = (Bb @ Bb.T)[sel][:, sel].toarray()
        check("anti-normal-ordered B B^+ differs on truncated space (cut=%d)" % cut, np.max(np.abs(AN_s - AN_b)) > 1e-3)
        # B strictly lowers the level, B^+ strictly raises it: in (B^+)^m B^(k-m)
        # every intermediate level is <= max(level_in, level_out)
        Bc = big.B.tocoo()
        check("B strictly lowers the bath level (cut=%d)" % cut, np.all(big.lev[Bc.row] < big.lev[Bc.col]))


def test_reflection_average():
    d = 0.13
    cut = 6
    fp = ih.FullBath(d, cut, +1)
    fm = ih.FullBath(d, cut, -1)
    lev = fp.lev
    R = np.diag((-1.0) ** lev)
    ev = np.where(lev % 2 == 0)[0]
    od = np.where(lev % 2 == 1)[0]
    for k in range(1, 5):
        Vp, Vm = fp.W[k].toarray(), fm.W[k].toarray()
        avg = 0.5 * (Vp + Vm)
        c1 = np.max(np.abs(R @ Vp @ R - Vm))
        c2 = np.max(np.abs(avg[np.ix_(ev, ev)] - Vp[np.ix_(ev, ev)]))
        c3 = np.max(np.abs(avg[np.ix_(ev, od)])) if len(od) else 0.0
        check("reflection: R W_k(+1) R = W_k(-1), k=%d" % k, c1 < 1e-14)
        check("sphere average == W_k(+1) on even sector, k=%d" % k, c2 < 1e-14)
        check("sphere average has no even-odd block, k=%d" % k, c3 < 1e-14)


def test_zero_mode_normal_ordering():
    nmax = 60
    a = np.diag(np.sqrt(np.arange(1, nmax + 1)), 1)
    ad = a.T
    q = a + ad
    ok = True
    for k, He in ((2, lambda q: q @ q - np.eye(nmax + 1)),
                  (3, lambda q: q @ q @ q - 3 * q),
                  (4, lambda q: q @ q @ q @ q - 6 * q @ q + 3 * np.eye(nmax + 1))):
        no = sum(math.comb(k, m) * np.linalg.matrix_power(ad, m) @ np.linalg.matrix_power(a, k - m) for m in range(k + 1))
        diff = np.max(np.abs((He(q) - no)[: nmax - 4, : nmax - 4]))
        ok = ok and diff < 1e-9
    check(":q^k: = He_k(q) = sum C(k,m) a+^m a^(k-m)", ok)
    # delta a+a = delta p^2/4 + delta q^2/4 - delta/2
    p = (a - ad) / 1j
    lhs = (0.3 * (p @ p / 4 + q @ q / 4) - 0.3 / 2 * np.eye(nmax + 1)).real
    rhs = 0.3 * ad @ a
    check("delta a+a = delta(p^2+q^2)/4 - delta/2", np.max(np.abs((lhs - rhs)[:-2, :-2])) < 1e-10)


def free_spectrum(delta, cut, f, nlev):
    b = ih.Bath(delta, cut)
    vals = []
    for Eb, npart in itertools.chain(zip(b.EbE, b.npE), zip(b.EbO, b.npO)):
        for k in range(0, 40):
            if (k + npart) % 2 == f:
                vals.append(k * delta + Eb)
    return np.sort(vals)[:nlev]


def test_free_limit():
    for d in (0.25, 0.1):
        for cut in (2, 4):
            h = 0.25 if d == 0.25 else 0.2
            prob = ih.Problem(d, cut, h, int(14 / h), "raw")
            ev = prob.evaluate(0.0, 0.0, k=8)
            for f, name in ((0, "even"), (1, "odd")):
                ref = free_spectrum(d, cut, f, 8)
                err = np.max(np.abs(np.array(ev[name]) - ref))
                check("free limit d=%g N=%d %s (8 levels)" % (d, cut, name), err < 1e-10, "max err %.1e" % err)
    # with the window at g=r=0: Ev(L)=0, D=0, spectrum unchanged
    prob = ih.Problem(0.2, 4, 0.25, 56, "consistent")
    ev = prob.evaluate(0.0, 0.0, k=6)
    ref = free_spectrum(0.2, 4, 0, 6)
    check("free limit, consistent window: Ev(L)=0", np.max(np.abs(np.array(ev["Ev"])[::2])) < 1e-10)
    check("free limit, consistent window spectrum", np.max(np.abs(np.array(ev["even"]) - ref)) < 1e-10)


def test_hermiticity():
    rng = np.random.default_rng(1)
    for f in (0, 1):
        prob = ih.Problem(0.12, 4, 0.3, 20, "raw")
        sec = prob.sector(f, 4)
        D = np.zeros(5)
        D[2], D[4] = rng.normal(), rng.normal()
        P = sec.prepare(ih.coefs_H(0.12, 0.7, 2.3), D)
        H = sec.dense(P)
        err = np.max(np.abs(H - H.T)) / np.max(np.abs(H))
        check("Hermiticity f=%d (rel)" % f, err < 1e-14, "%.1e" % err)
        for co in (ih.COEF_DR, ih.COEF_DG):
            Hd = sec.dense(sec.prepare(co))
            check("Hermiticity of dH f=%d" % f, np.max(np.abs(Hd - Hd.T)) < 1e-12)
        # linearity in (r,g): H(r,g) = H(0,0) + r dH/dr + g dH/dg
        H0 = sec.dense(sec.prepare(ih.coefs_H(0.12, 0.0, 0.0), D))
        Hr = sec.dense(sec.prepare(ih.COEF_DR))
        Hg = sec.dense(sec.prepare(ih.COEF_DG))
        check("H linear in r,g f=%d" % f, np.max(np.abs(H - H0 - 0.7 * Hr - 2.3 * Hg)) < 1e-11)


def number_basis_levels(delta, r, g, cut, f, n0max, nlev):
    """Independent check of the zero-mode treatment: zero mode in the
    oscillator number basis (truncated at n0max), bath as in Bath, full dense
    Kronecker construction with Z2 projection."""
    b = ih.Bath(delta, cut)
    nb = len(b.EbE) + len(b.EbO)
    Eb = np.concatenate([b.EbE, b.EbO])
    npb = np.concatenate([b.npE, b.npO])
    nE = len(b.EbE)
    W = {}
    W[2] = np.zeros((nb, nb)); W[2][:nE, :nE] = b.W2EE; W[2][nE:, nE:] = b.W2OO
    W[4] = np.zeros((nb, nb)); W[4][:nE, :nE] = b.W4EE; W[4][nE:, nE:] = b.W4OO
    W[1] = np.zeros((nb, nb)); W[1][:nE, nE:] = b.W1EO; W[1][nE:, :nE] = b.W1EO.T
    W[3] = np.zeros((nb, nb)); W[3][:nE, nE:] = b.W3EO; W[3][nE:, :nE] = b.W3EO.T
    big = n0max + 8
    a = np.diag(np.sqrt(np.arange(1, big + 1)), 1)
    q = a + a.T
    I = np.eye(big + 1)
    q2, q3, q4 = q @ q, q @ q @ q, q @ q @ q @ q
    Hz = delta * a.T @ a + r * (q2 - I) + g / 12 * (q4 - 6 * q2 + 3 * I)
    L1 = (2 * r - g) * q + g / 3 * (q3 - 0 * q)  # (2r)q + (g/3)(q^3-3q) = (2r-g) q + g/3 q^3
    L2 = (r - g / 2) * I + g / 2 * q2
    L3 = g / 3 * q
    L4 = g / 12 * I
    sl = slice(0, n0max + 1)
    Hz, L1, L2, L3, L4 = Hz[sl, sl], L1[sl, sl], L2[sl, sl], L3[sl, sl], L4[sl, sl]
    n0 = n0max + 1
    H = np.kron(np.diag(Eb), np.eye(n0)) + np.kron(np.eye(nb), Hz)
    H += np.kron(W[1], L1) + np.kron(W[2], L2) + np.kron(W[3], L3) + np.kron(W[4], L4)
    par = np.array([(npb[i] + k) % 2 for i in range(nb) for k in range(n0)])
    sel = np.where(par == f)[0]
    w = np.linalg.eigvalsh(H[np.ix_(sel, sel)])
    return w[:nlev]


def test_dvr_vs_number_basis():
    d, r, g = 0.15, 0.05, 0.6
    cut = 4
    prob = ih.Problem(d, cut, 0.18, 70, "raw")
    ev = prob.evaluate(r, g, k=6)
    for f, name in ((0, "even"), (1, "odd")):
        ref = number_basis_levels(d, r, g, cut, f, 120, 6)
        err = np.max(np.abs(np.array(ev[name]) - ref))
        check("DVR vs oscillator number basis, N=4 %s" % name, err < 1e-11, "max err %.1e" % err)


def test_dvr_convergence_1d():
    # anharmonic oscillator  -d^2/dq^2 + q^4 (delta=1, A=0, g=12) -> E0 = 1.0603620904841829...
    V = lambda q: q ** 4
    for h in (0.2, 0.12, 0.08):
        w = ih.dvr1d_levels(1.0, V, h, int(6 / h), 3)
        print("   quartic h=%.3f E0=%.15f E1=%.15f" % (h, w[0], w[1]))
    w = ih.dvr1d_levels(1.0, V, 0.08, 75, 3)
    check("DVR quartic oscillator E0 (ref 1.0603620904841829)", abs(w[0] - 1.0603620904841829) < 1e-12, "%.2e" % abs(w[0] - 1.0603620904841829))
    check("DVR quartic oscillator E1 (ref 3.7996730298013941)", abs(w[1] - 3.7996730298013941) < 1e-12, "%.2e" % abs(w[1] - 3.7996730298013941))


def test_dvr_convergence_full():
    d, r, g = 0.15, 0.05, 0.6
    out = []
    for h, M in ((0.25, 40), (0.25 / 1.5, 60), (0.25, 60)):
        prob = ih.Problem(d, 4, h, M, "raw")
        ev = prob.evaluate(r, g)
        out.append(ih.delta_eps(ev))
    check("full-problem DVR convergence (fine)", abs(out[1] - out[0]) < 1e-11, "%.1e" % abs(out[1] - out[0]))
    check("full-problem DVR convergence (wide)", abs(out[2] - out[0]) < 1e-11, "%.1e" % abs(out[2] - out[0]))


def test_derivatives():
    d, r, g = 0.18, 0.04, 0.5
    for presc in ("raw", "literal", "consistent"):
        prob = ih.Problem(d, 4, 0.25, 48, presc)
        ev = prob.evaluate(r, g)
        J = ih.jacobian(ev)
        dD = ih.d_delta_eps(ev)
        hstep = 1e-6
        Jfd = np.zeros((2, 2))
        dDfd = np.zeros(2)
        for i in range(2):
            th = np.array([r, g])
            th[i] += hstep
            ep = prob.evaluate(*th)
            th[i] -= 2 * hstep
            em = prob.evaluate(*th)
            Jfd[:, i] = (ih.residuals(d, ep) - ih.residuals(d, em)) / (2 * hstep)
            dDfd[i] = (ih.delta_eps(ep) - ih.delta_eps(em)) / (2 * hstep)
        err = max(np.max(np.abs(J - Jfd)), np.max(np.abs(dD - dDfd)))
        check("Hellmann-Feynman Jacobian vs FD (%s)" % presc, err < 1e-6, "max diff %.1e" % err)
        if presc == "consistent":
            check("consistent: E_even0 == Ev(cut)", abs(ev["consistency"]) < 1e-12, "%.1e" % ev["consistency"])


def test_window_fixed_point():
    d, r, g = 0.18, 0.04, 0.5
    prob = ih.Problem(d, 6, 0.25, 48, "consistent")
    Ev, dEv, it = prob.window_table(r, g)
    ok = True
    for L in range(2, 7, 2):
        sec = prob.sector(0, L)
        D = np.zeros(7)
        for N in range(2, L + 1, 2):
            D[N] = Ev[L] - Ev[L - N]
        w = np.linalg.eigvalsh(sec.dense(sec.prepare(ih.coefs_H(d, r, g), D)))
        ok = ok and abs(w[0] - Ev[L]) < 1e-12
    check("consistent window: s = lambda_min(H(L)+D_L(s)) for each L", ok)
    prob2 = ih.Problem(d, 6, 0.25, 48, "literal")
    Ev2, _, _ = prob2.window_table(r, g)
    ok = True
    for L in range(0, 7, 2):
        sec = prob2.sector(0, L)
        w = np.linalg.eigvalsh(sec.dense(sec.prepare(ih.coefs_H(d, r, g))))
        ok = ok and abs(w[0] - Ev2[L]) < 1e-12
    check("literal window: Ev(L) = lambda_min(H(L))", ok)
    # H(L) is the N<=L block of H(cut)
    secc = prob.sector(0, 6)
    secL = prob.sector(0, 4)
    Hc = secc.dense(secc.prepare(ih.coefs_H(d, r, g)))
    HL = secL.dense(secL.prepare(ih.coefs_H(d, r, g)))
    # map indices
    selE = np.arange(secL.nE * secc.mE)
    selO = secc.sE + np.arange(secL.nO * secc.mO)
    sel = np.concatenate([selE, selO])
    check("H(L) = level<=L block of H(cut)", np.max(np.abs(Hc[np.ix_(sel, sel)] - HL)) < 1e-14)


def test_first_order():
    # weak coupling: first-order tuning g = eps/3, r = 0 at N=0 (zero mode alone)
    d = 0.2499
    eps = 1 - 4 * d
    prob = ih.Problem(d, 0, 0.25, 60, "raw")
    th, ev = ih.tune(prob, 0.0, eps / 3)
    De = ih.delta_eps(ev)
    check("N=0 weak coupling: g ~ eps/3", abs(th[1] / (eps / 3) - 1) < 10 * eps, "g/(eps/3)-1=%.2e" % (th[1] / (eps / 3) - 1))
    c2 = (De - 0.5 + eps / 6) / eps ** 2
    check("N=0: (De - 1/2 + eps/6)/eps^2 ~ 34/81", abs(c2 - 34 / 81) < 0.01, "C2(est)=%.6f vs %.6f" % (c2, 34 / 81))


def test_arpack_vs_dense():
    d, r, g = 0.18, 0.04, 0.5
    out = {}
    for dm in (10 ** 6, 50):
        ih.DENSE_MAX = dm
        prob = ih.Problem(d, 4, 0.25, 48, "consistent")
        ev = prob.evaluate(r, g)
        out[dm] = np.array(ev["even"] + ev["odd"] + ev["Ev"][::2])
    ih.DENSE_MAX = 1200
    err = np.max(np.abs(out[10 ** 6] - out[50]))
    check("ARPACK path == dense path (levels and window table)", err < 1e-11, "max diff %.1e" % err)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            print("--", name)
            fn()
    nf = sum(1 for r in RESULTS if not r[1])
    print("\n%d checks, %d failed" % (len(RESULTS), nf))
    sys.exit(1 if nf else 0)
