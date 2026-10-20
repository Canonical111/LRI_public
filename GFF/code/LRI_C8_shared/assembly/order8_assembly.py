#!/usr/bin/env python3
"""General-d finite-scheme fixed-point assembly at order 7 or 8 (shared by LRI_C8_D2_HPC and LRI_C8_D3_HPC).

Owner: session C63d (LRI_C8_shared/assembly). Vendored byte-identically by both C8 packages, with its hash pinned.

Conventions are those of the two delivered order-7 functions, LRI_C7_D3_HPC/tools/assemble.py:41-57 and
LRI_C7_D2_HPC/tools/assemble.py:28-43, which differ only in the constant ga[0] += d/2:

  beta(g,z)  = -z g + sum_{L>=1} b_L(z) g^(L+1),   gamma_r(g,z) = sum_{L>=1} c_L(z) g^L,
  b_1 = 3, c_1 = 1, b_2 = B2(z), c_2 = B2(z)/6,    Delta_E = d/2 - eps/2 + gamma_r(g_*, eps),
  g_*(eps) = (eps - sum_{L=2}^{order} b_L(eps) g_*^L)/3  mod eps^(order+1)  (order+1 iterations from g = 0).

Inputs:
  vals    {L: vector} for L = 3..order. The vector has 2k entries, k = order+1-L: the b_L Taylor jet z^0..z^(k-1)
          followed by the c_L jet z^0..z^(k-1). Real or complex (complex step), or object/Fraction (exact mode).
          Missing loops count as zero (the delivered prefix-plan behaviour).
  B2      two-loop jet b_2(z), z^0..z^(order-2) at least; extra entries are ignored (truncated, so a z^0..z^6 B2
          gives bit-identical order-7 results to its z^0..z^5 prefix). Floats, complex, the strings of
          two_loop.json (read as float, as delivered), or rationals for exact mode (see below). A B2 in exact mode
          is accepted by coefficients() and affinity_gate() only; jacobians() and sector_assembly() need a real
          float B2 (complex step) and raise ValueError otherwise (repair round 2). A plain list or array of ints is
          NOT exact mode: numpy makes it an int64 array, which takes the float path (float64 output, correct
          numbers, accepted by jacobians()).
  order   7 or 8.
  half_d  d/2: 1 for d=2, 1.5 for d=3 (C_0 = d/2); an int, float or Fraction.
Output: the array C_0..C_order of Delta_E(d, eps), eps = 2s - d.

Exact mode (repair round 1; the interface of LRI_C8_D2_HPC_loop/PLAN.md:446-448): when a vals vector has object
dtype, or B2 has object dtype with at least one int or Fraction element (an object array of Fractions or Python
ints, or a list that numpy turns into an object array, i.e. one holding a Fraction), every input number (ints,
Fractions and floats, the latter by their exact binary value) becomes a Fraction and the same algorithm runs in
exact rational arithmetic, with the constants 0, 1/2 and d/2 as Fractions. The output is then an object array of
Fractions. A list or array of plain ints alone is int64, not object, and stays on the float path (repair round 3,
documentation only). The float/complex path is unchanged (it never enters the exact branch).

At order 7 coefficients() and jacobians() perform the same floating-point operations in the same order as the
delivered functions, so they agree with them bit for bit on identical inputs on one machine (tests). The covariance
helpers repeat the delivered assemble.py arithmetic (D3 lines 88-102, D2 lines 92-106) with the order as a
parameter.

Gates: top_slot_gate, loop7_gate, affinity_gate (float on Jacobians; exact second differences when a `means` vector
has object dtype or B2 is in exact mode, see _b2_holds_rational).
ms8_rows/ms8_value: the constant-coefficient MS polynomial 19683 C8 (b_2 = -6A, c_2 = -A; or general b_2, c_2) as a
fixed table, checked in the tests against the independent sympy derivation of exact_check.py.
"""
from __future__ import annotations
import numbers
from fractions import Fraction
import numpy as np

ORDERS = (7, 8)
COMPLEX_STEP = 1e-20  # the delivered step (assemble.py jacobians)


