#!/usr/bin/env python3
"""
lri_framework.py  --  reusable numerical map (pure Python + mpmath)

    raw ordered moments            A_{2m+1}, Z_{2m}, Q_{2m} and their v / delta / EE derivatives
      (Laurent-log coefficients [eps^p l^k], l = log eps, at v=1, delta=0, eta=0)
  -> normalized responses          C_n = (sum A g^odd)/(sum Z g^even),  K_n = (sum Q g^even)/(sum Z g^even)
      products formed BEFORE extracting [eps^0 l^0], [eps^0 l^1]          (note eq:normalization)
  -> auxiliary beta coefficients   b_n(z,delta), h_n(z,delta) from J0 beta = R1
      (derived in derive_rg.py; reproduces eq:subtraction + h8/b9)
  -> essential jets                F = z + sum_k b_{2k+1} u^k,  H = -delta - 4 sum_k h_{2k} u^k
  -> beta inputs                   a,p,A,E,V,alpha,beta,gamma,b,G,R,Phi,Psi,J,Omega,
                                   c,f,q,L,M,Q,k,N,P,K   (+ W,S,U,J9,L3,M21,M12,N2,Ndelta,Kv for C8)
  -> fixed point, T(delta), D(delta)  ->  C_1 ... C_7 (C_8)

Features
  * exact two-kink sector (Z2, Q2 and all their v/delta/EE derivatives) and A1 are built in;
  * STRICT MODE (default): every scalar in required_inputs() must be supplied, otherwise
    MissingInputError is raised; an absent scalar is NEVER treated as zero.  strict=False reports
    every output that depends on an absent scalar as MISSING (with the names it needs);
  * linear (first-order) error propagation with exact forward-mode gradients:
    independent sigmas, covariance blocks, or the sample covariance of QMC replicates;
  * per-replicate assembly (from_replicates): the full nonlinear map run once per QMC replicate,
    mean and replicate standard error reported next to the linear propagation;
  * adapters for the flat, spec-agent, engine (campaign results.json) and canonical
    'lri-framework-raw/1' JSON formats (INPUT_FORMAT.md).

NAMING SCHEME (raw)      <M><n>[_<deriv>][eps^<p> l^<k>]       e.g.  A5_vvd[eps^-1 l^1]
    M in {A, Z, Q};  n = moment order (A odd, Z/Q even);
    deriv = letters  v (d/dv at v=1), d (d/ddelta at delta=0), E (EE = d/deta at eta=0,
            two-sided source: U^odd (+) for A, U^even (-) for Z, Q; 'd' also differentiates the
            f_delta inside the source); any order of letters, E at most once;
    DEFAULT convention = plain derivatives  (A3_dd = d^2 A3/ddelta^2, NOT the Taylor
            coefficient [delta^2] = A3_dd/2).  Pass convention="taylor" for Taylor coefficients.
    [eps^p l^k]: coefficient of eps^p (log eps)^k in the small-eps expansion of that derivative.
NAMING SCHEME (normalized)  C<n>[_<deriv>][l^<k>]  or  K<n>[_<deriv>][l^<k>]   ([eps^0 l^k])
    C1 = A1, K2 = Q2.
Internally every number is a TAYLOR coefficient; gradients (Val.g) are with respect to the
internal (Taylor-scaled) inputs.  Result.gradient() converts back to the input convention.
"""
from __future__ import annotations

import json
import math
import os
import re
from fractions import Fraction
from functools import lru_cache

import mpmath as mp

INF = 10 ** 9
HERE = os.path.dirname(os.path.abspath(__file__))
CANONICAL_FORMAT = "lri-framework-raw/1"

# ============================================================================
#  errors
# ============================================================================


class MissingInputError(ValueError):
    """strict mode: required inputs were not supplied (they are never treated as zero)"""

    def __init__(self, missing, level="raw", order="D4"):
        self.missing = sorted(missing)
        self.level = level
        self.order = order
        head = ", ".join(self.missing[:25]) + (" ..." if len(self.missing) > 25 else "")
        super().__init__(
            f"{len(self.missing)} required {level} input(s) for order {order} not supplied: {head}. "
            "Strict mode never treats an absent input as zero: supply every scalar of the required "
            "list (structural/exact zeros explicitly, as value 0 with sigma 0 and \"exact\": true), "
            "or pass strict=False (CLI --allow-missing) to get MISSING outputs instead.")


class TruncationError(ValueError):
    """an output needs an eps power beyond the internal series cap (increase pcap)"""


# ============================================================================
#  Val : value + gradient (forward-mode linear error propagation) + missing tags
# ============================================================================


class Val:
    __slots__ = ("v", "g", "miss")

    def __init__(self, v=None, g=None, miss=None):
        self.v = v
        self.g = g if g is not None else {}
        self.miss = miss  # None or frozenset of names

    # -- constructors
    @staticmethod
    def const(x):
        return Val(mp.mpf(x) if not isinstance(x, mp.mpf) else x)

    @staticmethod
    def missing(names):
        return Val(None, None, frozenset(names))

    @staticmethod
    def input(name, x, track=True):
        x = mp.mpf(x)
        return Val(x, {name: mp.mpf(1)} if track else {})

    @property
    def is_missing(self):
        return self.miss is not None

    @property
    def is_exact_zero(self):
        """zero that does not depend on any input (value 0 and gradient identically 0).
        Multiplying by it gives an exact 0 even if the other factor is missing: the product's
        value and first-order gradient are 0 whatever the missing value is."""
        return self.miss is None and self.v == 0 and all(x == 0 for x in self.g.values())

    def _coerce(self, o):
        if isinstance(o, Val):
            return o
        if isinstance(o, Fraction):
            return Val(mp.mpf(o.numerator) / o.denominator)
        return Val(mp.mpf(o))

    def __add__(self, o):
        o = self._coerce(o)
        if self.miss is not None or o.miss is not None:
            return Val.missing((self.miss or frozenset()) | (o.miss or frozenset()))
        g = dict(self.g)
        for k, x in o.g.items():
            g[k] = g.get(k, 0) + x
        return Val(self.v + o.v, g)

    __radd__ = __add__

    def __neg__(self):
        if self.miss is not None:
            return self
        return Val(-self.v, {k: -x for k, x in self.g.items()})

    def __sub__(self, o):
        return self + (-self._coerce(o))

    def __rsub__(self, o):
        return self._coerce(o) + (-self)

    def __mul__(self, o):
        if not isinstance(o, Val):
            if isinstance(o, (int, Fraction)) and o == 0:
                return Val(mp.mpf(0))
            o = self._coerce(o)
            if self.miss is not None:
                return self
            return Val(self.v * o.v, {k: x * o.v for k, x in self.g.items()})
        if self.miss is not None or o.miss is not None:
            # an exact (input-free) zero annihilates even a missing factor
            if self.is_exact_zero or o.is_exact_zero:
                return Val(mp.mpf(0))
            return Val.missing((self.miss or frozenset()) | (o.miss or frozenset()))
        g = {k: x * o.v for k, x in self.g.items()}
        for k, x in o.g.items():
            g[k] = g.get(k, 0) + x * self.v
        return Val(self.v * o.v, g)

    __rmul__ = __mul__

    def __truediv__(self, o):
        o = self._coerce(o)
        if self.miss is not None or o.miss is not None:
            return Val.missing((self.miss or frozenset()) | (o.miss or frozenset()))
        inv = 1 / o.v
        g = {k: x * inv for k, x in self.g.items()}
        for k, x in o.g.items():
            g[k] = g.get(k, 0) - x * self.v * inv * inv
        return Val(self.v * inv, g)

    def __pow__(self, n):
        assert isinstance(n, int) and n >= 0
        r = Val(mp.mpf(1))
        for _ in range(n):
            r = r * self
        return r

    def sigma(self, sig):
        """propagated 1-sigma.  sig: an ErrorModel (independent sigmas + covariance blocks +
        replicate deviations, all in internal units) or a plain dict {name: sigma}
        (independent errors)."""
        if self.miss is not None:
            return None
        if isinstance(sig, ErrorModel):
            return mp.sqrt(sig.variance(self.g))
        s = mp.mpf(0)
        for k, x in self.g.items():
            if k in sig:
                s += (x * sig[k]) ** 2
        return mp.sqrt(s)

    def __repr__(self):
        if self.miss is not None:
            return f"Val(MISSING:{sorted(self.miss)[:4]}{'...' if len(self.miss) > 4 else ''})"
        return f"Val({mp.nstr(self.v, 20)})"


ZERO = Val(mp.mpf(0))

# ============================================================================
#  ErrorModel : what is known about the input errors (internal = Taylor units)
# ============================================================================


class ErrorModel:
    """variance of a linear functional g.x of the inputs (internal units):
         sum_k (g_k sig_k)^2                                independent sigmas (incl. systematic floors)
       + sum_blocks g_B^T C_B g_B                           covariance blocks (names disjoint)
       + sum_rb sum_r (sum_{k in rb} g_k dev_{k,r})^2 / (R_rb (R_rb - 1))
                                                            sample covariance of the mean of the R_rb
                                                            replicates of each replicate block rb
    Replicate blocks are independent of each other (the producer guarantees independent random
    streams); within a block, replicate r of every scalar comes from the same random shift.
    A name is in at most one covariance/replicate block; a replicated name may also carry an
    independent systematic sigma (its error floor)."""

    def __init__(self, sig=None, blocks=None, rep_blocks=None):
        self.sig = dict(sig or {})
        self.blocks = list(blocks or [])            # [(names list, matrix list of lists)]
        self.rep_blocks = dict(rep_blocks or {})    # block id -> (R, {name: [x_r - mean]})

    def __bool__(self):
        return bool(self.sig) or bool(self.blocks) or bool(self.rep_blocks)

    def __contains__(self, k):
        return k in self.names()

    def names(self):
        s = set(self.sig)
        for nm, _ in self.blocks:
            s |= set(nm)
        for _, devs in self.rep_blocks.values():
            s |= set(devs)
        return s

    @property
    def n_replicated(self):
        return sum(len(d) for _, d in self.rep_blocks.values())

    def variance(self, g):
        v = mp.mpf(0)
        for k, s in self.sig.items():
            x = g.get(k)
            if x:
                v += (x * s) ** 2
        for names, C in self.blocks:
            nz = [(a, g[n]) for a, n in enumerate(names) if g.get(n)]
            for a, xa in nz:
                for b, xb in nz:
                    v += xa * C[a][b] * xb
        for R, devs in self.rep_blocks.values():
            if R < 2:
                continue
            proj = [mp.mpf(0)] * R
            hit = False
            for k, dev in devs.items():
                x = g.get(k)
                if x:
                    hit = True
                    for r in range(R):
                        proj[r] += x * dev[r]
            if hit:
                v += sum(p * p for p in proj) / (R * (R - 1))
        return v

    def restricted(self, keep_sig=None, keep_blocks=None, keep_reps=None):
        """sub-model: independent sigmas of names in keep_sig, covariance blocks restricted to
        keep_blocks (cross terms to other names dropped), replicate blocks restricted to keep_reps
        (None keeps nothing of that part)"""
        ks, kb, kr = (set(x) if x is not None else set() for x in (keep_sig, keep_blocks, keep_reps))
        blocks = []
        for names, C in self.blocks:
            idx = [a for a, n in enumerate(names) if n in kb]
            if idx:
                blocks.append(([names[a] for a in idx], [[C[a][b] for b in idx] for a in idx]))
        reps = {}
        for bid, (R, devs) in self.rep_blocks.items():
            d = {k: x for k, x in devs.items() if k in kr}
            if d:
                reps[bid] = (R, d)
        return ErrorModel({k: s for k, s in self.sig.items() if k in ks}, blocks, reps)

    def cross_terms(self, set_a):
        """largest |C_ab| between a name in set_a and a name outside it (within covariance blocks)"""
        worst = mp.mpf(0)
        for names, C in self.blocks:
            for a, na in enumerate(names):
                for b, nb in enumerate(names):
                    if (na in set_a) != (nb in set_a):
                        worst = max(worst, abs(C[a][b]))
        return worst


# ============================================================================
#  LSeries : Laurent-log series sum c[p,k] eps^p l^k, valid through eps^pmax
# ============================================================================


class LSeries:
    __slots__ = ("t", "pmax", "miss", "tag")

    def __init__(self, terms=None, pmax=INF, miss=None, tag=""):
        self.t = terms if terms is not None else {}
        self.pmax = pmax
        self.miss = miss
        self.tag = tag

    @staticmethod
    def missing(names, tag=""):
        return LSeries({}, -INF, frozenset(names), tag)

    @property
    def pmin(self):
        """lowest power carrying a coefficient that is not an exact (input-free) zero.
        A supplied input counts as nonzero even when its value is 0 (its gradient is not zero),
        so the validity bookkeeping is structural and identical to the required-list probe."""
        return min((p for (p, _), x in self.t.items() if not x.is_exact_zero), default=INF)

    def __add__(self, o):
        if self.miss is not None or o.miss is not None:
            return LSeries.missing((self.miss or frozenset()) | (o.miss or frozenset()))
        pm = min(self.pmax, o.pmax)
        t = {}
        for src in (self.t, o.t):
            for key, x in src.items():
                if key[0] <= pm:
                    t[key] = t[key] + x if key in t else x
        return LSeries(t, pm)

    def neg(self):
        if self.miss is not None:
            return self
        return LSeries({k: -x for k, x in self.t.items()}, self.pmax)

    def __sub__(self, o):
        return self + o.neg()

    def mul(self, o, kmax, pcap):
        if self.miss is not None or o.miss is not None:
            return LSeries.missing((self.miss or frozenset()) | (o.miss or frozenset()))
        # effective lowest powers (known terms or first unknown order)
        a0 = min(self.pmin, self.pmax + 1 if self.pmax < INF else INF)
        b0 = min(o.pmin, o.pmax + 1 if o.pmax < INF else INF)
        t1 = self.pmax + b0 if (self.pmax < INF and b0 < INF) else INF
        t2 = o.pmax + a0 if (o.pmax < INF and a0 < INF) else INF
        pm = min(t1, t2, pcap) if min(t1, t2) < INF else (INF if a0 >= INF or b0 >= INF else pcap)
        if a0 >= INF or b0 >= INF:     # one factor is an exact zero
            return LSeries({}, INF)
        t = {}
        for (p1, k1), x in self.t.items():
            for (p2, k2), y in o.t.items():
                p, k = p1 + p2, k1 + k2
                if p <= pm and k <= kmax:
                    t[(p, k)] = t[(p, k)] + x * y if (p, k) in t else x * y
        return LSeries(t, pm)

    def coef(self, p, k, why=""):
        if self.miss is not None:
            return Val.missing(self.miss)
        if p > self.pmax:
            return Val.missing({f"<{self.tag or why} needs eps^{p} beyond validity eps^{self.pmax}>"})
        return self.t.get((p, k), ZERO)


