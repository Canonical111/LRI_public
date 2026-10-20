#!/usr/bin/env python3
"""tools/margin_probe8.py: the L8 margin re-derivation (RECON "Margin re-derivation", steps (a)-(e); user decision
2026-10-08). The package form of gen3/margin_probe.py (the C7(3), L <= 7 research script, cd3:margin_probe), for any
loop L <= 8, reading every payload through the package's member reader. Read-only on the inputs; it never plans,
submits or changes a production value. Its verdicts are evidence for the user's decision (RECON (e)): a lower proposal
rate for a graph is a pre-registered change the user must approve.

  select    pick the graphs to probe from the pilot report (default: the committed
            benchmarks/symmetry_2026-10-c8/pilot/evidence/pilot_report.json and its sigma_cost.csv). Per sector the
            PC-confirmed "possible infinite variance" graphs (action2_confirm), ranked by variance share (--rank-by;
            see shares()), the top --top (default 12); --controls light controls (default 2: PC-checked graphs not
            confirmed, no double-lift subset, cost M T at most the median of the unconfirmed, lowest two-campaign
            xi(32,768)); --class-reps K adds the K highest-ranked members of each action-3b double-lift class not
            already chosen. Writes a selection JSON (schema c8-d3-margin-selection-1): every graph's id, role, reason,
            share, xi_a / xi_b / face-model xi_b, M, T, double-lift and clamped counts (inputs/d3/rate_audit_L8.json).
  probe     steps (a)-(d) for the graphs of a selection (--selection) or a list (--graphs sector:L:id,...), over
            --workers processes (default: the CPUs this process may use), one JSON per graph in --out (schema
            c8-d3-margin-probe-graph-1; never overwritten, --skip-existing resumes) and probe_run.json.
  report    the per-graph JSONs of one or more probe directories as a markdown summary (and --json).
  estimate  core-seconds per graph of a selection from the timings of earlier probe runs (--calibration).

Usage:
  python3 -B tools/margin_probe8.py select --out SEL.json [--pilot-report R] [--sigma-cost CSV] [--top 12]
      [--controls 2] [--class-reps 0] [--rank-by share|share_pf|xi] [--inputs DIR]
  python3 -B tools/margin_probe8.py probe (--selection SEL.json | --graphs power:7:228,...) --out DIR [--workers N]
      [--inputs DIR] [--xi XI.json] [--anchors A.json] [--tight-anchors 4] [--max-flags 40000] [--max-chains 20000]
      [--depth 40] [--tol 0.02] [--skip-existing]
  python3 -B tools/margin_probe8.py report DIR [DIR ...] [--out SUMMARY.md] [--json SUMMARY.json]
  python3 -B tools/margin_probe8.py estimate --selection SEL.json --calibration DIR [DIR ...] [--speed 1.5] [--cores 64]

The probe (RECON:1357-1376; margin_probe.py [M1]-[M3]):
  (a) the d=3 rate line recomputed from the payload's masks and forest terms (regenerate_rates.cpp:16, margin_probe
      [M1]): per term p4 = 3|s| + 4 nu_N - 6 h, a non-positive p4 lifted into (0, 4] quarter units, the minimum over
      terms; compared with the payload's rate line at every subset, its raw line with the package's own
      prepare_inputs.raw_valuations, its double-lift count (raw <= -5) with the inventory's.
  (b) single scale: at every clamped subset s (raw <= 0) the exponent of the forest sum
      f = prod x^(-1/4) sum_T N_T / (S U_T^(3/2)) along x_e -> t x_e (e in s), |s| + d ln|f| / d ln t, at margin_probe's
      base point (y_e/1000, y_e = numpy default_rng(3).integers(500, 2000, E)) between t = 1e-10 and 1e-14 (margin_probe's
      two scalings: the "shallow" exponent, reported for comparison with its record) and on the depth ladder below.
      Compared with the table rate alpha (the payload's) and the proposal rates 0.8 alpha (campaign a) and 0.7 alpha
      (campaign b). An exponent below alpha contradicts the single-scale bound (RECON:1360-1364) and is listed apart.
  (c) multi scale: two-scale flags S1 < S2 with an anchor as the inner or the outer set (every proper non-empty subset
      of the anchor, every proper superset below the full set; levels between 1e-9 and 1e-13 with the other at 1e-11)
      and chains of >= 3 nested scales inside each anchor of >= 3 edges (the ordered set partitions of its edges into
      >= 3 blocks; levels between 1e-6 and 1e-8, the others at 1e-4): margin_probe's scales. The exponent of level k is
      |S_k| + d ln|f| / d ln t_k. Anchors: the double-lift subsets (raw <= -5), then the --tight-anchors clamped
      subsets with the smallest single-scale margin e - 0.8 alpha (the substitute for "the flags its argmax points
      approach" until those points exist; --anchors FILE adds any others). Budgets: --max-flags unique two-scale
      flags and --max-chains chains per graph (the chain budget shared over the anchors, smallest first); a larger
      population is sampled uniformly without replacement with a registered seed (--sample-seed and the graph), and
      the JSON says so.
  The depth ladder. At margin_probe's scales a level can be sub-asymptotic: a competing power of t_k whose coefficient
      carries high powers of the other (fixed, small) scales takes over only far deeper (graph 228: a chain level
      measured 0.689 at 1e-6..1e-8 is 1.000 from 1e-12 on; another reads 1.5 down to 1e-30 and 1.0 below 1e-46). The
      tail index of the weight is set by the asymptotic exponent, the smallest power of t_k as t_k -> 0 at fixed other
      scales. So every level is also measured with t_k pushed --depth and 2 --depth decades deeper (4 --depth when
      those differ by more than --tol); the asymptotic exponent is the converged value, else the smallest on the
      ladder (flagged unconverged). Deficits use the asymptotic exponent; a level below its proposal rate only at the
      shallow scales is a "dip" (a peaked, sub-asymptotic weight), counted and listed apart.
  (d) the cross-campaign shift from the pilot's xi_a and xi_b (32,768 points; or --xi FILE): a rate-driven tail
      predicts xi_b = 1 - (8/7)(1 - xi_a) (rates 0.8 and 0.7); no rate dependence predicts xi_b = xi_a.
  (e) the verdict: an asymptotic level exponent m below its proposal rate r by more than --tol (default 0.02) gives the
      tail index a = r/(r - m) (infinite variance when r >= 2m): "deficit at <flag> (level exponent m < proposal rate
      r ...; a = r/(r - m))", the worst level (smallest a) first; otherwise "no deficit found within the probed flags
      (finite-variance, peaked)".

Arithmetic. Every probe point is a power-of-ten scaling of the base point, so after one common power of ten all
coordinates are integers X_e = y_e 10^(A - alpha_e): the monomials, U_T, N_T and S are exact integers (the monomial
sums grouped by the flag's overlap vector, accumulated in 30-bit limbs, exact in float64). The only rounding is in
sum_T N_T / U_T^(3/2), done in fixed point with integer square roots and a rigorous error bound: the precision grows
until the sum has --min-bits (default 60) correct bits however deep the cancellation (no digit count is guessed;
margin_probe's fixed 80 digits cancel to zero at some deep points). gmpy2 is used when present, else Python ints.
--mp-check N re-evaluates N points per graph with margin_probe's own mpmath evaluation of f (Kern.f) at
max(--mp-dps, the fixed-point bits / 3.32 + 30) digits and at twice that, and records the largest |ln f| difference.

Reads: the inputs (--inputs, else C8_INPUTS, else the package's inputs/) through tools/members.py (inventory sha256
against inputs/manifest.json; each member against its inventory sha256 and, at L >= 7, MEMBERS_d3.sha256);
inputs/d3/rate_audit_L8.json (sha256 against the manifest) for the clamped-subset counts of `select`. The members are
extracted into a private directory under --scratch (default C8_SCRATCH, else TMPDIR), removed on exit. Writes only
under --out (select: its --out file). One BLAS thread per process (OPENBLAS_NUM_THREADS etc. default to 1): the
parallelism is the worker processes. Python >= 3.10, numpy, mpmath, scipy (estimate); gmpy2 optional.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import itertools
import json
import math
import multiprocessing
import os
import platform
import socket
import sys
import time
from pathlib import Path

for _v in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(_v, '1')   # one BLAS thread per process: the parallelism is --workers processes
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, dump, utc  # noqa: E402
import members  # noqa: E402

try:  # optional: faster big integers (the results are the same, bit for bit)
    import gmpy2
    _Z, _isqrt, BIGINT = gmpy2.mpz, gmpy2.isqrt, f'gmpy2 {gmpy2.version()}'
except ImportError:  # pragma: no cover - depends on the host
    gmpy2 = None
    _Z, _isqrt, BIGINT = int, math.isqrt, 'python int'

SCHEMA_SELECTION = 'c8-d3-margin-selection-1'
SCHEMA_GRAPH = 'c8-d3-margin-probe-graph-1'
SCHEMA_RUN = 'c8-d3-margin-probe-run-1'
SCHEMA_REPORT = 'c8-d3-margin-probe-report-1'
PILOT_EVIDENCE = ROOT / 'benchmarks/symmetry_2026-10-c8/pilot/evidence'
PILOT_REPORT_SCHEMA = 'c8-d3-pilot-report-1'
DOUBLE_LIFT_RAW = -5          # raw p4 <= -5: two units of cancellation (prepare_inputs.DOUBLE_LIFT_RAW; RECON:1346-1350)
PROPOSAL = (('a', 0.8), ('b', 0.7))   # campaign a: rate 0.8, campaign b: rate 0.7 (docs/NUMERICS.md "Groups")
XI_CONFIRM = 0.44             # action 2's threshold on the two-campaign mean xi(32,768)
SECTOR_CODE = {'free': 1, 'power': 2}
LN10, LN2 = math.log(10.0), math.log(2.0)
LIMB = 30                     # base monomials < 2^88 (y_e < 2^11, L <= 8): three 30-bit limbs
POP16 = np.array([bin(i).count('1') for i in range(1 << 16)], dtype=np.int16)
DEFAULTS = dict(base_seed=3, single=(10, 14), depth=40, two=(9, 13, 11), chain=(6, 8, 4), tol=0.02,
                tight_anchors=4, max_flags=40000, max_chains=20000, sample_seed=20261008, min_bits=60,
                mp_check=6, mp_dps=80)


class ProbeError(ValueError):
    pass


def pcount(s: int) -> int:
    return bin(s).count('1')


def edges(s: int) -> list:
    return [e for e in range(s.bit_length()) if s >> e & 1]


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


# ---- payloads ------------------------------------------------------------------------------------------------------
class Graph:
    """One d=3 G-file (C7D3GRAPH1): the package's structural parse (prepare_inputs.Member) plus the rate line."""

    def __init__(self, data: bytes, sector: str, where: str):
        import prepare_inputs as pi
        m = pi.Member(data, where)
        if m.magic != 'C7D3GRAPH1':
            raise ProbeError(f'{where}: magic {m.magic} is not C7D3GRAPH1')
        lines = data[:-1].split(b'\n')
        self.sector, self.L, self.id, self.M, self.T = sector, m.L, m.id, m.M, m.T
        self.E = 2 * m.L
        self.wa, self.wb = m.wa, m.wb
        self.masks = list(m.masks)
        self.terms = [(list(ids), list(co)) for ids, co in m.terms]
        self.rates = np.array([float(x) for x in lines[3 + m.T].split()], dtype=np.float64)
        self.sha256 = hashlib.sha256(data).hexdigest()
        if len(self.rates) != 1 << self.E:
            raise ProbeError(f'{where}: {len(self.rates)} rates, expected 2^E')

    @property
    def key(self) -> str:
        return f'{self.sector}:{self.L}:{self.id}'