def slots(order: int) -> dict:
    """Number of Taylor slots k = order+1-L per sampled loop L = 3..order (vector length 2k)."""
    _check_order(order)
    return {L: order + 1 - L for L in range(3, order + 1)}


def _check_order(order) -> None:
    if order not in ORDERS:
        raise ValueError(f'order must be 7 or 8, got {order!r}')


def _is_rational(x) -> bool:
    return isinstance(x, numbers.Rational) and not isinstance(x, (bool, np.bool_))


def _exact_array(a) -> np.ndarray:
    """Object array of Fractions: ints and Fractions as they are, floats by their exact binary value; anything else
    (e.g. complex) is left unchanged."""
    out = []
    for x in np.asarray(a, dtype=object).tolist():
        if _is_rational(x) or isinstance(x, float): x = Fraction(x)
        elif isinstance(x, np.floating): x = Fraction(float(x))
        out.append(x)
    return np.array(out, dtype=object)


def _b2(B2, order):
    B2 = np.asarray(B2)
    if B2.ndim != 1 or len(B2) < order - 1:
        raise ValueError(f'B2 needs at least {order - 1} Taylor entries (z^0..z^{order - 2}) at order {order}')
    if B2.dtype.kind in 'US' or (B2.dtype.kind == 'O' and not any(_is_rational(x) for x in B2.tolist())):
        # strings of two_loop.json (or Python floats/complex in an object array): float, or complex where given
        B2 = np.asarray([complex(x) if isinstance(x, complex) else float(x) for x in B2.tolist()])
    elif B2.dtype.kind == 'O':
        B2 = _exact_array(B2)  # holds a rational: exact mode
    return B2[:order - 1]


def coefficients(vals: dict, B2, order: int, half_d) -> np.ndarray:
    _check_order(order)
    if isinstance(half_d, (bool, np.bool_)) or not isinstance(half_d, numbers.Real):
        raise ValueError('half_d must be d/2 as an int, float or Fraction (1 for d=2, 1.5 or Fraction(3, 2) for d=3)')
    B2 = _b2(B2, order)
    dtype = np.result_type(*[np.asarray(v).dtype for v in vals.values()]) if vals else np.dtype(float)
    if np.iscomplexobj(B2):
        dtype = np.result_type(dtype, B2.dtype)  # B2 complex step only; never on the delivered (real B2) path
    if B2.dtype == object:
        dtype = np.dtype(object)
    if dtype == object:  # exact mode (module docstring); the float/complex path below is the delivered one
        vals = {L: _exact_array(a) for L, a in vals.items()}; B2 = _exact_array(B2)
        half_d = Fraction(half_d) if (_is_rational(half_d) or isinstance(half_d, float)) else Fraction(float(half_d))
        zero1, half = np.array([Fraction(0)], dtype=object), Fraction(1, 2)
        def zeros(n): return np.array([Fraction(0)] * n, dtype=object)
    else:
        if not isinstance(half_d, (int, float, np.integer, np.floating)): half_d = float(half_d)  # e.g. Fraction(3, 2)
        zero1, half = np.zeros(1), .5
        def zeros(n): return np.zeros(n, dtype=dtype)
    N = order + 1
    b = {1: np.array([3], dtype=dtype), 2: B2.astype(dtype)}; c = {1: np.array([1], dtype=dtype), 2: B2.astype(dtype) / 6}
    for L, a in vals.items():
        a = np.asarray(a); k = N - L
        if L not in range(3, N) or a.shape != (2 * k,): raise ValueError('Wrong loop jet shape')
        b[L] = a[:k]; c[L] = a[k:]
    def mul(x, y): return np.convolve(x, y)[:N]
    g = zeros(N); e = g.copy(); e[1] = 1
    for _ in range(N):
        gp = g.copy(); tmp = g.copy() * 0
        for L in range(2, N): gp = mul(gp, g); tmp += mul(b.get(L, zero1), gp)
        g = (e - tmp) / 3
    ga = zeros(N); gp = ga.copy(); gp[0] = 1
    for L in range(1, N): gp = mul(gp, g); ga += mul(c.get(L, zero1), gp)
    ga[0] += half_d; ga[1] -= half; return ga


