"""Arbitrary-N continuum analysis of the 2D LRI C2 Hamiltonian records.

Implements PLAN_ANALYSIS.md rev 4 (sha256 bf30ba3c...): fixed-regulator spectral
extrapolation N -> infinity with windows as fractions of N (M3), its validation
(M4: prefix, cross-N, lambda*N flags, extraction, roundoff), auxiliary-cutoff
alignment and uncertainties (M1, M2, M2b), point selection from the PRIMARY pool
(M5), the regulator limit lambda -> 0 per order (M6), the combination of orders
(M7) and the error budget (M8).

Every selection rule is fixed in RULES below, before any result is computed, and
is written to the output. No proposed closed-form value of C2 is an input, a
prior or a selection criterion anywhere in this module. The quoted errors are
numerical diagnostics (linear L1 propagation of systematic sensitivities), not
rigorous bounds and not statistical standard deviations.

The scientific helpers of code/hamiltonian are imported read-only
(analyze_fine.analyze, mixed_sequence.extrapolate, regulator_extrapolation.basis);
nothing there is modified, and no bytecode is written next to them.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PKG = HERE.parents[1]
SCIENCE = PKG / 'code' / 'hamiltonian'
if str(SCIENCE) not in sys.path:
    sys.path.append(str(SCIENCE))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import analyze_fine                                   # noqa: E402  (read-only)
from mixed_sequence import extrapolate as mixed_extrapolate   # noqa: E402  (read-only)
from regulator_extrapolation import basis             # noqa: E402  (read-only)

PLAN = dict(file='LRI_C2_expanse_loop/PLAN_ANALYSIS.md', revision=7,
            sha256='f76af1bfb81f40474c2e83c9067df24824a85da8e950680a276322517494a378',
            history='rev 4 (bf30ba3c...) built first; rev 6/7 replace the extraction rule (A5-1 on measured '
                    'full-coverage profiles, A6-1 completion rows, R6-002 frozen rev-4 exception) and the A1 '
                    'identity checks (A6-2, R6-001)')
EPS = 2.0 ** -52
RCOND = 1e-13

# ------------------------------------------------------------------ pre-declared rules
POWER_SETS = [(2.75, 3.75), (2.75, 3.75, 4.75), (2.75, 3.5, 3.75, 4.75), (2.75, 3.5, 3.75, 4.75, 5.5)]
EXP_ORDERS = (0, 1, 2, 3)
NMIN_LABELS = ('N/2', '5N/8', '3N/4', '7N/8')
SELECTED = dict(n_powers=(3, 4), exponential_orders=(1, 2), nmin_labels=('5N/8', '3N/4'))
LAMBDA_N_MINIMUM = {1: 50, 2: 60, 3: 75}
TERM_SETS = [('2', '2log'), ('2', '3'), ('2', '2log', '3'), ('2', '2log', '4'), ('2', '3', '4'),
             ('2', '2log', '3', '4')]
SENSITIVITY_TERM_SET = ('2', '2log', '3', '3log')
ALL_TERM_SETS = TERM_SETS + [SENSITIVITY_TERM_SET]
CUTS = {1: (0.15, 0.2, 0.25), 2: (0.15, 0.2, 0.25), 3: (0.2, 0.25, 0.35)}
PREFERRED = dict(terms=('2', '2log', '3'), weighted=False, cut={1: 0.25, 2: 0.25, 3: 0.35})
ADMISSIBLE = dict(min_dof=2, residual_factor=3.0, max_condition=1e8)
MIN_DISTINCT_ADMISSIBLE = 3

RULES = dict(
    plan=PLAN,
    pools=('PRIMARY = archived records (data/hamiltonian/raw) + the production plan records; DIAGNOSTIC = the '
           'M4d extraction-check plan records. M5 selects from PRIMARY only; DIAGNOSTIC records enter only '
           'epsilon_grid on their overlap and are reported alongside (they never enter M6/M7, and never enter '
           'epsilon_cross, which feeds epsilon_spec).'),
    point_selection=('M5: per (order, lambda) the largest-N PRIMARY record; ties at the same N: the production '
                     'grid family (oversample 4, radius_cost 4.5) first, then larger mixed, tail and collapsed '
                     'cutoffs; same configuration on several sites = one replica (Expanse representative), '
                     'cross-site difference recorded.'),
    auxiliary=dict(
        aligned_cutoffs=dict(mixed=16384, collapsed=800000, tail=8192),
        mixed_selection='M1: mixed_sequence.extrapolate fits with >= 3 powers and Nmin >= Nmix/2; limit = median; '
                        'half-spread = (max - min)/2; prefix check = same rule on the first Nmix/2 entries '
                        '(Nmin >= Nmix/4)',
        eps_mix='|t| * max(selected mixed half-spread, |prefix limit - limit|), t = ct/lambda + c_th*lambda',
        eps_coll='|h(collapsed 400000 inputs: two_point and A_face(8192)) - h(800000 inputs)|',
        eps_tailcut='|h(A_face at tail 2048, 800000 norms) - h(A_face at tail 8192, 800000 norms)|; a '
                    'conservative one-step estimate of the residual tail-cutoff error at 8192',
        sources='production records supply their own two_point 800000, mixed 16384 and sidecar A_face 8192; '
                'the c2aux job supplies them for archived-only (order, lambda) and supplies every 400000 and '
                'tail-2048 variant; one aligned set per (order, lambda) is used for every record of that '
                '(order, lambda), so cross-N comparisons differ only in the spectral part'),
    spectral=dict(
        power_sets=[list(p) for p in POWER_SETS], exponential_orders=list(EXP_ORDERS),
        nmin=['N//2', '5*N//8', '3*N//4', '7*N//8'],
        columns='as analyze_extended.py: 1, (n/N)^-p, exp(-lam (n-nmin)) (n/N)^(r-1-j), '
                'exp(-2 lam (n-nmin)) (n/N)^(2r+3/4-j), j < e; column-normalised; numpy lstsq rcond=1e-13',
        fitted_quantity='h_n + A_face n^(-7/4) with the aligned A_face',
        selected='3 or 4 power terms, e in {1, 2}, nmin in {5N//8, 3N//4} (8 fits; = 240/288 at N=384, '
                 '160/192 at N=256)',
        guards='a fit is accepted only with full numerical rank (singular values of the column-normalised '
               'design > 1e-13 s_max) and >= 2 residual degrees of freedom; rejected selected fits are '
               'reported and excluded',
        estimate='h(lambda) = median of the accepted selected fits; half-spread = (max - min)/2',
        influence='v = intercept row of pinv(design, rcond=1e-13) / column scale: limit = sum_n v_n y_n'),
    validation=dict(
        prefix="M4a: N' in {round(N/2), round(2N/3), round(3N/4), N}, same fractional windows of N'; drift = "
               "max - min over N'; epsilon_spec uses |h(N) - h(round(3N/4))|",
        cross_N='M4b: every retained record of the same (order, lambda), aligned auxiliary inputs; '
                'epsilon_cross = max over LOWER-N PRIMARY records with lambda*N >= the order minimum of '
                '|h(max N) - h(lower N)|; diagnostic records are compared and reported but do not enter '
                'epsilon_cross',
        lambda_N_minimum=LAMBDA_N_MINIMUM,
        eps_spec='max(half-spread, |h(N) - h(round(3N/4))|, epsilon_cross when available)',
        eps_grid=('M4d, rev 6/7 (A5-1, A6-1): delta_n = raw chain of the primary record - raw chain of a '
                  'DIAGNOSTIC record of the same (order, lambda) with N_check >= N (a different Cauchy grid), SIGNED, '
                  'at every n <= N (full coverage). On each accepted selected M3 window W: s = least-squares cubic in '
                  'x = (n - mean_W n)/(max_W n - min_W n), rho = delta - s; value = |sum_W v_n s_n| + '
                  'sum_W |v_n| |rho_n|; epsilon_grid = max over the selected fits and over ALL full-coverage '
                  'comparisons of the point. Reported, not in E: the rev-4 L1 max sum_W |v_n| |delta_n| (superseded), '
                  'the plain signed shift max |sum_W v_n delta_n| and max_W |rho_n|. The archived N=256 vs N=384 '
                  'overlap is a full-coverage comparison for the N=256 records (reported; those records are not '
                  'primary); the partial N=384 overlap is reported and never used. No transport, inheritance or '
                  'continuation. A point without a full-coverage comparison (failed completion row) reuses its '
                  'FROZEN rev-4 epsilon_grid and provenance from evidence/rev4/continuum_points.json, is flagged '
                  '"extraction comparison missing: rev-4 exception", and the estimate is labelled "extraction '
                  'coverage incomplete" (R6-002). A grid difference measures extraction sensitivity; it does not '
                  'bound an error that both grids share.'),
        eps_round='M4e: r_n = |Xchain_n| 2^-52 sqrt(n) + |con| 2^-52; max over accepted selected fits of '
                  'sum_n |v_n| r_n'),
    regulator=dict(
        term_sets=[list(t) for t in TERM_SETS], sensitivity_term_set=list(SENSITIVITY_TERM_SET),
        sensitivity_term_set_role='enumerated with the others: it can be admissible and then enters epsilon_model',
        basis='regulator_extrapolation.basis: lambda^p and lambda^p log(lambda)',
        windows=dict(all='all points', drop1='drop the largest lambda', drop2='drop the largest two',
                     cuts={str(k): list(v) for k, v in CUTS.items()}),
        weightings=['unweighted', 'weighted by 1/epsilon_spec (no floor)'],
        fit='numpy lstsq on [1, basis...] (rcond=None, as final_analysis.py); influence row w = pinv(B)[0] '
            '(/epsilon_spec when weighted)',
        underdetermined='fits with more parameters than points are not attempted (as final_analysis.py)',
        admissible=dict(ADMISSIBLE, residual='max |residual| <= 3 * the largest epsilon_spec in the window',
                        condition='np.linalg.cond of the design as fitted'),
        preferred=dict(terms=list(PREFERRED['terms']), weighted=False,
                       window='lambda <= 0.25 (orders 1, 2) or lambda <= 0.35 (order 3)'),
        fallback='if the preferred fit is not admissible: the admissible fit with the fewest parameters, then the '
                 'most points, then unweighted, then the smaller condition number; result marked '
                 '"preferred rejected"',
        deduplication='fits are deduplicated by (set of point identities, term set, weighting) before anything '
                      'is counted; window labels selecting the same points are kept as metadata',
        validation=f'an order with fewer than {MIN_DISTINCT_ADMISSIBLE} distinct admissible fits is "insufficiently '
                   'validated" and excluded',
        eps_model='max over admissible fits of |h0_fit - h0(S_r)|',
        propagation='every per-order epsilon is sum_i |w_i| epsilon_i with the influence row w of S_r (L1, no '
                    'averaging)',
        E_r='eps_prop + eps_mix + eps_coll + eps_grid + eps_round + eps_tailcut + eps_model (linear sum)'),
    joint=dict(
        model='shared h0, per-order coefficients; each retained order with its S_r (term set, points, weighting)',
        acceptance='every order block has n_r - |T_r| - 1 >= 2, the residual rule per block (max |res| <= 3 * '
                   'largest epsilon_spec of the block), condition < 1e8',
        propagation='the same components through the h0 row of the joint pseudo-inverse (L1; shared '
                    'systematics are never averaged down: worst-case signs)',
        variants='the same alternative term set for every order x the same window variant (by index: all, '
                 'drop1, drop2, cut1, cut2, cut3) x weighting; deduplicated by (per-order point sets, term set, '
                 'weighting)',
        eps_model_joint='max over admissible joint variants of |h0_variant - h0_joint|'),
    consistency='orders r, r\' retained: consistent iff |h0_r - h0_r\'| <= E_r + E_r\' for every pair',
    outcome_table=[
        '1: no retained order -> no estimate ("insufficiently validated")',
        '2: one retained order -> h0_r +- E_r ("single order, not cross-validated")',
        '3: >= 2 retained, not consistent -> envelope [min(h0_r - E_r), max(h0_r + E_r)] as midpoint +- '
        'half-width ("orders inconsistent")',
        '4: >= 2 retained, consistent, joint accepted with >= 3 distinct admissible joint variants -> '
        'h0_joint +- E_joint',
        '5: >= 2 retained, consistent, joint rejected or < 3 distinct admissible variants -> envelope as in 3 '
        '("orders consistent, joint fit not validated")'],
    conversion='C2 = -pi^2/(4 b0) + h0/b0^2, mpmath 50 digits, b0 = 9 pi^2/8 (Gamma(3/4)/Gamma(1/4))^2; '
               'Delta C2 = Delta h0 / b0^2',
    status='numerical diagnostics, not rigorous bounds; no proposed closed form is used anywhere')


# ------------------------------------------------------------------ helpers

def nmin_windows(N: int) -> dict[str, int]:
    return {'N/2': N // 2, '5N/8': 5 * N // 8, '3N/4': 3 * N // 4, '7N/8': 7 * N // 8}


def prefix_sizes(N: int) -> list[int]:
    return sorted({round(N / 2), round(2 * N / 3), round(3 * N / 4), N})


def mixed_select(fits: list[dict], nmix: int) -> dict:
    """M1: >= 3 powers and Nmin >= Nmix/2 (= 2048 for the archived Nmix = 4096)."""
    sel = [f for f in fits if len(f['powers']) >= 3 and f['Nmin'] >= nmix / 2]
    if not sel:
        raise ValueError(f'no mixed fit selected for Nmix={nmix}')
    v = [f['limit'] for f in sel]
    return dict(nmix=nmix, selected=sel, n_selected=len(sel), median=float(np.median(v)),
                minimum=float(min(v)), maximum=float(max(v)), half_spread=float((max(v) - min(v)) / 2))


def assemble(record_data: dict, two_point: dict, mixed_fits_selected: list[dict]) -> tuple[np.ndarray, dict]:
    """The finite-cutoff sequence h_N with given auxiliary inputs, by analyze_fine.analyze (read-only).
    analyze() keeps fits with >= 3 powers and Nmin >= 2048; the pre-selected list passes unchanged
    because Nmix/2 >= 2048 for the cutoffs used here (checked)."""
    if any(len(f['powers']) < 3 or f['Nmin'] < 2048 for f in mixed_fits_selected):
        raise ValueError('pre-selected mixed fits would be filtered again by analyze_fine.analyze')
    d = {k: record_data[k] for k in ('order', 'lam', 'N', 'raw', 'planar', 'curvature')}
    d['two_point'] = two_point
    d['mixed'] = dict(fits=mixed_fits_selected)
    a = analyze_fine.analyze(d)
    seq = np.asarray(a['sequence'], dtype=float)
    con = float(seq[-1] - record_data['raw']['Xchain'][-1])
    return seq, dict(t=a['t2_improved'], mixed_limit=a['mixed_limit'], last=a['last'], constant=con)


def design(n: np.ndarray, N: int, lam: float, k: int, powers, ex: int, nmin: int) -> np.ndarray:
    u = n / N
    cols = [np.ones_like(u)] + [u ** (-p) for p in powers]
    if ex:
        for j in range(ex):
            cols.append(np.exp(-lam * (n - nmin)) * u ** (k - 1 - j))
        for j in range(ex):
            cols.append(np.exp(-2 * lam * (n - nmin)) * u ** (2 * k + .75 - j))
    return np.array(cols).T


def spectral_fit(y: np.ndarray, N: int, lam: float, k: int, powers, ex: int, nmin: int, a_face: float,
                 influence: bool = False) -> dict:
    n = np.arange(nmin, N + 1)
    yy = y[n - 1] + a_face * n.astype(float) ** (-1.75)
    A = design(n, N, lam, k, powers, ex, nmin)
    sc = np.linalg.norm(A, axis=0)
    AA = A / sc
    cf = np.linalg.lstsq(AA, yy, rcond=RCOND)[0]
    res = AA @ cf - yy
    s = np.linalg.svd(AA, compute_uv=False)
    rank = int(np.sum(s > RCOND * s[0]))
    ncols = A.shape[1]
    dof = len(n) - ncols
    out = dict(powers=list(powers), exponential_order=ex, Nmin=int(nmin), N=int(N), limit=float(cf[0] / sc[0]),
               max_residual=float(np.max(np.abs(res))), condition=float(np.linalg.cond(AA)),
               columns=ncols, points=int(len(n)), dof=int(dof), rank=rank,
               accepted=bool(rank == ncols and dof >= 2))
    if influence:
        v = np.linalg.pinv(AA, rcond=RCOND)[0] / sc[0]
        out['_v'] = v
        out['_n'] = n
        out['sum_abs_v'] = float(np.sum(np.abs(v)))
        out['influence_reproduces_limit'] = float(abs(v @ yy - out['limit']))
    return out


def m3(y: np.ndarray, N: int, lam: float, k: int, a_face: float, full: bool = True) -> dict:
    """M3 at cutoff N (y holds at least N entries; the first N are used)."""
    y = np.asarray(y[:N], dtype=float)
    windows = nmin_windows(N)
    fits = []
    for ps in POWER_SETS:
        for ex in EXP_ORDERS:
            for label in NMIN_LABELS:
                sel = (len(ps) in SELECTED['n_powers'] and ex in SELECTED['exponential_orders']
                       and label in SELECTED['nmin_labels'])
                if not (full or sel):
                    continue
                f = spectral_fit(y, N, lam, k, ps, ex, windows[label], a_face, influence=sel)
                f['window'] = label
                f['selected'] = sel
                fits.append(f)
    chosen = [f for f in fits if f['selected'] and f['accepted']]
    rejected = [f for f in fits if f['selected'] and not f['accepted']]
    out = dict(N=int(N), a_face=float(a_face), windows=windows, fits=fits,
               n_selected=sum(f['selected'] for f in fits), n_selected_accepted=len(chosen),
               rejected_selected=[dict(powers=f['powers'], e=f['exponential_order'], Nmin=f['Nmin'], rank=f['rank'],
                                       columns=f['columns'], dof=f['dof']) for f in rejected])
    if not chosen:
        out.update(h=None, half_spread=None, status='no accepted selected fit')
        return out
    v = [f['limit'] for f in chosen]
    out.update(h=float(np.median(v)), minimum=float(min(v)), maximum=float(max(v)),
               half_spread=float((max(v) - min(v)) / 2), values=v, status='ok',
               max_sum_abs_v=float(max(f['sum_abs_v'] for f in chosen)),
               max_selected_condition=float(max(f['condition'] for f in chosen)),
               max_selected_residual=float(max(f['max_residual'] for f in chosen)))
    out['_chosen'] = chosen
    return out


def propagate(chosen: list[dict], per_n: np.ndarray) -> float:
    """max over the accepted selected fits of sum_n |v_n| e_n (per_n indexed by n-1)."""
    return float(max(np.sum(np.abs(f['_v']) * per_n[f['_n'] - 1]) for f in chosen))


def split_profile(n: np.ndarray, delta_w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """A5-1: on a window W, s = least-squares cubic in x = (n - mean_W n)/(max_W n - min_W n), rho = delta - s."""
    n = np.asarray(n, dtype=float)
    x = (n - n.mean()) / (n.max() - n.min())
    X = np.vander(x, 4, increasing=True)
    c = np.linalg.lstsq(X, delta_w, rcond=None)[0]
    s = X @ c
    return s, delta_w - s


def grid_split(chosen: list[dict], delta: np.ndarray) -> dict:
    """epsilon_grid of one full-coverage comparison (PLAN rev 6/7, A5-1 on a measured profile):
    max over the accepted selected fits of |sum_W v_n s_n| + sum_W |v_n| |rho_n|, with the SIGNED
    delta = primary - check indexed by n-1 and covering every n of the record. Also reported (not in E):
    the rev-4 L1 max sum_W |v_n| |delta_n|, the plain signed shift max |sum_W v_n delta_n| and max_W |rho_n|."""
    rows = []
    for f in chosen:
        v, n = f['_v'], f['_n']
        d = delta[n - 1]
        s, rho = split_profile(n, d)
        smooth, rough = float(abs(v @ s)), float(np.sum(np.abs(v) * np.abs(rho)))
        rows.append(dict(powers=f['powers'], exponential_order=f['exponential_order'], Nmin=f['Nmin'],
                         smooth=smooth, rough=rough, eps=smooth + rough,
                         rev4_l1=float(np.sum(np.abs(v) * np.abs(d))), signed_shift=float(abs(v @ d)),
                         max_abs_rho=float(np.max(np.abs(rho))), max_abs_delta_window=float(np.max(np.abs(d)))))
    best = max(rows, key=lambda r: r['eps'])
    return dict(eps_grid=best['eps'], smooth=best['smooth'], rough=best['rough'],
                rev4_l1=max(r['rev4_l1'] for r in rows), signed_shift=max(r['signed_shift'] for r in rows),
                max_abs_rho=max(r['max_abs_rho'] for r in rows), per_fit=rows)


def clean(x):
    """JSON-ready copy: numpy scalars to Python, keys starting with '_' dropped."""
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items() if not str(k).startswith('_')}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return [clean(v) for v in x.tolist()]
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, float) and not math.isfinite(x):
        return str(x)
    return x


# ------------------------------------------------------------------ fixed-regulator points

class PointAnalysis:
    """M1-M4 for one record with its (order, lambda)'s aligned auxiliary inputs."""

    def __init__(self, rec, aux, full: bool = True):
        self.rec = rec
        self.aux = aux
        d = rec.data
        self.k, self.lam, self.N = rec.order, rec.lam, rec.N
        self.mixed = mixed_select(aux.mixed_fits, aux.mixed_cutoff)
        self.mixed_prefix = mixed_select(aux.mixed_prefix_fits, aux.mixed_cutoff // 2)
        self.seq, self.asm = assemble(d, aux.tp800, self.mixed['selected'])
        self.main = m3(self.seq, self.N, self.lam, self.k, aux.a8192_800, full=full)

    # M4a
    def prefix_test(self) -> dict:
        rows = []
        for Np in prefix_sizes(self.N):
            r = self.main if Np == self.N else m3(self.seq, Np, self.lam, self.k, self.aux.a8192_800, full=False)
            rows.append(dict(N_prime=Np, h=r['h'], half_spread=r['half_spread'],
                             n_selected_accepted=r['n_selected_accepted']))
        hs = [r['h'] for r in rows if r['h'] is not None]
        three = round(3 * self.N / 4)
        h34 = [r['h'] for r in rows if r['N_prime'] == three][0]
        return dict(rows=rows, drift=float(max(hs) - min(hs)),
                    d34=None if h34 is None or self.main['h'] is None else float(abs(self.main['h'] - h34)),
                    three_quarter_N=three)

    def variant_h(self, two_point: dict | None = None, a_face: float | None = None, mixed_fits=None) -> float:
        tp = self.aux.tp800 if two_point is None else two_point
        a = self.aux.a8192_800 if a_face is None else a_face
        mf = self.mixed['selected'] if mixed_fits is None else mixed_fits
        seq, _ = assemble(self.rec.data, tp, mf)
        return m3(seq, self.N, self.lam, self.k, a, full=False)['h']

    def eps_mix(self) -> dict:
        t = self.asm['t']
        prefix_shift = abs(self.mixed_prefix['median'] - self.mixed['median'])
        return dict(t=t, mixed_limit=self.mixed['median'], mixed_half_spread=self.mixed['half_spread'],
                    prefix_limit=self.mixed_prefix['median'], prefix_shift=prefix_shift,
                    eps_mix=float(abs(t) * max(self.mixed['half_spread'], prefix_shift)))

    def eps_coll(self) -> dict:
        h400 = self.variant_h(two_point=self.aux.tp400, a_face=self.aux.a8192_400)
        tp4, tp8 = self.aux.tp400, self.aux.tp800
        return dict(h_collapsed_400000=h400, h_collapsed_800000=self.main['h'],
                    Xdisc_shift=tp8['Xdisc'] - tp4['Xdisc'], Dmixed_shift=tp8['Dmixed'] - tp4['Dmixed'],
                    X2_shift=tp8['X2'] - tp4['X2'], A_face_shift=self.aux.a8192_800 - self.aux.a8192_400,
                    eps_coll=float(abs(h400 - self.main['h'])))

    def eps_tailcut(self) -> dict:
        h2048 = self.variant_h(a_face=self.aux.a2048_800)
        return dict(A_face_8192=self.aux.a8192_800, A_face_2048=self.aux.a2048_800,
                    h_tail_2048=h2048, eps_tailcut=float(abs(h2048 - self.main['h'])))

    def roundoff(self) -> dict:
        x = np.abs(np.asarray(self.rec.data['raw']['Xchain'], dtype=float))
        n = np.arange(1, len(x) + 1)
        r = x * EPS * np.sqrt(n) + abs(self.asm['constant']) * EPS
        return dict(eps_round=propagate(self.main['_chosen'], r), constant=self.asm['constant'],
                    max_abs_raw_chain=float(np.max(x)))

    def grid_split(self, delta_signed: np.ndarray) -> dict:
        """A5-1 epsilon_grid of a FULL-coverage signed profile (len(delta) >= N)."""
        if len(delta_signed) < self.N:
            raise ValueError('epsilon_grid needs a profile that covers every n of the record')
        return grid_split(self.main['_chosen'], np.asarray(delta_signed[:self.N], dtype=float))

    def illustrative_grid(self, signed: np.ndarray, other_chain: np.ndarray | None) -> dict:
        """Illustrative checks only (NOT epsilon_grid, never in any budget): the signed shift of each
        accepted selected fit, sum_n v_n delta_n, with delta = primary - check; constant and linear
        shifts fitted to delta over the last quarter of the overlap; and, when the check covers every
        n of this record, the change of the median when its chain replaces this record's chain."""
        m = len(signed)
        tail = slice(max(0, m - m // 4), m)
        n = np.arange(1, m + 1)
        const = float(np.mean(signed[tail]))
        b, a = np.polyfit(n[tail], signed[tail], 1)
        out = dict(constant_shift=const, linear_shift_at_N=float(a + b * self.N),
                   linear_model=dict(intercept=float(a), slope=float(b)))
        if m >= self.N:
            out['max_abs_signed_fit_shift'] = float(max(abs(f['_v'] @ signed[f['_n'] - 1]) for f in self.main['_chosen']))
        if other_chain is not None and len(other_chain) >= self.N:
            d = dict(self.rec.data, raw=dict(self.rec.data['raw'], Xchain=list(other_chain[:self.N])))
            seq, _ = assemble(d, self.aux.tp800, self.mixed['selected'])
            h2 = m3(seq, self.N, self.lam, self.k, self.aux.a8192_800, full=False)['h']
            out['median_shift_by_replacement'] = float(self.main['h'] - h2)
        return out


# ------------------------------------------------------------------ regulator fits (M6)

def windows_for(points: list[dict], order: int) -> list[tuple[str, int, list[dict]]]:
    pts = sorted(points, key=lambda p: p['lam'])
    out = [('all', 0, pts), ('drop1', 1, pts[:-1]), ('drop2', 2, pts[:-2])]
    for i, c in enumerate(CUTS[order]):
        out.append((f'lam<={c}', 3 + i, [p for p in pts if p['lam'] <= c + 1e-12]))
    return out


def reg_fit(points: list[dict], terms, weighted: bool) -> dict:
    x = np.array([p['lam'] for p in points])
    y = np.array([p['h'] for p in points])
    s = np.array([p['eps_spec'] for p in points])
    A = np.array([np.ones_like(x)] + [basis(x, t) for t in terms]).T
    B = A / s[:, None] if weighted else A
    b = y / s if weighted else y
    c = np.linalg.lstsq(B, b, rcond=None)[0]
    res = A @ c - y
    pinv0 = np.linalg.pinv(B)[0]
    w = pinv0 / s if weighted else pinv0
    cond = float(np.linalg.cond(B))
    dof = len(x) - len(c)
    max_res = float(np.max(np.abs(res)))
    lim = ADMISSIBLE['residual_factor'] * float(np.max(s))
    adm = bool(dof >= ADMISSIBLE['min_dof'] and max_res <= lim and cond < ADMISSIBLE['max_condition'])
    reasons = [r for r, bad in [('dof < 2', dof < ADMISSIBLE['min_dof']), ('residual', max_res > lim),
                                ('condition', cond >= ADMISSIBLE['max_condition'])] if bad]
    return dict(order=points[0]['order'], point_ids=[p['id'] for p in points], lambdas=x.tolist(),
                terms=list(terms), weighted=weighted, h0=float(c[0]), coefficients=c.tolist(),
                residuals=res.tolist(), max_residual=max_res, residual_limit=lim, condition=cond,
                number_of_points=len(x), number_of_parameters=len(c), dof=dof, saturated=dof <= 0,
                admissible=adm, rejection_reasons=reasons, influence=w.tolist())


def dedup_key(fit: dict) -> tuple:
    return (tuple(sorted(fit['point_ids'])), tuple(fit['terms']), fit['weighted'])


def regulator_order(points: list[dict], order: int) -> dict:
    """All M6 fits of one order (deduplicated), S_r, eps_model and validation status."""
    fits: dict[tuple, dict] = {}
    skipped = []
    for label, index, pts in windows_for(points, order):
        for terms in ALL_TERM_SETS:
            if len(terms) + 1 > len(pts):
                skipped.append(dict(window=label, terms=list(terms), points=len(pts)))
                continue
            for weighted in (False, True):
                f = reg_fit(pts, terms, weighted)
                key = dedup_key(f)
                if key in fits:
                    fits[key]['windows'].append(label)
                    fits[key]['window_indices'].append(index)
                else:
                    f['windows'] = [label]
                    f['window_indices'] = [index]
                    f['sensitivity_variant'] = tuple(terms) == SENSITIVITY_TERM_SET
                    fits[key] = f
    allfits = list(fits.values())
    pref_label = f'lam<={PREFERRED["cut"][order]}'
    pref = [f for f in allfits if pref_label in f['windows'] and tuple(f['terms']) == PREFERRED['terms']
            and f['weighted'] is PREFERRED['weighted']]
    if len(pref) > 1:
        raise ValueError(f'order {order}: preferred fit not unique')
    if pref:
        pref = pref[0]
        pref['preferred'] = True
    else:
        # R002: the preferred window has too few points for the preferred model (it is underdetermined and was not
        # fitted). It is represented as a rejected, unavailable fit; the fallback and validation rules then apply.
        n_pref = len([p for p in points if p['lam'] <= PREFERRED['cut'][order] + 1e-12])
        pref = dict(order=order, terms=list(PREFERRED['terms']), weighted=PREFERRED['weighted'], windows=[pref_label],
                    number_of_points=n_pref, number_of_parameters=len(PREFERRED['terms']) + 1, admissible=False,
                    available=False, preferred=True,
                    rejection_reasons=[f'unavailable: {n_pref} point(s) in {pref_label} for '
                                       f'{len(PREFERRED["terms"]) + 1} parameters (fit not attempted; admissibility '
                                       f'needs >= {len(PREFERRED["terms"]) + 1 + ADMISSIBLE["min_dof"]} points)'])
    admissible = [f for f in allfits if f['admissible']]
    if pref['admissible']:
        S, status = pref, 'preferred admissible'
    elif admissible:
        S = sorted(admissible, key=lambda f: (f['number_of_parameters'], -f['number_of_points'],
                                               f['weighted'], f['condition']))[0]
        status = 'preferred rejected' if pref.get('available', True) else 'preferred unavailable'
    else:
        S, status = None, 'no admissible fit'
    for f in allfits:
        f['selected'] = f is S
    out = dict(order=order, fits=allfits, skipped_underdetermined=skipped, n_fits=len(allfits),
               n_admissible_distinct=len(admissible), preferred=pref, S=S, selection_status=status)
    if S is None or len(admissible) < MIN_DISTINCT_ADMISSIBLE:
        out['validated'] = False
        out['validation_status'] = 'insufficiently validated'
        out['exclusion_reason'] = ('no admissible fit' if S is None else
                                   f'{len(admissible)} distinct admissible fit(s) < {MIN_DISTINCT_ADMISSIBLE}')
    else:
        out['validated'] = True
        out['validation_status'] = f'{len(admissible)} distinct admissible fits'
    if S is not None:
        dev = [abs(f['h0'] - S['h0']) for f in admissible] or [0.0]
        out['eps_model'] = float(max(dev))
        hs = [f['h0'] for f in admissible]
        out['admissible_descriptive'] = dict(minimum=min(hs), maximum=max(hs), half_range=(max(hs) - min(hs)) / 2,
                                             count=len(hs)) if hs else None
    return out


COMPONENTS = ('eps_spec', 'eps_mix', 'eps_coll', 'eps_grid', 'eps_round', 'eps_tailcut')
BREAKDOWN = ('half_spread', 'prefix_d34', 'eps_cross')
# Reported through the same influence rows, never in E (rev 6/7): the parts of eps_grid and the superseded rev-4 L1.
REPORTED = ('grid_smooth', 'grid_rough', 'grid_rev4_l1', 'grid_signed')


def propagate_points(influence: dict[str, float], points: dict[str, dict]) -> dict:
    out = {}
    for c in COMPONENTS + BREAKDOWN + REPORTED:
        if c in REPORTED and not all(c in points[i] for i in influence):
            continue
        out[c] = float(sum(abs(w) * (points[i][c] or 0.0) for i, w in influence.items()))
    out['eps_prop'] = out.pop('eps_spec')
    return out


def order_budget(reg: dict, points: dict[str, dict]) -> dict:
    S = reg['S']
    w = dict(zip(S['point_ids'], S['influence']))
    comp = propagate_points(w, points)
    E = (comp['eps_prop'] + comp['eps_mix'] + comp['eps_coll'] + comp['eps_grid'] + comp['eps_round']
         + comp['eps_tailcut'] + reg['eps_model'])
    return dict(h0=S['h0'], components=dict(comp, eps_model=reg['eps_model']), E=float(E),
                sum_abs_influence=float(sum(abs(x) for x in w.values())))


# ------------------------------------------------------------------ joint fit (M7)

def joint_fit(blocks: list[dict]) -> dict:
    """blocks: [{'order', 'points', 'terms', 'weighted'}]; shared intercept h0."""
    ncols = 1 + sum(len(b['terms']) for b in blocks)
    rows, y, s, owner, ids = [], [], [], [], []
    col = 1
    for bi, b in enumerate(blocks):
        for p in b['points']:
            r = np.zeros(ncols)
            r[0] = 1.0
            for j, t in enumerate(b['terms']):
                r[col + j] = basis(np.array([p['lam']]), t)[0]
            rows.append(r)
            y.append(p['h'])
            s.append(p['eps_spec'] if b['weighted'] else 1.0)
            owner.append(bi)
            ids.append(p['id'])
        col += len(b['terms'])
    A = np.array(rows)
    y = np.array(y)
    s = np.array(s)
    owner = np.array(owner)
    B = A / s[:, None]
    c = np.linalg.lstsq(B, y / s, rcond=None)[0]
    res = A @ c - y
    w = np.linalg.pinv(B)[0] / s
    cond = float(np.linalg.cond(B))
    checks = []
    ok = cond < ADMISSIBLE['max_condition']
    for bi, b in enumerate(blocks):
        m = owner == bi
        dof_b = int(m.sum()) - len(b['terms']) - 1
        mr = float(np.max(np.abs(res[m])))
        lim = ADMISSIBLE['residual_factor'] * max(p['eps_spec'] for p in b['points'])
        good = dof_b >= ADMISSIBLE['min_dof'] and mr <= lim
        ok = ok and good
        checks.append(dict(order=b['order'], points=int(m.sum()), terms=list(b['terms']), weighted=b['weighted'],
                           block_dof=dof_b, max_residual=mr, residual_limit=lim, passed=bool(good)))
    return dict(h0=float(c[0]), coefficients=c.tolist(), condition=cond, total_dof=int(len(y) - len(c)),
                blocks=checks, accepted=bool(ok), point_ids=ids, influence=w.tolist(),
                residuals=res.tolist())


def joint_analysis(regs: dict[int, dict], retained: list[int], points: dict[str, dict],
                   points_by_order: dict[int, list[dict]]) -> dict:
    blocks = []
    for r in retained:
        S = regs[r]['S']
        pts = [points[i] for i in S['point_ids']]
        blocks.append(dict(order=r, points=pts, terms=tuple(S['terms']), weighted=S['weighted']))
    pref = joint_fit(blocks)
    variants: dict[tuple, dict] = {}
    for terms in ALL_TERM_SETS:
        for index in range(6):
            for weighted in (False, True):
                bl = []
                for r in retained:
                    wins = {i: pts for _, i, pts in windows_for(points_by_order[r], r)}
                    bl.append(dict(order=r, points=wins[index], terms=tuple(terms), weighted=weighted))
                if any(len(b['points']) < len(b['terms']) + 1 for b in bl):
                    continue
                key = (tuple(tuple(sorted(p['id'] for p in b['points'])) for b in bl), tuple(terms), weighted)
                if key in variants:
                    variants[key]['window_indices'].append(index)
                    continue
                f = joint_fit(bl)
                f.update(terms=list(terms), weighted=weighted, window_indices=[index])
                variants[key] = f
    allv = list(variants.values())
    adm = [v for v in allv if v['accepted']]
    eps_model = float(max([abs(v['h0'] - pref['h0']) for v in adm] or [0.0]))
    w = dict(zip(pref['point_ids'], pref['influence']))
    comp = propagate_points(w, points)
    E = (comp['eps_prop'] + comp['eps_mix'] + comp['eps_coll'] + comp['eps_grid'] + comp['eps_round']
         + comp['eps_tailcut'] + eps_model)
    for v in allv:
        v.pop('influence', None)
        v.pop('residuals', None)
    return dict(preferred=pref, variants=allv, n_variants=len(allv), n_admissible_distinct=len(adm),
                eps_model_joint=eps_model, components=dict(comp, eps_model=eps_model), E=float(E),
                validated=bool(pref['accepted'] and len(adm) >= MIN_DISTINCT_ADMISSIBLE))


def outcome(per_order: dict[int, dict], joint: dict | None) -> dict:
    """The pre-declared outcome table (M7)."""
    retained = sorted(per_order)
    if not retained:
        return dict(branch=1, label='insufficiently validated', h0=None, E=None)
    if len(retained) == 1:
        r = retained[0]
        return dict(branch=2, label='single order, not cross-validated', h0=per_order[r]['h0'],
                    E=per_order[r]['E'], orders=retained)
    pairs = []
    consistent = True
    for i, a in enumerate(retained):
        for b in retained[i + 1:]:
            d = abs(per_order[a]['h0'] - per_order[b]['h0'])
            lim = per_order[a]['E'] + per_order[b]['E']
            pairs.append(dict(orders=[a, b], difference=d, limit=lim, consistent=d <= lim))
            consistent = consistent and d <= lim
    lo = min(per_order[r]['h0'] - per_order[r]['E'] for r in retained)
    hi = max(per_order[r]['h0'] + per_order[r]['E'] for r in retained)
    envelope = dict(low=lo, high=hi, midpoint=(lo + hi) / 2, half_width=(hi - lo) / 2)
    base = dict(orders=retained, pairs=pairs, consistent=consistent, envelope=envelope)
    if not consistent:
        return dict(base, branch=3, label='orders inconsistent', h0=envelope['midpoint'], E=envelope['half_width'])
    if joint is not None and joint['validated']:
        return dict(base, branch=4, label='joint fit (orders consistent, joint fit validated)', h0=joint['preferred']['h0'],
                    E=joint['E'])
    return dict(base, branch=5, label='orders consistent, joint fit not validated', h0=envelope['midpoint'],
                E=envelope['half_width'])


def c2_from_h0(h0: float, dh0: float | None = None) -> dict:
    import mpmath as mp
    mp.mp.dps = 50
    b0 = 9 * mp.pi ** 2 / 8 * (mp.gamma(mp.mpf(3) / 4) / mp.gamma(mp.mpf(1) / 4)) ** 2
    a1 = -mp.pi ** 2 / 4
    out = dict(b0=str(b0), a1_over_b0=str(a1 / b0), C2=float(a1 / b0 + mp.mpf(h0) / b0 ** 2),
               dC2_per_dh0=float(1 / b0 ** 2))
    if dh0 is not None:
        out['dC2'] = float(mp.mpf(dh0) / b0 ** 2)
    return out
