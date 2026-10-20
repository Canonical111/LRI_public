"""
indep_nrg.py -- independent bosonic NRG for the sub-ohmic spin-boson model.

Written from SPEC.md only (no other implementation consulted).  Units: omega_c = 1.

Model
    H = -(Delta/2) sigma_x + sum_j omega_j b_j^+ b_j + (sigma_z/2) sum_j lambda_j (b_j + b_j^+),
    rho(omega) = sum_j lambda_j^2 delta(omega - omega_j) = 2 alpha omega^s   on 0 < omega <= 1.

Pipeline (SPEC section in brackets)
    star_unit / lanczos / wilson_chain   [2, 3]  exact log-bin integrals + Lanczos in mpmath
    nrg_flow                             [4]     iterative diagonalization in parity sectors (float64)
    find_alpha_c                         [5]     bracket + bisection on f(alpha) = g_{N-1}(alpha) - target
    fd_derivatives                       [6]     D_n(h) = [g_n(a_c(1+h)) - g_n(a_c(1-h))] / (2 h a_c)
    window_audit, fd_agreement           [6]     sliding-window slope fits and h-agreement ranges
    run_pipeline                                 everything above for one configuration

Conventions (see NOTES.md for the reasoning behind each choice)
    * Spin basis = sigma_x eigenbasis: state 0 has sigma_x = +1 (energy -Delta/2, parity +1),
      state 1 has sigma_x = -1 (energy +Delta/2, parity -1); sigma_z = [[0,1],[1,0]].
    * Oscillator levels 0..n_b-1, b|k> = sqrt(k)|k-1>.
    * Product basis at every step: (previous kept state i, new-site level k) -> index i*n_b + k
      (i.e. numpy.kron ordering, previous block first, new site last).
    * Kept states of a step are ordered [even kept (ascending energy), odd kept (ascending energy)].
    * Energies are rescaled: H_n = Lambda^n x (physical Hamiltonian of spin + sites 0..n),
      minus a running constant; g_n is the parity gap in these rescaled units.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import mpmath
import numpy as np
import scipy.linalg

DELTA_DEFAULT = 0.1           # tunnelling Delta (SPEC 1)
H_VALUES_DEFAULT = (1e-9, 1e-10, 1e-11)   # finite-difference steps (SPEC 6)


# =====================================================================================
# 2-3.  Logarithmic star discretization and Lanczos tridiagonalization (mpmath)
# =====================================================================================

def default_dps(N: int, Lambda: float) -> int:
    """Working precision for the Lanczos run.

    SPEC 3 asks for at least 30 + 1.3 N log10(Lambda) decimal digits; we add 10 more as margin.
    """
    return int(math.ceil(30.0 + 1.3 * N * math.log10(Lambda))) + 10


def star_unit(Lam, s, M):
    """Star parameters for the bins I_m = (Lam^-(m+1), Lam^-m], m = 0..M-1 (current mp precision).

    Returns (xi, w) with
        w_m  = int_{I_m} omega^s d omega      (so that gamma_m^2 = 2 alpha w_m),
        xi_m = int_{I_m} omega^{s+1} d omega / w_m.
    Both integrals are done analytically, so the star is exact to working precision.
    """
    sp1 = s + 1
    sp2 = s + 2
    xi, w = [], []
    for m in range(M):
        top = Lam ** (-m)           # upper bin edge
        bot = Lam ** (-(m + 1))     # lower bin edge
        wm = (top ** sp1 - bot ** sp1) / sp1
        first_moment = (top ** sp2 - bot ** sp2) / sp2
        w.append(wm)
        xi.append(first_moment / wm)
    return xi, w


def lanczos(xi, w, nsteps, reorth=True):
    """Lanczos for the diagonal matrix diag(xi), start vector gamma/|gamma| ~ sqrt(w).

    Returns (a, b, norm2):
        a[n] = eps_n        (n = 0 .. nsteps-1)   on-site energies,
        b[n] = t_n          (n = 0 .. nsteps-2)   hopping between chain sites n and n+1,
        norm2 = sum_m w_m   (so |gamma|^2 = 2 alpha norm2).

    Full reorthogonalization (classical Gram-Schmidt applied twice against all previous Lanczos
    vectors) is ON by default and is essential: the plain three-term recurrence is violently
    unstable here.  The Ritz values lock onto the high-frequency modes after a few steps, and
    rounding errors in those components are then amplified by ~1/t_n ~ Lambda^n per step, i.e.
    by ~Lambda^{n^2/2} overall, which no affordable precision can absorb (the self-test shows
    the plain recurrence failing completely at N = 60, Lambda = 3, 78 digits).  With full
    reorthogonalization the vectors stay orthonormal to working precision, the coefficients have
    absolute error ~10^-dps, and the rescaled ones (relative error ~10^-dps Lambda^n) are
    accurate once dps exceeds N log10(Lambda) by a margin, as SPEC 3 assumes.  The precision
    margin is verified independently by repeating the run at higher precision (chain_convergence).
    """
    if nsteps > len(xi):
        raise ValueError("Lanczos: nsteps > M (Krylov space would be exhausted)")
    norm2 = mpmath.fsum(w)
    v = [mpmath.sqrt(wm / norm2) for wm in w]          # normalized gamma_m / |gamma|
    V = [v]                                            # all Lanczos vectors so far
    beta_prev = mpmath.mpf(0)
    a, b = [], []
    for n in range(nsteps):
        Av = [x * y for x, y in zip(xi, v)]
        an = mpmath.fdot(v, Av)
        a.append(an)
        if n == nsteps - 1:
            break
        if n == 0:
            r = [p - an * q for p, q in zip(Av, v)]
        else:
            r = [p - an * q - beta_prev * u for p, q, u in zip(Av, v, V[-2])]
        if reorth:
            for _pass in range(2):                     # CGS2: Gram-Schmidt twice
                for u in V:
                    c = mpmath.fdot(u, r)
                    r = [ri - c * ui for ri, ui in zip(r, u)]
        bn = mpmath.sqrt(mpmath.fdot(r, r))
        if bn == 0:
            raise ArithmeticError("Lanczos breakdown (t_n = 0); increase M")
        b.append(bn)
        v = [ri / bn for ri in r]
        V.append(v)
        beta_prev = bn
    return a, b, norm2


@dataclass
class Chain:
    """Wilson-chain coefficients, rescaled: eps_r[n] = Lambda^n eps_n, t_r[n] = Lambda^n t_{n-1}."""
    Lambda_str: str
    s_str: str
    N: int
    M: int
    dps: int
    Lambda: float
    s: float
    eps_r: np.ndarray            # length N
    t_r: np.ndarray              # length N, t_r[0] = nan (no hopping into site 0)
    eps_r_mp: list = field(repr=False, default_factory=list)
    t_r_mp: list = field(repr=False, default_factory=list)   # t_r_mp[0] is None
    norm_deficit: float = 0.0    # 1 - (s+1) sum_m w_m = Lambda^{-M(s+1)} (finite-M star norm)
    seconds: float = 0.0

    def lam_tot(self, alpha: float) -> float:
        """lambda_tot = sqrt(2 alpha/(s+1)) (SPEC 3; differs from |gamma| only by Lambda^{-M(s+1)})."""
        return math.sqrt(2.0 * alpha / (self.s + 1.0))


def wilson_chain(Lambda_str: str, s_str: str, N: int, M: int | None = None,
                 dps: int | None = None) -> Chain:
    """Build the rescaled Wilson chain for sites 0..N-1.

    Lambda_str, s_str are exact decimal strings (e.g. '2.5', '0.502'); they are parsed by mpmath
    at full working precision, so no float64 representation error enters the chain.
    """
    t0 = time.perf_counter()
    Lf = float(Lambda_str)
    if M is None:
        M = N + 80
    if dps is None:
        dps = default_dps(N, Lf)
    with mpmath.workdps(dps):
        Lam = mpmath.mpf(Lambda_str)
        s = mpmath.mpf(s_str)
        xi, w = star_unit(Lam, s, M)
        a, b, norm2 = lanczos(xi, w, N)
        eps_r_mp = [Lam ** n * a[n] for n in range(N)]
        t_r_mp = [None] + [Lam ** n * b[n - 1] for n in range(1, N)]
        deficit = 1 - (s + 1) * norm2
        eps_r = np.array([float(x) for x in eps_r_mp], dtype=np.float64)
        t_r = np.array([np.nan] + [float(x) for x in t_r_mp[1:]], dtype=np.float64)
        deficit_f = float(deficit)
    return Chain(Lambda_str=Lambda_str, s_str=s_str, N=N, M=M, dps=dps, Lambda=Lf,
                 s=float(s_str), eps_r=eps_r, t_r=t_r, eps_r_mp=eps_r_mp, t_r_mp=t_r_mp,
                 norm_deficit=deficit_f, seconds=time.perf_counter() - t0)


def chain_strings(chain: Chain, digits: int = 30):
    """30-digit decimal strings of the rescaled coefficients (for the JSON record)."""
    with mpmath.workdps(chain.dps):
        eps = [mpmath.nstr(x, digits) for x in chain.eps_r_mp]
        tt = [None] + [mpmath.nstr(x, digits) for x in chain.t_r_mp[1:]]
    return eps, tt


def _max_rel_diff_mp(xs, ys, dps):
    with mpmath.workdps(dps):
        worst = mpmath.mpf(0)
        for x, y in zip(xs, ys):
            if x is None or y is None:
                continue
            d = abs(x - y) / max(abs(x), abs(y))
            worst = max(worst, d)
        return float(worst)


def chain_convergence(chain: Chain, dM: int = 40, ddps: int = 40):
    """Independent convergence checks of the chain: rerun with M+dM bins and with dps+ddps digits.

    Returns the largest relative change of any rescaled coefficient (eps and t together).
    """
    out = {}
    c_M = wilson_chain(chain.Lambda_str, chain.s_str, chain.N, M=chain.M + dM, dps=chain.dps)
    c_p = wilson_chain(chain.Lambda_str, chain.s_str, chain.N, M=chain.M, dps=chain.dps + ddps)
    for tag, other in (("M_plus_%d" % dM, c_M), ("dps_plus_%d" % ddps, c_p)):
        hi = max(chain.dps, other.dps)
        out[tag] = max(_max_rel_diff_mp(chain.eps_r_mp, other.eps_r_mp, hi),
                       _max_rel_diff_mp(chain.t_r_mp, other.t_r_mp, hi))
    return out


# =====================================================================================
# 4.  Iterative diagonalization (float64)
# =====================================================================================

SIGMA_Z_XBASIS = np.array([[0.0, 1.0], [1.0, 0.0]])   # sigma_z in the sigma_x eigenbasis


def boson_ops(nb: int):
    """Truncated oscillator: b (b[k-1,k] = sqrt(k)), occupation numbers, parities (-1)^k."""
    b = np.diag(np.sqrt(np.arange(1, nb, dtype=np.float64)), k=1)
    num = np.arange(nb, dtype=np.float64)
    par = np.where(np.arange(nb) % 2 == 0, 1, -1).astype(np.int8)
    return b, num, par


def _apply_b_new_site(U: np.ndarray, kprev: int, nb: int) -> np.ndarray:
    """Apply (1 (x) b) to the columns of U, U given in the product basis i*nb + k.

    (1 (x) b)|i, l> = sqrt(l) |i, l-1>  =>  (bU)[i, k] = sqrt(k+1) U[i, k+1].
    """
    cols = U.shape[1]
    V = U.reshape(kprev, nb, cols)
    out = np.zeros_like(V)
    out[:, :-1, :] = V[:, 1:, :] * np.sqrt(np.arange(1, nb, dtype=np.float64))[None, :, None]
    return out.reshape(kprev * nb, cols)


def nrg_step(A, par_prev, X, e_n, c_n, nb, K, b_ops, want_B=True, check_parity=False):
    """One NRG step.

    Builds, in the product basis (previous kept state i) x (new-site level k),
        H = diag(A) (x) 1 + e_n 1 (x) b^+b + c_n (X^T (x) b + X (x) b^+),
    diagonalizes it separately in the even and odd parity sectors, keeps the K lowest states of
    each sector (all if the sector is smaller), and returns the kept data.

    For step 0: A = (-Delta/2, +Delta/2), X = sigma_z, c_0 = lambda_tot/2, e_0 = eps_0.
    For step n>=1: A = Lambda * E^{(n-1)}, X = B_{n-1}, c_n = Lambda^n t_{n-1}, e_n = Lambda^n eps_n.
    """
    b, num, par_osc = b_ops
    kprev = A.size
    D = kprev * nb

    # coupling term: c (X (x) b^+) + h.c.  (X real => h.c. is the matrix transpose)
    H = np.kron(c_n * X, b.T)
    H += H.T
    H[np.diag_indices(D)] += np.repeat(A, nb) + e_n * np.tile(num, kprev)

    par = np.repeat(par_prev, nb) * np.tile(par_osc, kprev)   # parity(i) * (-1)^k
    idx_e = np.flatnonzero(par > 0)
    idx_o = np.flatnonzero(par < 0)
    if check_parity:
        leak = np.max(np.abs(H[np.ix_(idx_e, idx_o)])) if idx_e.size and idx_o.size else 0.0
        if leak != 0.0:
            raise AssertionError("H couples different parity sectors (max |H_eo| = %g)" % leak)

    w_e, U_e = scipy.linalg.eigh(H[np.ix_(idx_e, idx_e)], check_finite=False, driver="evd")
    w_o, U_o = scipy.linalg.eigh(H[np.ix_(idx_o, idx_o)], check_finite=False, driver="evd")
    ke = min(K, w_e.size)
    ko = min(K, w_o.size)

    raw_min = min(w_e[0], w_o[0])                      # global minimum over both sectors
    gap = w_o[0] - w_e[0]                              # parity gap E0(odd) - E0(even)
    E_new = np.concatenate([w_e[:ke], w_o[:ko]]) - raw_min
    par_new = np.concatenate([np.ones(ke, np.int8), -np.ones(ko, np.int8)])

    out = dict(E=E_new, par=par_new, ke=ke, ko=ko, raw_min=raw_min, gap=gap,
               w_e_kept=w_e[:ke], w_o_kept=w_o[:ko])

    if want_B:
        # kept eigenvectors embedded in the full product space (zeros on the other sector)
        Uf_e = np.zeros((D, ke))
        Uf_e[idx_e, :] = U_e[:, :ke]
        Uf_o = np.zeros((D, ko))
        Uf_o[idx_o, :] = U_o[:, :ko]
        # b of the new site connects opposite parities only: fill the off-diagonal blocks
        B = np.zeros((ke + ko, ke + ko))
        B[:ke, ke:] = Uf_e.T @ _apply_b_new_site(Uf_o, kprev, nb)   # <even| b |odd>
        B[ke:, :ke] = Uf_o.T @ _apply_b_new_site(Uf_e, kprev, nb)   # <odd| b |even>
        out["B"] = B
        out["Ufull"] = np.hstack([Uf_e, Uf_o])
    return out


@dataclass
class Flow:
    alpha: float
    g: np.ndarray                    # parity gap g_n, n = 0..N-1 (rescaled units)
    levels: dict                     # n -> {'even': [...], 'odd': [...]} (8 lowest, shifted), n <= 12
    kept: list                       # (ke, ko) per step
    emax: list                       # (max kept even, max kept odd) shifted energies per step
    raw_min: np.ndarray              # minimum raw eigenvalue per step (before shifting)
    offset: np.ndarray               # C_n: physical energy = E_shifted / Lambda^n + C_n
    last_raw: tuple = None           # (raw kept even, raw kept odd) eigenvalues at the last step
    Ufull: list = None               # per step, kept eigenvectors in the product basis (optional)
    B: list = None                   # per step, b of the new site in the kept basis (optional)
    par: list = None                 # per step, parity labels of kept states (optional)
    seconds: float = 0.0


def nrg_flow(chain: Chain, alpha: float, nb: int, K: int, N: int | None = None,
             Delta: float = DELTA_DEFAULT, levels_upto: int = 12, n_levels: int = 8,
             keep_vectors: bool = False, check_parity: bool = False) -> Flow:
    """Run the NRG map for steps n = 0..N-1 at coupling alpha (SPEC 4)."""
    t0 = time.perf_counter()
    N = chain.N if N is None else N
    if N > chain.N:
        raise ValueError("chain too short")
    Lam = chain.Lambda
    b_ops = boson_ops(nb)

    g = np.empty(N)
    raw_min = np.empty(N)
    offset = np.empty(N)
    levels, kept, emax = {}, [], []
    Ufull_l, B_l, par_l = ([], [], []) if keep_vectors else (None, None, None)

    # step-0 "previous block" = the bare spin
    A = np.array([-Delta / 2.0, +Delta / 2.0])
    par_prev = np.array([1, -1], dtype=np.int8)
    X = SIGMA_Z_XBASIS
    e_n = chain.eps_r[0]
    c_n = 0.5 * chain.lam_tot(alpha)
    C_prev = 0.0
    last_raw = None

    for n in range(N):
        if n > 0:
            A = Lam * st["E"]
            par_prev = st["par"]
            X = st["B"]
            e_n = chain.eps_r[n]
            c_n = chain.t_r[n]
        need_B = (n < N - 1) or keep_vectors
        st = nrg_step(A, par_prev, X, e_n, c_n, nb, K, b_ops, want_B=need_B,
                      check_parity=check_parity)
        g[n] = st["gap"]
        raw_min[n] = st["raw_min"]
        # physical energy = raw / Lambda^n + C_{n-1};  C_n = C_{n-1} + raw_min / Lambda^n
        scale = Lam ** n
        offset[n] = C_prev + st["raw_min"] / scale
        C_prev = offset[n]
        ke, ko = st["ke"], st["ko"]
        kept.append((ke, ko))
        emax.append((float(st["E"][ke - 1]), float(st["E"][ke + ko - 1])))
        if n <= levels_upto:
            levels[n] = {"even": st["E"][:min(n_levels, ke)].tolist(),
                         "odd": st["E"][ke:ke + min(n_levels, ko)].tolist()}
        if keep_vectors:
            Ufull_l.append(st["Ufull"])
            B_l.append(st["B"])
            par_l.append(st["par"])
        if n == N - 1:
            last_raw = (st["w_e_kept"].copy(), st["w_o_kept"].copy())

    return Flow(alpha=alpha, g=g, levels=levels, kept=kept, emax=emax, raw_min=raw_min,
                offset=offset, last_raw=last_raw, Ufull=Ufull_l, B=B_l, par=par_l,
                seconds=time.perf_counter() - t0)


# =====================================================================================
# 5.  Critical coupling
# =====================================================================================

def find_alpha_c(f, lo: float = 0.01, hi: float = 2.0, max_iter: int = 48,
                 rel_tol: float = 5e-14, log=None):
    """Bracket + bisection exactly as in SPEC 5.  f(alpha) > 0 on the delocalized side.

    Returns a dict with status ('ok', 'bracket_failed' or 'not_converged'), alpha_c, the final
    bracket, the iteration count and the full evaluation history.
    """
    history = []

    def ev(label, a):
        val = f(a)
        history.append({"stage": label, "alpha": a, "f": val})
        if log is not None:
            log("  %-9s alpha = %.17g   f = %+.6e" % (label, a, val))
        return val

    flo = ev("lo", lo)
    fhi = ev("hi", hi)
    for _ in range(40):
        if flo > 0:
            break
        lo = lo / 2.0
        flo = ev("lo", lo)
    for _ in range(40):
        if fhi < 0:
            break
        hi = 2.0 * hi
        if hi > 100:
            break
        fhi = ev("hi", hi)
    res = {"bracket_initial": [lo, hi], "f_bracket_initial": [flo, fhi], "history": history}
    if not (flo > 0 > fhi):
        res.update(status="bracket_failed", alpha_c=None, bracket=[lo, hi], iterations=0)
        return res

    iteration = 0
    while iteration < max_iter:
        mid = (lo + hi) / 2.0
        if hi - lo < rel_tol * max(1.0, abs(mid)):
            break
        fm = ev("bisect", mid)
        if fm > 0:
            lo = mid
        else:
            hi = mid
        iteration += 1
    converged = (hi - lo) < rel_tol * max(1.0, abs((lo + hi) / 2.0))
    res.update(status="ok" if converged else "not_converged", alpha_c=(lo + hi) / 2.0,
               bracket=[lo, hi], iterations=iteration, converged=converged)
    return res


# =====================================================================================
# 6.  Finite differences, window audit, h-agreement
# =====================================================================================

def fd_alphas(alpha_c: float, h: float):
    """alpha_c(1+h), alpha_c(1-h) as in SPEC 6 (evaluated literally in float64)."""
    return alpha_c * (1.0 + h), alpha_c * (1.0 - h)


def fd_derivative(g_plus: np.ndarray, g_minus: np.ndarray, alpha_c: float, h: float) -> np.ndarray:
    """D_n(h) = [g_n(alpha_c(1+h)) - g_n(alpha_c(1-h))] / (2 h alpha_c)."""
    return (g_plus - g_minus) / (2.0 * h * alpha_c)


def window_geometry(N: int):
    """Window width and start range of SPEC 6 (floors done in exact integer arithmetic)."""
    f13 = (13 * N) // 100            # floor(0.13 N)
    f76 = (76 * N) // 100            # floor(0.76 N)
    w = max(12, f13)
    starts = range(max(8, f13), f76 - w)
    return w, starts


def window_audit(D: np.ndarray, g: np.ndarray, Lambda: float, var_tol: float = 0.005,
                 res_tol: float = 0.003):
    """Sliding-window fits of L_n = log|D_n| (SPEC 6).  g is the critical flow at alpha_c."""
    N = len(D)
    w, starts = window_geometry(N)
    L = np.log(np.maximum(np.abs(D), 1e-290))
    lnL = math.log(Lambda)
    windows = []
    for start in starts:
        n = np.arange(start, start + w)
        Lw, gw = L[n], g[n]
        rec = {"start": int(start), "end": int(start + w - 1)}
        if np.any(gw <= 0) or not np.all(np.isfinite(Lw)):
            rec.update(skipped=True, reason="g_n <= 0" if np.any(gw <= 0) else "non-finite L_n")
            windows.append(rec)
            continue
        nf = n.astype(np.float64)
        nbar, Lbar = nf.mean(), Lw.mean()
        c1 = float(np.sum((nf - nbar) * (Lw - Lbar)) / np.sum((nf - nbar) ** 2))
        c0 = float(Lbar - c1 * nbar)
        resid = float(np.max(np.abs(Lw - (c1 * nf + c0))))
        variation = float((gw.max() - gw.min()) / abs(gw.mean()))
        y_t = c1 / lnL
        quality = bool(variation < var_tol and resid < res_tol)
        rec.update(skipped=False, slope=c1, intercept=c0, y_t=y_t, delta_E=1.0 - y_t,
                   residual=resid, variation=variation, quality=quality)
        windows.append(rec)
    q = [r["delta_E"] for r in windows if not r["skipped"] and r["quality"]]
    summary = {"width": w, "start_first": starts.start, "start_stop_exclusive": starts.stop,
               "n_windows": len(windows), "n_quality": len(q),
               "delta_E_min": min(q) if q else None, "delta_E_max": max(q) if q else None,
               "delta_E_mid": 0.5 * (min(q) + max(q)) if q else None}
    return {"summary": summary, "windows": windows}


def _true_runs(mask):
    """Contiguous runs of True in a boolean array, as [start, end] (inclusive)."""
    runs, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        if not v and start is not None:
            runs.append([start, i - 1])
            start = None
    if start is not None:
        runs.append([start, len(mask) - 1])
    return runs


def fd_agreement(hs, D_by_h, tol: float = 1e-4):
    """For each h and each neighbouring h' (neighbours in the order of hs), compare D_n(h), D_n(h').

    rel_n = |D_n(h) - D_n(h')| / max(|D_n(h)|, |D_n(h')|); agreement means rel_n < tol.
    Reported: the largest n with agreement (pointwise), every contiguous agreement run, and the
    longest run.  The full rel_n array is returned too.
    """
    out = {}
    for i, h in enumerate(hs):
        per = {}
        for j in (i - 1, i + 1):
            if not (0 <= j < len(hs)):
                continue
            Da, Db = np.asarray(D_by_h[h]), np.asarray(D_by_h[hs[j]])
            den = np.maximum(np.abs(Da), np.abs(Db))
            with np.errstate(invalid="ignore", divide="ignore"):
                rel = np.where(den > 0, np.abs(Da - Db) / np.where(den > 0, den, 1.0), 0.0)
            agree = rel < tol
            runs = _true_runs(agree)
            longest = max(runs, key=lambda r: (r[1] - r[0], r[1])) if runs else None
            idx = np.flatnonzero(agree)
            # Extra diagnostic (not in SPEC): agreement of the local log-slope
            # L_{n} - L_{n-1} (index n = 1..N-1), which is blind to an n-independent factor
            # in D_n (e.g. the alpha-increment rounding or an early-step rounding offset).
            La = np.log(np.maximum(np.abs(Da), 1e-290))
            Lb = np.log(np.maximum(np.abs(Db), 1e-290))
            dsl = np.abs(np.diff(La) - np.diff(Lb))
            sl_ok = np.concatenate([[False], dsl < tol])
            sl_runs = _true_runs(sl_ok)
            sl_idx = np.flatnonzero(sl_ok)
            per[repr(hs[j])] = {
                "largest_n_agree": int(idx[-1]) if idx.size else None,
                "longest_run": longest, "runs": runs, "rel_diff": rel.tolist(),
                "extra_log_slope": {
                    "largest_n_agree": int(sl_idx[-1]) if sl_idx.size else None,
                    "longest_run": (max(sl_runs, key=lambda r: (r[1] - r[0], r[1]))
                                    if sl_runs else None),
                    "abs_diff": [None] + dsl.tolist()}}
        out[repr(h)] = per
    return out


# =====================================================================================
# Full pipeline for one configuration
# =====================================================================================

def run_pipeline(Lambda_str: str, s_str: str, K: int, nb: int, N: int,
                 Delta: float = DELTA_DEFAULT, hs=H_VALUES_DEFAULT, M: int | None = None,
                 convergence_check: bool = True, log=print):
    """Chain -> free flow -> critical search -> critical flow -> finite differences -> audit."""
    T0 = time.perf_counter()
    timing = {}
    res = {"params": {"Lambda": Lambda_str, "s": s_str, "K": K, "n_b": nb, "N": N,
                      "Delta": Delta, "h_values": list(hs)}}

    # --- chain ---------------------------------------------------------------------
    chain = wilson_chain(Lambda_str, s_str, N, M=M)
    eps_s, t_s = chain_strings(chain)
    res["chain"] = {"M": chain.M, "dps": chain.dps, "norm_deficit": chain.norm_deficit,
                    "eps_rescaled": chain.eps_r, "t_rescaled": chain.t_r,
                    "eps_rescaled_str": eps_s, "t_rescaled_str": t_s,
                    "definition": "eps_rescaled[n] = Lambda^n eps_n (n=0..N-1); "
                                  "t_rescaled[n] = Lambda^n t_{n-1} (n=1..N-1), entry 0 unused"}
    log("chain: M=%d dps=%d (%.2fs)  eps_r[0..3]=%s  t_r[1..3]=%s"
        % (chain.M, chain.dps, chain.seconds, np.array2string(chain.eps_r[:4], precision=6),
           np.array2string(chain.t_r[1:4], precision=6)))
    if convergence_check:
        conv = chain_convergence(chain)
        res["chain"]["convergence_max_rel_change"] = conv
        log("chain convergence (max rel change): %s" % conv)
    timing["chain"] = time.perf_counter() - T0

    flow_count = [0]
    flow_time = [0.0]

    def flow(alpha, **kw):
        fl = nrg_flow(chain, alpha, nb, K, N=N, Delta=Delta, **kw)
        flow_count[0] += 1
        flow_time[0] += fl.seconds
        return fl

    # --- free chain and target -------------------------------------------------------
    t1 = time.perf_counter()
    free = flow(0.0)
    target = 0.3 * free.g[-1]
    res["free_flow"] = {"g": free.g, "g_last": free.g[-1], "levels": free.levels}
    res["target"] = target
    log("free flow: g_{N-1}(0) = %.15g  target = %.15g  (%.2fs/flow)"
        % (free.g[-1], target, free.seconds))
    timing["free_flow"] = time.perf_counter() - t1

    # --- critical search -------------------------------------------------------------
    t2 = time.perf_counter()

    def f(alpha):
        return float(flow(alpha).g[-1] - target)

    crit = find_alpha_c(f, log=log)
    timing["critical_search"] = time.perf_counter() - t2
    res["critical_search"] = crit
    if crit["status"] == "bracket_failed":
        log("critical search FAILED: no bracket (lo=%g, hi=%g)" % tuple(crit["bracket"]))
        res["status"] = "bracket_failed"
        timing["total"] = time.perf_counter() - T0
        res["timing"] = timing
        return res
    alpha_c = crit["alpha_c"]
    log("alpha_c = %.17g  bracket = [%.17g, %.17g]  iterations = %d  status = %s"
        % (alpha_c, crit["bracket"][0], crit["bracket"][1], crit["iterations"], crit["status"]))

    # --- critical flow ---------------------------------------------------------------
    t3 = time.perf_counter()
    cf = flow(alpha_c)
    terminal = float(cf.g[-1] - target)
    res["critical_search"]["terminal_residual"] = terminal
    res["critical_flow"] = {"alpha": alpha_c, "g": cf.g, "levels": cf.levels,
                            "kept": cf.kept, "emax_kept": cf.emax}
    log("terminal residual f(alpha_c) = %+.3e" % terminal)
    timing["critical_flow"] = time.perf_counter() - t3

    # --- finite differences ----------------------------------------------------------
    t4 = time.perf_counter()
    fd = {}
    D_by_h = {}
    for h in hs:
        ap, am = fd_alphas(alpha_c, h)
        gp = flow(ap).g
        gm = flow(am).g
        D = fd_derivative(gp, gm, alpha_c, h)
        D_by_h[h] = D
        fd[repr(h)] = {"h": h, "alpha_plus": ap, "alpha_minus": am,
                       "denominator_2h_alpha_c": 2.0 * h * alpha_c,
                       "actual_alpha_increment": ap - am,
                       "D": D, "g_plus": gp, "g_minus": gm}
        log("FD h=%g done: D_n at n=10,20,..: %s" % (h, np.array2string(D[10::10], precision=5)))
    timing["finite_differences"] = time.perf_counter() - t4

    # --- audit -----------------------------------------------------------------------
    audits = {}
    for h in hs:
        a = window_audit(D_by_h[h], cf.g, chain.Lambda)
        audits[repr(h)] = a
        s = a["summary"]
        if s["n_quality"]:
            log("audit h=%g: %d/%d quality windows, Delta_E in [%.6f, %.6f], mid %.6f"
                % (h, s["n_quality"], s["n_windows"], s["delta_E_min"], s["delta_E_max"],
                   s["delta_E_mid"]))
        else:
            log("audit h=%g: 0/%d quality windows" % (h, s["n_windows"]))
    agreement = fd_agreement(list(hs), D_by_h)
    for hk, per in agreement.items():
        for nk, d in per.items():
            log("agreement h=%s vs %s: largest n = %s, longest run = %s   "
                "[extra, log-slope: largest n = %s, longest run = %s]"
                % (hk, nk, d["largest_n_agree"], d["longest_run"],
                   d["extra_log_slope"]["largest_n_agree"], d["extra_log_slope"]["longest_run"]))

    res["finite_differences"] = fd
    res["window_audit"] = audits
    res["fd_agreement"] = agreement
    res["status"] = "ok" if crit["status"] == "ok" else "bisection_not_converged"
    # compact digest of the headline numbers (everything is also in the full records above)
    res["summary"] = {
        "alpha_c": alpha_c, "bisection_status": crit["status"], "terminal_residual": terminal,
        "g_plateau_hint": float(np.median(cf.g[N // 4: (3 * N) // 4])),
        "per_h": {repr(h): {**audits[repr(h)]["summary"],
                            "agreement_largest_n": {k: v["largest_n_agree"]
                                                    for k, v in agreement[repr(h)].items()},
                            "agreement_longest_run": {k: v["longest_run"]
                                                      for k, v in agreement[repr(h)].items()}}
                  for h in hs},
    }
    timing["total"] = time.perf_counter() - T0
    timing["n_flows"] = flow_count[0]
    timing["mean_seconds_per_flow"] = flow_time[0] / max(1, flow_count[0])
    res["timing"] = timing
    return res