def _b2_holds_rational(B2, order) -> bool:
    """True when B2 would put coefficients() into exact mode: B2 has object dtype with at least one int or Fraction
    element (an object array, or a list that numpy turns into one, e.g. one holding a Fraction). False for a plain
    list or array of ints (int64: float path), floats, complex or strings."""
    return _b2(B2, order).dtype == object


def jacobians(means: dict, B2, order: int, half_d) -> dict:
    """Complex-step Jacobians {L: (order+1) x 2k}, column j = d C / d means[L][j] (the delivered algorithm).

    B2 must be real float (or the strings of two_loop.json; an int64 list or array is read as float). A B2 in exact
    mode (_b2_holds_rational: object dtype with an int or Fraction element) would switch coefficients() into exact
    mode, where the imaginary step is lost (numpy's .imag of an object array is 0), and a complex B2 with a nonzero
    imaginary part would add its own step; both raise ValueError (repair round 2). Rational `means` are read as
    complex floats, as in the delivered code."""
    _check_order(order)
    if _b2_holds_rational(B2, order):
        raise ValueError('jacobians: B2 holds a rational (exact mode); the complex step needs a float B2. Pass float '
                         'B2, or use exact second differences (affinity_gate exact mode, exact_check.py).')
    if np.iscomplexobj(_b2(B2, order)) and np.any(_b2(B2, order).imag != 0):
        raise ValueError('jacobians: B2 has a nonzero imaginary part; the complex step needs a real B2')
    out = {}
    for L, a in means.items():
        columns = []
        for j in range(len(a)):
            tmp = {k: np.asarray(v, dtype=complex).copy() for k, v in means.items()}; tmp[L][j] += 1e-20j
            columns.append(coefficients(tmp, B2, order, half_d).imag / 1e-20)
        out[L] = np.array(columns).T
    return out


SECTORS = ('free', 'power')  # the delivered load_campaign order; results are always keyed and summed in this order


def _loop_set(loops, where: str, max_order: int) -> range:
    """The delivered loop-set rule (LRI_C7_D3_HPC/tools/assemble.py:81-82; LRI_C7_D2_HPC/tools/assemble.py:89 has
    K = 7 only): the loops are exactly 3..K, 5 <= K <= max_order, with no repeats. Returns range(3, K+1)."""
    lp = list(loops)
    ok = bool(lp) and all(isinstance(L, (int, np.integer)) and not isinstance(L, (bool, np.bool_)) for L in lp)
    K = int(max(lp)) if ok else None
    if not ok or K not in range(5, max_order + 1) or sorted(int(L) for L in lp) != list(range(3, K + 1)):
        raise ValueError(f'{where}: the loops must be exactly 3..K with 5 <= K <= {max_order} (the delivered rule '
                         f'"Need loops 3..K"), got {sorted(lp, key=str)}')
    return range(3, K + 1)


