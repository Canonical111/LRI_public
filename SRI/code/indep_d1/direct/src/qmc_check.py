#!/usr/bin/env python3
"""Randomized-QMC cross-check of the direct finite-cutoff moments.

Independent of direct_moments.c in three respects:
  * separate implementation (numpy) of the kernel, insertions and source term;
  * a different parametrization of the domain: every gap is sampled
    log-uniformly and independently, r_k = eps*(Rmax/eps)**w_k, w in [0,1]^m,
    and the simplex constraint sum r <= 1 is imposed by the factor
    Lambda_+ = max(1-R, 0) (translation integral), so the integrand is continuous
    with a kink on R = 1;
  * the source term uses the two-sided endpoint factor of the note,
    sum_i q_i [f(X_i) +- f(1-X_i)] (no reflection shortcut), with the X_1
    translation integral done analytically on both pieces.

Integrator: Owen-scrambled Sobol points (scipy.stats.qmc.Sobol, scramble=True);
R independent scramblings give the mean and the empirical standard error.

Output: one JSON line with mean/stderr of [z^a delta^b] coefficients.
"""
import argparse
import json
import math
import sys
import time

import numpy as np
from scipy.stats import qmc


def ser_mul(x, y, ord_):
    out = {}
    for (a1, b1), xv in x.items():
        for (a2, b2), yv in y.items():
            a, b = a1 + a2, b1 + b2
            if a + b <= ord_:
                out[(a, b)] = out.get((a, b), 0.0) + xv * yv
    return out


def ser_exp(X, ord_, P):
    acc = {(0, 0): np.ones(P)}
    term = {(0, 0): np.ones(P)}
    for k in range(1, ord_ + 1):
        term = ser_mul(term, X, ord_)
        term = {key: v / k for key, v in term.items()}
        for key, v in term.items():
            acc[key] = acc.get(key, 0.0) + v
    return acc


def antideriv_log_pow(j, y):
    """int_0^y log^j u du, vectorized, y>=0 (0 at y=0)."""
    out = np.zeros_like(y)
    pos = y > 0
    yy = y[pos]
    L = np.log(yy)
    s = np.zeros_like(yy)
    fac = 1.0
    for i in range(j, -1, -1):
        s += ((-1) ** (j - i)) * fac * L ** i
        fac *= i
    out[pos] = yy * s
    return out


def gaps_box(w, eps):
    """independent log-uniform gaps on [eps, Rmax]; simplex imposed by Lambda_+."""
    P, m = w.shape
    Rmax = 1.0 - (m - 1) * eps
    a = math.log(Rmax / eps)
    r = eps * np.exp(a * w)
    jac = np.prod(r, axis=1) * a ** m
    return r, jac


def gaps_seq(w, eps):
    """sequential one-sided log map, r_k = eps*(B_k/eps)**w_k with the remaining budget
    B_k = 1 - sum_{j<k} r_j - (m-k) eps (no rejection; squeeze peaks not smoothed)."""
    P, m = w.shape
    r = np.empty_like(w)
    jac = np.ones(P)
    used = np.zeros(P)
    for k in range(m):
        B = 1.0 - used - (m - 1 - k) * eps
        a = np.log(B / eps)
        r[:, k] = eps * np.exp(a * w[:, k])
        jac *= r[:, k] * a
        used += r[:, k]
    return r, jac