def parse_key(k: str) -> tuple:
    s, L, g = k.split(':')
    if s not in SECTOR_CODE:
        raise ProbeError(f'graph key {k!r}: sector must be free or power')
    return s, int(L), int(g)


# ---- (a) the rate line ---------------------------------------------------------------------------------------------
def rate_line(g: Graph, chunk: int = 32) -> tuple:
    """(raw, lifted) over all 2^E subsets: raw = min over terms of p4 (quarter units), lifted = min over terms of p4
    lifted into (0, 4] when p4 <= 0 (regenerate_rates.cpp:16; margin_probe [M1]). Entries 0 and 2^E - 1 unused."""
    L, E = g.L, g.E
    N = 1 << E
    ALL = N - 1
    idx = np.arange(N, dtype=np.int64)
    pc = POP16[idx & 0xFFFF].astype(np.int32) if E <= 16 else np.array([pcount(s) for s in range(N)], np.int32)
    comp = ALL ^ idx
    masks = np.asarray(g.masks, dtype=np.int64)
    raw = np.full(N, 1000, dtype=np.int32)
    pos = np.full(N, 1000, dtype=np.int32)
    for c0 in range(0, g.T, chunk):
        part = g.terms[c0:c0 + chunk]
        tc = len(part)
        d = np.full((tc, N), 100, dtype=np.int16)
        supp = np.zeros(tc, dtype=np.int64)
        for t, (ids, co) in enumerate(part):
            d[t, masks[ids]] = 0
            supp[t] = sum(1 << j for j, c in enumerate(co) if c)
        for b in range(E):  # Hamming distance to the term's nearest monomial mask (E min-plus passes)
            v = d.reshape(tc, N >> (b + 1), 2, 1 << b)
            x, y = v[:, :, 0, :], v[:, :, 1, :]
            np.minimum(y, x + 1, out=y)   # min(x, y_new + 1) == min(x, y_old + 1): the in-place order is exact
            np.minimum(x, y + 1, out=x)
        h = (L - E + pc[None, :] + d[:, comp].astype(np.int32)) // 2
        nu = ((idx[None, :] & supp[:, None]) == supp[:, None]).astype(np.int32)
        p4 = 3 * pc[None, :] + 4 * nu - 6 * h
        cl = np.where(p4 <= 0, np.where(p4 % 4 == 0, 4, p4 % 4), p4)
        raw = np.minimum(raw, p4.min(0))
        pos = np.minimum(pos, cl.min(0))
    return raw, pos


def check_rate_line(g: Graph, inventory_double_lift=None, package_raw: bool = True) -> dict:
    raw, pos = rate_line(g)
    N = 1 << g.E
    ALL = N - 1
    tab = pos * 0.25
    tab[0] = 0.0
    tab[ALL] = 0.0
    bad = np.nonzero(tab != g.rates)[0]
    inner = raw[1:ALL]
    cl = np.nonzero(inner <= 0)[0] + 1
    hist = collections.Counter(int(v) for v in raw[cl])
    tabcl = collections.Counter(float(v) for v in g.rates[cl])
    dl = [int(s) for s in cl if raw[s] <= DOUBLE_LIFT_RAW]
    out = dict(subsets=int(N), mismatches=int(len(bad)), mismatch_examples=[dict(subset=int(s), recomputed=float(tab[s]),
               payload=float(g.rates[s])) for s in bad[:20]], clamped=int(len(cl)),
               raw_histogram={str(k): v for k, v in sorted(hist.items())},
               clamped_table_rates={f'{k:g}': v for k, v in sorted(tabcl.items())},
               double_lift=len(dl), double_lift_subsets=[f'{s:#06x}' for s in dl],
               min_raw=int(inner.min()) if len(inner) else 0)
    if inventory_double_lift is not None:
        out['inventory_double_lift'] = int(inventory_double_lift)
        out['inventory_double_lift_agrees'] = int(inventory_double_lift) == len(dl)
    if package_raw:  # the package's own vectorized raw valuation (tools/prepare_inputs.py), an independent code path
        import prepare_inputs as pi
        pr = pi.raw_valuations(g.L, g.masks, g.terms)
        out['package_raw_agrees'] = bool(np.array_equal(pr.astype(np.int32), inner))
    return out, raw, pos


# ---- the forest sum in exact integers ------------------------------------------------------------------------------
class Prep:
    __slots__ = ('sets', 'hvec', 'B', 'inS', 'size')

    def __init__(self, sets, hvec, B, inS):
        self.sets, self.hvec, self.B, self.inS = sets, hvec, B, inS
        self.size = [pcount(S) for S in sets]


class Forest:
    """f(x) = prod_e x_e^(-1/4) sum_T N_T(x) / (S(x) U_T(x)^(3/2)) (margin_probe Kern.f) at x_e = (y_e/1000) prod_k
    t_k^[e in S_k], t_k = 10^(-a_k). With X_e = y_e 10^(A - alpha_e) (alpha_e = sum_k a_k [e in S_k], A = max alpha_e)
    every polynomial is an exact integer and ln f(x) = 2L(A + 3) ln 10 + ln f(X) (f is homogeneous of degree -2L)."""

    def __init__(self, g: Graph, seed: int = 3, min_bits: int = 60):
        self.g = g
        self.L, self.E, self.T, self.M = g.L, g.E, g.T, g.M
        self.y = [int(v) for v in np.random.default_rng(seed).integers(500, 2000, g.E)]
        self.lny = [math.log(v) for v in self.y]
        self.masks = np.asarray(g.masks, dtype=np.int64)
        base = []
        for m in g.masks:
            p = 1
            for e in range(g.E):
                if m >> e & 1:
                    p *= self.y[e]
            base.append(p)
        if max(base) >= 1 << (3 * LIMB):
            raise ProbeError('a base monomial exceeds three limbs')
        lm = (1 << LIMB) - 1
        self.limbs = np.array([[(b >> (LIMB * k)) & lm for k in range(3)] for b in base], dtype=np.float64)
        P = np.zeros((g.T, g.M), dtype=np.float64)
        for t, (ids, co) in enumerate(g.terms):
            P[t, ids] = 1.0
        self.PL = np.stack([P * self.limbs[:, k][None, :] for k in range(3)])   # 3 x T x M: limb k of each monomial in each term
        numer = {}
        self.tnum = [numer.setdefault(tuple(co), len(numer)) for ids, co in g.terms]
        self.numer = [[(j, c) for j, c in enumerate(co) if c] for co in numer]
        self.min_bits = min_bits
        self.target = 160
        self._p10 = {}
        self.evals = 0
        self.max_target = 0
        self.last_target = 0

    def p10(self, n: int):
        v = self._p10.get(n)
        if v is None:
            v = self._p10[n] = _Z(10) ** n
        return v

    def prepare(self, sets) -> Prep:
        sets = tuple(int(S) for S in sets)
        K = len(sets)
        H = np.stack([POP16[self.masks & S] for S in sets], 1).astype(np.int64)   # M x K overlaps
        key = (H * (self.L + 1) ** np.arange(K, dtype=np.int64)).sum(1)
        _, first, inv = np.unique(key, return_index=True, return_inverse=True)
        inv = inv.reshape(-1)
        order = np.argsort(inv, kind='stable')
        starts = np.concatenate(([0], np.cumsum(np.bincount(inv))[:-1]))
        # per term and limb, the sum of the monomials of each overlap group: exact (integers below 2^42 < 2^53)
        B = np.add.reduceat(self.PL[:, :, order], starts, axis=2).transpose(1, 0, 2)   # T x 3 x G
        inS = np.array([[S >> e & 1 for e in range(self.E)] for S in sets], dtype=np.int64)
        return Prep(sets, H[first], B, inS)

    def lnf(self, prep: Prep, a) -> tuple:
        """(ln|f(x)|, sign, correct bits of the forest sum) at decades a (one per level of prep)."""
        a = np.asarray(a, dtype=np.int64)
        alpha = a @ prep.inS
        A = int(alpha.max()) if len(alpha) else 0
        D = prep.hvec @ a
        ds, dinv = np.unique(D, return_inverse=True)
        OH = np.zeros((len(D), len(ds)), dtype=np.float64)
        OH[np.arange(len(D)), dinv.reshape(-1)] = 1.0
        C = (prep.B @ OH).astype(np.int64)        # T x 3 x nd, exact
        LA = self.L * A
        pw = [self.p10(LA - int(d)) for d in ds]
        c0, c1, c2 = C[:, 0, :].tolist(), C[:, 1, :].tolist(), C[:, 2, :].tolist()
        U = []
        for t in range(self.T):
            u = 0
            for j, p in enumerate(pw):
                c = c0[t][j] + (c1[t][j] << LIMB) + (c2[t][j] << (2 * LIMB))
                if c:
                    u += c * p
            U.append(_Z(u))
        X = [_Z(self.y[e]) * self.p10(A - int(alpha[e])) for e in range(self.E)]
        S = sum(X)
        Nv = [sum(c * X[j] for j, c in nm) for nm in self.numer]
        r = self._forest_sum(U, Nv)
        self.evals += 1
        if r is None:
            return None, 0, 0
        Z, shift, good = r
        lnS = _ln(S)
        lnf = (2 * self.L * (A + 3) * LN10 - 0.25 * sum(self.lny[e] + (A - int(alpha[e])) * LN10 for e in range(self.E))
               - lnS + _ln(abs(Z)) + shift * LN2)
        return lnf, (1 if Z > 0 else -1), good

    def _forest_sum(self, U, Nv):
        """sum_T N_T / U_T^(3/2) as (Z, shift, good): the sum = Z 2^shift (1 + d), |d| < 2^-good, good >= min_bits."""
        T = self.T
        target = self.target
        while True:
            p = target + 16
            dens = [None] * T
            emax = None
            for t in range(T):
                n = Nv[self.tnum[t]]
                if n == 0:
                    continue
                u = U[t]
                den = u * _isqrt(u << (2 * p))       # U^(3/2) 2^p (1 - d), 0 <= d < 2^-p
                dens[t] = den
                e = int(n.bit_length()) - int(den.bit_length())
                emax = e if emax is None or e > emax else emax
            if emax is None:
                return None
            W = target + 4 - emax
            Z = 0
            absq = 0
            for t in range(T):
                den = dens[t]
                if den is None:
                    continue
                n = _Z(Nv[self.tnum[t]])
                q = (n << W) // den if W >= 0 else n // (den << -W)
                Z += q
                absq += abs(q)
            err = 2 * T + 2 + (absq >> (p - 2))
            good = int(abs(Z).bit_length()) - int(err.bit_length()) if Z != 0 else -1
            if good >= self.min_bits:
                self.max_target = max(self.max_target, target)
                self.last_target = target
                self.target = max(160, target - max(good - self.min_bits - 32, 0))
                return _Z(Z), p - W, good
            if target > 1 << 17:
                return None
            target += max(self.min_bits - good, 0) + 64

    def level(self, prep: Prep, k: int, lo: int, hi: int, fix: int) -> tuple:
        """|S_k| + d ln|f| / d ln t_k between t_k = 10^-lo and 10^-hi, the other levels at 10^-fix:
        (exponent or None, min correct bits, sign change)."""
        a = [fix] * len(prep.sets)
        a[k] = lo
        f1, s1, b1 = self.lnf(prep, a)
        a[k] = hi
        f2, s2, b2 = self.lnf(prep, a)
        if f1 is None or f2 is None:
            return None, 0, False
        return prep.size[k] + (f2 - f1) / (-(hi - lo) * LN10), min(b1, b2), s1 != s2


    def measure(self, prep: Prep, k: int, lo: int, hi: int, fix: int, depth: int, tol: float) -> tuple:
        """Level k at margin_probe's scales (shallow) and on the ladder towards its asymptotic exponent: the scanned
        level pushed depth and 2 depth decades deeper at the same fixed other levels, and 4 depth when those two
        differ by more than tol. (shallow, e_D, e_2D, e_4D or None, min correct bits, sign change)."""
        e0, b0, f0 = self.level(prep, k, lo, hi, fix)
        if not depth:
            return e0, e0, e0, None, b0, f0
        e1, b1, f1 = self.level(prep, k, lo + depth, hi + depth, fix)
        e2, b2, f2 = self.level(prep, k, lo + 2 * depth, hi + 2 * depth, fix)
        e4, b4, f4 = None, b2, False
        if e1 is None or e2 is None or abs(e2 - e1) > tol:
            e4, b4, f4 = self.level(prep, k, lo + 4 * depth, hi + 4 * depth, fix)
        return e0, e1, e2, e4, min(b0, b1, b2, b4), f0 or f1 or f2 or f4