def campaign_moments(ar: dict, loops) -> tuple[dict, dict]:
    """Equal-weight campaign means and covariances of the campaign-mean vectors, as delivered:
    ar[sector][campaign][L] is a (replicates x 2k) array; two campaigns with fixed weights 1/2.
    The weights 1/2 (means) and 1/4 (covariances) are right only for exactly two campaigns, so, as in the delivered
    wrappers (LRI_C7_D3_HPC/tools/assemble.py:76-85, LRI_C7_D2_HPC/tools/assemble.py:85-91), ValueError is raised
    unless the sectors are {'free', 'power'}, each has exactly the campaigns {'a', 'b'}, and every campaign holds
    every loop as a finite 2-d array with at least 2 replicates (repair round 2).
    Loop-set rule (repair round 3; D3 assemble.py:81-82, D2 :89): `loops` must be exactly 3..K with 5 <= K <= 8, in
    any iteration order, and every campaign must hold exactly those loops. A loop in `ar` outside `loops` (e.g.
    order-8 data with loops=range(3, 8)) or a missing one raises ValueError instead of being dropped.
    The results are keyed free, power and L = 3..K whatever the key order of `ar` or `loops`, so they compose with
    sector_assembly for any input order (repair round 3); the arithmetic is the delivered one."""
    loops = _loop_set(loops, 'campaign_moments', max(ORDERS))
    if not isinstance(ar, dict) or set(ar) != set(SECTORS): raise ValueError("campaign_moments: both sectors 'free' and 'power' are required")
    for s in SECTORS:
        if not isinstance(ar[s], dict) or set(ar[s]) != {'a', 'b'}:
            raise ValueError(f"campaign_moments: sector {s!r} needs exactly the two campaigns 'a' and 'b' (weights 1/2), got {sorted(ar[s]) if isinstance(ar[s], dict) else type(ar[s]).__name__}")
        for t, x in ar[s].items():
            if not isinstance(x, dict) or set(x) != set(loops):
                raise ValueError(f'campaign_moments: {s}/{t} holds loops {sorted(x, key=str) if isinstance(x, dict) else type(x).__name__}, '
                                 f'need exactly {list(loops)} (loop-set rule: a loop outside `loops` is never dropped silently)')
            for L in loops:
                a = np.asarray(x[L])
                if a.ndim != 2 or len(a) < 2 or not np.isfinite(a).all(): raise ValueError(f'campaign_moments: invalid replicate data in {s}/{t}/L{L}')
    means = {s: {L: sum(np.asarray(x[L]).mean(0) for x in ar[s].values()) / 2 for L in loops} for s in SECTORS}
    vc = {s: {L: sum(np.cov(np.asarray(x[L]), rowvar=False, ddof=1) / len(x[L]) for x in ar[s].values()) / 4 for L in loops} for s in SECTORS}
    return means, vc


def sector_assembly(means: dict, vc: dict, B2, order: int, half_d) -> dict:
    """C = F(f+p), C_pf = F(f), Delta_p = F(f+p) - F(f) and their propagated covariances (note eq. c7d2:covariance):
      V_C = sum_L J_L (V_f + V_p) J_L^T,
      V_Delta = sum_L (J_L - J_fL) V_f (J_L - J_fL)^T + sum_L J_L V_p J_L^T,
      V_pf = sum_L J_fL V_f J_fL^T,  cross = sum_L J_fL V_f (J_L - J_fL)^T,  V_C = V_pf + V_Delta + cross + cross^T.
    means/vc: {'free': {L: ...}, 'power': {L: ...}}, the two sectors in either key order (they are always combined in
    the delivered order free, power, and loops in the order 3..K, so the result does not depend on the key order;
    repair round 3). B2 must be float (jacobians() refuses an exact-mode B2). ValueError otherwise.
    Loop-set rule (repair round 3; LRI_C7_D3_HPC/tools/assemble.py:81-82): all four blocks hold the same loops,
    exactly 3..K with 5 <= K <= order. K < order is a prefix plan: as in the delivered D3 calculate (:124-133),
    nothing above order K is reported. Every order-indexed array (coefficients, errors, covariances, the rows of
    J/Jf and the contribution matrices) is cut to orders 0..K, and the result carries max_order = K and the loops."""
    _check_order(order)
    if not (isinstance(means, dict) and isinstance(vc, dict) and set(means) == set(SECTORS) == set(vc)):
        raise ValueError("means and vc need exactly the sectors 'free' and 'power'")
    # repair round 2: the loop keys must match across sectors and between means and vc (a missing or extra loop would
    # otherwise fail with KeyError or silently drop a covariance block)
    if not (set(means['free']) == set(means['power']) == set(vc['free']) == set(vc['power'])):
        raise ValueError(f"means and vc need the same loops in both sectors: means {[sorted(means[s], key=str) for s in SECTORS]}, vc {[sorted(vc[s], key=str) for s in SECTORS]}")
    loops = _loop_set(means['free'], 'sector_assembly', order); K = loops[-1]
    m = {L: means['free'][L] + means['power'][L] for L in loops}
    J = jacobians(m, B2, order, half_d); Jf = jacobians({L: means['free'][L] for L in loops}, B2, order, half_d)
    mu = coefficients(m, B2, order, half_d); pf = coefficients(means['free'], B2, order, half_d); delta = mu - pf
    contributions = {s: {L: J[L] @ vc[s][L] @ J[L].T for L in m} for s in SECTORS}
    cov = sum(sum(v.values()) for v in contributions.values())
    df = {L: J[L] - Jf[L] for L in m}
    dcov = sum(df[L] @ vc['free'][L] @ df[L].T + contributions['power'][L] for L in m)
    cross = sum(Jf[L] @ vc['free'][L] @ df[L].T for L in m)
    pcov = sum(Jf[L] @ vc['free'][L] @ Jf[L].T for L in m)
    if not np.allclose(cov, pcov + dcov + cross + cross.T, rtol=1e-10, atol=1e-8): raise ArithmeticError('Covariance decomposition failed')
    se = np.sqrt(np.maximum(0, np.diag(cov))); dse = np.sqrt(np.maximum(0, np.diag(dcov))); pse = np.sqrt(np.maximum(0, np.diag(pcov)))
    out = dict(coefficients=mu, power_free_coefficients=pf, power_differences=delta, covariance=cov, power_difference_covariance=dcov,
               power_free_covariance=pcov, cross=cross, standard_errors=se, power_difference_errors=dse, power_free_standard_errors=pse,
               contributions=contributions, J=J, Jf=Jf)
    if K < order:  # prefix plan: orders above K would need the missing loops; nothing above K is reported
        c = K + 1
        for key in ('coefficients', 'power_free_coefficients', 'power_differences', 'standard_errors', 'power_difference_errors', 'power_free_standard_errors'):
            out[key] = out[key][:c]
        for key in ('covariance', 'power_difference_covariance', 'power_free_covariance', 'cross'): out[key] = out[key][:c, :c]
        out['contributions'] = {s: {L: v[:c, :c] for L, v in d.items()} for s, d in contributions.items()}
        out['J'] = {L: v[:c] for L, v in J.items()}; out['Jf'] = {L: v[:c] for L, v in Jf.items()}
    out.update(order=order, max_order=K, loops=list(loops))
    return out