ONE_SERIES = LSeries({(0, 0): Val(mp.mpf(1))}, INF)
ZERO_SERIES = LSeries({}, INF)

# ============================================================================
#  monomials / jets in (z, delta, eta)   (Taylor coefficients)
# ============================================================================


def monos(deg, emax=1):
    return [(i, j, e) for e in range(emax + 1) for i in range(deg + 1) for j in range(deg + 1 - i)]


def jet_mul(A, B, mlist, kmax, pcap):
    """product of two jets of LSeries, keeping monomials in mlist; missing entries propagate"""
    out = {}
    for m in mlist:
        acc = None
        for i1 in range(m[0] + 1):
            for j1 in range(m[1] + 1):
                for e1 in range(m[2] + 1):
                    m1 = (i1, j1, e1)
                    m2 = (m[0] - i1, m[1] - j1, m[2] - e1)
                    a = A.get(m1)
                    b = B.get(m2)
                    if a is None or b is None:   # structurally absent = zero
                        continue
                    prod = a.mul(b, kmax, pcap)
                    acc = prod if acc is None else acc + prod
        out[m] = acc if acc is not None else LSeries({}, INF)
    return out


def jet_add(A, B, mlist, sign=1):
    out = {}
    for m in mlist:
        a, b = A.get(m), B.get(m)
        if a is None and b is None:
            continue
        if b is not None and sign < 0:
            b = b.neg()
        out[m] = a if b is None else (b if a is None else a + b)
    return out


# ============================================================================
#  exact two-kink sector  Z2, Q2  (and A1)
# ============================================================================
#  Z2 = int_eps^1 dr w(r) T(r),  Q2 = int_eps^1 dr r w(r) T(r),
#  w = exp[-2 v f_d(r)],  f_d(r) = (r^d - 1)/d,
#  T(r) = int_0^{1-r} dX U^even:  T_eta^0 = 1-r,  T_eta^1 = 2[F_d(1-r) + F_d(r) - F_d(1)],
#  F_d(x) = (x^{1+d}/(1+d) - x)/d.

def _poly_mul(a, b):
    r = {}
    for i, x in a.items():
        for j, y in b.items():
            r[i + j] = r.get(i + j, 0) + x * y
    return r


@lru_cache(maxsize=None)
def _W_taylor(i, j):
    """[z^i delta^j] of r^2 * exp[-2(1+z) f_delta(r)] as polynomial in L=log r: dict m->Fraction"""
    # exponent X = -2 z L - 2 (1+z) sum_{k>=2} delta^{k-1} L^k/k!
    # represent bivariate series in (z,delta) with coefficients polynomials in L
    maxd = j
    X = {}  # (zi, dj) -> poly in L

    def addX(key, poly):
        X.setdefault(key, {})
        for m, c in poly.items():
            X[key][m] = X[key].get(m, 0) + c
    addX((1, 0), {1: Fraction(-2)})
    for k in range(2, maxd + 2):
        c = Fraction(-2, math.factorial(k))
        addX((0, k - 1), {k: c})
        addX((1, k - 1), {k: c})
    # exp(X) truncated at z^i delta^j
    res = {(0, 0): {0: Fraction(1)}}
    term = {(0, 0): {0: Fraction(1)}}
    for n in range(1, i + j + 1):
        new = {}
        for (a1, b1), p1 in term.items():
            for (a2, b2), p2 in X.items():
                a, b = a1 + a2, b1 + b2
                if a <= i and b <= j:
                    pr = _poly_mul(p1, p2)
                    new.setdefault((a, b), {})
                    for m, c in pr.items():
                        new[(a, b)][m] = new[(a, b)].get(m, 0) + c / n
        term = new
        for key, poly in term.items():
            res.setdefault(key, {})
            for m, c in poly.items():
                res[key][m] = res[key].get(m, 0) + c
    return {m: c for m, c in res.get((i, j), {}).items() if c != 0}


def _cpoly(n):
    """c_n(L) = sum_{a=0}^n (-1)^{n-a} L^a/a!  (delta^{n-1} coefficient of F_delta(x)/x)"""
    return {a: Fraction((-1) ** (n - a), math.factorial(a)) for a in range(n + 1)}


def _G(p, m, x):
    """antiderivative of r^p log^m r (p != -1) evaluated at x (mpf)"""
    L = mp.log(x)
    s = mp.mpf(0)
    for t in range(m + 1):
        s += (-1) ** t * mp.mpf(math.factorial(m)) / math.factorial(m - t) * L ** (m - t) / mp.mpf(p + 1) ** (t + 1)
    return x ** (p + 1) * s


def _Gcoef(p, m):
    """G_{p,m}(eps) = eps^{p+1} sum_s g_s l^{m-s}; returns dict (m-s) -> Fraction g_s"""
    return {m - t: Fraction((-1) ** t * math.factorial(m), math.factorial(m - t)) / Fraction(p + 1) ** (t + 1)
            for t in range(m + 1)}


def two_kink(kind, i, j, e, pcap=6, kmax=None, dps=None):
    if dps is not None and dps != mp.mp.dps:
        old = mp.mp.dps
        mp.mp.dps = dps
        try:
            return _two_kink(kind, i, j, e, pcap, kmax, dps)
        finally:
            mp.mp.dps = old
    return _two_kink(kind, i, j, e, pcap, kmax, mp.mp.dps)


@lru_cache(maxsize=None)
def _two_kink(kind, i, j, e, pcap, kmax, dps):
    """Laurent-log series of the [z^i delta^j eta^e] TAYLOR coefficient of Z2 (kind='Z') or
    Q2 (kind='Q'):  dict (p,k)->mpf for p<=pcap (all k unless kmax given).  Exact rational
    local parts; the finite-part constant of eta^1 pieces by quadrature at the current dps."""
    s = 0 if kind == "Z" else 1
    out = {}

    def add(p, k, x):
        if p <= pcap and (kmax is None or k <= kmax):
            out[(p, k)] = out.get((p, k), 0) + x

    # integrand K(r) = r^{s-2} sum_{j1+j2=j} W_{i,j1}(L) T_{e,j2}(r)
    # analytic pieces: r^p L^m monomials ;  numeric piece: (1-r) c(log(1-r)) part for e=1
    mono = {}   # (p,m) -> Fraction  : exact monomial part (finite sum)
    numparts = []  # list of (Wpoly, j2) for the log(1-r) pieces
    for j1 in range(j + 1):
        j2 = j - j1
        Wp = _W_taylor(i, j1)
        if not Wp:
            continue
        if e == 0:
            if j2 != 0:
                continue
            for m, c in Wp.items():          # (1-r) r^{s-2} L^m
                mono[(s - 2, m)] = mono.get((s - 2, m), 0) + c
                mono[(s - 1, m)] = mono.get((s - 1, m), 0) - c
        else:
            # T1_{j2} = 2[(1-r) c_{j2+1}(log(1-r)) + r c_{j2+1}(L) - (-1)^{j2+1}]
            cp = _cpoly(j2 + 1)
            for m, c in Wp.items():
                for a, ca in cp.items():          # 2 r^{s-1} L^{m+a}
                    mono[(s - 1, m + a)] = mono.get((s - 1, m + a), 0) + 2 * c * ca
                mono[(s - 2, m)] = mono.get((s - 2, m), 0) - 2 * c * (-1) ** (j2 + 1)
            numparts.append((Wp, j2))
    # exact monomial contributions: int_eps^1 r^p L^m
    for (p, m), c in mono.items():
        if c == 0:
            continue
        if p == -1:
            add(0, m + 1, -c / (m + 1))
        else:
            add(0, 0, c * Fraction((-1) ** m * math.factorial(m)) / Fraction(p + 1) ** (m + 1))
            for kk, gc in _Gcoef(p, m).items():
                add(p + 1, kk, -c * gc)
    # log(1-r) pieces: K_n(r) = 2 r^{s-2} W(L) (1-r) c(log(1-r))
    if numparts:
        r0 = mp.mpf(1) / 8
        NT = int(mp.mp.dps * 1.2 / math.log10(8)) + 10
        for Wp, j2 in numparts:
            cp = _cpoly(j2 + 1)
            # local power series of (1-r) c(log(1-r)) = sum_n d_n r^n  (exact rationals)
            # log(1-r) = -sum r^n/n ; powers of it
            lg = [Fraction(0)] + [Fraction(-1, n) for n in range(1, NT + 1)]
            powl = {0: [Fraction(1)] + [Fraction(0)] * NT}
            for a in range(1, max(cp) + 1):
                prev = powl[a - 1]
                nxt = [Fraction(0)] * (NT + 1)
                for x_, cx in enumerate(prev):
                    if cx:
                        for y_ in range(1, NT + 1 - x_):
                            nxt[x_ + y_] += cx * lg[y_]
                powl[a] = nxt
            ser = [Fraction(0)] * (NT + 1)
            for a, ca in cp.items():
                for n_, cn in enumerate(powl[a]):
                    ser[n_] += ca * cn
            dser = [ser[n_] - (ser[n_ - 1] if n_ >= 1 else 0) for n_ in range(NT + 1)]   # times (1-r)
            # local monomials: 2 * W_m * d_n * r^{s-2+n} L^m
            fp0 = mp.mpf(0)
            for m, c in Wp.items():
                for n_, dn in enumerate(dser):
                    if dn == 0:
                        continue
                    p = s - 2 + n_
                    coef = 2 * c * dn
                    # eps-expansion terms (p != -1): -coef * G_{p,m}(eps)
                    if p == -1:
                        add(0, m + 1, -coef / (m + 1))
                        fp0 += mp.mpf(coef.numerator) / coef.denominator * mp.log(r0) ** (m + 1) / (m + 1)
                    else:
                        if p + 1 <= pcap:
                            for kk, gc in _Gcoef(p, m).items():
                                add(p + 1, kk, -coef * gc)
                        fp0 += mp.mpf(coef.numerator) / coef.denominator * _G(p, m, r0)

            def integrand(r, Wp=Wp, cp=cp):
                L = mp.log(r)
                l1 = mp.log(1 - r)
                wv = sum(mp.mpf(c.numerator) / c.denominator * L ** m for m, c in Wp.items())
                cv = sum(mp.mpf(c.numerator) / c.denominator * l1 ** a for a, c in cp.items())
                return 2 * r ** (s - 2) * wv * (1 - r) * cv
            num = mp.quad(integrand, [r0, mp.mpf(1) / 2, 1])
            out[(0, 0)] = out.get((0, 0), 0) + fp0 + num
    res = {}
    for key, x in out.items():
        if isinstance(x, Fraction):
            x = mp.mpf(x.numerator) / x.denominator
        if x != 0:
            res[key] = x
    return res


def A1_taylor(j, e):
    """A1 = int_0^1 U^odd: [delta^j eta^e]; eta^0 -> delta_{j0}; eta^1 -> [-2/(1+delta)]_j"""
    if e == 0:
        return mp.mpf(1) if j == 0 else mp.mpf(0)
    return mp.mpf(-2 * (-1) ** j)


# ============================================================================
#  names
# ============================================================================

RAW_RE = re.compile(r"^\s*([AZQ])(\d+)(?:_([vdE]+))?\s*\[\s*eps\^\(?(-?\d+)\)?\s*,?\s*(?:l|ell|L)\^(\d+)\s*\]\s*$")
NORM_RE = re.compile(r"^\s*([CK])(\d+)(?:_([vdE]+))?\s*\[\s*(?:eps\^0\s*,?\s*)?(?:l|ell|L)\^(\d+)\s*\]\s*$")


def parse_deriv(s):
    s = s or ""
    i, j, e = s.count("v"), s.count("d"), s.count("E")
    if e > 1:
        raise ValueError("only first EE derivatives are defined/needed")
    return i, j, e


def deriv_str(i, j, e):
    return "v" * i + "d" * j + ("E" if e else "")


def raw_name(M, n, i, j, e, p, k):
    ds = deriv_str(i, j, e)
    return f"{M}{n}{'_' + ds if ds else ''}[eps^{p} l^{k}]"


def norm_name(X, n, i, j, e, k):
    ds = deriv_str(i, j, e)
    return f"{X}{n}{'_' + ds if ds else ''}[l^{k}]"


def parse_raw_name(name):
    """'A5_dv[eps^-1 l^1]' -> ('A', 5, 1, 1, 0, -1, 1)"""
    mt = RAW_RE.match(name)
    if not mt:
        raise ValueError(f"cannot parse raw input name {name!r}")
    M, n = mt.group(1), int(mt.group(2))
    i, j, e = parse_deriv(mt.group(3))
    p, k = int(mt.group(4)), int(mt.group(5))
    if (M == "A") != (n % 2 == 1):
        raise ValueError(f"{name!r}: A moments have odd order, Z and Q moments even order")
    return M, n, i, j, e, p, k


def parse_norm_name(name):
    mt = NORM_RE.match(name)
    if not mt:
        raise ValueError(f"cannot parse normalized name {name!r}")
    X, n = mt.group(1), int(mt.group(2))
    i, j, e = parse_deriv(mt.group(3))
    return X, n, i, j, e, int(mt.group(4))


def canonical_raw_name(name):
    M, n, i, j, e, p, k = parse_raw_name(name)
    return raw_name(M, n, i, j, e, p, k)