def asymptotic(e1, e2, e4, tol) -> tuple:
    """The asymptotic exponent the verdict uses, and whether the ladder converged: e_2D when e_D and e_2D agree within
    tol, e_4D when it was needed and agrees with e_2D; otherwise the smallest value on the ladder (not converged; the
    conservative choice, since a crossover only ever moves the exponent down to the smallest power of t_k)."""
    vals = [e for e in (e1, e2, e4) if e is not None]
    if not vals:
        return None, False
    if e4 is None:
        return (e2, True) if e1 is not None and e2 is not None and abs(e2 - e1) <= tol else (min(vals), False)
    return (e4, True) if e2 is not None and abs(e4 - e2) <= tol else (min(vals), False)


def _ln(z) -> float:
    b = int(z.bit_length())
    if b <= 64:
        return math.log(int(z))
    return math.log(int(z >> (b - 64))) + (b - 64) * LN2


def mp_lnf(g: Graph, y, sets, a, dps: int) -> float:
    """margin_probe's mpmath evaluation of f (Kern.f) at the same point, at dps digits: ln|f|."""
    import mpmath as mp
    E = g.E
    with mp.workdps(dps):
        x = [mp.mpf(int(v)) / 1000 for v in y]
        for S, ak in zip(sets, a):
            sc = mp.mpf(10) ** (-int(ak))
            for e in range(E):
                if S >> e & 1:
                    x[e] *= sc
        mono = [mp.fprod(x[e] for e in range(E) if m >> e & 1) for m in g.masks]
        S = mp.fsum(x)
        tot = mp.mpf(0)
        for ids, c in g.terms:
            tot += mp.fsum(c[j] * x[j] for j in range(E) if c[j]) / (S * mp.fsum(mono[i] for i in ids) ** mp.mpf(1.5))
        f = mp.fprod(xe ** mp.mpf(-0.25) for xe in x) * tot
        return float(mp.log(abs(f))) if f != 0 else None   # None: the sum cancelled to zero at these digits


# ---- chains: ordered set partitions ---------------------------------------------------------------------------------
def stirling2(n: int, k: int) -> int:
    S = [[0] * (k + 1) for _ in range(n + 1)]
    S[0][0] = 1
    for i in range(1, n + 1):
        for j in range(1, min(i, k) + 1):
            S[i][j] = S[i - 1][j - 1] + j * S[i - 1][j]
    return S[n][k]


def chain_population(n: int, kmin: int = 3) -> int:
    """Ordered set partitions of n elements into >= kmin blocks (n = 6: 4,620; margin_probe's 228 chains)."""
    return sum(math.factorial(b) * stirling2(n, b) for b in range(kmin, n + 1))


def all_chains(el: list, kmin: int = 3):
    """Every ordered set partition of el into >= kmin blocks, in margin_probe's order (its chains() generator)."""
    def rec(elems):
        if not elems:
            yield []
            return
        for k in range(1, len(elems) + 1):
            for blk in itertools.combinations(elems, k):
                for ch in rec([e for e in elems if e not in blk]):
                    yield [blk] + ch
    for parts in rec(list(el)):
        if len(parts) >= kmin:
            yield parts


def sample_chain(el: list, rng, kmin: int = 3) -> list:
    """One ordered set partition of el into >= kmin blocks, uniformly: b with probability b! S(n, b) / total, then a
    uniform set partition into b blocks (S(n, b) = S(n-1, b-1) + b S(n-1, b), element by element), then a uniform
    order of its blocks."""
    n = len(el)
    w = [math.factorial(b) * stirling2(n, b) for b in range(kmin, n + 1)]
    r = int(rng.integers(0, sum(w))) if sum(w) < 1 << 62 else int(rng.random() * sum(w))
    b = kmin
    for x in w:
        if r < x:
            break
        r -= x
        b += 1
    blocks = []
    need = b

    def place(i, need):   # elements el[:i+1] into exactly `need` blocks (blocks built in place)
        if i < 0:
            return
        if need == i + 1:   # every remaining element alone
            for j in range(i + 1):
                blocks.append([el[j]])
            return
        p_single = stirling2(i, need - 1) / stirling2(i + 1, need)
        if rng.random() < p_single:
            place(i - 1, need - 1)
            blocks.append([el[i]])
        else:
            place(i - 1, need)
            blocks[int(rng.integers(0, need))].append(el[i])
    place(n - 1, need)
    order = rng.permutation(len(blocks))
    return [tuple(sorted(blocks[j])) for j in order]


def chain_sets(parts) -> tuple:
    return tuple(itertools.accumulate([sum(1 << e for e in p) for p in parts], lambda x, y: x | y))


# ---- worker side ---------------------------------------------------------------------------------------------------
_CACHE: collections.OrderedDict = collections.OrderedDict()