# ---------------------------------------------------------------------------------------------------------------
# Structural gates on complex-step Jacobians (float). Exact-rational versions: exact_check.py.

def top_slot_gate(J: dict, order: int, rtol: float = 1e-12) -> dict:
    """Top slot z^(order-L) of loop L (L = 3..order) enters C_order only as (3 c - b)/3^(L+1) and no lower C_n.
    Hard failure (ArithmeticError) otherwise. J: jacobians() output at any point."""
    _check_order(order); rows = []
    for L in range(3, order + 1):
        if L not in J: continue
        k = order + 1 - L; jb, jc = J[L][:, k - 1], J[L][:, 2 * k - 1]; s = 3.0 ** (L + 1)
        want_b, want_c = -1 / s, 3 / s
        dev = max(abs(jb[order] - want_b) / abs(want_b), abs(jc[order] - want_c) / abs(want_c))
        lower = float(max(np.max(np.abs(jb[:order])), np.max(np.abs(jc[:order]))))
        rows.append(dict(L=L, dC_db=float(jb[order]), dC_dc=float(jc[order]), expected=[f'-1/{3 ** (L + 1)}', f'3/{3 ** (L + 1)}'],
                         rel_deviation=float(dev), max_lower_order_entry=lower))
        if not (dev <= rtol and lower <= rtol * abs(want_b)):
            raise ArithmeticError(f'top-slot rule fails at L={L}: {rows[-1]}')
    return dict(order=order, rows=rows, rule='dC_order/d(b,c)_{L,order-L} = (-1,+3)/3^(L+1); no lower-order dependence')


def loop7_gate(J: dict, B2, order: int = 8, rtol: float = 1e-12) -> dict:
    """At order 8: dC8/d(b_{7,0}, c_{7,0}) = (3 b_{2,0} - 2 c_{2,0}, -7 b_{2,0})/3^9 = (-16 A_d, 42 A_d)/19683, with
    b_{2,0} = -6 A_d and c_{2,0} = b_{2,0}/6 = -A_d. Hard failure otherwise."""
    if order != 8: raise ValueError('the loop-7 entry gate is an order-8 gate (at order 7 loop 7 is the top loop)')
    A = -float(_b2(B2, order)[0].real) / 6  # float, complex or Fraction b_{2,0}
    jb, jc = J[7][8, 0], J[7][8, 2]; want_b, want_c = -16 * A / 19683, 42 * A / 19683
    dev = max(abs(jb - want_b) / abs(want_b), abs(jc - want_c) / abs(want_c))
    out = dict(A_d=A, dC8_db70=float(jb), dC8_dc70=float(jc), expected=[want_b, want_c], ratio_c_over_b=float(jc / jb), rel_deviation=float(dev))
    if not dev <= rtol: raise ArithmeticError(f'loop-7 entry gate fails: {out}')
    return out