def struct_pmin(M, n):
    """structural lowest eps power of the raw moment (power divergences)"""
    if M in ("A",):
        return -(n - 1) // 2
    if M == "Z":
        return -(n // 2)
    if M == "Q":
        return -(n // 2 - 1)
    raise ValueError(M)


# ============================================================================
#  input parsing (values, sigmas, covariance blocks, replicates)
# ============================================================================


def _to_mpf(x, what=""):
    if isinstance(x, bool) or x is None:
        raise ValueError(f"{what}: not a number: {x!r}")
    if isinstance(x, mp.mpf):
        r = +x
    elif isinstance(x, Fraction):
        r = mp.mpf(x.numerator) / x.denominator
    elif isinstance(x, (int, float, str)):
        r = mp.mpf(x)
    else:
        raise ValueError(f"{what}: not a number: {x!r}")
    # gate review 2026-10-03: a NaN/inf value, replicate, sigma or covariance entry (e.g. a failed
    # producer coefficient) is rejected here instead of propagating into NaN or MISSING outputs
    if not mp.isfinite(r):
        raise ValueError(f"{what}: not a finite number: {x!r}")
    return r


_ENTRY_KEYS = {"value", "sigma", "exact", "reps", "mean", "sys", "block", "note", "source"}


DEFAULT_REP_BLOCK = "default"


def _entry(name, val):
    """normalize one input entry -> None (absent) or dict(value|reps, sigma, exact, mean)"""
    if val is None:
        return None
    if isinstance(val, dict):
        bad = set(val) - _ENTRY_KEYS
        if bad:
            raise ValueError(f"{name}: unknown entry keys {sorted(bad)} (allowed: {sorted(_ENTRY_KEYS)})")
        if "reps" in val:
            if "value" in val or val.get("exact"):
                raise ValueError(f"{name}: an entry has either 'reps' or 'value'/'exact', not both")
            reps = val["reps"]
            if not isinstance(reps, (list, tuple)) or any(x is None for x in reps):
                raise ValueError(f"{name}: 'reps' must be a list of numbers")
            sys_ = None if val.get("sys") is None else _to_mpf(val["sys"], name)
            if sys_ is not None and sys_ < 0:
                raise ValueError(f"{name}: negative systematic sigma")
            return {"reps": [_to_mpf(x, name) for x in reps],
                    "mean": None if val.get("mean") is None else _to_mpf(val["mean"], name),
                    "sigma": None if val.get("sigma") is None else _to_mpf(val["sigma"], name),
                    "sys": sys_, "block": str(val.get("block", DEFAULT_REP_BLOCK)), "exact": False}
        if "sys" in val or "block" in val:
            raise ValueError(f"{name}: 'sys' and 'block' belong to replicated entries ('reps')")
        if val.get("value") is None:
            return None
        exact = bool(val.get("exact", False))
        s = None if val.get("sigma") is None else _to_mpf(val["sigma"], name)
        if exact and s not in (None, 0):
            raise ValueError(f"{name}: an exact entry cannot carry a nonzero sigma")
        if s is not None and s < 0:
            raise ValueError(f"{name}: negative sigma")
        return {"value": _to_mpf(val["value"], name), "sigma": s, "exact": exact}
    if isinstance(val, (list, tuple)):
        if len(val) != 2:
            raise ValueError(f"{name}: a list entry must be [value, sigma]")
        x, s = val
        if x is None:
            return None
        s = None if s is None else _to_mpf(s, name)
        if s is not None and s < 0:
            raise ValueError(f"{name}: negative sigma")
        return {"value": _to_mpf(x, name), "sigma": s, "exact": False}
    return {"value": _to_mpf(val, name), "sigma": None, "exact": False}


def _cov_blocks(cov):
    """cov: None | {"names", "matrix"} | [blocks]  ->  list of (names, matrix)"""
    if cov is None:
        return []
    if isinstance(cov, dict):
        cov = [cov]
    out = []
    for b in cov:
        if isinstance(b, (list, tuple)) and len(b) == 2 and not isinstance(b, dict):
            names, C = b
        else:
            names, C = b["names"], b["matrix"]
        out.append((list(names), [[_to_mpf(x, "covariance") for x in row] for row in C]))
    return out


def _psd_check(names, C):
    """float LDL^T test: raises if the block is clearly not positive semidefinite"""
    n = len(names)
    A = [[float(C[a][b]) for b in range(n)] for a in range(n)]
    scale = [math.sqrt(A[a][a]) if A[a][a] > 0 else 1.0 for a in range(n)]
    A = [[A[a][b] / (scale[a] * scale[b]) for b in range(n)] for a in range(n)]
    L = [[0.0] * n for _ in range(n)]
    d = [0.0] * n
    for j in range(n):
        d[j] = A[j][j] - sum(L[j][k] ** 2 * d[k] for k in range(j))
        if d[j] < -1e-9:
            raise ValueError(f"covariance block is not positive semidefinite (pivot {d[j]:.3g} at {names[j]})")
        for i in range(j + 1, n):
            if d[j] > 1e-14:
                L[i][j] = (A[i][j] - sum(L[i][k] * L[j][k] * d[k] for k in range(j))) / d[j]


class InputSet:
    """parsed inputs of one level ('raw' | 'normalized' | 'beta'), in INTERNAL (Taylor) units"""

    def __init__(self, level, convention):
        self.level = level
        self.convention = convention
        self.values = {}      # canonical name -> mpf (mean for replicated scalars)
        self.reps = {}        # name -> [mpf]
        self.rep_block = {}   # name -> replicate block id
        self.block_R = {}     # replicate block id -> R
        self.sig = {}         # name -> independent sigma (fixed scalars) or systematic floor (replicated)
        self.sys = {}         # name -> systematic floor of a replicated scalar (also in sig)
        self.exact = set()
        self.absent = set()   # explicitly null
        self.scale = {}       # name -> factor f: internal = input / f
        self.blocks = []
        self.rep_sigma_ratio = {}   # name -> given (statistical) sigma / replicate standard error
        self.errmodel = ErrorModel()

    @property
    def n_rep(self):
        """the common number of replicates of all replicate blocks (0: none; None: blocks differ)"""
        Rs = set(self.block_R.values())
        return 0 if not Rs else (Rs.pop() if len(Rs) == 1 else None)

    # -------------------------------------------------------------- names
    def canon(self, name):
        if self.level == "raw":
            M, n, i, j, e, p, k = parse_raw_name(name)
            return raw_name(M, n, i, j, e, p, k), self._fac(i, j)
        if self.level == "normalized":
            X, n, i, j, e, k = parse_norm_name(name)
            return norm_name(X, n, i, j, e, k), self._fac(i, j)
        if name not in DICT:
            raise ValueError(f"unknown beta input {name!r}")
        return name, 1

    def _fac(self, i, j):
        if self.convention == "derivative":
            return math.factorial(i) * math.factorial(j)
        if self.convention == "taylor":
            return 1
        raise ValueError("convention must be 'derivative' or 'taylor'")

    # -------------------------------------------------------------- parse
    def parse(self, raw, sigmas=None, cov=None):
        seen = {}
        for name, val in raw.items():
            cn, fac = self.canon(name)
            if cn in seen:
                raise ValueError(f"input {cn!r} supplied twice (as {seen[cn]!r} and {name!r})")
            seen[cn] = name
            ent = _entry(name, val)
            if ent is None:
                self.absent.add(cn)
                continue
            self.scale[cn] = fac
            if "reps" in ent:
                reps = [x / fac for x in ent["reps"]]
                R = len(reps)
                if R < 2:
                    raise ValueError(f"{name}: at least 2 replicates are needed")
                bid = ent["block"]
                if self.block_R.get(bid, R) != R:
                    raise ValueError(f"{name}: {R} replicates, but other scalars of replicate block {bid!r} have "
                                     f"{self.block_R[bid]}; replicate r of a block must be the same random shift "
                                     "for all its scalars")
                self.block_R[bid] = R
                self.rep_block[cn] = bid
                mean = sum(reps) / R
                if ent["mean"] is not None:
                    tol = mp.mpf(10) ** -10 * max(abs(x) for x in reps) + mp.mpf(10) ** -40
                    if abs(ent["mean"] / fac - mean) > tol:
                        raise ValueError(f"{name}: given mean {mp.nstr(ent['mean'], 17)} differs from the mean of "
                                         f"its replicates {mp.nstr(mean * fac, 17)}")
                self.reps[cn] = reps
                self.values[cn] = mean
                if ent["sigma"] is not None:
                    se = mp.sqrt(sum((x - mean) ** 2 for x in reps) / (R * (R - 1)))
                    self.rep_sigma_ratio[cn] = (ent["sigma"] / fac) / se if se > 0 else None
                if ent["sys"]:
                    self.sys[cn] = self.sig[cn] = ent["sys"] / fac
                continue
            self.values[cn] = ent["value"] / fac
            if ent["exact"]:
                self.exact.add(cn)
            if ent["sigma"] is not None and ent["sigma"] != 0:
                self.sig[cn] = ent["sigma"] / fac
        # ---- sigmas keyword (honoured on every entry point)
        for name, s in (sigmas or {}).items():
            cn, fac = self.canon(name)
            if cn not in self.values:
                raise ValueError(f"sigma given for {name!r}, which is not supplied")
            if cn in self.reps:
                raise ValueError(f"sigma given for the replicated scalar {name!r}; its error comes from the "
                                 "replicates (a systematic floor goes into its entry as 'sys')")
            s = _to_mpf(s, name)
            if s < 0:
                raise ValueError(f"{name}: negative sigma")
            if cn in self.exact and s != 0:
                raise ValueError(f"sigma given for {name!r}, which is declared exact")
            si = s / fac
            if cn in self.sig and abs(self.sig[cn] - si) > mp.mpf(10) ** -12 * max(abs(si), abs(self.sig[cn])):
                raise ValueError(f"conflicting sigmas for {name!r}: {mp.nstr(self.sig[cn] * fac, 6)} in the "
                                 f"input entry and {mp.nstr(s, 6)} in sigmas=")
            if si != 0:
                self.sig[cn] = si
        # ---- covariance blocks
        in_block = set()
        for names, C in _cov_blocks(cov):
            n = len(names)
            if len(C) != n or any(len(row) != n for row in C):
                raise ValueError("covariance block: matrix must be square and match 'names'")
            cns, facs = [], []
            for nm in names:
                cn, fac = self.canon(nm)
                if cn not in self.values:
                    raise ValueError(f"covariance given for {nm!r}, which is not supplied")
                if cn in in_block or cn in cns:
                    raise ValueError(f"{nm!r} appears in more than one covariance row/block")
                cns.append(cn)
                facs.append(fac)
            for a in range(n):
                if C[a][a] < 0:
                    raise ValueError(f"covariance block: negative variance for {names[a]!r}")
                for b in range(a):
                    tol = mp.mpf(10) ** -12 * mp.sqrt(abs(C[a][a] * C[b][b])) + mp.mpf(10) ** -300
                    if abs(C[a][b] - C[b][a]) > tol:
                        raise ValueError(f"covariance block is not symmetric ({names[a]!r}, {names[b]!r})")
            _psd_check(names, C)
            Ci = [[C[a][b] / (facs[a] * facs[b]) for b in range(n)] for a in range(n)]
            for a, cn in enumerate(cns):
                if cn in self.exact and any(Ci[a][b] != 0 for b in range(n)):
                    raise ValueError(f"covariance given for {cn!r}, which is declared exact")
                if cn in self.sig and cn not in self.sys:
                    sd = mp.sqrt(Ci[a][a])
                    if abs(sd - self.sig[cn]) > mp.mpf(10) ** -6 * max(sd, self.sig[cn]):
                        raise ValueError(f"{cn!r}: sigma {mp.nstr(self.sig[cn] * facs[a], 6)} disagrees with the "
                                         f"covariance diagonal {mp.nstr(sd * facs[a], 6)}")
                    del self.sig[cn]       # the block carries it
            in_block |= set(cns)
            self.blocks.append((cns, Ci))
        # ---- replicate blocks (statistical part of replicated scalars not covered by a covariance block)
        rep_blocks = {}
        for cn, reps in self.reps.items():
            if cn in in_block:
                continue
            bid = self.rep_block[cn]
            rep_blocks.setdefault(bid, (self.block_R[bid], {}))[1][cn] = [x - self.values[cn] for x in reps]
        self.errmodel = ErrorModel(self.sig, self.blocks, rep_blocks)
        return self

    @property
    def fixed_names(self):
        return set(self.values) - set(self.reps)


# ============================================================================
#  beta-input dictionary and named sectors
# ============================================================================

BETA_NAMES_D4 = ["a", "p", "A", "E", "V", "alpha", "beta", "gamma", "b", "G", "R", "Phi", "Psi", "J", "Omega",
                 "c", "f", "q", "L", "M", "Q", "k", "N", "P", "K"]
BETA_NAMES_C8 = ["W", "S", "U", "J9", "L3", "M21", "M12", "N2", "Ndelta", "Kv"]
# (which, i, j, factor):  value = factor * [z^i delta^j] which
DICT = {
    "a": ("b3", 1, 0, 1), "p": ("b3", 0, 1, 1), "A": ("b3", 2, 0, 1), "E": ("b3", 1, 1, 1),
    "V": ("b3", 0, 2, 1), "alpha": ("b3", 3, 0, 1), "beta": ("b3", 2, 1, 1), "gamma": ("b3", 1, 2, 1),
    "b": ("b5", 0, 0, 1), "G": ("b5", 1, 0, 1), "R": ("b5", 0, 1, 1), "Phi": ("b5", 2, 0, 1),
    "Psi": ("b5", 1, 1, 1), "J": ("b7", 0, 0, 1), "Omega": ("b7", 1, 0, 1),
    "c": ("h4", 0, 0, -4), "f": ("h4", 1, 0, -4), "q": ("h4", 0, 1, -4), "L": ("h4", 2, 0, -4),
    "M": ("h4", 1, 1, -4), "Q": ("h4", 0, 2, -4), "k": ("h6", 0, 0, -4), "N": ("h6", 1, 0, -4),
    "P": ("h6", 0, 1, -4), "K": ("h8", 0, 0, -4),
    "W": ("b3", 0, 3, 1), "S": ("b5", 0, 2, 1), "U": ("b7", 0, 1, 1), "J9": ("b9", 0, 0, 1),
    "L3": ("h4", 3, 0, -4), "M21": ("h4", 2, 1, -4), "M12": ("h4", 1, 2, -4),
    "N2": ("h6", 2, 0, -4), "Ndelta": ("h6", 1, 1, -4), "Kv": ("h8", 1, 0, -4),
}
# F = z + sum u^i z^j delta^k F_ijk ; H = -delta + 4u + sum H_ijk  (named sectors only;
# power counting in derive_invariants.py proves nothing else enters T<=4, D<=4)
FSEC = {(1, 0, 0): None, (1, 1, 0): "a", (1, 0, 1): "p", (1, 2, 0): "A", (1, 1, 1): "E", (1, 0, 2): "V",
        (1, 3, 0): "alpha", (1, 2, 1): "beta", (1, 1, 2): "gamma", (1, 0, 3): "W",
        (2, 0, 0): "b", (2, 1, 0): "G", (2, 0, 1): "R", (2, 2, 0): "Phi", (2, 1, 1): "Psi", (2, 0, 2): "S",
        (3, 0, 0): "J", (3, 1, 0): "Omega", (3, 0, 1): "U", (4, 0, 0): "J9"}
HSEC = {(2, 0, 0): "c", (2, 1, 0): "f", (2, 0, 1): "q", (2, 2, 0): "L", (2, 1, 1): "M",
        (2, 0, 2): "Q", (2, 3, 0): "L3", (2, 2, 1): "M21", (2, 1, 2): "M12",
        (3, 0, 0): "k", (3, 1, 0): "N", (3, 0, 1): "P", (3, 2, 0): "N2", (3, 1, 1): "Ndelta",
        (4, 0, 0): "K", (4, 1, 0): "Kv"}

# ---- C8 = 8 T4 through eq:C8assembly (note l.1162-1166, appendix app:C8polynomial l.2781).
# derive_C8.py proves from the delta^4 trace that C8 = 8 T4 is AFFINE in the ten new inputs with the
# constant coefficients C8_LINEAR, and that the remainder B_old is the polynomial B_OLD_C8_TERMS in the 25
# old inputs (identical to the appendix, which derive_C8.py parses from the note's TeX).  The module
# evaluates C8 both ways (res.C[8] = 8 T4 from the fixed point; res.c8["C8_asm"] from this table) and
# checks that they agree.  tests/test_c8.py checks this table against out/C8_trace.json.
C8_LINEAR = {"W": Fraction(4), "S": Fraction(2), "U": Fraction(3, 4), "J9": Fraction(1, 4),
             "L3": Fraction(3, 32), "M21": Fraction(-1, 4), "M12": Fraction(1, 2), "N2": Fraction(-1, 16),
             "Ndelta": Fraction(1, 8), "Kv": Fraction(1, 32)}
# the six new inputs that enter the archive's assembly as 'inherited numerical records' (note l.1240-1252);
# B_done = B_old + their terms (note l.1404)
C8_INHERITED = ("W", "S", "L3", "M21", "M12", "N2")
C8_PACKAGES = ("Ndelta", "U", "Kv", "J9")          # the four packages F1..F4 (note l.1255)
# B_old = sum coef * prod name^power   (61 terms, the 25 old inputs only)
B_OLD_C8_TERMS = (
    (Fraction(-1, 16), (("alpha", 1),)),
    (Fraction(1, 4), (("beta", 1),)),
    (Fraction(-1, 1), (("gamma", 1),)),
    (Fraction(1, 8), (("Phi", 1),)),
    (Fraction(-1, 2), (("Psi", 1),)),
    (Fraction(-3, 16), (("Omega", 1),)),
    (Fraction(3, 64), (("L", 1),)),
    (Fraction(-1, 16), (("M", 1),)),
    (Fraction(-1, 4), (("Q", 1),)),
    (Fraction(-1, 64), (("N", 1),)),
    (Fraction(-1, 16), (("P", 1),)),
    (Fraction(-1, 64), (("K", 1),)),
    (Fraction(-3, 16), (("a", 1), ("A", 1),)),
    (Fraction(1, 2), (("a", 1), ("E", 1),)),
    (Fraction(-1, 1), (("a", 1), ("V", 1),)),
    (Fraction(3, 16), (("a", 1), ("G", 1),)),
    (Fraction(-1, 4), (("a", 1), ("R", 1),)),
    (Fraction(-1, 16), (("a", 1), ("J", 1),)),
    (Fraction(-1, 64), (("a", 1), ("f", 1),)),
    (Fraction(1, 8), (("a", 1), ("q", 1),)),
    (Fraction(1, 16), (("a", 1), ("L", 1),)),
    (Fraction(1, 32), (("a", 1), ("k", 1),)),
    (Fraction(1, 2), (("p", 1), ("A", 1),)),
    (Fraction(-1, 1), (("p", 1), ("E", 1),)),
    (Fraction(-1, 2), (("p", 1), ("G", 1),)),
    (Fraction(-1, 4), (("p", 1), ("q", 1),)),
    (Fraction(-1, 4), (("p", 1), ("L", 1),)),
    (Fraction(-1, 16), (("p", 1), ("k", 1),)),
    (Fraction(1, 8), (("A", 1), ("b", 1),)),
    (Fraction(-3, 64), (("A", 1), ("c", 1),)),
    (Fraction(-1, 4), (("E", 1), ("b", 1),)),
    (Fraction(1, 8), (("E", 1), ("c", 1),)),
    (Fraction(-1, 4), (("V", 1), ("c", 1),)),
    (Fraction(-1, 8), (("b", 1), ("G", 1),)),
    (Fraction(3, 64), (("b", 1), ("f", 1),)),
    (Fraction(-1, 4), (("b", 1), ("q", 1),)),
    (Fraction(-1, 16), (("b", 1), ("L", 1),)),
    (Fraction(-1, 16), (("b", 1), ("k", 1),)),
    (Fraction(3, 32), (("G", 1), ("c", 1),)),
    (Fraction(-1, 4), (("R", 1), ("c", 1),)),
    (Fraction(-9, 64), (("J", 1), ("c", 1),)),
    (Fraction(1, 256), (("c", 1), ("f", 1),)),
    (Fraction(1, 16), (("c", 1), ("q", 1),)),
    (Fraction(3, 64), (("c", 1), ("L", 1),)),
    (Fraction(-1, 16), (("c", 1), ("M", 1),)),
    (Fraction(5, 256), (("c", 1), ("k", 1),)),
    (Fraction(-3, 128), (("c", 1), ("N", 1),)),
    (Fraction(1, 64), (("f", 2),)),
    (Fraction(-1, 16), (("f", 1), ("q", 1),)),
    (Fraction(-1, 64), (("f", 1), ("k", 1),)),
    (Fraction(-1, 16), (("a", 3),)),
    (Fraction(1, 4), (("a", 2), ("p", 1),)),
    (Fraction(1, 8), (("a", 1), ("p", 1), ("c", 1),)),
    (Fraction(1, 16), (("a", 2), ("b", 1),)),
    (Fraction(3, 64), (("a", 1), ("b", 1), ("c", 1),)),
    (Fraction(-3, 64), (("a", 2), ("c", 1),)),
    (Fraction(-5, 256), (("a", 1), ("c", 2),)),
    (Fraction(1, 32), (("p", 1), ("c", 2),)),
    (Fraction(5, 128), (("b", 1), ("c", 2),)),
    (Fraction(-5, 1024), (("c", 3),)),
    (Fraction(5, 512), (("c", 2), ("f", 1),)),
)
C8_PARTS_DOC = {
    "B_old8": "B_old: the appendix polynomial in the 25 old inputs (eq:C8assembly, app:C8polynomial)",
    "B_done8": "B_done = B_old + 4W + 2S + 3/32 L3 - 1/4 M21 + 1/2 M12 - 1/16 N2 (old inputs + the six "
               "inherited-record terms); MISSING if any of the six is absent",
    "C8_asm": "B_old + all ten linear terms of eq:C8assembly (must equal C8 = 8 T4); MISSING if any is absent",
    "C8_partial": "B_old + the linear terms of the new inputs that ARE available; the absent ones are NOT "
                  "included (never set to zero) and are listed in c8_info['partial_missing']",
}


def c8_parts(beta, order="C8"):
    """eq:C8assembly pieces from beta-level Vals.  beta: {name: Val} (absent names count as MISSING).
    Returns (parts, info): parts = {'B_old8'} at order D4, {'B_old8', 'B_done8', 'C8_asm', 'C8_partial'} at
    order C8 (Val each); info = {'terms_included': [...], 'partial_missing': {name: [what it needs]}}."""
    def bget(nm):
        x = beta.get(nm)
        return x if x is not None else Val.missing({f"<beta {nm} absent>"})
    bold = ZERO
    for c, mon in B_OLD_C8_TERMS:
        t = Val(mp.mpf(c.numerator) / c.denominator)
        for nm, pw in mon:
            t = t * bget(nm) ** pw
        bold = bold + t
    parts = {"B_old8": bold}
    if order != "C8":
        return parts, {}
    terms = {nm: bget(nm) * c for nm, c in C8_LINEAR.items()}
    done = bold
    for nm in C8_INHERITED:
        done = done + terms[nm]
    asm = bold
    for nm in C8_LINEAR:
        asm = asm + terms[nm]
    part = bold
    included, absent = [], {}
    for nm in C8_LINEAR:
        if terms[nm].is_missing:
            absent[nm] = sorted(terms[nm].miss)
        else:
            part = part + terms[nm]
            included.append(nm)
    parts.update({"B_done8": done, "C8_asm": asm, "C8_partial": part})
    return parts, {"terms_included": included, "partial_missing": absent}




class Result:
    """outputs of one assembly.  Values are Val (value + gradient w.r.t. INTERNAL inputs, or MISSING)."""

    def __init__(self):
        self.normalized = {}   # name -> Val   e.g. 'C3_vv[l^1]'  (derivative convention)
        self.bh = {}           # 'b3' -> {(i,j): Val}
        self.beta = {}         # 'a' -> Val
        self.inv = {}          # 'T2','D3',... -> Val
        self.C = {}            # n -> Val
        self.c8 = {}           # eq:C8assembly pieces (c8_parts): 'B_old8' always; 'B_done8', 'C8_asm', 'C8_partial' at C8
        self.c8_info = {}      # terms included in / missing from C8_partial; C8_asm - 8 T4 check
        self.sig = ErrorModel()    # input error model (internal units)
        self.scale = {}        # input name -> f  (internal = input / f)
        self.warnings = []
        self.two_kink_check = {}
        self.unused = []       # supplied inputs that no output needs
        self.meta = {}

    def value(self, x):
        return None if x.is_missing else x.v

    def outputs(self):
        """flat ordered dict of every output: beta names, T1.., D1.., C1.."""
        out = dict(self.beta)
        out.update(self.inv)
        out.update({f"C{n}": v for n, v in self.C.items()})
        out.update(self.c8)
        return out

    def get(self, name):
        return self.outputs()[name]

    def sigma(self, x):
        if isinstance(x, str):
            x = self.get(x)
        return x.sigma(self.sig)

    def gradient(self, x):
        """{input name: d output / d input} in the INPUT convention (undoes the Taylor scaling)"""
        if isinstance(x, str):
            x = self.get(x)
        if x.is_missing:
            return None
        return {k: g / self.scale.get(k, 1) for k, g in x.g.items() if g != 0}

    def table(self, which="all", digits=25):
        rows = []
        groups = []
        if which in ("all", "beta"):
            groups.append(("beta", self.beta))
        if which in ("all", "inv"):
            groups.append(("inv", self.inv))
        if which in ("all", "C"):
            groups.append(("C", {f"C{n}": v for n, v in self.C.items()}))
        if which in ("all", "C8parts"):
            groups.append(("C8parts", self.c8))
        for gname, d in groups:
            for k, x in d.items():
                if x.is_missing:
                    rows.append((gname, k, "MISSING", ", ".join(sorted(x.miss)[:6]) + (" ..." if len(x.miss) > 6 else "")))
                else:
                    s = x.sigma(self.sig) if self.sig else None
                    rows.append((gname, k, mp.nstr(x.v, digits), "" if s is None else mp.nstr(s, 3)))
        return rows

    def as_dict(self, digits=30):
        def enc(x):
            if x.is_missing:
                return {"missing": sorted(x.miss)}
            d = {"value": mp.nstr(x.v, digits)}
            if self.sig:
                d["sigma"] = mp.nstr(x.sigma(self.sig), 4)
            return d
        return {"meta": self.meta,
                "beta": {k: enc(v) for k, v in self.beta.items()},
                "invariants": {k: enc(v) for k, v in self.inv.items()},
                "C": {f"C{n}": enc(v) for n, v in self.C.items()},
                "C8_parts": {k: enc(v) for k, v in self.c8.items()},
                "C8_info": {k: (mp.nstr(v, 5) if isinstance(v, mp.mpf) else v) for k, v in self.c8_info.items()},
                "warnings": list(self.warnings),
                "two_kink_check": {k: mp.nstr(v, 3) for k, v in self.two_kink_check.items()},
                "unused_inputs": list(self.unused)}


class ReplicateResult:
    """per-replicate assembly.  central: Result at the mean inputs (linear errors);
    per_rep[output] = [value in replicate r]; stats[output] = dict(value, sigma_linear, rep_mean,
    rep_se, sigma_extra, sigma_rep_total, nonlinearity, n_rep)  or  {'missing': [...]}"""

    def __init__(self, central, per_rep, stats, meta):
        self.central = central
        self.per_rep = per_rep
        self.stats = stats
        self.meta = meta

    @property
    def beta(self):
        return self.central.beta

    @property
    def inv(self):
        return self.central.inv

    @property
    def C(self):
        return self.central.C

    @property
    def warnings(self):
        return self.central.warnings

    def table(self, digits=20):
        rows = []
        for o, st in self.stats.items():
            if "missing" in st:
                rows.append((o, "MISSING", ", ".join(st["missing"][:6]), "", "", ""))
                continue
            rows.append((o, mp.nstr(st["value"], digits), mp.nstr(st["sigma_linear"], 3),
                         mp.nstr(st["rep_mean"], digits), mp.nstr(st["sigma_rep_total"], 3),
                         mp.nstr(st["nonlinearity"], 3)))
        return rows

    def as_dict(self, digits=30):
        st = {}
        for o, s in self.stats.items():
            if "missing" in s:
                st[o] = s
                continue
            st[o] = {k: (mp.nstr(v, digits if k in ("value", "rep_mean") else 4) if isinstance(v, mp.mpf) else v)
                     for k, v in s.items()}
        d = self.central.as_dict(digits)
        d["meta"] = self.meta
        d["replicate_stats"] = st
        def enc(xs):
            if isinstance(xs, dict):
                return {k: enc(v) for k, v in xs.items()}
            return [None if x is None else mp.nstr(x, digits) for x in xs]
        d["replicate_values"] = {o: enc(xs) for o, xs in self.per_rep.items()}
        return d


class Framework:
    """
    order = "D4": everything needed for D3, T3 (C6) and D4 (C7)  [default]
    order = "C8": additionally T4 (C8) inputs W..Kv
    Public entry points (all strict by default, all honour sigmas= and cov=):
      from_raw(raw, ...)          raw moment coefficients -> Result
      from_replicates(raw, ...)   raw coefficients with QMC replicates -> ReplicateResult
      from_normalized(norm, ...)  normalized coefficients -> Result
      from_beta(beta, ...)        beta inputs -> invariants and C_n
      required_inputs(...), required_names(...)
    The global mpmath precision is not changed: every call works inside mp.workdps(dps).
    """

    def __init__(self, order="D4", dps=50, kmax=1, pcap=6):
        assert order in ("D4", "C8")
        self.order = order
        self.dps = dps
        self.kmax = kmax          # log power kept in all products (1 suffices for beta functions)
        self.pcap = pcap          # highest eps power ever formed (and validity of the internal Z2, Q2)
        self.deg = 3 if order == "D4" else 4          # total (z,delta) degree of jets
        self.nodd = 7 if order == "D4" else 9          # highest odd response C_n
        self.neven = 8                                  # highest current response K_n (h8 -> K, Kv)
        self.nz = max(self.nodd - 1, self.neven - 2)    # highest vacuum moment Z_n
        self.beta_names = BETA_NAMES_D4 + (BETA_NAMES_C8 if order == "C8" else [])
        self.warnings = []
        self.two_kink_check = {}
        self._probe_cache = {}

    # ------------------------------------------------------------------ outputs
    def default_outputs(self):
        outs = list(self.beta_names) + [f"C{n}" for n in range(3, 8 if self.order == "D4" else 9)]
        if self.order == "C8":
            outs += ["B_old8", "B_done8"]
        return outs

    @staticmethod
    def _get_output(res, o):
        if o in res.beta:
            return res.beta[o]
        if o in res.inv:
            return res.inv[o]
        if o.startswith("C") and o[1:].isdigit() and int(o[1:]) in res.C:
            return res.C[int(o[1:])]
        if o in res.c8:
            return res.c8[o]
        raise ValueError(f"unknown output {o!r}")

    # ------------------------------------------------------------- requirements
    def _probe(self, level, use_internal):
        key = (level, use_internal)
        if key not in self._probe_cache:
            with mp.workdps(self.dps):
                res = Result()
                if level == "raw":
                    jets = self._raw_jets({}, use_internal, compare=False)
                    C, K = self._normalize(jets)
                    c, kk = self._extract(C, K)
                    self._finish(c, kk, res)
                elif level == "normalized":
                    c, kk = self._norm_slots({}, use_internal, compare=False)
                    self._finish(c, kk, res)
                elif level == "beta":
                    for nm in self.beta_names:
                        res.beta[nm] = Val.missing({nm})
                    self._invariants(self._bh_tree(), res)
                else:
                    raise ValueError(f"level must be raw, normalized or beta, not {level!r}")
            self._probe_cache[key] = res
        return self._probe_cache[key]

    def required_inputs(self, outputs=None, use_internal_two_kink=True, level="raw"):
        """{output: sorted names of the inputs it needs}  (structural: an input is listed if the
        output depends on it for generic values; inputs multiplying exact zeros are omitted).
        level: 'raw' (default), 'normalized' or 'beta'."""
        res = self._probe(level, use_internal_two_kink)
        need = {}
        for o in (outputs or self.default_outputs()):
            x = self._get_output(res, o)
            need[o] = sorted(x.miss) if x.is_missing else []
        return need

    def required_names(self, outputs=None, use_internal_two_kink=True, level="raw"):
        """sorted union of required_inputs() over `outputs` (default: all beta inputs and C3..C7/C8)"""
        return sorted({x for v in self.required_inputs(outputs, use_internal_two_kink, level).values() for x in v})

    def check_inputs(self, supplied, outputs=None, use_internal_two_kink=True, level="raw"):
        """strict-mode validation: raises TruncationError / MissingInputError"""
        need = set(self.required_names(outputs, use_internal_two_kink, level))
        pseudo = sorted(n for n in need if n.startswith("<"))
        if pseudo:
            raise TruncationError("the requested outputs need eps powers beyond the internal series cap "
                                  f"pcap={self.pcap}: {pseudo[:6]}; increase pcap")
        missing = need - set(supplied)
        if missing:
            raise MissingInputError(missing, level, self.order)

    # ------------------------------------------------------------------ inputs
    def _raw_jets(self, vals, use_internal, compare=True, fill_missing=True):
        """vals: canonical raw name -> Val (internal units).  Builds jets {(M,n)} -> {(i,j,e): LSeries}.
        Every atom carries every structural slot eps^pmin..eps^pcap, l^0..l^kmax: a supplied value
        or a MISSING tag with its own name (never an implicit zero); validity pmax = pcap.
        use_internal: True -> exact internal A1, Z2, Q2 (supplied ones are only compared, see
        self.warnings); 'auto' -> supplied if present else internal; False -> never internal.
        fill_missing=False (used only for the per-replicate re-assemblies, after the strict check
        has passed) leaves unsupplied slots out instead of tagging them: by the required-list
        probe no output depends on them, so the outputs are identical and the run is ~8x faster."""
        series = {}   # (M,n,i,j,e) -> {(p,k): Val}
        for name, val in vals.items():
            M, n, i, j, e, p, k = parse_raw_name(name)
            if k > self.kmax or p > self.pcap:
                continue      # higher logs / powers never reach the outputs at this kmax, pcap
            if p < struct_pmin(M, n):
                if val.v != 0:
                    raise ValueError(f"{name}: eps^{p} lies below the structural lowest power "
                                     f"eps^{struct_pmin(M, n)} of {M}{n}; such a coefficient must vanish")
                continue
            series.setdefault((M, n, i, j, e), {})[(p, k)] = val
        jets = {}
        ml = monos(self.deg + 1)
        for M, ns in (("A", range(1, self.nodd + 1, 2)), ("Z", range(2, self.nz + 1, 2)),
                      ("Q", range(2, self.neven + 1, 2))):
            for n in ns:
                jet = {}
                for (i, j, e) in ml:
                    key = (M, n, i, j, e)
                    tag = f"{M}{n}" + ("_" + deriv_str(i, j, e) if deriv_str(i, j, e) else "")
                    sup = series.get(key, {})
                    internal = bool(use_internal) and ((M == "A" and n == 1) or (M in ("Z", "Q") and n == 2))
                    if internal and sup and use_internal != "auto" and compare:
                        self._compare_two_kink(M, n, i, j, e, sup)
                    if internal and (not sup or use_internal != "auto"):
                        if M == "A":
                            x = A1_taylor(j, e) if i == 0 else mp.mpf(0)
                            # A1 = int_0^1 U^odd does not depend on eps: exact to all orders
                            jet[(i, j, e)] = LSeries({(0, 0): Val(x)} if x != 0 else {}, INF, tag=tag)
                            continue
                        terms = two_kink(M, i, j, e, self.pcap, None, self.dps)
                        # the internal Z2/Q2 series hold terms through eps^pcap only: validity pcap
                        jet[(i, j, e)] = LSeries({pk: Val(x) for pk, x in terms.items() if pk[1] <= self.kmax},
                                                 self.pcap, tag=tag)
                        continue
                    pmin = struct_pmin(M, n)
                    terms = {}
                    for p in range(pmin, self.pcap + 1):
                        for k in range(self.kmax + 1):
                            if (p, k) in sup:
                                terms[(p, k)] = sup[(p, k)]
                            elif fill_missing:
                                terms[(p, k)] = Val.missing({raw_name(M, n, i, j, e, p, k)})
                    jet[(i, j, e)] = LSeries(terms, self.pcap, tag=tag)
                jets[(M, n)] = jet
        return jets

    def _compare_two_kink(self, M, n, i, j, e, terms):
        """compare supplied two-kink/one-kink coefficients (internal units) with the exact internal sector"""
        if M == "A":
            exact = {(0, 0): A1_taylor(j, e)} if i == 0 else {}
        else:
            exact = two_kink(M, i, j, e, self.pcap, None, self.dps)
        worst = mp.mpf(0)
        for (p, k), x in terms.items():
            if x.is_missing or p > self.pcap:
                continue
            d = abs(x.v - exact.get((p, k), 0))
            worst = max(worst, d / (1 + abs(exact.get((p, k), 0))))
        tag = f"{M}{n}" + ("_" + deriv_str(i, j, e) if deriv_str(i, j, e) else "")
        self.two_kink_check[tag] = worst
        if worst > mp.mpf(10) ** (-(self.dps // 2)):
            self.warnings.append(f"supplied {tag} differs from the exact internal sector (max rel. diff {mp.nstr(worst, 3)})")

    def _internal_normalized(self, X, i, j, e, k):
        if X == "K":
            return two_kink("Q", i, j, e, self.pcap, None, self.dps).get((0, k), mp.mpf(0))
        return A1_taylor(j, e) if (i == 0 and k == 0) else mp.mpf(0)

    def _norm_slots(self, vals, use_internal, compare=True):
        """normalized numeric jets c[n][k][(i,j,e)], kk[n][k][(i,j,e)]: supplied value, exact
        internal C1 = A1 / K2 = Q2, or a MISSING tag with its own name (never an implicit zero)"""
        c, kk = {}, {}
        ml = monos(self.deg + 1)
        for X, ns, dst in (("C", range(1, self.nodd + 1, 2), c), ("K", range(2, self.neven + 1, 2), kk)):
            for n in ns:
                internal = bool(use_internal) and ((X == "C" and n == 1) or (X == "K" and n == 2))
                for k in range(self.kmax + 1):
                    slot = dst.setdefault(n, {}).setdefault(k, {})
                    for (i, j, e) in ml:
                        nm = norm_name(X, n, i, j, e, k)
                        if internal:
                            # documented phase-1 contract: the exact C1 = A1 / K2 = Q2 fill the slots
                            # that are NOT given; a supplied value is used (and compared)
                            x = self._internal_normalized(X, i, j, e, k)
                            if nm in vals:
                                if compare:
                                    d = abs(vals[nm].v - x) / (1 + abs(x))
                                    self.two_kink_check[nm] = d
                                    if d > mp.mpf(10) ** (-(self.dps // 2)):
                                        self.warnings.append(f"supplied {nm} differs from the exact internal value "
                                                             f"(rel. diff {mp.nstr(d, 3)}); the supplied value is used")
                                slot[(i, j, e)] = vals[nm]
                            else:
                                slot[(i, j, e)] = Val(x)
                        else:
                            slot[(i, j, e)] = vals[nm] if nm in vals else Val.missing({nm})
        return c, kk

    @staticmethod
    def _bh_tree():
        return {"b3": {(0, 0): Val(mp.mpf(1))}, "h2": {(0, 0): Val(mp.mpf(-1))}}

    # --------------------------------------------------------------- normalize
    def _normalize(self, jets):
        ml = monos(self.deg + 1)
        one = {(0, 0, 0): ONE_SERIES}
        Z = {0: one}
        for n in range(2, self.nz + 1, 2):
            Z[n] = jets[("Z", n)]
        C = {}
        for n in range(1, self.nodd + 1, 2):
            acc = jets[("A", n)]
            for m in range(2, n, 2):
                acc = jet_add(acc, jet_mul(Z[m], C[n - m], ml, self.kmax, self.pcap), ml, -1)
            C[n] = acc
        K = {}
        for n in range(2, self.neven + 1, 2):
            acc = jets[("Q", n)]
            for m in range(2, n, 2):
                acc = jet_add(acc, jet_mul(Z[m], K[n - m], ml, self.kmax, self.pcap), ml, -1)
            K[n] = acc
        return C, K

    # ------------------------------------------------------------ recurrence
    def _extract(self, C, K):
        """numeric jets c[n][k][(i,j,e)] = [eps^0 l^k] (Taylor coefficient)"""
        c, kk = {}, {}
        for n, jet in C.items():
            c[n] = {k: {m: s.coef(0, k) for m, s in jet.items()} for k in range(self.kmax + 1)}
        for n, jet in K.items():
            kk[n] = {k: {m: s.coef(0, k) for m, s in jet.items()} for k in range(self.kmax + 1)}
        return c, kk

    def _bh_from_normalized(self, c, kk):
        """solve J0 beta = R1 with (z,delta)-jets; returns dict 'b3','h4',... -> {(i,j): Val}"""
        D = self.deg
        m2 = [(i, j) for i in range(D + 1) for j in range(D + 1 - i)]
        m2p = [(i, j) for i in range(D + 2) for j in range(D + 2 - i)]

        def get(src, n, k, i, j, e):
            return src.get(n, {}).get(k, {}).get((i, j, e), Val.missing({f"<jet {n} k={k} {(i, j, e)} absent>"}))

        def J(src, n, k, e=0):          # numeric (z,delta) jet, one degree beyond D (for d/dz)
            return {(i, j): get(src, n, k, i, j, e) for (i, j) in m2p}

        def dz(A):
            return {(i, j): ((i + 1) * A[(i + 1, j)] if (i + 1, j) in A else Val.missing({"<dz truncation>"}))
                    for (i, j) in m2}

        def mul(A, B):
            out = {}
            for (i, j) in m2:
                acc = ZERO
                for i1 in range(i + 1):
                    for j1 in range(j + 1):
                        acc = acc + A[(i1, j1)] * B[(i - i1, j - j1)]
                out[(i, j)] = acc
            return out

        def add(A, B, s=1):
            return {m: A[m] + (B[m] if s == 1 else -B[m]) for m in m2}

        def cut(A):
            return {m: A[m] for m in m2}

        def scal(x, A):
            return {m: x * A[m] for m in m2}

        vjet = {m: (Val(mp.mpf(1)) if m in ((0, 0), (1, 0)) else ZERO) for m in m2}
        zero = {m: ZERO for m in m2}
        oddn = list(range(1, self.nodd + 1, 2))
        evn = list(range(2, self.neven + 1, 2))
        c0p = {n: J(c, n, 0) for n in oddn}
        k0p = {n: J(kk, n, 0) for n in evn}
        c0 = {n: cut(c0p[n]) for n in oddn}
        c1 = {n: cut(J(c, n, 1)) for n in oddn}
        cE = {n: cut(J(c, n, 0, 1)) for n in oddn}
        k0 = {n: cut(k0p[n]) for n in evn}
        k1 = {n: cut(J(kk, n, 1)) for n in evn}
        kE = {n: cut(J(kk, n, 0, 1)) for n in evn}
        jn = {n: add(scal(-2, dz(c0p[n])), cE[n]) for n in oddn}
        lam = {n: add(scal(-2, k0[n]), scal(2, mul(vjet, add(scal(-2, dz(k0p[n])), kE[n])))) for n in evn}
        b = {}
        h = {0: zero}
        for N in range(1, max(self.nodd, self.neven) + 1):
            if N % 2 == 0:
                if N > self.neven:
                    continue
                acc = k1[N]
                for n in evn:
                    if n <= N and N - n + 1 in b:
                        acc = add(acc, scal(n, mul(k0[n], b[N - n + 1])), -1)
                    if n <= N and N - n in h:
                        acc = add(acc, mul(lam[n], h[N - n]), -1)
                h[N] = acc
            else:
                if N > self.nodd:
                    continue
                acc = c1[N]
                for n in oddn:
                    if 3 <= n <= N and N - n + 1 in b:
                        acc = add(acc, scal(n, mul(c0[n], b[N - n + 1])), -1)
                for n in oddn:
                    if n <= N and N - n in h:
                        acc = add(acc, scal(2, mul(vjet, mul(jn[n], h[N - n]))), -1)
                # coefficient of b_N is c0[1] = A1|eta=0 = 1 exactly (built in)
                b[N] = acc
        out = {f"b{n}": b[n] for n in oddn}
        out.update({f"h{n}": h[n] for n in evn})
        return out

    # ------------------------------------------------------------ invariants
    def _invariants(self, bh, res):
        nT = 3 if self.order == "D4" else 4
        nD = 4
        n = 4

        def bv(name):
            return res.beta.get(name, Val.missing({f"<beta {name} not computed at order {self.order}>"}))
        Fc, Hc = {}, {}
        for key, nm in FSEC.items():
            Fc[key] = (bh["b3"][(0, 0)] if nm is None else bv(nm))
        for key, nm in HSEC.items():
            Hc[key] = bv(nm)
        # one-pair u^1 sector of H: -4 h2(z,delta)  (h2 = [l^1]Q2 = -1 identically)
        for (i, j), x in bh["h2"].items():
            if i + j <= 4 and not x.is_missing:
                Hc[(1, i, j)] = -4 * x
            elif i + j == 0:
                Hc[(1, 0, 0)] = -4 * x

        def smul(a, b_):
            r = [ZERO] * (n + 1)
            for i, x in enumerate(a):
                for j in range(n + 1 - i):
                    if i + j <= n:
                        r[i + j] = r[i + j] + x * b_[j]
            return r

        def sadd(a, b_, s=1):
            return [x + (y if s == 1 else -y) for x, y in zip(a, b_)]

        def const(x):
            return [x if isinstance(x, Val) else Val(mp.mpf(x))] + [ZERO] * n
        dl = [ZERO, Val(mp.mpf(1))] + [ZERO] * (n - 1)

        def ev(coefs, base, us, zs, du=0, dz_=0):
            tot = [ZERO] * (n + 1)
            if base == "F" and du == 0:
                if dz_ == 0:
                    tot = sadd(tot, zs)
                elif dz_ == 1:
                    tot = sadd(tot, const(1))
            if base == "H" and du == 0 and dz_ == 0:
                tot = sadd(tot, dl, -1)
            for (i, j, k), cval in coefs.items():
                if i < du or j < dz_:
                    continue
                fac = 1
                for t_ in range(du):
                    fac *= (i - t_)
                for t_ in range(dz_):
                    fac *= (j - t_)
                # skip terms that cannot reach order n (degree counting, u,z ~ delta)
                if (i - du) + (j - dz_) + k > n:
                    continue
                term = const(fac * cval if fac != 1 else cval)
                for _ in range(i - du):
                    term = smul(term, us)
                for _ in range(j - dz_):
                    term = smul(term, zs)
                for _ in range(k):
                    term = smul(term, dl)
                tot = sadd(tot, term)
            return tot
        def solve(Fc, Hc):
            """fixed point u*, z* (delta series) and T, D (eq:TD) for the jets Fc, Hc"""
            us = [ZERO] * (n + 1)
            zs = [ZERO] * (n + 1)
            F100, H100 = Fc[(1, 0, 0)], Hc[(1, 0, 0)]
            for m in range(1, n + 1):
                rF = ev(Fc, "F", us, zs)[m]
                rH = ev(Hc, "H", us, zs)[m]
                um = (-rH) / H100
                zm = -rF - F100 * um
                us[m] = us[m] + um
                zs[m] = zs[m] + zm
            Fu, Fz = ev(Fc, "F", us, zs, 1, 0), ev(Fc, "F", us, zs, 0, 1)
            Hu, Hz = ev(Hc, "H", us, zs, 1, 0), ev(Hc, "H", us, zs, 0, 1)
            onez = sadd(const(1), zs)
            T = sadd(smul(smul(const(2), us), Fu), smul(onez, Hz))
            Dd = smul(smul(smul(const(2), us), onez), sadd(smul(Fu, Hz), smul(Fz, Hu), -1))
            return T, Dd
        T, Dd = solve(Fc, Hc)
        for m in range(1, nT + 1):
            res.inv[f"T{m}"] = T[m]
        for m in range(1, nD + 1):
            res.inv[f"D{m}"] = Dd[m]
        T2, T3, D2, D3, D4 = (res.inv[x] for x in ("T2", "T3", "D2", "D3", "D4"))
        C3 = D2 - Fraction(1, 16)
        C5 = 2 * D3 - T2 * Fraction(1, 2) + C3 * C3 * Fraction(1, 4)
        res.C = {1: Val(mp.mpf(-2)), 2: Val(mp.mpf(1) / 2), 3: C3, 4: 2 * T2, 5: C5, 6: 4 * T3,
                 7: 4 * D4 - T3 - T2 * T2 + C3 * C5 * Fraction(1, 2)}
        if self.order == "C8":
            res.C[8] = 8 * res.inv["T4"]
        # eq:C8assembly: B_old (both orders) and, at C8, B_done, C8_asm, C8_partial
        res.c8, res.c8_info = c8_parts(res.beta, self.order)
        # The trace polynomial behind eq:C8assembly assumes the exact tree / one-pair data b3(0,0) = 1
        # (C3_1 = 5, i.e. A3[eps^0 l^1] = 6) and H = -delta + 4u + O(u^2) (h2 = -1 identically).  8 T4 above
        # uses the supplied data (e.g. the engine's A3[eps^0 l^1] = 5.999999999999999).  Check:
        #   (i)  C8_asm == 8 T4 recomputed with the tree data set to their exact values: an algebraic identity
        #        for ANY point (values and gradients, to working precision); a failure is a bug;
        #   (ii) report 8 T4 - 8 T4[exact tree data] = the effect of the supplied tree data's deviation.
        F100 = Fc[(1, 0, 0)]
        tree = [(F100, 1)] + [(x, 4 if key == (1, 0, 0) else 0) for key, x in Hc.items() if key[0] == 1]
        dev = max([abs(x.v - y) for x, y in tree if not x.is_missing] or [mp.mpf(0)])
        res.c8_info["tree_data_max_deviation"] = dev
        if dev > mp.mpf(10) ** -10 and self.order == "C8":
            msg = (f"b3(0,0) = {mp.nstr(F100.v, 12)} or h2 deviates from the exact tree data (b3(0,0) = 1, h2 = -1) "
                   f"by {mp.nstr(dev, 3)} (synthetic data?): eq:C8assembly / B_old then differ from 8 T4")
            if msg not in self.warnings:
                self.warnings.append(msg)
        if self.order == "C8":
            Fx = dict(Fc)
            Fx[(1, 0, 0)] = Val(mp.mpf(1))
            Hx = {key: x for key, x in Hc.items() if key[0] != 1}
            Hx[(1, 0, 0)] = Val(mp.mpf(4))
            Tx, _ = solve(Fx, Hx)
            a, t, tx = res.c8["C8_asm"], res.C[8], 8 * Tx[4]
            if not a.is_missing and not tx.is_missing:
                tol = mp.mpf(10) ** (-(mp.mp.dps - 12))
                scale = 1 + abs(res.c8["B_old8"].v) + sum(abs(C8_LINEAR[nm]) * abs(res.beta[nm].v) for nm in C8_LINEAR)
                dv = a.v - tx.v
                keys = set(a.g) | set(tx.g)
                dg = max([abs(a.g.get(k, 0) - tx.g.get(k, 0)) for k in keys] or [mp.mpf(0)])
                gs = 1 + max([abs(x) for x in tx.g.values()] or [mp.mpf(0)])
                res.c8_info["C8_asm_minus_8T4_exact_tree"] = dv
                res.c8_info["C8_asm_minus_8T4_exact_tree_gradient_max"] = dg
                if abs(dv) > tol * scale or dg > tol * scale * gs:
                    raise RuntimeError(f"internal inconsistency: eq:C8assembly differs from 8 T4 (exact tree data) by "
                                       f"{mp.nstr(dv, 5)} (gradient {mp.nstr(dg, 5)})")
                if not t.is_missing:
                    res.c8_info["8T4_minus_8T4_exact_tree"] = t.v - tx.v

    def _finish(self, c, kk, res):
        bh = self._bh_from_normalized(c, kk)
        res.bh = bh
        for nm in self.beta_names:
            w, i, j, fac = DICT[nm]
            res.beta[nm] = fac * bh[w][(i, j)]
        self._invariants(bh, res)
        return res

    # ------------------------------------------------------------ public API
    @staticmethod
    def _resolve(data, convention, cov):
        """accept a flat dict, a canonical 'lri-framework-raw/1' dict, or a path to any supported
        file; returns (entries, convention, covariance blocks, meta, n_replicates declared)"""
        meta = {}
        if isinstance(data, str):
            meta["source"] = data
            data = load_inputs(data)
        if not isinstance(data, dict):
            raise ValueError("inputs must be a dict (or a path to a JSON file)")
        if isinstance(data.get("format"), str):
            if data["format"] != CANONICAL_FORMAT:
                raise ValueError(f"unsupported input format {data['format']!r} (expected {CANONICAL_FORMAT!r})")
            fconv = data.get("convention")
            if convention is not None and fconv is not None and convention != fconv:
                raise ValueError(f"convention {convention!r} requested but the input says {fconv!r}")
            convention = convention or fconv
            for key in ("producer", "declared_zeros", "sources"):
                if data.get(key) is not None:
                    meta[key] = data[key]
            return (data.get("scalars", {}), convention or "derivative",
                    _cov_blocks(data.get("covariance")) + _cov_blocks(cov), meta, data.get("n_replicates"))
        return data, convention or "derivative", _cov_blocks(cov), meta, None

    def _parse(self, data, level, sigmas, cov, convention):
        entries, conv, blocks, meta, nrep = self._resolve(data, convention, cov)
        inp = InputSet(level, conv).parse(entries, sigmas, blocks)
        if nrep is not None and inp.block_R and int(nrep) != inp.n_rep:
            raise ValueError(f"n_replicates = {nrep} declared, but the replicate blocks have R = "
                             f"{sorted(set(inp.block_R.values()))}")
        return inp, meta

    def _attach(self, res, inp, level, strict, outputs, use_internal, meta):
        res.sig = inp.errmodel
        res.scale = dict(inp.scale)
        res.warnings = list(self.warnings)
        res.two_kink_check = dict(self.two_kink_check)
        need = set(self.required_names(None, use_internal, level))
        res.unused = sorted(set(inp.values) - need)
        res.meta = dict(meta)
        res.meta.update({"order": self.order, "dps": self.dps, "level": level, "convention": inp.convention,
                         "strict": bool(strict), "strict_outputs": list(outputs) if outputs else "all",
                         "n_inputs": len(inp.values), "n_required": len(need),
                         "n_replicated": len(inp.reps), "n_replicates": inp.n_rep,
                         "replicate_blocks": len(inp.block_R),
                         "replicates_per_block": sorted(set(inp.block_R.values())),
                         "exact_inputs": sorted(inp.exact), "explicitly_absent": sorted(inp.absent),
                         "error_model": {"independent_or_floor": len(inp.errmodel.sig),
                                         "systematic_floors": len(inp.sys),
                                         "covariance_blocks": [len(b[0]) for b in inp.errmodel.blocks],
                                         "replicate_blocks": len(inp.errmodel.rep_blocks),
                                         "replicated_in_replicate_blocks": inp.errmodel.n_replicated}})
        return res

    def _assemble_raw(self, values, track, use_internal, keep_normalized, compare, fill_missing=True):
        if compare:
            self.warnings = []
            self.two_kink_check = {}
        vals = {nm: Val.input(nm, x, track) for nm, x in values.items()}
        jets = self._raw_jets(vals, use_internal, compare, fill_missing)
        C, K = self._normalize(jets)
        c, kk = self._extract(C, K)
        res = Result()
        if keep_normalized:
            for src, lab in ((c, "C"), (kk, "K")):
                for n, byk in src.items():
                    for k, jet in byk.items():
                        for (i, j, e), x in jet.items():
                            # store as DERIVATIVES (multiply Taylor coefficient by i! j!)
                            res.normalized[norm_name(lab, n, i, j, e, k)] = x * (math.factorial(i) * math.factorial(j))
        return self._finish(c, kk, res)

    def from_raw(self, raw, sigmas=None, cov=None, convention=None, use_internal_two_kink=True,
                 strict=True, outputs=None, track=True, keep_normalized=True):
        """raw: {name: value | [value, sigma] | {"value","sigma","exact"} | {"reps": [...]} | None},
        a canonical 'lri-framework-raw/1' dict, or a path to any supported file (INPUT_FORMAT.md).
        sigmas: {name: sigma} (independent);  cov: {"names", "matrix"} or a list of such blocks.
        strict (default): raise MissingInputError unless every input that `outputs` (default: all
        beta inputs and C3..C7/C8) needs is supplied.  strict=False: MISSING outputs instead.
        Replicated entries enter with their mean; their sample covariance gives the error
        (use from_replicates for the per-replicate assembly).  Returns Result."""
        with mp.workdps(self.dps):
            inp, meta = self._parse(raw, "raw", sigmas, cov, convention)
            if strict:
                self.check_inputs(inp.values, outputs, use_internal_two_kink, "raw")
            res = self._assemble_raw(inp.values, track, use_internal_two_kink, keep_normalized, compare=True)
            return self._attach(res, inp, "raw", strict, outputs, use_internal_two_kink, meta)

    def from_replicates(self, raw, sigmas=None, cov=None, convention=None, use_internal_two_kink=True,
                        strict=True, outputs=None, keep_normalized=False, mixed_R="refuse"):
        """full nonlinear assembly once per QMC replicate (INPUT_FORMAT.md, sec. 3a).
        Replicate r uses x_r for every replicated scalar and the fixed value for every other one.
        Replicate blocks must share one R (replicates of different blocks are independent, so pairing
        them by index is valid; within a block, index r is one random shift), unless mixed_R="group":
        then the blocks are grouped by R and each group g is assembled R_g times with only its own
        scalars varied (the others at their means); rep_se^2 = sum_g se_g^2 (the groups are independent),
        nonlinearity = sum_g (mean_g - value), rep_mean = value + nonlinearity, and the degrees of freedom
        are the Welch-Satterthwaite value (stats['dof']).  mixed_R="refuse" (default) raises instead.
        Returns ReplicateResult with, per output: value (assembly at the means), sigma_linear
        (exact gradients with the per-block sample covariance of the replicated means, the systematic
        floors and the fixed errors), rep_mean and rep_se (mean and sd/sqrt(R) of the R assemblies),
        sigma_extra (linear error of what the replicates do not carry: fixed scalars and systematic
        floors), sigma_rep_total = sqrt(rep_se^2 + sigma_extra^2), nonlinearity = rep_mean - value."""
        with mp.workdps(self.dps):
            inp, meta = self._parse(raw, "raw", sigmas, cov, convention)
            R = inp.n_rep
            if mixed_R not in ("refuse", "group"):
                raise ValueError("mixed_R must be 'refuse' or 'group'")
            if R is None and mixed_R == "group":
                return self._from_replicates_grouped(inp, meta, strict, outputs, use_internal_two_kink,
                                                     keep_normalized)
            if R is None:
                raise ValueError("the replicate blocks have different numbers of replicates "
                                 f"{sorted(set(inp.block_R.values()))}: the per-replicate assembly needs one R; "
                                 "use from_raw (linear errors with the per-block sample covariances), or "
                                 "mixed_R='group' (per-replicate assembly grouped by R)")
            if R < 2:
                raise ValueError("from_replicates needs replicated scalars ({'reps': [...]}, R >= 2)")
            if strict:
                self.check_inputs(inp.values, outputs, use_internal_two_kink, "raw")
            central = self._assemble_raw(inp.values, True, use_internal_two_kink, keep_normalized, compare=True)
            self._attach(central, inp, "raw", strict, outputs, use_internal_two_kink, meta)
            fixed = inp.fixed_names
            extra_model = inp.errmodel.restricted(keep_sig=inp.errmodel.sig, keep_blocks=fixed, keep_reps=None)
            cross = inp.errmodel.cross_terms(fixed)
            couts = central.outputs()
            per = {o: [] for o in couts}
            complete = not (set(self.required_names(None, use_internal_two_kink, "raw")) - set(inp.values))
            for r in range(R):
                vals = dict(inp.values)
                for nm, reps in inp.reps.items():
                    vals[nm] = reps[r]
                # when every required scalar (all outputs) is present, unsupplied slots cannot reach
                # any output, so they need no MISSING tags (identical outputs, faster)
                rr = self._assemble_raw(vals, False, use_internal_two_kink, False, compare=False,
                                        fill_missing=not complete)
                for o, x in rr.outputs().items():
                    per[o].append(None if x.is_missing else x.v)
            stats = {}
            for o, x in couts.items():
                xs = per[o]
                if x.is_missing or any(v is None for v in xs):
                    stats[o] = {"missing": sorted(x.miss) if x.is_missing else ["<missing in a replicate>"]}
                    continue
                m = sum(xs) / R
                sd = mp.sqrt(sum((v - m) ** 2 for v in xs) / (R - 1))
                se = sd / mp.sqrt(R)
                sx = mp.sqrt(extra_model.variance(x.g))
                stats[o] = {"value": x.v, "sigma_linear": x.sigma(inp.errmodel), "rep_mean": m, "rep_se": se,
                            "sigma_extra": sx, "sigma_rep_total": mp.sqrt(se ** 2 + sx ** 2),
                            "nonlinearity": m - x.v, "n_rep": R}
            ratios = [v for v in inp.rep_sigma_ratio.values() if v is not None]
            rmeta = dict(central.meta)
            rmeta.update({"mode": "per-replicate assembly", "n_replicates": R, "dof": R - 1,
                          "n_fixed": len(fixed), "n_systematic_floors": len(inp.sys),
                          "fixed_replicated_cross_covariance_dropped": mp.nstr(cross, 3),
                          "given_sigma_over_replicate_se": (None if not ratios else
                                                            {"min": mp.nstr(min(ratios), 3),
                                                             "max": mp.nstr(max(ratios), 3)})})
            if cross != 0:
                central.warnings.append("covariance between fixed and replicated scalars is not representable "
                                        "in the per-replicate errors and was dropped from sigma_extra")
            return ReplicateResult(central, per, stats, rmeta)

    def _from_replicates_grouped(self, inp, meta, strict, outputs, use_internal, keep_normalized):
        """per-replicate assembly with replicate blocks of different R (see from_replicates)"""
        groups = {}
        for nm in inp.reps:
            groups.setdefault(inp.block_R[inp.rep_block[nm]], []).append(nm)
        if min(groups) < 2:
            raise ValueError("from_replicates needs replicated scalars ({'reps': [...]}, R >= 2)")
        if strict:
            self.check_inputs(inp.values, outputs, use_internal, "raw")
        central = self._assemble_raw(inp.values, True, use_internal, keep_normalized, compare=True)
        self._attach(central, inp, "raw", strict, outputs, use_internal, meta)
        fixed = inp.fixed_names
        extra_model = inp.errmodel.restricted(keep_sig=inp.errmodel.sig, keep_blocks=fixed, keep_reps=None)
        cross = inp.errmodel.cross_terms(fixed)
        couts = central.outputs()
        complete = not (set(self.required_names(None, use_internal, "raw")) - set(inp.values))
        per = {o: {} for o in couts}
        for Rg in sorted(groups):
            for o in couts:
                per[o][f"R{Rg}"] = []
            for r in range(Rg):
                vals = dict(inp.values)
                for nm in groups[Rg]:
                    vals[nm] = inp.reps[nm][r]
                rr = self._assemble_raw(vals, False, use_internal, False, compare=False, fill_missing=not complete)
                for o, x in rr.outputs().items():
                    per[o][f"R{Rg}"].append(None if x.is_missing else x.v)
        stats = {}
        for o, x in couts.items():
            if x.is_missing or any(v is None for xs in per[o].values() for v in xs):
                stats[o] = {"missing": sorted(x.miss) if x.is_missing else ["<missing in a replicate>"]}
                continue
            var, nonlin, w = mp.mpf(0), mp.mpf(0), mp.mpf(0)
            for key, xs in per[o].items():
                Rg = len(xs)
                m = sum(xs) / Rg
                v2 = sum((v - m) ** 2 for v in xs) / (Rg - 1) / Rg
                var += v2
                w += v2 ** 2 / (Rg - 1)
                nonlin += m - x.v
            se = mp.sqrt(var)
            sx = mp.sqrt(extra_model.variance(x.g))
            stats[o] = {"value": x.v, "sigma_linear": x.sigma(inp.errmodel), "rep_mean": x.v + nonlin, "rep_se": se,
                        "sigma_extra": sx, "sigma_rep_total": mp.sqrt(se ** 2 + sx ** 2), "nonlinearity": nonlin,
                        "n_rep": "+".join(str(R_) for R_ in sorted(groups)),
                        "dof": (var ** 2 / w) if w > 0 else None}
        ratios = [v for v in inp.rep_sigma_ratio.values() if v is not None]
        rmeta = dict(central.meta)
        rmeta.update({"mode": "per-replicate assembly grouped by R", "n_replicates": None,
                      "replicate_groups": {f"R{Rg}": len(nms) for Rg, nms in sorted(groups.items())},
                      "dof": "Welch-Satterthwaite per output (stats[o]['dof'])",
                      "n_fixed": len(fixed), "n_systematic_floors": len(inp.sys),
                      "fixed_replicated_cross_covariance_dropped": mp.nstr(cross, 3),
                      "given_sigma_over_replicate_se": (None if not ratios else
                                                        {"min": mp.nstr(min(ratios), 3),
                                                         "max": mp.nstr(max(ratios), 3)})})
        if cross != 0:
            central.warnings.append("covariance between fixed and replicated scalars is not representable "
                                    "in the per-replicate errors and was dropped from sigma_extra")
        return ReplicateResult(central, per, stats, rmeta)

    def from_normalized(self, norm, sigmas=None, cov=None, convention=None, use_internal_two_kink=True,
                        strict=True, outputs=None, track=True):
        """norm: {'C3_vv[l^1]': value | [value, sigma] | ...}  ([eps^0 l^k] of the derivative of the
        normalized response).  K2 (=Q2) and C1 (=A1) are filled from the exact sector unless given
        (given values are used and compared, see warnings).  strict: every normalized coefficient
        that the outputs need, other than K2 and C1, must be given."""
        with mp.workdps(self.dps):
            inp, meta = self._parse(norm, "normalized", sigmas, cov, convention)
            if strict:
                self.check_inputs(inp.values, outputs, use_internal_two_kink, "normalized")
            self.warnings = []
            self.two_kink_check = {}
            vals = {nm: Val.input(nm, x, track) for nm, x in inp.values.items()}
            c, kk = self._norm_slots(vals, use_internal_two_kink, compare=True)
            res = self._finish(c, kk, Result())
            return self._attach(res, inp, "normalized", strict, outputs, use_internal_two_kink, meta)

    def from_beta(self, beta, sigmas=None, cov=None, strict=True, outputs=None, track=True):
        """beta: {'a': value | [value, sigma] | ...}; computes the invariants and C_n only."""
        with mp.workdps(self.dps):
            inp, meta = self._parse(beta, "beta", sigmas, cov, None)
            if strict:
                self.check_inputs(inp.values, outputs, True, "beta")
            self.warnings = []
            self.two_kink_check = {}
            res = Result()
            for nm in self.beta_names:
                res.beta[nm] = Val.input(nm, inp.values[nm], track) if nm in inp.values else Val.missing({nm})
            self._invariants(self._bh_tree(), res)
            return self._attach(res, inp, "beta", strict, outputs, True, meta)



# ============================================================================
#  adapters  (formats: INPUT_FORMAT.md)
# ============================================================================

SPEC_ATOM_RE = re.compile(r"^(E?)([AZQ])(\d+)_(base|[vd]+)$")
GROUP_RE = re.compile(r"^([AZQ])(\d+)(?:_(base|[vdE]+))?$")


def spec_atom_to_prefix(atom):
    """'EA5_vd' -> 'A5_vdE' ; 'Q8_base' -> 'Q8' (naming of spec/scripts/assemble_from_raw.py)"""
    m = SPEC_ATOM_RE.match(atom)
    if not m:
        raise ValueError(f"not a spec raw atom: {atom!r}")
    E, M, n, der = m.groups()
    der = "" if der == "base" else der
    ds = deriv_str(der.count("v"), der.count("d"), 1 if E else 0)
    return f"{M}{n}" + (f"_{ds}" if ds else "")


def prefix_to_spec_atom(M, n, i, j, e):
    """('A', 5, 1, 1, 1) -> 'EA5_vd' ; ('Q', 8, 0, 0, 0) -> 'Q8_base'"""
    return ("E" if e else "") + f"{M}{n}_" + (("v" * i + "d" * j) or "base")


def group_to_prefix(group):
    """engine group name ('A3_base', 'A5_vE', 'Q4_dE', also with a run suffix '_N16001') or spec
    atom ('EA5_vd') -> flat prefix"""
    group = re.sub(r"_N\d+$", "", group)
    if SPEC_ATOM_RE.match(group) and group.startswith("E"):
        return spec_atom_to_prefix(group)
    m = GROUP_RE.match(group)
    if not m:
        raise ValueError(f"cannot parse group name {group!r}")
    M, n, der = m.groups()
    der = "" if der in (None, "base") else der
    i, j, e = parse_deriv(der)
    ds = deriv_str(i, j, e)
    return f"{M}{n}" + (f"_{ds}" if ds else "")


def load_spec_raw(src):
    """Convert the spec agent's raw-coefficient JSON
         {"A3_base": {"-1": {"0": "...", "1": "..."}, ...}, "EA5_vd": {...}, ...}
    (or the archive layout {"raw": {atom: {p: {"coefficients_by_log_power": {...}}}}})
    into this module's flat naming {"A3[eps^-1 l^0]": "...", ...}.
    Values may be strings/numbers or [value, sigma] pairs.  null values are KEPT as None and count
    as absent (strict mode raises if a required one is null; they are never zeros)."""
    d = json.load(open(src)) if isinstance(src, str) else src
    if "raw" in d and isinstance(d["raw"], dict):
        d = {atom: {p: rec.get("coefficients_by_log_power", rec) for p, rec in ps.items()}
             for atom, ps in d["raw"].items()}
    out = {}
    for atom, ps in d.items():
        pref = spec_atom_to_prefix(atom)
        for p, ks in ps.items():
            for k, val in ks.items():
                out[f"{pref}[eps^{int(p)} l^{int(k)}]"] = val
    return out


def load_engine_results(src):
    """engine campaign results.json -> canonical dict (INPUT_FORMAT.md sec. 3c).
    v2 collect output (engine_pipeline 'v2'):
        {"results": {group: {"k,j": [mean, err]}}, "replicates": {group: {"k,j": [x_1..x_R]}},
         "errors": {group: {"k,j": {"stat", "floor", "block", "zero"?, ...}}},
         "zeros": [flat names] (or the earlier draft "structural_zeros": ["group:k,j"]),
         "complete", "problems", ...}
      -> replicated entries {"reps", "mean", "sigma": stat, "sys": floor, "block"}; structural zeros
         (errors[...]['zero'], 'zeros', 'structural_zeros') -> exact zeros.  Different jobs (blocks)
         use independent random streams.  (The engine also writes framework_input.json directly in
         the canonical format.)
    phase-1 output {"results": {group: {"k,j": [mean, err]}}} -> [mean, err] (independent errors).
    Also accepted: "zeros": [flat names] (proved structural zeros)."""
    d = json.load(open(src)) if isinstance(src, str) else src
    res = d.get("results")
    if not isinstance(res, dict):
        raise ValueError("engine results: no 'results' object")
    reps = d.get("replicates") or {}
    errs = d.get("errors") or {}
    szeros = set(d.get("structural_zeros") or [])
    scal, zeros, Rs = {}, [], set()
    groups = list(res) + [g for g in reps if g not in res]
    for grp in groups:
        pref = group_to_prefix(grp)
        keys = list(res.get(grp, {})) + [k for k in reps.get(grp, {}) if k not in res.get(grp, {})]
        for key in keys:
            k, j = (int(x) for x in key.split(","))
            name = f"{pref}[eps^{k} l^{j}]"
            if name in scal:
                raise ValueError(f"engine results: {name} appears twice (group {grp})")
            if f"{grp}:{key}" in szeros or (errs.get(grp, {}).get(key) or {}).get("zero"):
                ve = res.get(grp, {}).get(key)
                if ve is not None and float(ve[0]) != 0:
                    raise ValueError(f"engine results: structural zero {name} has the value {ve[0]}")
                scal[name] = {"value": "0", "sigma": "0", "exact": True}
                zeros.append(name)
                continue
            ve = res.get(grp, {}).get(key)
            rl = reps.get(grp, {}).get(key)
            ex = errs.get(grp, {}).get(key) or {}
            if rl is not None and len(rl) >= 2:
                ent = {"reps": list(rl)}
                if ve is not None:
                    ent["mean"] = ve[0]
                if ex.get("stat") is not None:
                    ent["sigma"] = ex["stat"]
                if ex.get("floor"):
                    ent["sys"] = ex["floor"]
                if ex.get("block") is not None:
                    ent["block"] = ex["block"]
                Rs.add(len(rl))
                scal[name] = ent
            elif ve is not None:
                scal[name] = [ve[0], ve[1]] if isinstance(ve, (list, tuple)) else ve
            else:
                scal[name] = None
    for z in d.get("zeros") or []:
        cz = canonical_raw_name(z)
        if cz in scal:
            ent = _entry(cz, scal[cz])
            if ent is not None and ("reps" in ent or ent["value"] != 0):
                raise ValueError(f"engine results: {cz} is listed as a structural zero but has a nonzero value")
        scal[cz] = {"value": "0", "sigma": "0", "exact": True}
        if cz not in zeros:
            zeros.append(cz)
    producer = {"component": "engine", "source": src if isinstance(src, str) else "<dict>"}
    for key in ("engine_pipeline", "floor_rel", "complete", "problems"):
        if key in d:
            producer[key] = d[key]
    out = {"format": CANONICAL_FORMAT, "convention": "derivative", "scalars": scal, "producer": producer}
    if len(Rs) == 1:
        out["n_replicates"] = Rs.pop()
    if zeros:
        out["declared_zeros"] = zeros
    return out


def _detect_format(d):
    if isinstance(d.get("format"), str):
        return "canonical"
    if isinstance(d.get("results"), dict):
        return "engine"
    if "raw" in d and isinstance(d["raw"], dict):
        return "spec"
    keys = [k for k in d if not k.startswith("_")]
    if keys and all(RAW_RE.match(k) for k in keys):
        return "flat"
    if keys and all(SPEC_ATOM_RE.match(k) for k in keys):
        return "spec"
    raise ValueError("cannot detect the input format (see INPUT_FORMAT.md)")


def load_inputs(src, fmt="auto"):
    """any supported raw-level file/dict -> canonical dict {'format', 'convention', 'scalars', ...}"""
    d = json.load(open(src)) if isinstance(src, str) else src
    if fmt == "auto":
        fmt = _detect_format(d)
    if fmt == "canonical":
        if d.get("format") != CANONICAL_FORMAT:
            raise ValueError(f"unsupported format {d.get('format')!r}")
        out = dict(d)
    elif fmt == "engine":
        out = load_engine_results(d)
    elif fmt == "spec":
        out = {"format": CANONICAL_FORMAT, "convention": None, "scalars": load_spec_raw(d)}
    elif fmt == "flat":
        out = {"format": CANONICAL_FORMAT, "convention": None,
               "scalars": {k: v for k, v in d.items() if not k.startswith("_")}}
    else:
        raise ValueError(f"unknown format {fmt!r}")
    if isinstance(src, str):
        out.setdefault("sources", [src])
    return out


def _rep_blocks_of(item):
    out = set()
    for v in (item.get("scalars") or {}).values():
        if isinstance(v, dict) and "reps" in v:
            out.add(str(v.get("block", DEFAULT_REP_BLOCK)))
    return out


def merge_inputs(items, zeros=(), independent=None):
    """merge canonical dicts (load_inputs) into one; a name supplied twice is an error.
    zeros: names declared exact zeros by hand (recorded as 'declared_zeros').
    Replicate blocks: a block id that occurs in more than one item would make the error model pair
    their replicates as one random shift.  independent=True renames every block of item i to
    '<tag_i>:<block>' (items from independent runs, e.g. the production and a later C8 run);
    independent=False keeps the ids (the items are parts of one run); independent=None (default)
    raises if a block id is shared."""
    items = list(items)
    blocks = [_rep_blocks_of(it) for it in items]
    shared = sorted({b for i, bi in enumerate(blocks) for bj in blocks[i + 1:] for b in bi & bj})
    if shared and independent is None:
        raise ValueError(f"replicate block id(s) {shared[:5]}{' ...' if len(shared) > 5 else ''} occur in more than "
                         "one input; pass independent=True (CLI --independent-files) if the inputs come from "
                         "independent runs (blocks are then renamed per input), or independent=False if they are "
                         "parts of one run")
    if independent:
        tags, renamed = [], []
        for i, it in enumerate(items):
            src = (it.get("sources") or [None])[0]
            tag = os.path.splitext(os.path.basename(src))[0] if isinstance(src, str) else f"input{i}"
            while tag in tags:
                tag = f"{tag}_{i}"
            tags.append(tag)
            new = dict(it)
            new["scalars"] = {k: ({**v, "block": f"{tag}:{v.get('block', DEFAULT_REP_BLOCK)}"}
                                  if isinstance(v, dict) and "reps" in v else v)
                              for k, v in (it.get("scalars") or {}).items()}
            renamed.append(new)
        items = renamed
    scal, cov, conv, nrep, sources, declared, producers = {}, [], None, None, [], [], []
    for it in items:
        c = it.get("convention")
        if c is not None:
            if conv is not None and c != conv:
                raise ValueError(f"inputs use different conventions ({conv!r}, {c!r})")
            conv = c
        if it.get("n_replicates") is not None:
            if nrep is not None and int(it["n_replicates"]) != nrep:
                if not independent:
                    raise ValueError("inputs declare different numbers of replicates (independent runs: "
                                     "independent=True, then from_replicates(..., mixed_R='group'))")
                nrep = -1
            elif nrep != -1:
                nrep = int(it["n_replicates"])
        for name, v in it.get("scalars", {}).items():
            cn = canonical_raw_name(name)
            if cn in scal:
                raise ValueError(f"{cn} is supplied by more than one input")
            scal[cn] = v
        cov += _cov_blocks(it.get("covariance"))
        sources += it.get("sources", [])
        declared += it.get("declared_zeros", [])
        if it.get("producer") is not None:
            producers.append(it["producer"])
    for z in zeros:
        cz = canonical_raw_name(z)
        if cz in scal and _entry(cz, scal[cz]) is not None:
            raise ValueError(f"{cz} is declared zero (--zero) but is also supplied")
        scal[cz] = {"value": "0", "sigma": "0", "exact": True}
        declared.append(cz)
    out = {"format": CANONICAL_FORMAT, "convention": conv, "scalars": scal,
           "covariance": [{"names": n, "matrix": C} for n, C in cov]}
    if nrep is not None and nrep != -1:
        out["n_replicates"] = nrep
    if sources:
        out["sources"] = sources
    if declared:
        out["declared_zeros"] = declared
    if producers:
        out["producer"] = producers if len(producers) > 1 else producers[0]
    return out


# ============================================================================
#  convenience
# ============================================================================

def c8_combine(res, extra=None, dps=50):
    """eq:C8assembly pieces (B_old8, B_done8, C8_asm, C8_partial) from an assembly `res` (Result or
    ReplicateResult, order D4 or C8) plus optional beta-level values of NEW inputs from another, independent
    source (e.g. the framework's own semi-analytic W).
      extra: {name: value | [value, sigma] | {"value", "sigma"}} -- only for new inputs that are absent
             (not computed, or MISSING) in res; giving one that res has is an error.
    Missing new inputs are never zeros: they make B_done8 / C8_asm MISSING and are listed as missing terms
    of C8_partial.  Errors: linear propagation (the raw error model of res, plus the extra sigmas, which are
    independent of it); for a ReplicateResult also the per-replicate values (the extras held fixed) with
    rep_se, sigma_extra (fixed raw scalars, floors and the extras) and sigma_rep_total.
    Returns {"parts": {name: {...}}, "terms": {name: {...}}, "partial_missing": [...]}."""
    with mp.workdps(dps):
        rep = isinstance(res, ReplicateResult)
        cen = res.central if rep else res
        extra = dict(extra or {})
        bad = set(extra) - set(C8_LINEAR)
        if bad:
            raise ValueError(f"extra beta inputs must be new C8 inputs {sorted(C8_LINEAR)}, not {sorted(bad)}")
        beta = dict(cen.beta)
        src, xsig = {}, {}
        for nm in C8_LINEAR:
            have = nm in beta and not beta[nm].is_missing
            if nm in extra:
                if have:
                    raise ValueError(f"{nm} is given in extra but the assembly already computes it")
                ent = _entry(nm, extra[nm])
                if ent is None or "reps" in ent:
                    raise ValueError(f"extra {nm}: give a value (and sigma)")
                key = f"extra:{nm}"
                beta[nm] = Val.input(key, ent["value"])
                if ent["sigma"]:
                    xsig[key] = ent["sigma"]
                src[nm] = "extra"
            else:
                src[nm] = "assembly" if have else "MISSING"
                if not have:
                    beta[nm] = beta.get(nm) or Val.missing({f"<{nm} not computed at order {cen.meta.get('order')}>"})
        parts, info = c8_parts(beta, "C8")
        em = ErrorModel(dict(cen.sig.sig, **xsig), cen.sig.blocks, cen.sig.rep_blocks)
        out = {"parts": {}, "terms": {}, "partial_missing": sorted(info["partial_missing"]),
               "partial_included": info["terms_included"]}
        for nm, c in C8_LINEAR.items():
            x = beta[nm]
            e = {"source": src[nm], "coefficient": str(c)}
            if x.is_missing:
                e["missing"] = sorted(x.miss)[:8]
            else:
                e.update(value=x.v, sigma=mp.sqrt(em.variance(x.g)), contribution=x.v * mp.mpf(c.numerator) / c.denominator)
            out["terms"][nm] = e
        # per-replicate values (extras fixed)
        per = None
        if rep:
            per = {}
            pr = res.per_rep
            some = pr[next(iter(pr))]
            layout = list(some.keys()) if isinstance(some, dict) else [None]
            for g in layout:
                n = len(some[g]) if g is not None else len(some)
                for r in range(n):
                    br = {}
                    for nm in list(BETA_NAMES_D4) + list(C8_LINEAR):
                        if src.get(nm) == "extra":
                            br[nm] = Val(beta[nm].v)
                            continue
                        xs = pr.get(nm)
                        v = None if xs is None else (xs[g][r] if g is not None else xs[r])
                        br[nm] = Val(v) if v is not None else Val.missing({nm})
                    pp, _ = c8_parts(br, "C8")
                    for k, x in pp.items():
                        per.setdefault(k, {}).setdefault(g, []).append(None if x.is_missing else x.v)
        fixed_model = None
        if rep:
            # what the replicates do not carry: independent sigmas and floors, covariance blocks of the fixed
            # scalars (as in from_replicates), and the extras
            fixed = set(cen.sig.names()) - {k for _, d in cen.sig.rep_blocks.values() for k in d}
            fm = cen.sig.restricted(keep_sig=cen.sig.sig, keep_blocks=fixed, keep_reps=None)
            fixed_model = ErrorModel(dict(fm.sig, **xsig), fm.blocks, {})
        for k, x in parts.items():
            if x.is_missing:
                out["parts"][k] = {"missing": sorted(x.miss)[:12]}
                continue
            e = {"value": x.v, "sigma_linear": mp.sqrt(em.variance(x.g)), "doc": C8_PARTS_DOC[k]}
            if k == "C8_partial":
                e["missing_terms"] = sorted(info["partial_missing"])
            if rep and per is not None and k in per and all(v is not None for xs in per[k].values() for v in xs):
                var, nonlin, w = mp.mpf(0), mp.mpf(0), mp.mpf(0)
                for g, xs in per[k].items():
                    R = len(xs)
                    m = sum(xs) / R
                    v2 = sum((v - m) ** 2 for v in xs) / (R - 1) / R
                    var, w, nonlin = var + v2, w + v2 ** 2 / (R - 1), nonlin + m - x.v
                sx = mp.sqrt(fixed_model.variance(x.g))
                e.update(rep_mean=x.v + nonlin, rep_se=mp.sqrt(var), sigma_extra=sx,
                         sigma_rep_total=mp.sqrt(var + sx ** 2), nonlinearity=nonlin,
                         dof=(var ** 2 / w) if w > 0 else None)
            out["parts"][k] = e
        return out


def closed_forms(dps=50):
    """closed forms of the old inputs (note lines 516-521, 580-584) and target values
    (computed at `dps` digits; the global mpmath precision is not changed)"""
    with mp.workdps(dps):
        z2, z3, z4, z5, z6 = (mp.zeta(n) for n in range(2, 7))
        L2, L3 = mp.log(2), mp.log(3)
        Li2h = mp.polylog(2, -mp.mpf(1) / 2)
        Li4h = mp.polylog(4, mp.mpf(1) / 2)
        beta = {
            "a": -4 * z2, "c": mp.mpf(-16), "p": 8 - 2 * z2 - 7 * z3 - 8 * L2,
            "b": -18 - 6 * z2 + mp.mpf(28) / 3 * z3 + 32 * L2 - 12 * L3 - 4 * L2 ** 2 - 8 * Li2h,
            "f": 32 - mp.mpf(136) / 3 * z3 - 64 * L2 + 48 * L3 + 16 * L2 ** 2 + 32 * Li2h,
            "A": -8 - 4 * z2 - 2 * z3 + 16 * L2,
            "E": (-16 + 14 * z2 - 22 * z3 + 12 * z4 + 8 * L2 - 8 * L2 ** 2 - 16 * Li4h - 14 * z3 * L2
                  + 4 * z2 * L2 ** 2 - mp.mpf(2) / 3 * L2 ** 4),
        }
        targets = {
            "D2": mp.mpf(5) / 2 + 2 * z2, "T2": 2 - 2 * z2 - 4 * z3,
            "D3": mp.mpf(21) / 4 - 13 * z2 + 11 * z3 + 11 * z4,
            "T3": (26 - 38 * z2 + 104 * z3 - 80 * z4 - 272 * z5 + 112 * z2 * z3) / 4,
            "D4": (13 - mp.mpf(179) / 8 * z2 + mp.mpf(47) / 2 * z3 - mp.mpf(493) / 8 * z4 + 289 * z5
                   - 130 * z2 * z3 + mp.mpf(499) / 4 * z6 - 76 * z3 ** 2),
            "C3": mp.mpf(39) / 16 + 2 * z2, "C4": 4 - 4 * z2 - 8 * z3,
            "C5": mp.mpf(11249) / 1024 - mp.mpf(361) / 16 * z2 + 24 * z3 + mp.mpf(49) / 2 * z4,
            "C6": 26 - 38 * z2 + 104 * z3 - 80 * z4 - 272 * z5 + 112 * z2 * z3,
            "C7": (mp.mpf(1798583) / 32768 - mp.mpf(90637) / 1024 * z2 + mp.mpf(453) / 4 * z3
                   - mp.mpf(16835) / 64 * z4 + 1224 * z5 - 540 * z2 * z3 + mp.mpf(4335) / 8 * z6 - 320 * z3 ** 2),
        }
    return beta, targets


if __name__ == "__main__":
    fw = Framework("D4", dps=30)
    need = fw.required_inputs()
    allnames = sorted({x for v in need.values() for x in v})
    print(f"{len(allnames)} raw coefficients needed for order D4 (internal two-kink sector used).")
    for o, lst in need.items():
        print(f"  {o}: {len(lst)}")