def integrand(w, n, kind, E, eps, ord_, gmap='box'):
    P, m = w.shape
    r, jac = (gaps_box if gmap == 'box' else gaps_seq)(w, eps)
    R = r.sum(axis=1)
    Lam = 1.0 - R
    inside = Lam > 0
    # positions relative to X_1
    c = np.zeros((P, n))
    c[:, 1:] = np.cumsum(r, axis=1)
    q = np.array([1.0 if (i % 2 == 0) else -1.0 for i in range(n)])  # q_1=+1
    W = np.ones(P)
    S = [None] + [np.zeros(P) for _ in range(ord_ + 1)]
    for i in range(n):
        for j in range(i + 1, n):
            d = c[:, j] - c[:, i]
            sg = q[i] * q[j]
            W *= d ** (2 * sg)
            L = np.log(d)
            Lp = L.copy()
            for k in range(1, ord_ + 2):
                S[k] += sg * Lp
                Lp = Lp * L
    # log W(v,delta)/W_0 = 2 z S1 + 2(1+z) sum_k delta^k S_{k+1}/(k+1)!
    X = {(1, 0): 2.0 * S[1]}
    for k in range(1, ord_ + 1):
        coef = 2.0 * S[k + 1] / math.factorial(k + 1)
        X[(0, k)] = coef
        if 1 + k <= ord_:
            X[(1, k)] = coef
    EX = ser_exp(X, ord_, P)
    base = W * jac
    if kind == 'Q':
        D = r[:, 0::2].sum(axis=1)               # odd-index gaps r_1, r_3, ...
        base = base * D
    LamP = np.where(inside, Lam, 0.0)
    if not E:
        T = {(0, 0): LamP}
    else:
        # sum_i q_i [f_delta(X_i) +- f_delta(1-X_i)], X_i = X_1 + c_i, X_1 in [0, Lam]
        # int_0^Lam f_delta(x+c) dx and int_0^Lam f_delta(1-x-c) dx = int_{d}^{d+Lam} f(y) dy,
        # with d = 1-Lam-c_i = R - c_i; f_delta = sum_k delta^k log^{k+1}/(k+1)!
        sgn_ref = 1.0 if (n % 2 == 1) else -1.0  # U^odd: +, U^even: -
        T = {}
        for k in range(0, ord_ + 1):
            tot = np.zeros(P)
            for i in range(n):
                ci = c[:, i]
                left = antideriv_log_pow(k + 1, LamP + ci) - antideriv_log_pow(k + 1, ci)
                di = R - ci
                right = antideriv_log_pow(k + 1, di + LamP) - antideriv_log_pow(k + 1, di)
                tot += q[i] * (left + sgn_ref * right)
            T[(0, k)] = tot / math.factorial(k + 1)
    out = {}
    for (a1, b1), ev in EX.items():
        for (a2, b2), tv in T.items():
            aa, bb = a1 + a2, b1 + b2
            if aa + bb <= ord_:
                out[(aa, bb)] = out.get((aa, bb), 0.0) + ev * tv
    return {k: np.where(inside, base * v, 0.0) for k, v in out.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-n', type=int, required=True)
    ap.add_argument('-k', dest='kind', required=True)
    ap.add_argument('-E', action='store_true')
    ap.add_argument('-e', dest='eps', type=float, required=True)
    ap.add_argument('-o', dest='ord', type=int, default=0)
    ap.add_argument('--log2', type=int, default=16, help='points per replicate = 2^log2')
    ap.add_argument('--reps', type=int, default=8)
    ap.add_argument('--chunk', type=int, default=17)
    ap.add_argument('--seed', type=int, default=20261002)
    ap.add_argument('--map', default='box', choices=['box', 'seq'])
    a = ap.parse_args()
    n, m = a.n, a.n - 1
    t0 = time.time()
    ss = np.random.SeedSequence(a.seed)
    child = ss.spawn(a.reps)
    ests = []
    for rep in range(a.reps):
        eng = qmc.Sobol(d=m, scramble=True, bits=52, seed=np.random.default_rng(child[rep]))  # bits=52: default 30-bit grid biases means at ~1e-9
        tot = None
        npts = 2 ** a.log2
        chunk = 2 ** min(a.chunk, a.log2)
        done = 0
        while done < npts:
            w = eng.random(chunk)
            vals = integrand(w, n, a.kind, a.E, a.eps, a.ord, a.map)
            s = {k: float(np.sum(v)) for k, v in vals.items()}
            tot = s if tot is None else {k: tot[k] + s[k] for k in tot}
            done += chunk
        ests.append({k: v / npts for k, v in tot.items()})
    keys = sorted(ests[0].keys())
    res = {}
    for k in keys:
        arr = np.array([e[k] for e in ests])
        res['%d,%d' % k] = [float(arr.mean()), float(arr.std(ddof=1) / math.sqrt(len(arr)))]
    out = dict(n=n, kind=a.kind, E=int(a.E), eps=a.eps, ord=a.ord, method='scrambled-Sobol RQMC, %s log-gap map' % a.map,
               points_per_rep=2 ** a.log2, reps=a.reps, seed=a.seed, seconds=round(time.time() - t0, 2), coef=res)
    print(json.dumps(out))


if __name__ == '__main__':
    main()