def affinity_gate(means: dict, B2, order: int, half_d, *, loops=None, rel_step: float = 1e-2, seed: int = 20261003,
                  rtol: float = 1e-10) -> dict:
    """C_0..C_order are affine in the jets of loops >= 5 taken together (exact_check.exact_affinity), so the Jacobians
    with respect to those jets do not depend on them. Loops 2-4 do move J_5..J_order (exact controls: (3,5) and (2,6)
    are nonzero at orders 7 and 8; (4,5) is nonzero at order 8 only, since at order 7 every loop-4 x loop-5 second
    derivative vanishes identically), so only the jets of `loops` (default 5..order, those present in `means`) are
    perturbed.

    Float/complex means: J_L at the means and at means + delta, delta_{L,j} = rel_step (|m_{L,j}| + 1) u_{L,j} with
    u ~ N(0,1) from `seed`, must agree for every L in loops: max|J_L(m+delta) - J_L(m)| <= rtol max|J_L(m)|. The
    linear-response residual C(m+delta) - C(m) - sum_L J_L(m) delta_L is reported (not gated: it carries the
    rounding of two O(|C|) numbers).
    Every J_L has the nonzero top-slot entry -1/3^(L+1), so an identically zero J_L is an error (ArithmeticError).
    Exact mode, when a `means` vector has object dtype or B2 is in exact mode (_b2_holds_rational: object dtype with
    an int or Fraction element; an int64 list or array is float; repair round 2):
    every second difference of C_0..C_order over all pairs (repeats included) of slots of `loops`, with unit steps,
    must vanish exactly (order 8, loops 5..8: 20 slots, 210 pairs). Float means then enter by their exact binary
    values.
    Hard failure (ArithmeticError) otherwise."""
    _check_order(order)
    loops = [L for L in (range(5, order + 1) if loops is None else loops) if L in means]
    exact = any(np.asarray(v).dtype == object for v in means.values()) or _b2_holds_rational(B2, order)
    if exact:
        base = coefficients(means, B2, order, half_d)
        sl = [(L, j) for L in loops for j in range(len(means[L]))]
        def bump(m, s):
            out = {k: _exact_array(v) for k, v in m.items()}; out[s[0]][s[1]] += 1; return out
        single = {s: coefficients(bump(means, s), B2, order, half_d) for s in sl}; pairs = 0
        for i, s in enumerate(sl):
            for t in sl[i:]:
                sd = coefficients(bump(bump(means, s), t), B2, order, half_d) - single[s] - single[t] + base
                if any(x != 0 for x in sd):
                    raise ArithmeticError(f'affinity gate fails (exact): slots {s} x {t}, second differences {[str(x) for x in sd]}')
                pairs += 1
        return dict(mode='exact', order=order, loops=loops, slots=len(sl), pairs=pairs, all_second_differences_zero=True)
    rng = np.random.default_rng(seed)
    pert = {k: np.asarray(v).copy() for k, v in means.items()}; delta = {}
    for L in loops:
        a = np.asarray(means[L]); delta[L] = rel_step * (np.abs(a) + 1) * rng.standard_normal(a.shape); pert[L] = a + delta[L]
    J0 = jacobians(means, B2, order, half_d); J1 = jacobians(pert, B2, order, half_d); rows = []
    for L in loops:
        scale = float(np.max(np.abs(J0[L])))
        if not scale > 0:  # the top slot alone gives |dC_order/db_{L,order-L}| = 1/3^(L+1)
            raise ArithmeticError(f'affinity gate: J_{L} is identically zero (or not finite) at the means; the top slot '
                                  f'must give -1/3^{L + 1}, so the Jacobian is wrong')
        dev = float(np.max(np.abs(J1[L] - J0[L]))) / scale
        rows.append(dict(L=L, max_abs_J=scale, rel_deviation=dev))
        if not dev <= rtol: raise ArithmeticError(f'affinity gate fails at L={L}: {rows[-1]}')
    resid = None
    if loops:
        lin = coefficients(pert, B2, order, half_d) - coefficients(means, B2, order, half_d) - sum(J0[L] @ delta[L] for L in loops)
        resid = [float(abs(x)) for x in np.asarray(lin)]
    return dict(mode='float', order=order, loops=loops, rows=rows, rtol=rtol, linear_response_residual=resid,
                rule='J_L, L in loops, independent of the loop>=5 jets (C affine in them)')