def _load(task) -> tuple:
    key = (task['key'], task['seed'], task['min_bits'])
    hit = _CACHE.get(key)
    if hit is None:
        data = Path(task['path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != task['sha256']:
            raise ProbeError(f'{task["path"]}: sha256 differs from the member read by the main process')
        g = Graph(data, task['key'].split(':')[0], task['path'])
        hit = (g, None)
        _CACHE[key] = hit
        while len(_CACHE) > 3:
            _CACHE.popitem(last=False)
    if task['kind'] != 'rate' and hit[1] is None:
        hit = (hit[0], Forest(hit[0], task['seed'], task['min_bits']))
        _CACHE[key] = hit
    _CACHE.move_to_end(key)
    return hit


def run_task(task) -> dict:
    t0, c0 = time.perf_counter(), time.process_time()
    g, F = _load(task)
    kind = task['kind']
    ev0 = F.evals if F else 0
    if kind == 'rate':
        res, raw, pos = check_rate_line(g, task.get('inventory_double_lift'))
        out = dict(result=res, raw=raw.astype(np.int16), pos=pos.astype(np.int8), rates=g.rates,
                   header=dict(L=g.L, E=g.E, M=g.M, T=g.T, wa=g.wa, wb=g.wb, sha256=g.sha256))
    elif kind == 'single':
        lo, hi = task['scales']
        rows = []
        for S in task['subsets']:
            e0, e1, e2, e4, good, flip = F.measure(F.prepare([S]), 0, lo, hi, 0, task['depth'], task['tol'])
            rows.append((S, e0, e1, e2, e4, good, flip))
        out = dict(rows=rows)
    elif kind == 'multi':
        lo, hi, fix = task['scales']
        rows = []
        for item in task['items']:
            sets = item['sets']
            prep = F.prepare(sets)
            lev = []
            good = 1 << 30
            flip = False
            for k in range(len(sets)):
                e0, e1, e2, e4, b, sc = F.measure(prep, k, lo, hi, fix, task['depth'], task['tol'])
                lev.append((e0, e1, e2, e4))
                good = min(good, b)
                flip = flip or sc
            rows.append((item['cls'], item['anchor'], tuple(sets), lev, good, flip))
        out = dict(rows=rows)
    elif kind == 'mpcheck':
        rows = []
        for pr in task['probes']:
            prep = F.prepare(pr['sets'])
            fi = F.lnf(prep, pr['a'])[0]
            # digits: at least --mp-dps, and enough for the cancellation the fixed-point sum needed (its bits + 30)
            dps = max(task['dps'], int(F.last_target * 0.30103) + 30)
            m1 = mp_lnf(g, F.y, pr['sets'], pr['a'], dps)
            m2 = mp_lnf(g, F.y, pr['sets'], pr['a'], 2 * dps)
            rows.append(dict(what=pr['what'], sets=[f'{S:#06x}' for S in pr['sets']], a=list(pr['a']), lnf_int=fi,
                             lnf_mp=m1, lnf_mp2=m2, dps=dps))
        out = dict(rows=rows)
    else:
        raise ProbeError(f'unknown task kind {kind}')
    out.update(key=task['key'], kind=kind, cls=task.get('cls'), chunk=task.get('chunk', 0), seconds=time.perf_counter() - t0,
               cpu_seconds=time.process_time() - c0, evals=(F.evals - ev0) if F else 0,
               max_target=F.max_target if F else 0)
    return out


def run_tasks(tasks: list, workers: int, label: str, log) -> list:
    tasks = sorted(tasks, key=lambda t: -t.get('weight', 0))
    out = []
    t0 = time.time()
    n = len(tasks)
    step = max(1, n // 10)
    if workers <= 1:
        it = map(run_task, tasks)
        pool = None
    else:
        ctx = multiprocessing.get_context('fork' if 'fork' in multiprocessing.get_all_start_methods()
                                          and platform.system() == 'Linux' else 'spawn')
        pool = ctx.Pool(workers)
        it = pool.imap_unordered(run_task, tasks, chunksize=1)
    try:
        for i, r in enumerate(it, 1):
            out.append(r)
            if i % step == 0 or i == n:
                log(f'{label}: {i}/{n} tasks, {time.time() - t0:.1f} s')
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    return out


# ---- the probe (main process) --------------------------------------------------------------------------------------
def _chunks(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def flag_population(anchors: list, E: int) -> tuple:
    """Two-scale flags with an anchor as the inner or the outer set: ({flag: first anchor that gives it}, margin_probe's
    enumerated count with repeats, per-anchor counts). Inner: every proper non-empty subset of the anchor; outer: every
    proper superset below the full set (margin_probe [M3])."""
    ALL = (1 << E) - 1
    pop = {}
    enum = 0
    per = []
    for D in anchors:
        inner = [S1 for S1 in range(1, D) if S1 & D == S1]
        outer = [S2 for S2 in range(D + 1, ALL) if S2 & D == D]
        for S1 in inner:
            pop.setdefault((S1, D), D)
        for S2 in outer:
            pop.setdefault((D, S2), D)
        enum += len(inner) + len(outer)
        per.append(dict(anchor=f'{D:#06x}', inner=len(inner), outer=len(outer)))
    return pop, enum, per


def plan_multi(key: str, anchors: list, kinds: list, E: int, a: argparse.Namespace) -> tuple:
    """The two-scale flags and the chains of one graph, within the budgets (registered-seed samples beyond them)."""
    s, L, gid = parse_key(key)
    popd, enum, per = flag_population(anchors, E)
    pop = sorted(popd)
    rng = np.random.default_rng([a.sample_seed, SECTOR_CODE[s], L, gid, 2])
    if len(pop) > a.max_flags:
        pick = np.sort(rng.choice(len(pop), size=a.max_flags, replace=False))
        flags = [pop[i] for i in pick]
        sampled = True
    else:
        flags = pop
        sampled = False
    items = [dict(cls='two', anchor=f'{popd[f]:#06x}', sets=f) for f in flags]
    two = dict(anchors=per, population_unique=len(pop), enumerated_with_repeats=enum, probed=len(flags), sampled=sampled)
    chain_info = []
    remaining = a.max_chains
    # the chain budget, shared over the anchors of >= 3 edges in increasing population order: an anchor whose whole
    # population fits its share (what is left over the anchors still to come) is enumerated, and what it leaves flows
    # to the larger ones; the others are sampled
    ch_anchors = sorted([D for D in anchors if pcount(D) >= 3], key=lambda D: (chain_population(pcount(D)), D))
    for i, D in enumerate(ch_anchors):
        el = edges(D)
        popn = chain_population(len(el))
        allot = remaining // (len(ch_anchors) - i) if remaining > 0 else 0
        if popn <= allot:
            parts_list = list(all_chains(el))
            smp = False
        else:
            crng = np.random.default_rng([a.sample_seed, SECTOR_CODE[s], L, gid, 3, D])
            seen = set()
            parts_list = []
            tries = 0
            while len(parts_list) < allot and tries < 50 * allot + 100:
                tries += 1
                p = sample_chain(el, crng)
                sig = chain_sets(p)
                if sig not in seen:
                    seen.add(sig)
                    parts_list.append(p)
            smp = True
        remaining -= len(parts_list)
        for p in parts_list:
            items.append(dict(cls='chain', anchor=f'{D:#06x}', sets=chain_sets(p)))
        chain_info.append(dict(anchor=f'{D:#06x}', edges=len(el), kind=kinds[anchors.index(D)], population=popn,
                               probed=len(parts_list), sampled=smp))
    return items, two, chain_info


def _hex(S: int) -> str:
    return f'{S:#06x}'


CLASS_ORDER = {'single': 0, 'two': 1, 'chain': 2}


def describe_level(cls: str, sets: tuple, k: int) -> str:
    if cls == 'single':
        return f'single-scale face {_hex(sets[0])} (edges {edges(sets[0])})'
    name = 'two-scale flag' if cls == 'two' else f'{len(sets)}-scale chain'
    return f'{name} {" < ".join(_hex(S) for S in sets)}, level {k + 1} = {_hex(sets[k])} (edges {edges(sets[k])})'


def verdict(levels: list, tol: float, dips: list = ()) -> dict:
    """levels: (cls, sets, k, m, alpha) with m the asymptotic level exponent; dips: (cls, sets, k, shallow, m, alpha)
    for the levels below their proposal rate only at margin_probe's (shallow) scales. The deficits per campaign and the
    verdict text (RECON (e))."""
    out = {}
    worst = None
    for camp, fac in PROPOSAL:
        defs = []
        near = 0
        for cls, sets, k, m, alpha in levels:
            if m is None or alpha <= 0:
                continue
            r = fac * alpha
            if m < r - tol:
                a_tail = r / (r - m) if m > 0 else None
                defs.append(dict(where=describe_level(cls, sets, k), cls=cls, sets=[_hex(S) for S in sets], level=k + 1,
                                 exponent=m, table_rate=alpha, proposal_rate=r, tail_index=a_tail,
                                 infinite_variance=(r >= 2 * m), nonpositive_exponent=m <= 0))
            elif m < r:
                near += 1
        # the worst first: the smallest tail index (non-positive exponents before all), equal ones (to 1e-6) by the
        # simplest flag (single scale, two-scale, chain; fewer levels)
        defs.sort(key=lambda d: (round(d['tail_index'], 6) if d['tail_index'] is not None else -1.0,
                                 CLASS_ORDER[d['cls']], len(d['sets']), round(d['exponent'] - d['proposal_rate'], 6)))
        dd = sorted([(sh - fac * al, cls, sets, k, sh, m, al) for cls, sets, k, sh, m, al in dips
                     if al > 0 and sh < fac * al - tol and m is not None and m >= fac * al - tol], key=lambda x: x[0])
        out[camp] = dict(proposal_factor=fac, deficits=len(defs), near_misses_within_tol=near, worst=defs[:25],
                         shallow_dips=len(dd), worst_dips=[dict(where=describe_level(cls, sets, k), shallow_exponent=sh,
                                                                asymptotic_exponent=m, table_rate=al,
                                                                proposal_rate=fac * al) for _, cls, sets, k, sh, m, al in dd[:25]])
        if defs and worst is None:
            worst = (camp, defs[0])
    if worst:
        camp, d = worst
        a_txt = (f'a = {d["proposal_rate"]:.3f}/({d["proposal_rate"]:.3f} - {d["exponent"]:.3f}) = {d["tail_index"]:.2f}'
                 if d['tail_index'] is not None else 'a undefined: non-positive exponent (the integral itself would '
                 'diverge here; check the precision and the payload)')
        text = (f'deficit at {d["where"]} (level exponent {d["exponent"]:.3f} < proposal rate {d["proposal_rate"]:.3f} = '
                f'{dict(PROPOSAL)[camp]} x {d["table_rate"]:g}, campaign {camp}; {a_txt}'
                f'{"; infinite variance (r >= 2m)" if d["infinite_variance"] else ""})')
        status = 'deficit'
    else:
        text = 'no deficit found within the probed flags (finite-variance, peaked)'
        status = 'no_deficit'
    return dict(status=status, text=text, campaigns=out)


def shift_check(xa, xb) -> dict:
    """(d): xi_b against the face model 1 - (8/7)(1 - xi_a) and against no rate dependence (xi_b = xi_a)."""
    if xa is None or xb is None:
        return dict(available=False)
    face = 1 - (8 / 7) * (1 - xa)
    d_face, d_none = abs(xb - face), abs(xb - xa)
    return dict(available=True, xi_a=xa, xi_b=xb, face_model_xi_b=face, observed_shift=xb - xa,
                face_model_shift=face - xa, distance_to_face_model=d_face, distance_to_no_shift=d_none,
                closer_to='face model (rate-driven)' if d_face < d_none else 'no rate dependence',
                note=('xi_a >= 1 lies outside the face model (a = r/(r - m) > 1 for every m > 0)' if xa >= 1 else None))


def load_selection(path: Path) -> tuple:
    d = json.loads(Path(path).read_text())
    if d.get('schema') != SCHEMA_SELECTION:
        raise ProbeError(f'{path}: schema {d.get("schema")!r} is not {SCHEMA_SELECTION}')
    rows = d['graphs']
    return [(r['sector'], int(r['L']), int(r['id'])) for r in rows], {f'{r["sector"]}:{r["L"]}:{r["id"]}': r for r in rows}


def probe(a: argparse.Namespace) -> int:
    log = (lambda m: print(f'[{time.strftime("%H:%M:%S")}] {m}', file=sys.stderr, flush=True))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sel_rows = {}
    if a.selection:
        graphs, sel_rows = load_selection(a.selection)
    else:
        graphs = [parse_key(k) for k in a.graphs.split(',') if k]
    graphs = list(dict.fromkeys(graphs))
    if a.limit:
        graphs = graphs[:a.limit]
    xi = json.loads(Path(a.xi).read_text()) if a.xi else {}
    anchors_extra = json.loads(Path(a.anchors).read_text()) if a.anchors else {}
    todo = []
    for s, L, g in graphs:
        k = f'{s}:{L}:{g}'
        if (out / f'{s}_L{L}_G{g}.json').exists():
            if a.skip_existing:
                log(f'{k}: result exists, skipped')
                continue
            raise ProbeError(f'{out / f"{s}_L{L}_G{g}.json"} exists (results are never overwritten; --skip-existing)')
        todo.append((s, L, g))
    if not todo:
        log('nothing to do')
        return 0
    inputs = members.inputs_dir(a.inputs)
    inv = members.inventory(inputs)
    man_sha = sha256_file(inputs / 'manifest.json')
    rows = {}
    for s, L, g in todo:
        try:
            rows[(s, L, g)] = next(r for r in inv[s][str(L)] if r['id'] == g)
        except (KeyError, StopIteration):
            raise ProbeError(f'{s} L{L} graph {g} is not in {inputs / "inventory.json"}') from None
    t_start = time.time()
    base = Path(a.scratch) if a.scratch else (Path(os.environ['C8_SCRATCH']) if os.environ.get('C8_SCRATCH') else None)
    written = []
    with members.extracted(todo, inputs, base=base) as root:
        info = {}
        for s, L, g in todo:
            p = root / s / f'L{L}' / f'G{g}.txt'
            info[f'{s}:{L}:{g}'] = dict(key=f'{s}:{L}:{g}', path=str(p), sha256=sha256_file(p), seed=a.base_seed,
                                        min_bits=a.min_bits, depth=a.depth, tol=a.tol)
        # (a) the rate lines
        tasks = [dict(i, kind='rate', inventory_double_lift=rows[parse_key(k)].get('double_lift'),
                      weight=rows[parse_key(k)]['terms'] * (1 << 2 * parse_key(k)[1])) for k, i in info.items()]
        res_a = {r['key']: r for r in run_tasks(tasks, a.workers, '(a) rate lines', log)}
        # (b) single scale at every clamped subset
        tasks = []
        for k, r in res_a.items():
            raw = r['raw'].astype(np.int32)
            ALL = (1 << r['header']['E']) - 1
            cl = [int(x) for x in np.nonzero(raw[1:ALL] <= 0)[0] + 1]
            for j, ch in enumerate(_chunks(cl, a.chunk_single)):
                tasks.append(dict(info[k], kind='single', chunk=j, subsets=ch, scales=tuple(a.single),
                                  weight=len(ch) * r['header']['T']))
        res_b = collections.defaultdict(list)
        for r in run_tasks(tasks, a.workers, '(b) single scale', log):
            res_b[r['key']].append(r)
        # (c) two-scale flags and chains around the anchors
        tasks = []
        plans = {}
        for k, r in res_a.items():
            E = r['header']['E']
            raw = r['raw'].astype(np.int32)
            rates = r['rates']
            rows_b = sorted([x for rr in res_b[k] for x in rr['rows']], key=lambda x: x[0])
            ALL = (1 << E) - 1
            dl = sorted([int(S) for S in np.nonzero(raw[1:ALL] <= DOUBLE_LIFT_RAW)[0] + 1], key=lambda S: (pcount(S), S))
            kinds = ['double_lift'] * len(dl)
            anchors = list(dl)
            if a.tight_anchors:
                cand = []
                for S, e0, e1, e2, e4, good, flip in rows_b:
                    m = asymptotic(e1, e2, e4, a.tol)[0]
                    if e0 is None or m is None or S in anchors:
                        continue
                    cand.append((min(e0, m) - 0.8 * rates[S], pcount(S), S))
                for _, _, S in sorted(cand)[:a.tight_anchors]:
                    anchors.append(S)
                    kinds.append('tight')
            for S in anchors_extra.get(k, []):
                S = int(S, 0) if isinstance(S, str) else int(S)
                if S not in anchors and 0 < S < ALL:
                    anchors.append(S)
                    kinds.append('given')
            items, two, chains = plan_multi(k, anchors, kinds, E, a)
            plans[k] = dict(anchors=[dict(subset=_hex(S), edges=edges(S), kind=kd, table_rate=float(rates[S]),
                                          raw=int(raw[S])) for S, kd in zip(anchors, kinds)], two_scale=two, chains=chains)
            twos = [it for it in items if it['cls'] == 'two']
            chs = [it for it in items if it['cls'] == 'chain']
            for j, ch in enumerate(_chunks(twos, a.chunk_flags)):
                tasks.append(dict(info[k], kind='multi', cls='two', chunk=j, items=ch, scales=tuple(a.two),
                                  weight=12 * len(ch) * r['header']['T']))
            for j, ch in enumerate(_chunks(chs, a.chunk_chains)):
                tasks.append(dict(info[k], kind='multi', cls='chain', chunk=100000 + j, items=ch, scales=tuple(a.chain),
                                  weight=sum(6 * len(it['sets']) for it in ch) * r['header']['T']))
        res_c = collections.defaultdict(list)
        for r in run_tasks(tasks, a.workers, '(c) multi scale', log):
            res_c[r['key']].append(r)
        # the mpmath cross-check (margin_probe's Kern.f at --mp-dps and twice that): double-lift faces, random clamped
        # faces, then the multi-scale levels with the smallest asymptotic margins, at their deep scales
        tasks = []
        for k, r in res_a.items():
            if not a.mp_check:
                break
            rows_b = [x for rr in res_b[k] for x in rr['rows'] if x[1] is not None]
            raw = r['raw'].astype(np.int32)
            pr = []
            rng = np.random.default_rng([a.sample_seed, 7] + list(parse_key(k)[1:]))
            dls = [x for x in rows_b if raw[x[0]] <= DOUBLE_LIFT_RAW]
            pick_b = dls[:2] + ([rows_b[i] for i in rng.choice(len(rows_b), size=min(2, len(rows_b)), replace=False)]
                                if rows_b else [])
            for x in pick_b[:max(1, a.mp_check // 2)]:
                pr.append(dict(what='single', sets=(x[0],), a=(a.single[1] + 2 * a.depth,)))
            lv = []
            for rr in res_c[k]:
                for cls, anc, sets, lev, good, flip in rr['rows']:
                    for kk, (S, e) in enumerate(zip(sets, lev)):
                        m = asymptotic(e[1], e[2], e[3], a.tol)[0]
                        if m is not None:
                            lv.append((m - 0.8 * r['rates'][S], cls, sets, kk))
            lv.sort(key=lambda x: x[0])
            for _, cls, sets, kk in lv[:max(0, a.mp_check - len(pr))]:
                lo, hi, fix = a.two if cls == 'two' else a.chain
                av = [fix] * len(sets)
                av[kk] = hi + 2 * a.depth
                pr.append(dict(what=cls, sets=tuple(sets), a=tuple(av)))
            if pr:
                tasks.append(dict(info[k], kind='mpcheck', probes=pr, dps=a.mp_dps,
                                  weight=len(pr) * r['header']['T'] * r['header']['M']))
        res_d = {r['key']: r for r in run_tasks(tasks, a.workers, 'mpmath cross-check', log)} if tasks else {}
        for k, ra in res_a.items():
            doc = assemble(k, info[k], rows[parse_key(k)], ra, res_b[k], res_c[k], res_d.get(k), plans[k],
                           sel_rows.get(k), xi.get(k), a, man_sha, inputs)
            s, L, g = parse_key(k)
            bad = []
            doc = finite_doc(doc, '', bad)
            doc['nonfinite'] = bad
            dump(out / f'{s}_L{L}_G{g}.json', doc)
            written.append(k)
            log(f'{k}: {doc["verdict"]["text"]}')
    run = dict(schema=SCHEMA_RUN, made_utc=utc(), host=socket.gethostname(), cpu=_cpu(), python=sys.version.split()[0],
               numpy=np.__version__, bigint=BIGINT, workers=a.workers, inputs=str(inputs), inputs_manifest_sha256=man_sha,
               selection=(dict(path=str(a.selection), sha256=sha256_file(a.selection)) if a.selection else None),
               graphs=written, wall_seconds=time.time() - t_start, params=_params(a),
               slurm={k: os.environ.get(k) for k in ('SLURM_JOB_ID', 'SLURM_JOB_NODELIST', 'SLURM_CPUS_PER_TASK')})
    name = 'probe_run.json'
    i = 1
    while (out / name).exists():
        i += 1
        name = f'probe_run_{i}.json'
    dump(out / name, run)
    log(f'{len(written)} graphs in {time.time() - t_start:.1f} s; {out / name}')
    return 0


def _params(a) -> dict:
    keys = ('base_seed', 'single', 'two', 'chain', 'depth', 'tol', 'tight_anchors', 'max_flags', 'max_chains',
            'sample_seed', 'min_bits', 'mp_check', 'mp_dps', 'anchors')
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in ((k, getattr(a, k)) for k in keys)}


def _cpu() -> str:
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):
                return ' '.join(line.split(':', 1)[1].split())
    except OSError:
        pass
    return platform.processor() or platform.machine()


def finite_doc(obj, path='', bad=None):
    """obj with every non-finite float replaced by None; the paths go into bad (written to the JSON as 'nonfinite')."""
    bad = [] if bad is None else bad
    if isinstance(obj, float):
        if math.isfinite(obj):
            return obj
        bad.append(f'{path}: {obj}')
        return None
    if isinstance(obj, dict):
        return {k: finite_doc(v, f'{path}/{k}', bad) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [finite_doc(v, f'{path}/{i}', bad) for i, v in enumerate(obj)]
    if isinstance(obj, (np.floating,)):
        return finite_doc(float(obj), path, bad)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def _r6(x):
    return None if x is None else round(float(x), 6)


def assemble(k, info, row, ra, rb, rc, rd, plan, sel_row, xi_row, a, man_sha, inputs) -> dict:
    s, L, g = parse_key(k)
    rates = ra['rates']
    raw = ra['raw'].astype(np.int32)
    tol = a.tol
    levels, dips = [], []
    # (b)
    rows_b = sorted([x for r in rb for x in r['rows']], key=lambda x: x[0])
    per_subset, ms, tb = [], [], []
    unresolved = flips = unconverged = 0
    below_table, dlist = [], []
    drift_max = 0.0
    for S, e0, e1, e2, e4, good, flip in rows_b:
        al = float(rates[S])
        m, conv = asymptotic(e1, e2, e4, tol)
        per_subset.append([_hex(S), al, _r6(e0), _r6(m), int(raw[S]), conv])
        if e0 is None or m is None:
            unresolved += 1
            continue
        flips += bool(flip)
        unconverged += not conv
        drift_max = max(drift_max, abs(m - e0))
        ms.append(e0)
        tb.append(al)
        levels.append(('single', (S,), 0, m, al))
        dips.append(('single', (S,), 0, e0, m, al))
        if m < al - tol:
            below_table.append(dict(subset=_hex(S), table_rate=al, exponent=m))
        if raw[S] <= DOUBLE_LIFT_RAW:
            dlist.append(dict(subset=_hex(S), edges=len(edges(S)), table_rate=al, measured=e0, asymptotic=m))
    ms, tb = np.array(ms), np.array(tb)
    single = dict(clamped=len(rows_b), resolved=len(ms), unresolved=unresolved, sign_changes=flips,
                  unconverged=unconverged, drift_max=drift_max,
                  min_margin_a=min((m - 0.8 * al for _, _, _, m, al in levels), default=None),
                  min_margin_b=min((m - 0.7 * al for _, _, _, m, al in levels), default=None),
                  compat=dict(min_diff=float((ms - tb).min()) if len(ms) else None,
                              max_diff=float((ms - tb).max()) if len(ms) else None,
                              equal=int(np.sum(abs(ms - tb) < tol)), below_table=int(np.sum(ms < tb - tol)),
                              below_08=int(np.sum(ms < 0.8 * tb - tol)), below_07=int(np.sum(ms < 0.7 * tb - tol)),
                              note=f'margin_probe [M3]: the 1e-{a.single[0]}/1e-{a.single[1]} slope; equal = within +-{tol:g}'),
                  below_table_rate=below_table, double_lift=dlist, per_subset=per_subset,
                  per_subset_fields=['subset', 'table_rate', 'exponent_shallow', 'exponent_asymptotic', 'raw_p4', 'converged'],
                  evals=sum(r['evals'] for r in rb), cpu_seconds=sum(r['cpu_seconds'] for r in rb))
    # (c)
    blank = dict(items=0, levels=0, unresolved=0, unconverged=0, sign_changes=0, min_margin_a=None, min_margin_b=None,
                 min_margin_a_shallow=None)
    multi = {'two': dict(blank), 'chain': dict(blank)}
    per_anchor = collections.defaultdict(lambda: dict(items=0, levels=0, min_margin_a=None, min_margin_a_shallow=None))
    worst = {'two': [], 'chain': []}
    unconv = {'two': [], 'chain': []}

    def lower(d, key, v):
        d[key] = v if d[key] is None else min(d[key], v)
    rc = sorted(rc, key=lambda r: (r.get('cls') or '', r['chunk']))   # task order, not completion order
    for r in rc:
        for cls, anc, sets, lev, good, flip in r['rows']:
            c = multi[cls]
            pa = per_anchor[(cls, anc)]
            c['items'] += 1
            pa['items'] += 1
            c['sign_changes'] += bool(flip)
            for kk, (S, (e0, e1, e2, e4)) in enumerate(zip(sets, lev)):
                c['levels'] += 1
                pa['levels'] += 1
                m, conv = asymptotic(e1, e2, e4, tol)
                if e0 is None or m is None:
                    c['unresolved'] += 1
                    continue
                c['unconverged'] += not conv
                al = float(rates[S])
                if not conv and len(unconv[cls]) < 25:
                    unconv[cls].append(dict(where=describe_level(cls, tuple(sets), kk), shallow=e0, ladder=[e1, e2, e4],
                                            table_rate=al))
                levels.append((cls, tuple(sets), kk, m, al))
                dips.append((cls, tuple(sets), kk, e0, m, al))
                lower(c, 'min_margin_a', m - 0.8 * al)
                lower(c, 'min_margin_b', m - 0.7 * al)
                lower(c, 'min_margin_a_shallow', e0 - 0.8 * al)
                lower(pa, 'min_margin_a', m - 0.8 * al)
                lower(pa, 'min_margin_a_shallow', e0 - 0.8 * al)
                worst[cls].append((m - 0.8 * al, cls, tuple(sets), kk, e0, m, al, conv))
    for cls in ('two', 'chain'):
        multi[cls]['evals'] = sum(r['evals'] for r in rc if r.get('cls') == cls)
        multi[cls]['cpu_seconds'] = sum(r['cpu_seconds'] for r in rc if r.get('cls') == cls)
        multi[cls]['worst'] = [dict(where=describe_level(c2, st, kk), shallow_exponent=e0, asymptotic_exponent=m,
                                    converged=conv, table_rate=al, margin_a=ma)
                               for ma, c2, st, kk, e0, m, al, conv in sorted(worst[cls], key=lambda x: x[0])[:25]]
        multi[cls]['unconverged_levels'] = unconv[cls]
    multi['per_anchor'] = [dict(cls=c2, anchor=an, **v) for (c2, an), v in sorted(per_anchor.items())]
    multi['plan'] = plan
    multi['cpu_seconds'] = sum(r['cpu_seconds'] for r in rc)
    multi['evals'] = sum(r['evals'] for r in rc)
    v = verdict(levels, tol, dips)
    # (d)
    xa = xb = src = None
    if xi_row:
        xa, xb, src = xi_row.get('xi_a'), xi_row.get('xi_b'), 'xi file'
    elif sel_row and sel_row.get('xi_a') is not None:
        xa, xb, src = sel_row['xi_a'], sel_row['xi_b'], 'selection (pilot report, 32,768 points)'
    d = shift_check(xa, xb)
    d['source'] = src
    mp = None
    if rd:
        ok_rows = [x for x in rd['rows'] if None not in (x['lnf_int'], x['lnf_mp'], x['lnf_mp2'])]
        diffs = [abs(x['lnf_int'] - x['lnf_mp2']) for x in ok_rows]
        own = [abs(x['lnf_mp'] - x['lnf_mp2']) for x in ok_rows]
        mp = dict(points=len(rd['rows']), dps=a.mp_dps, max_abs_diff_int_vs_mp2=max(diffs) if diffs else None,
                  max_abs_diff_mp_vs_mp2=max(own) if own else None, rows=rd['rows'], cpu_seconds=rd['cpu_seconds'],
                  agrees=bool(diffs) and len(ok_rows) == len(rd['rows']) and max(diffs) < 1e-8)
    hdr = ra['header']
    parts = [ra] + list(rb) + list(rc)
    return dict(schema=SCHEMA_GRAPH, made_utc=utc(),
                graph=dict(sector=s, L=L, id=g, E=hdr['E'], M=hdr['M'], T=hdr['T'], wa=hdr['wa'], wb=hdr['wb'],
                           sha256=hdr['sha256'], s_G=row.get('s_G'), double_lift=row.get('double_lift')),
                inputs=dict(path=str(inputs), manifest_sha256=man_sha, member_sha256=info['sha256']),
                selection=sel_row, a_rate_line=ra['result'], b_single_scale=single, c_multi_scale=multi, d_shift=d,
                mp_cross_check=mp, verdict=v, params=_params(a),
                cost=dict(cpu_seconds=sum(x['cpu_seconds'] for x in parts) + (rd['cpu_seconds'] if rd else 0.0),
                          evals_b=single['evals'], evals_c=multi['evals'], cpu_seconds_a=ra['cpu_seconds'],
                          cpu_seconds_b=single['cpu_seconds'], cpu_seconds_c=multi['cpu_seconds'],
                          cpu_seconds_mp=rd['cpu_seconds'] if rd else 0.0,
                          max_fixed_point_bits=max([r['max_target'] for r in parts[1:]] or [0]),
                          host=socket.gethostname(), cpu=_cpu(), bigint=BIGINT))


# ---- select --------------------------------------------------------------------------------------------------------
def rate_audit(inputs: Path, L: int) -> dict:
    """{(sector, id): clamped-subset count} from inputs/d3/rate_audit_L<L>.json (sha256 against the manifest)."""
    rel = f'd3/rate_audit_L{L}.json'
    p = inputs / rel
    man = json.loads((inputs / 'manifest.json').read_text())
    if not p.exists():
        return {}
    data = p.read_bytes()
    if hashlib.sha256(data).hexdigest() != (man.get('sha256') or {}).get(rel):
        raise ProbeError(f'{p}: sha256 differs from {inputs / "manifest.json"}')
    out = {}
    for r in json.loads(data):
        sector = r['file'].split('/')[0].split('_', 1)[1]
        out[(sector, int(r['id']))] = dict(clamped=int(sum(r['raw_histogram'].values())), double_lift=r['double_lift_subsets'],
                                           raw_histogram=r['raw_histogram'])
    return out


def shares(report: dict, sigma_rows: list) -> dict:
    """Per (sector, graph): the action-3 variance share sum_t sigma_t sqrt(c_t) / sector sum over L8 graph-campaigns.
    'share_pf': sigma = PF's 4,096-point estimate (sigma_cost.csv). 'share': sigma = max(PF, PF sqrt(V_ratio)) for the
    (campaign, graph) keys whose 32,768-point estimate action 3 used (action3_hold.sigma_from_32768; V_ratio =
    V(32,768)/V(4,096) of the PC rows), the closest reconstruction of action 3's sigma from the committed files."""
    sig = {}
    for r in sigma_rows:
        if int(r['L']) == 8:
            sig[(r['campaign'], r['sector'], int(r['graph']))] = (float(r['sigma']), float(r['cost_per_point']))
    confs = report['action2_confirm']['confirmations'] + report['action2b']['p1c']['confirmations']
    sup = {(x['sector'], x['graph']): x.get('supporting') or {} for x in confs if x.get('supporting')}
    out = {}
    for s in ('free', 'power'):
        keys = [k for k in sig if k[1] == s]
        src = set((report.get('action3_hold') or {}).get(s, {}).get('sigma_from_32768') or [])

        def up(k):
            v = sig[k][0]
            vr = (sup.get((s, k[2])) or {}).get(k[0], {}).get('V_ratio')
            if f'{k[0]}:{k[2]}' in src and vr:
                v = max(v, v * math.sqrt(vr))
            return v
        tot_pf = sum(sig[k][0] * math.sqrt(sig[k][1]) for k in keys)
        tot = sum(up(k) * math.sqrt(sig[k][1]) for k in keys)
        for k in keys:
            o = out.setdefault((s, k[2]), dict(share=0.0, share_pf=0.0))
            o['share'] += up(k) * math.sqrt(sig[k][1]) / tot
            o['share_pf'] += sig[k][0] * math.sqrt(sig[k][1]) / tot_pf
    return out


def select(a: argparse.Namespace) -> int:
    rp = Path(a.pilot_report)
    data = rp.read_bytes()
    rep = json.loads(data)
    if rep.get('schema') != PILOT_REPORT_SCHEMA:
        raise ProbeError(f'{rp}: schema {rep.get("schema")!r} is not {PILOT_REPORT_SCHEMA}')
    sc = Path(a.sigma_cost) if a.sigma_cost else rp.parent / Path((rep.get('side_files') or {}).get('sigma_cost', 'sigma_cost.csv')).name
    with open(sc, newline='') as f:
        sigma_rows = list(csv.DictReader(f))
    inputs = members.inputs_dir(a.inputs)
    inv = members.inventory(inputs)
    inv8 = {s: {r['id']: r for r in inv[s]['8']} for s in ('free', 'power')}
    audit = rate_audit(inputs, 8)
    sh = shares(rep, sigma_rows)
    conf = rep['action2_confirm']['confirmations']
    piv = {(x['sector'], x['graph']) for x in rep['action2_confirm']['possible_infinite_variance']}
    by = {(x['sector'], x['graph']): x for x in conf}
    graphs = []

    def row(s, g, role, why, rank=None):
        x = by.get((s, g)) or {}
        r = inv8[s][g]
        ccs = x.get('cross_campaign_shift') or {}
        au = audit.get((s, g)) or {}
        return dict(sector=s, L=8, id=g, role=role, why=why, rank=rank, share=sh.get((s, g), {}).get('share'),
                    share_pf=sh.get((s, g), {}).get('share_pf'), xi_mean_32768=x.get('xi_mean_32768'),
                    xi_a=ccs.get('xi_a'), xi_b=ccs.get('xi_b'), face_model_xi_b=ccs.get('face_model_xi_b'),
                    possible_infinite_variance=(s, g) in piv, double_lift=r['double_lift'], monomials=r['monomials'],
                    terms=r['terms'], s_G=r['s_G'], clamped=au.get('clamped'), raw_histogram=au.get('raw_histogram'))
    keyf = {'share': lambda s, g: -(sh.get((s, g), {}).get('share') or 0.0),
            'share_pf': lambda s, g: -(sh.get((s, g), {}).get('share_pf') or 0.0),
            'xi': lambda s, g: -(by[(s, g)].get('xi_mean_32768') or 0.0)}[a.rank_by]
    for s in ('free', 'power'):
        cand = sorted([g for (ss, g) in piv if ss == s], key=lambda g: (keyf(s, g), g))
        chosen = cand[:a.top]
        for i, g in enumerate(chosen, 1):
            graphs.append(row(s, g, 'top', f'PC-confirmed possible infinite variance (two-campaign mean xi(32,768) '
                                           f'{by[(s, g)]["xi_mean_32768"]:.3f} > {XI_CONFIRM}); rank {i} of {len(cand)} in '
                                           f'the {s} sector by {a.rank_by}', i))
        if a.class_reps:
            classes = collections.defaultdict(list)
            for g in cand:
                classes[inv8[s][g]['double_lift']].append(g)
            for dl in sorted(classes):
                if dl == 0:
                    continue
                for g in [g for g in classes[dl] if g not in chosen][:max(0, a.class_reps - sum(
                        1 for h in chosen if inv8[s][h]['double_lift'] == dl))]:
                    chosen.append(g)
                    graphs.append(row(s, g, 'class', f'action-3b class {s}|double_lift={dl}: its highest-ranked member '
                                                     f'by {a.rank_by} not already chosen', cand.index(g) + 1))
        if a.controls:
            unc = [x for x in conf if x['sector'] == s and not x.get('confirmed') and x.get('xi_mean_32768') is not None
                   and inv8[s][x['graph']]['double_lift'] == 0]
            if unc:
                med = float(np.median([inv8[s][x['graph']]['cost'] for x in unc]))
                pool = sorted([x for x in unc if inv8[s][x['graph']]['cost'] <= med],
                              key=lambda x: (x['xi_mean_32768'], x['graph']))
                for x in pool[:a.controls]:
                    graphs.append(row(s, x['graph'], 'control',
                                      f'light control: PC-checked, not confirmed (xi(32,768) mean {x["xi_mean_32768"]:.3f} '
                                      f'<= {XI_CONFIRM}), no double-lift subset, cost M T = {inv8[s][x["graph"]]["cost"]} '
                                      f'<= the median {med:.0f} of the unconfirmed', None))
    doc = dict(schema=SCHEMA_SELECTION, made_utc=utc(), purpose='L8 margin re-derivation (RECON (a)-(e); user decision '
               '2026-10-08): the worst flagged graphs per sector plus light controls',
               rule=dict(top=a.top, controls=a.controls, class_reps=a.class_reps, rank_by=a.rank_by,
                         share_definition=shares.__doc__.split('\n', 1)[1].strip()),
               sources=dict(pilot_report=dict(path=str(rp), sha256=hashlib.sha256(data).hexdigest(),
                                              made_utc=rep.get('made_utc'), pc=rep.get('pc')),
                            sigma_cost=dict(path=str(sc), sha256=sha256_file(sc)),
                            inputs_manifest_sha256=sha256_file(inputs / 'manifest.json')),
               counts={s: dict(possible_infinite_variance=sum(1 for (ss, _) in piv if ss == s),
                               chosen=sum(1 for r in graphs if r['sector'] == s)) for s in ('free', 'power')},
               graphs=graphs)
    outp = Path(a.out)
    if outp.exists():
        raise ProbeError(f'{outp} exists (never overwritten)')
    dump(outp, doc)
    print(json.dumps(dict(selection=str(outp), graphs=[f'{r["sector"]}:{r["L"]}:{r["id"]} {r["role"]}' for r in graphs]),
                     indent=1))
    return 0


# ---- report --------------------------------------------------------------------------------------------------------
def _f(x, d=3):
    return '-' if x is None else (f'{x:+.{d}f}' if isinstance(x, float) else str(x))


def _key(x) -> str:
    g = x['graph']
    return f'{g["sector"]}:{g["L"]}:{g["id"]}'


def report(a: argparse.Namespace) -> int:
    docs = []
    for d in a.dirs:
        d = Path(d)
        files = sorted(d.glob('*_L*_G*.json')) if d.is_dir() else [d]
        for f in files:
            x = json.loads(f.read_text())
            if x.get('schema') == SCHEMA_GRAPH:
                docs.append(x)
    if not docs:
        raise ProbeError('no per-graph probe JSON found')
    order = {'top': 0, 'class': 1, 'control': 2}
    docs.sort(key=lambda x: (x['graph']['sector'], order.get((x.get('selection') or {}).get('role'), 3),
                             (x.get('selection') or {}).get('rank') or 0, x['graph']['L'], x['graph']['id']))
    L = ['# Margin re-derivation: summary', '',
         f'{len(docs)} graphs; made {utc()} by tools/margin_probe8.py report. RECON "Margin re-derivation" (a)-(e): '
         '(a) rate line recomputed from masks and terms; (b) single-scale exponents at every clamped subset; (c) '
         'two-scale flags and chains of >= 3 scales around the anchors (double-lift subsets, then the tightest '
         'single-scale faces); (d) the cross-campaign shift. Every level is measured at margin_probe\'s scales '
         '("shallow") and on a ladder towards its asymptotic exponent (the scanned level pushed --depth, 2 and 4 '
         '--depth decades deeper). A deficit is an asymptotic level exponent m below its proposal rate r (0.8 alpha, '
         'campaign a; 0.7 alpha, campaign b) by more than the tolerance; then a = r/(r - m). A dip is a level below r '
         'only at the shallow scales: a peaked, sub-asymptotic weight, not an infinite variance. Margins are m - 0.8 alpha.',
         '', '| graph | role | M | T | dl | (a) mism. | clamped | (b) margin | flags | chains | (c) margin | shallow '
         'margin | dips (a) | unconv. | xi_a / xi_b | (d) closer to | verdict |', '|' + '---|' * 17]
    nd = 0
    shifts = []
    for x in docs:
        g = x['graph']
        sel = x.get('selection') or {}
        b, c, d = x['b_single_scale'], x['c_multi_scale'], x['d_shift']
        cm = [v for v in (c['two']['min_margin_a'], c['chain']['min_margin_a']) if v is not None]
        cs = [v for v in (c['two']['min_margin_a_shallow'], c['chain']['min_margin_a_shallow']) if v is not None]
        nd += x['verdict']['status'] == 'deficit'
        if d.get('available') and sel.get('role') != 'control':
            shifts.append((d['observed_shift'], d['face_model_shift']))
        L.append(f'| {_key(x)} | {sel.get("role", "-")} | {g["M"]} | {g["T"]} | {x["a_rate_line"]["double_lift"]} | '
                 f'{x["a_rate_line"]["mismatches"]} | {b["clamped"]} | {_f(b["min_margin_a"])} | '
                 f'{c["plan"]["two_scale"]["probed"]} | {sum(p["probed"] for p in c["plan"]["chains"])} | '
                 f'{_f(min(cm) if cm else None)} | {_f(min(cs) if cs else None)} | '
                 f'{x["verdict"]["campaigns"]["a"]["shallow_dips"]} | '
                 f'{b["unconverged"] + c["two"]["unconverged"] + c["chain"]["unconverged"]} | '
                 f'{_f(d.get("xi_a"), 2)} / {_f(d.get("xi_b"), 2)} | {d.get("closer_to", "-")} | '
                 f'{"**deficit**" if x["verdict"]["status"] == "deficit" else "none"} |')
    L += ['', f'**Deficits: {nd} of {len(docs)} graphs.**', '']
    if shifts:
        o = np.array([s[0] for s in shifts])
        fm = np.array([s[1] for s in shifts])
        se = f'{float(o.std(ddof=1) / math.sqrt(len(o))):.3f}' if len(o) > 1 else 'n/a'
        L += [f'(d) over the {len(o)} probed non-control graphs with pilot xi: mean xi_b - xi_a = {o.mean():+.3f} +- {se} '
              f'(SE), against {fm.mean():+.3f} for the face model a = r/(r - m) at rates 0.8 / 0.7 and 0 for no rate '
              'dependence.', '']
    L += ['## Verdicts', '']
    for x in docs:
        dips = x['verdict']['campaigns']['a']
        extra = (f' Shallow dips below 0.8 alpha: {dips["shallow_dips"]} (deepest: {dips["worst_dips"][0]["where"]}, '
                 f'{dips["worst_dips"][0]["shallow_exponent"]:.3f} shallow, {dips["worst_dips"][0]["asymptotic_exponent"]:.3f} '
                 f'asymptotic, rate {dips["worst_dips"][0]["proposal_rate"]:.3f}).' if dips['shallow_dips'] else '')
        L.append(f'- {_key(x)}: {x["verdict"]["text"]}.{extra}')
    L += ['', '## Checks', '']
    for x in docs:
        ar, b, c = x['a_rate_line'], x['b_single_scale'], x['c_multi_scale']
        mp = x.get('mp_cross_check') or {}
        L.append(f'- {_key(x)}: (a) {ar["mismatches"]} mismatches of {ar["subsets"]} subsets, package raw line '
                 f'{"agrees" if ar.get("package_raw_agrees") else "DIFFERS"}, double-lift {ar["double_lift"]} '
                 f'(inventory {ar.get("inventory_double_lift")}); (b) {b["resolved"]}/{b["clamped"]} resolved, '
                 f'{len(b["below_table_rate"])} below the table rate, margin_probe-compatible min(e - alpha) '
                 f'{_f(b["compat"]["min_diff"])}, equal {b["compat"]["equal"]}, below 0.8 alpha {b["compat"]["below_08"]}; '
                 f'(c) {c["two"]["levels"]} two-scale levels (sampled: {c["plan"]["two_scale"]["sampled"]}), '
                 f'{c["chain"]["levels"]} chain levels, {c["two"]["unresolved"] + c["chain"]["unresolved"]} unresolved, '
                 f'{c["two"]["sign_changes"] + c["chain"]["sign_changes"]} sign changes; mpmath check: max |ln f| diff '
                 f'{"-" if mp.get("max_abs_diff_int_vs_mp2") is None else format(mp["max_abs_diff_int_vs_mp2"], ".1e")} over {mp.get("points", 0)} points '
                 f'({"agrees" if mp.get("agrees") else ("n/a" if not mp.get("points") else "CHECK")}); '
                 f'non-finite values {len(x.get("nonfinite") or [])}; '
                 f'{x["cost"]["cpu_seconds"]:.0f} cpu-s')
    text = '\n'.join(L) + '\n'
    if a.out:
        if Path(a.out).exists():
            raise ProbeError(f'{a.out} exists (never overwritten)')
        Path(a.out).write_text(text)
    else:
        print(text)
    if a.json:
        dump(Path(a.json), dict(schema=SCHEMA_REPORT, made_utc=utc(), deficits=nd, graphs=[dict(
            key=_key(x), role=(x.get('selection') or {}).get('role'), verdict=x['verdict']['status'],
            text=x['verdict']['text'], shallow_dips_a=x['verdict']['campaigns']['a']['shallow_dips'],
            cpu_seconds=x['cost']['cpu_seconds']) for x in docs]))
    return 0


# ---- estimate ------------------------------------------------------------------------------------------------------
def estimate(a: argparse.Namespace) -> int:
    """Core-seconds per graph of a selection, from the timings of earlier probe runs (--calibration directories).
    Per phase ((b) single scale, (c) two-scale flags, (c) chains) the cpu-seconds per evaluation t = c0 + c1 T
    (non-negative least squares over the calibration graphs, weighted by the square root of their evaluations; the
    cost of an evaluation grows with the number of forest terms T and, for chains, with the anchor's size, while M
    enters only the per-flag preparation, a few per cent), and
    the evaluations per graph: (b) e_b x the clamped subsets (the selection's rate-audit count), (c) the budgets:
    --max-flags flags x 2 levels and --max-chains chains x --chain-levels levels, at the calibration's evaluations per
    level. The (c) count is an upper bound (a smaller population is probed whole). --speed: cluster core-seconds per
    calibration core-second."""
    from scipy.optimize import nnls
    pts = {'b': [], 'two': [], 'chain': []}
    per = {'b': [0, 0], 'two': [0, 0], 'chain': [0, 0]}   # evaluations, units (clamped subsets or levels)
    ncal = 0
    for d in a.calibration:
        for f in sorted(Path(d).glob('*_L*_G*.json')):
            x = json.loads(f.read_text())
            if x.get('schema') != SCHEMA_GRAPH:
                continue
            ncal += 1
            T, M = x['graph']['T'], x['graph']['M']
            b, c = x['b_single_scale'], x['c_multi_scale']
            for ph, ev, sec, units in (('b', b['evals'], b['cpu_seconds'], b['clamped']),
                                       ('two', c['two'].get('evals', 0), c['two'].get('cpu_seconds', 0.0), c['two']['levels']),
                                       ('chain', c['chain'].get('evals', 0), c['chain'].get('cpu_seconds', 0.0), c['chain']['levels'])):
                if ev and sec:
                    pts[ph].append((T, M, ev, sec / ev))
                    per[ph][0] += ev
                    per[ph][1] += units
    fit = {}
    for ph, ps in pts.items():
        if len(ps) < 2:
            raise ProbeError(f'estimate: fewer than two calibration graphs with a {ph} phase')
        w = np.sqrt([p[2] for p in ps])
        A = np.array([[1.0, p[0]] for p in ps]) * w[:, None]
        coef = nnls(A, np.array([p[3] for p in ps]) * w)[0]
        fit[ph] = dict(c0=float(coef[0]), c1_T=float(coef[1]), points=len(ps),
                       evals_per_unit=per[ph][0] / per[ph][1] if per[ph][1] else None,
                       T_range=[min(p[0] for p in ps), max(p[0] for p in ps)], M_range=[min(p[1] for p in ps), max(p[1] for p in ps)])

    def t(ph, T, M):
        f = fit[ph]
        return (f['c0'] + f['c1_T'] * T) * a.speed
    sel = json.loads(Path(a.selection).read_text())
    if sel.get('schema') != SCHEMA_SELECTION:
        raise ProbeError(f'{a.selection}: not a {SCHEMA_SELECTION} file')
    rows = []
    for r in sel['graphs']:
        T, M, cl = r['terms'], r['monomials'], r.get('clamped') or 0
        sb = cl * fit['b']['evals_per_unit'] * t('b', T, M)
        st = 2 * a.max_flags * fit['two']['evals_per_unit'] * t('two', T, M) if cl else 0.0
        sc = a.max_chains * a.chain_levels * fit['chain']['evals_per_unit'] * t('chain', T, M) if cl else 0.0
        rows.append(dict(graph=f'{r["sector"]}:{r["L"]}:{r["id"]}', role=r['role'], T=T, M=M, clamped=cl,
                         core_seconds=dict(b=sb, two=st, chain=sc, total=sb + st + sc)))
    tot = sum(x['core_seconds']['total'] for x in rows)
    big = max(x['core_seconds']['total'] for x in rows)
    print(json.dumps(dict(calibration_graphs=ncal, fit=fit, unit='core-seconds per evaluation = (c0 + c1 T) x speed',
                          assumptions=dict(max_flags=a.max_flags, max_chains=a.max_chains, chain_levels=a.chain_levels,
                                           speed=a.speed, note='(c) at the full budgets: an upper bound'),
                          graphs=rows, total_core_hours=tot / 3600, largest_graph_core_hours=big / 3600, cores=a.cores,
                          wall_hours=tot / 3600 / (a.cores * a.efficiency), efficiency=a.efficiency), indent=1))
    return 0


# ---- CLI -----------------------------------------------------------------------------------------------------------
def _ints(s):
    return tuple(int(x) for x in s.split(','))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('select')
    s.add_argument('--out', required=True)
    s.add_argument('--pilot-report', default=str(PILOT_EVIDENCE / 'pilot_report.json'))
    s.add_argument('--sigma-cost')
    s.add_argument('--inputs')
    s.add_argument('--top', type=int, default=12)
    s.add_argument('--controls', type=int, default=2)
    s.add_argument('--class-reps', type=int, default=0)
    s.add_argument('--rank-by', choices=('share', 'share_pf', 'xi'), default='share')
    p = sub.add_parser('probe')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--selection')
    g.add_argument('--graphs', help='sector:L:id,...')
    p.add_argument('--out', required=True)
    p.add_argument('--inputs')
    p.add_argument('--scratch', help='where the members are extracted (default C8_SCRATCH, else TMPDIR)')
    p.add_argument('--workers', type=int, default=max(1, (len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity')
                                                         else os.cpu_count() or 1)))
    p.add_argument('--xi', help='JSON {"sector:L:id": {"xi_a": x, "xi_b": y}} for (d) (default: the selection\'s)')
    p.add_argument('--anchors', help='JSON {"sector:L:id": ["0x00ff", ...]}: extra anchors (e.g. from argmax points)')
    p.add_argument('--limit', type=int, default=0)
    p.add_argument('--skip-existing', action='store_true')
    p.add_argument('--base-seed', type=int, default=DEFAULTS['base_seed'])
    p.add_argument('--single', type=_ints, default=DEFAULTS['single'], help='decades lo,hi (default 10,14)')
    p.add_argument('--depth', type=int, default=DEFAULTS['depth'],
                   help='decades the scanned level is pushed deeper for the asymptotic exponent (0: off)')
    p.add_argument('--two', type=_ints, default=DEFAULTS['two'], help='lo,hi,fixed (default 9,13,11)')
    p.add_argument('--chain', type=_ints, default=DEFAULTS['chain'], help='lo,hi,fixed (default 6,8,4)')
    p.add_argument('--tol', type=float, default=DEFAULTS['tol'])
    p.add_argument('--tight-anchors', type=int, default=DEFAULTS['tight_anchors'])
    p.add_argument('--max-flags', type=int, default=DEFAULTS['max_flags'])
    p.add_argument('--max-chains', type=int, default=DEFAULTS['max_chains'])
    p.add_argument('--sample-seed', type=int, default=DEFAULTS['sample_seed'])
    p.add_argument('--min-bits', type=int, default=DEFAULTS['min_bits'])
    p.add_argument('--mp-check', type=int, default=DEFAULTS['mp_check'])
    p.add_argument('--mp-dps', type=int, default=DEFAULTS['mp_dps'])
    p.add_argument('--chunk-single', type=int, default=48)
    p.add_argument('--chunk-flags', type=int, default=96)
    p.add_argument('--chunk-chains', type=int, default=24)
    r = sub.add_parser('report')
    r.add_argument('dirs', nargs='+')
    r.add_argument('--out')
    r.add_argument('--json')
    e = sub.add_parser('estimate')
    e.add_argument('--selection', required=True)
    e.add_argument('--calibration', nargs='+', required=True)
    e.add_argument('--max-flags', type=int, default=DEFAULTS['max_flags'])
    e.add_argument('--max-chains', type=int, default=DEFAULTS['max_chains'])
    e.add_argument('--chain-levels', type=float, default=6.0, help='mean levels per chain (uniform ordered partitions '
                   'of an 8-edge anchor into >= 3 blocks: 6.0)')
    e.add_argument('--speed', type=float, default=1.0, help='cluster core-seconds per calibration core-second')
    e.add_argument('--cores', type=int, default=64)
    e.add_argument('--efficiency', type=float, default=0.85, help='parallel efficiency of the pool')
    a = ap.parse_args(argv)
    try:
        return {'select': select, 'probe': probe, 'report': report, 'estimate': estimate}[a.cmd](a)
    except (ProbeError, members.MemberError, OSError, KeyError) as ex:
        print(f'margin_probe8: {ex}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