# ---------------------------------------------------------------------------------------------------------------
# Constant-coefficient MS polynomial ms8 (eq:Lagrange of the condensed note with z-independent jets).
# 19683 C8 = sum coef * monomial. Derived with sympy by exact_check.ms_polynomials (independent of this file) and
# fixed here as a table; tests/test_order8_assembly.py checks the table against that derivation, C62d's RECON
# polynomial and coefficients() in Fraction mode.

MS8_SCALE = 19683
_MS8_A = (  # b_2 = -6A, c_2 = -A (gd:bc3 normalization): 34 monomials
    ('82368', 'A^7'), ('-25344', 'A^5 b3'), ('28512', 'A^5 c3'), ('-5280', 'A^4 b4'), ('7920', 'A^4 c4'),
    ('1980', 'A^3 b3^2'), ('-3960', 'A^3 b3 c3'), ('-960', 'A^3 b5'), ('1800', 'A^3 c5'), ('540', 'A^2 b3 b4'),
    ('-720', 'A^2 b3 c4'), ('-540', 'A^2 c3 b4'), ('-100/3', 'A b3^3'), ('90', 'A b3^2 c3'), ('-144', 'A^2 b6'),
    ('324', 'A^2 c6'), ('54', 'A b3 b5'), ('-90', 'A b3 c5'), ('-54', 'A c3 b5'), ('27', 'A b4^2'), ('-72', 'A b4 c4'),
    ('-5', 'b3^2 b4'), ('6', 'b3^2 c4'), ('9', 'b3 c3 b4'), ('-16', 'A b7'), ('42', 'A c7'), ('3', 'b3 b6'),
    ('-6', 'b3 c6'), ('-3', 'c3 b6'), ('3', 'b4 b5'), ('-5', 'b4 c5'), ('-4', 'c4 b5'), ('-1', 'b8'), ('3', 'c8'))
_MS8_GENERAL = (  # independent b_2, c_2: 45 monomials
    ('-143/243', 'b2^7'), ('143/81', 'b2^6 c2'), ('143/27', 'b2^5 b3'), ('-11/3', 'b2^5 c3'), ('-110/9', 'b2^4 c2 b3'),
    ('-55/9', 'b2^4 b4'), ('55/9', 'b2^4 c4'), ('110/9', 'b2^3 c2 b4'), ('-110/9', 'b2^3 b3^2'), ('55/3', 'b2^3 b3 c3'),
    ('55/3', 'b2^2 c2 b3^2'), ('55/9', 'b2^3 b5'), ('-25/3', 'b2^3 c5'), ('-10', 'b2^2 c2 b5'), ('55/3', 'b2^2 b3 b4'),
    ('-20', 'b2^2 b3 c4'), ('-15', 'b2^2 c3 b4'), ('-20', 'b2 c2 b3 b4'), ('55/9', 'b2 b3^3'), ('-15', 'b2 b3^2 c3'),
    ('-10/3', 'c2 b3^3'), ('-5', 'b2^2 b6'), ('9', 'b2^2 c6'), ('6', 'b2 c2 b6'), ('-10', 'b2 b3 b5'), ('15', 'b2 b3 c5'),
    ('9', 'b2 c3 b5'), ('-5', 'b2 b4^2'), ('12', 'b2 b4 c4'), ('6', 'c2 b3 b5'), ('3', 'c2 b4^2'), ('-5', 'b3^2 b4'),
    ('6', 'b3^2 c4'), ('9', 'b3 c3 b4'), ('3', 'b2 b7'), ('-7', 'b2 c7'), ('-2', 'c2 b7'), ('3', 'b3 b6'), ('-6', 'b3 c6'),
    ('-3', 'c3 b6'), ('3', 'b4 b5'), ('-5', 'b4 c5'), ('-4', 'c4 b5'), ('-1', 'b8'), ('3', 'c8'))


def ms8_rows(general: bool = False) -> list:
    """Rows (coefficient, {symbol: power}) with 19683 C8 = sum coefficient * prod symbol^power. Symbols: A, b3..b8,
    c3..c8 (default: b_2 = -6A, c_2 = -A), or b2..b8, c2..c8 (general=True). Coefficients are Fractions."""
    rows = []
    for co, mono in (_MS8_GENERAL if general else _MS8_A):
        m = {}
        for f in mono.split():
            s, _, p = f.partition('^'); m[s] = int(p or 1)
        rows.append((Fraction(co), m))
    return rows


def ms8_value(env: dict, general: bool = False):
    """C8 = (sum of ms8_rows) / 19683 at env {symbol: value} (Fractions give the exact value; missing symbols are 0)."""
    tot = 0
    for co, m in ms8_rows(general):
        t = co
        for s, p in m.items(): t = t * env.get(s, 0) ** p
        tot = tot + t
    return tot / MS8_SCALE


# ---------------------------------------------------------------------------------------------------------------
# Power-sector null rows (POWER_PROTOCOL.md). Diagnostics only: nothing here changes an estimate.

FLAG_PULL = 3.0
ORDER3_ROUNDING = 1e-12  # order 3 vanishes exactly by the weights (c_3^p = b_3^p/3); the LRI_C7_D2_HPC convention


def power_null_rows(delta, dse, order: int) -> dict:
    """Pre-registered rows: Delta_p at orders 3..order-1 are tested against zero (pull = Delta/SE; |pull| > 3 is
    flagged 'not proved zero'); Delta_p at the top order is the reported power correction (not a null row). Its
    vanishing is not proved. For d=2 and d=3 the note's C7 sections only say that no power correction is forced to
    vanish and that the lower rows are consistent with zero "but do not prove a cancellation at seventh order"
    (N:10655-10661, N:10811-10818; note md5 85f9a1ec). The only "conjecture" in the note is in the d=1 C7 section,
    where it is explicitly not imposed (N:10220-10221), and the d=1 C8 section states none. So its pull Delta/SE is
    reported as a diagnostic only: no flag, no threshold, never a gate (POWER_PROTOCOL.md section 3; wording
    corrected in repair round 3, rule unchanged since round 2)."""
    _check_order(order); rows = []
    for k in range(3, order):
        d, s = float(delta[k]), float(dse[k])
        if k == 3 and abs(d) < ORDER3_ROUNDING:
            rows.append(dict(order=k, delta=d, se=s, pull=None, flag=None, note='rounding level (exact zero by the weights c_3^p = b_3^p/3)')); continue
        p = d / s if s > 0 else None
        rows.append(dict(order=k, delta=d, se=s, pull=p, flag=('not proved zero' if p is not None and abs(p) > FLAG_PULL else None)))
    dt, st = float(delta[order]), float(dse[order])
    top = dict(order=order, delta=dt, se=st, pull=(dt / st if st > 0 else None),
               role='reported power correction; its vanishing is not proved (the d=2/3 C7 sections only report the '
                    'lower rows as consistent with zero, N:10659-10661, N:10817-10818); pull is a diagnostic only: not a '
                    'null test, no flag, not used as a gate')
    return dict(null_rows=rows, top=top, flags=[r for r in rows if r['flag']])


def md5_self() -> str:
    import hashlib
    with open(__file__, 'rb') as f: return hashlib.md5(f.read()).hexdigest()


if __name__ == '__main__':
    import json
    print(json.dumps(dict(module='order8_assembly', md5=md5_self(), orders=ORDERS, slots={o: slots(o) for o in ORDERS}), indent=1))
