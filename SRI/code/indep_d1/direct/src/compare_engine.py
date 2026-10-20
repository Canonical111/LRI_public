#!/usr/bin/env python3
"""Compare the engine's small-cutoff expansions with the direct finite-cutoff values.

Engine input (JSON).  One entry per raw moment; three layouts are accepted:

  (a) {"A7_v": {"terms": [[k, j, coeff], ...], "kmax": K}}
  (b) {"A7_v": {"k,j": coeff | [value, err], ...}}           (optionally wrapped in {"results": {...}})
  (c) {"A7_v[eps^0 l^1]": [value, err], ...}                 (the engine's flat e2e_*_raw_flat.json)

coeff multiplies eps^k l^j, l = log(eps); derivative convention d_v^a d_delta^b (NOT Taylor coefficients).
Engine names are mapped to the direct names: A5_vE -> EA5_v, A5_E -> EA5_base, Q8 -> Q8_base.
An entry may carry the covariance of its coefficients:
  "cov": {"keys": ["0,0", "0,1", ...], "matrix": [[...], ...]}            or
  "replicates": {"keys": [...], "values": [[...], ...]}   (independent replicate estimates of the mean;
                                                           covariance of the mean = sample cov / n_rep)
otherwise the quoted per-coefficient errors are used as independent (diagonal) priors.  The covariance is
used among the nuisance coefficients and within the tested pair (c00, c01); correlations between the tested
pair and the nuisances are not used, and --merge drops covariances.

Part 1 (always): direct - engine at every direct cutoff (raw table; for an engine series that omits
coefficients, e.g. the negative eps powers the framework does not need, the raw difference is dominated by
the omitted terms and is flagged 'partial').

Part 2 (--offset-fit): generalized least squares test of the engine's [eps^0 l^0] and [eps^0 l^1].
For one moment, with r_i = direct(eps_i) - engine(eps_i) over the cutoffs eps_i <= --fit-eps-max:

    r(eps) = d0 + d1 l                                          test parameters (free)
           + sum_{(k,j) quoted with err > 0} x_kj eps^k l^j      engine nuisance shifts, Gaussian prior
                                                                 x ~ N(0, Sigma_engine)   (prior rows)
           + sum_{(k,j) in the structure, not quoted} f_kj eps^k l^j   missing structural terms (free)
           + sum_{k=K+1}^{K+P} sum_{j<=J} t_kj eps^k l^j        omitted eps powers (free)

  * data weights are the DIRECT errors only (the engine's errors enter through the prior rows, once,
    because each coefficient error is common to all cutoffs);
  * coefficients quoted with err = 0 are taken as exact;
  * the structure (which (k, j) with k <= K can occur) is: eps powers from p_min (spec tight bounds:
    A_{2m+1}, Z_{2m}, EA_{2m+1}: -m; Q_{2m}, EZ_{2m}, EQ_{2m}: -(m-1)) to K, log degree at k = 0 the
    highest nonzero one quoted by the engine (J0); at a power k != 0 where the engine quotes entries, its own
    range (incl. structural zeros); at k < 0 where it quotes nothing, max(0, J0 + 2k + 1) (satisfied by every
    complete engine series available: A3, A5, Z4, Z6, Q4, Q6 and derivatives);
  * tail model variants: J from max(0, J_K - 2) to J_K + 1 (J_K = highest nonzero log degree at k = K),
    P = 1, 2, 3; a variant needs dof >= --min-dof; MODEL-FAIL unless some variant has chi2/dof <= --chi2-max
    (chi2 = data rows + prior rows, dof = n_points - free parameters);
  * tail selection: the direct errors are conservative (a correct model gives chi2/dof ~ 0.01-0.1), so the
    absolute gate alone would accept biased, under-fitted tails; the central variant minimizes
    BIC = chi2/s2 + nfree ln(npts) with the observed noise scale s2 = min(1, smallest chi2/dof among the
    variants with dof >= 4), which does not depend on the overall scale of the quoted errors; variants with
    BIC - BIC_min <= 6 are 'competitive';
  * u is inflated (never deflated) by sqrt(max(1, chi2/dof)).

Reported per moment (central variant): d0 +- u0 (posterior sd), the engine's own sigma e00, the pull
pull0 = d0 / sqrt(u0^2 + e00^2); the same for d1; the joint 2-dof statistic X2 = d^T (C_d + C_eng)^-1 d;
chi2/dof; 3-sigma detectable sizes 3 sqrt(u^2 + e^2).  Verdicts:
  MODEL-FAIL   no tail variant passes the absolute gate (engine series + structure + tail cannot describe
               the data: e.g. a wrong exact or higher-log coefficient, a missing structural term);
  OFFSET       |pull0| >= 3 or |pull1| >= 3 or X2 >= 11.83 (2-dof 3-sigma) in the central variant AND in
               every competitive variant;
  TENSION      flagged in the central variant but not in every competitive variant (tail-model dependent;
               inspect, do not quote as an error);
  PASS         otherwise;
  INCONCLUSIVE the engine series omits structural coefficients (other than the tested c00): they enter as free
               parameters, can mimic the tail, and the verdict is unreliable (false 3-7 sigma flags were
               seen on the engine's pilot5 series whose complete counterparts PASS); verdict_raw is kept;
  UNTESTABLE   no variant with enough degrees of freedom (an engine series that omits most negative powers).
  --merge completes a partial series with the coefficients of other files (e.g. validation runs).
A coefficient the engine does not quote (e.g. [eps^0 l^0] of A7, only l^1 enters the beta inputs) is a free
parameter and is reported as untested.
d = (value preferred by the direct data) - (engine value); an error +delta injected into the engine's
c00 therefore shows up as d0 -> d0 - delta.
"""
import argparse
import glob
import json
import math
import os
import re

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'results')
JOINT_3SIGMA_2DOF = 11.829  # chi2_2 quantile at p = 0.0027


# ----------------------------------------------------------------------------------------------------
# engine input
# ----------------------------------------------------------------------------------------------------
NAME_RE = re.compile(r'^(E?)([AZQ])(\d+)(?:_(base|[vdE]+))?$')


def direct_name(nm):
    """engine name -> direct-table name (A5_vE -> EA5_v, Q8 -> Q8_base); None if not a moment name."""
    m = NAME_RE.match(nm)
    if not m:
        return None
    e, T, n, ders = m.groups()
    ders = '' if ders in (None, 'base') else ders
    if 'E' in ders:
        if ders.count('E') > 1 or e:
            return None          # second source derivative: no direct counterpart
        e, ders = 'E', ders.replace('E', '')
    return '%s%s%s_%s' % (e, T, n, ders or 'base')


def moment_info(dn):
    m = NAME_RE.match(dn)
    e, T, n, ders = m.groups()
    ders = '' if ders in (None, 'base') else ders
    return dict(src=bool(e), T=T, n=int(n), a=ders.count('v'), b=ders.count('d'))


def pmin_tight(info):
    """lowest eps power (spec/out/raw_requirements.json 'tight_bounds')."""
    m = info['n'] // 2
    if info['T'] == 'A':
        return -m
    if info['T'] == 'Z':
        return -(m - 1) if info['src'] else -m
    return -(m - 1)             # Q, EQ


def _val_err(c):
    if isinstance(c, (list, tuple)):
        return mp.mpf(str(c[0])), (mp.mpf(str(c[1])) if len(c) > 1 else mp.mpf(0))
    return mp.mpf(str(c)), mp.mpf(0)


def _key(s):
    k, j = map(int, str(s).strip('()[] ').split(','))
    return (k, j)


def parse_entry(e):
    terms = {}
    if isinstance(e, dict) and 'terms' in e:
        for t in e['terms']:
            terms[(int(t[0]), int(t[1]))] = _val_err(t[2:] if len(t) > 3 else t[2])
    elif isinstance(e, dict):
        for key, c in e.items():
            if ',' not in str(key):
                continue
            terms[_key(key)] = _val_err(c)
    else:
        raise ValueError('unrecognised entry')
    cov = None
    if isinstance(e, dict) and isinstance(e.get('cov'), dict):
        cov = ([_key(k) for k in e['cov']['keys']], [[mp.mpf(str(x)) for x in row] for row in e['cov']['matrix']])
    elif isinstance(e, dict) and isinstance(e.get('replicates'), dict):
        keys = [_key(k) for k in e['replicates']['keys']]
        vals = [[mp.mpf(str(x)) for x in row] for row in e['replicates']['values']]
        nr = len(vals)
        mean = [sum(v[i] for v in vals) / nr for i in range(len(keys))]
        cm = [[sum((v[i] - mean[i]) * (v[j] - mean[j]) for v in vals) / (nr - 1) / nr for j in range(len(keys))]
              for i in range(len(keys))]
        cov = (keys, cm)
    kmax = e.get('kmax') if isinstance(e, dict) else None
    return terms, cov, kmax


FLAT_RE = re.compile(r'^(.+)\[eps\^(-?\d+) l\^(\d+)\]$')


def _merge(old, new):
    """union of the coefficients of two engine entries of the same moment; for a coefficient quoted by both
    the one with the smaller error is kept (exact = error 0 wins)."""
    terms = dict(old['terms'])
    for t, (c, e) in new['terms'].items():
        if t not in terms or e < terms[t][1]:
            terms[t] = (c, e)
    km = [k for k in (old.get('kmax'), new.get('kmax')) if k is not None]
    return dict(terms=terms, cov=None, kmax=max(km) if km else None, source=old['source'] + ' + ' + new['source'],
                engine_name=old['engine_name'])


def load_engine(paths, merge=False):
    data = {}
    files = []
    for p in paths:
        if os.path.isdir(p):
            files += sorted(glob.glob(os.path.join(p, '**', '*.json'), recursive=True))
        else:
            files.append(p)
    for f in files:
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        if isinstance(d.get('results'), dict):
            d = d['results']
        flat = {}
        for nm, e in d.items():
            m = FLAT_RE.match(nm)
            if m:                                   # layout (c)
                flat.setdefault(m.group(1), {})['%s,%s' % (m.group(2), m.group(3))] = e
                continue
            dn = direct_name(nm)
            if dn is None:
                continue
            try:
                terms, cov, kmax = parse_entry(e)
            except Exception:
                continue
            if terms:
                ent = dict(terms=terms, cov=cov, kmax=kmax, source=f, engine_name=nm)
                data[dn] = _merge(data[dn], ent) if (merge and dn in data) else ent
        for nm, e in flat.items():
            dn = direct_name(nm)
            if dn is None:
                continue
            terms, cov, kmax = parse_entry(e)
            ent = dict(terms=terms, cov=cov, kmax=kmax, source=f, engine_name=nm)
            data[dn] = _merge(data[dn], ent) if (merge and dn in data) else ent
    return data


# ----------------------------------------------------------------------------------------------------
# structure of the expansion and the residual model
# ----------------------------------------------------------------------------------------------------
def nz_degree(terms, k):
    js = [j for (kk, j), (c, e) in terms.items() if kk == k and c != 0]
    return max(js) if js else None


def structure(dn, ent):
    terms = ent['terms']
    info = moment_info(dn)
    ks = sorted({k for k, j in terms})
    K = int(ent['kmax']) if ent.get('kmax') is not None else max(max(ks), 0)
    J0 = nz_degree(terms, 0)
    if J0 is None:
        J0 = max([j for (k, j) in terms if k == 0] or [max(j for k, j in terms)])
    pm = min(pmin_tight(info), min(ks))
    S = set()
    for k in range(pm, K + 1):
        decl = [j for (kk, j) in terms if kk == k]
        if decl:                    # the engine's own (pole-order) range at this power, incl. structural zeros
            jm = max(decl)
        elif k < 0:
            jm = max(0, J0 + 2 * k + 1)
        else:
            jm = max(0, J0 - k)
        S |= {(k, j) for j in range(jm + 1)}
    JK = nz_degree(terms, K)
    if JK is None:
        JK = J0
    return dict(S=S, K=K, J0=J0, JK=JK, pmin=pm)


def evaluate(terms, eps):
    e = mp.mpf(eps)
    l = mp.log(e)
    return sum((c * e ** k * l ** j for (k, j), (c, err) in terms.items()), mp.mpf(0))


def fit_points(tab, dn, ent, eps_max, eps_min=0.0):
    pts = []
    for el in sorted(tab, key=float):
        x = float(el)
        if eps_min <= x <= eps_max and dn in tab[el]:
            d = tab[el][dn]
            sg = d.get('err') or 2e-15 * abs(d.get('abs_integral') or d['value'])
            r = mp.mpf(repr(d['value'])) - evaluate(ent['terms'], el)
            pts.append((mp.mpf(el), r, mp.mpf(repr(sg)), el))
    return pts


def _prior_whitener(ent, nuis):
    """matrix W with W x ~ N(0, 1) for the nuisance vector x (rows = prior rows)."""
    n = len(nuis)
    errs = [ent['terms'][t][1] for t in nuis]
    Sig = mp.matrix(n, n)
    for i in range(n):
        Sig[i, i] = errs[i] ** 2
    if ent.get('cov'):
        keys, M = ent['cov']
        pos = {k: i for i, k in enumerate(keys)}
        for a, ta in enumerate(nuis):
            for b, tb in enumerate(nuis):
                if ta in pos and tb in pos:
                    Sig[a, b] = M[pos[ta]][pos[tb]]
        L = mp.cholesky(Sig)
        return mp.inverse(L)
    W = mp.matrix(n, n)
    for i in range(n):
        W[i, i] = 1 / errs[i]
    return W


def engine_test_cov(ent, tests):
    """engine covariance block of the tested coefficients (0 if not quoted)."""
    n = len(tests)
    C = mp.matrix(n, n)
    for i, t in enumerate(tests):
        if t in ent['terms']:
            C[i, i] = ent['terms'][t][1] ** 2
    if ent.get('cov'):
        keys, M = ent['cov']
        pos = {k: i for i, k in enumerate(keys)}
        for a, ta in enumerate(tests):
            for b, tb in enumerate(tests):
                if ta in pos and tb in pos:
                    C[a, b] = M[pos[ta]][pos[tb]]
    return C


_DESIGN_CACHE = {}


def _design(pts, ent, st, J, P):
    """design matrix (data rows / direct err, prior rows), column scaling and its QR factor.
    It depends on the cutoffs, the direct errors, the error structure of the engine entry and the tail,
    not on the coefficient values, so it is cached (injection tests reuse it)."""
    terms = ent['terms']
    tests = [t for t in ((0, 0), (0, 1)) if t in st['S'] or t in terms]
    nuis = sorted(t for t, (c, e) in terms.items() if e > 0 and t not in tests)
    free = sorted(t for t in st['S'] if t not in terms and t not in tests)
    tail = [(k, j) for k in range(st['K'] + 1, st['K'] + P + 1) for j in range(J + 1)]
    nfree = len(tests) + len(free) + len(tail)
    dof = len(pts) - nfree
    if dof < 1:
        return None
    key = (tuple(p[3] for p in pts), tuple(str(p[2]) for p in pts), tuple(tests), tuple(nuis),
           tuple(str(terms[t][1]) for t in nuis), repr(ent.get('cov')), tuple(free), J, P, st['K'], mp.mp.dps)
    if key in _DESIGN_CACHE:
        return _DESIGN_CACHE[key]
    cols = [('t',) + t for t in tests] + [('n',) + t for t in nuis] + [('f',) + t for t in free] + \
           [('x',) + t for t in tail]
    rows = []
    for x, r, sg, el in pts:
        l = mp.log(x)
        rows.append([x ** c[1] * l ** c[2] / sg for c in cols])
    ndata = len(rows)
    if nuis:
        W = _prior_whitener(ent, nuis)
        off = len(tests)
        for i in range(len(nuis)):
            row = [mp.mpf(0)] * len(cols)
            for j in range(len(nuis)):
                row[off + j] = W[i, j]
            rows.append(row)
    A = mp.matrix(rows)
    sc = []
    for c in range(A.cols):
        s_ = max(abs(A[i, c]) for i in range(A.rows)) or mp.mpf(1)
        sc.append(s_)
        for i in range(A.rows):
            A[i, c] /= s_
    Qm, Rm = mp.qr(A)
    n = A.cols
    Rinv = mp.inverse(Rm[0:n, 0:n])
    d = dict(tests=tests, nuis=nuis, free=free, tail=tail, nfree=nfree, dof=dof, ndata=ndata, A=A,
             QT=Qm[:, 0:n].T, Rinv=Rinv, cov=Rinv * Rinv.T, sc=sc, n=n)
    _DESIGN_CACHE[key] = d
    return d


def gls_variant(pts, ent, st, J, P):
    """one GLS fit; returns dict or None (not enough data)."""
    terms = ent['terms']
    D = _design(pts, ent, st, J, P)
    if D is None:
        return None
    tests, nuis, free, tail, nfree, dof, ndata = (D[k] for k in ('tests', 'nuis', 'free', 'tail', 'nfree', 'dof',
                                                                    'ndata'))
    A, n, sc, cov = D['A'], D['n'], D['sc'], D['cov']
    bb = mp.matrix([r / sg for x, r, sg, el in pts] + [mp.mpf(0)] * len(nuis))
    xs = D['Rinv'] * (D['QT'] * bb)
    res = bb - A * xs
    chi2_data = sum(res[i] ** 2 for i in range(ndata))
    chi2_prior = sum(res[i] ** 2 for i in range(ndata, A.rows))
    xv = [xs[i] / sc[i] for i in range(n)]
    cv = [[cov[i, j] / (sc[i] * sc[j]) for j in range(len(tests))] for i in range(len(tests))]
    out = dict(J=J, P=P, npts=len(pts), n_test=len(tests), n_nuis=len(nuis), n_free_missing=len(free),
               n_tail=len(tail), nfree=nfree, dof=dof, chi2_data=chi2_data, chi2_prior=chi2_prior,
               chi2_dof=(chi2_data + chi2_prior) / dof, tests=tests, free_missing=free)
    Ceng = engine_test_cov(ent, tests)
    S2 = max(mp.mpf(1), out['chi2_dof'])      # PDG-style scale factor: inflate (never deflate) the data errors
    cv = [[c * S2 for c in row] for row in cv]
    out['scale_factor'] = mp.sqrt(S2)
    for i, t in enumerate(tests):
        tag = 'd%d' % t[1]
        e = mp.sqrt(Ceng[i, i])
        u = mp.sqrt(abs(cv[i][i]))
        out[tag] = xv[i]
        out['u' + tag[1]] = u
        out['e' + tag[1]] = e
        out['quoted' + tag[1]] = t in terms
        out['pull' + tag[1]] = xv[i] / mp.sqrt(u ** 2 + e ** 2) if t in terms else None
        out['detect3_' + tag[1]] = 3 * mp.sqrt(u ** 2 + e ** 2)
    q = [i for i, t in enumerate(tests) if t in terms]
    if q:
        M = mp.matrix(len(q), len(q))
        v = mp.matrix(len(q), 1)
        for a, i in enumerate(q):
            v[a] = xv[i]
            for bq, j in enumerate(q):
                M[a, bq] = cv[i][j] + Ceng[i, j]
        X2 = (v.T * mp.inverse(M) * v)[0]
        out['joint_X2'] = X2
        out['joint_ndof'] = len(q)
    return out


def tail_variants(st, Js=None, Ps=(1, 2, 3)):
    JK = st['JK']
    Js = Js or list(range(max(0, JK - 2), JK + 2))
    return [(J, P) for P in Ps for J in Js]


def offset_test(tab, dn, ent, eps_max=0.021, eps_min=0.0, chi2_max=2.5, min_dof=3, Js=None, Ps=(1, 2, 3),
                noise_min_dof=4, dbic_competitive=6.0):
    """GLS test of one moment over the tail variants (see the module docstring).

    Gate:   MODEL-FAIL unless some variant has chi2/dof <= chi2_max with the quoted direct errors.
    Select: the quoted direct errors are conservative (a correct model gives chi2/dof ~ 0.01-0.1), so the
            tail is chosen by BIC = chi2/s2 + nfree*ln(npts), with the observed noise scale
            s2 = min(1, smallest chi2/dof among the variants with dof >= noise_min_dof); this does not depend
            on the overall scale of the quoted errors.  Central = minimum BIC; 'competitive' variants have
            BIC - BIC_min <= dbic_competitive.
    Verdict: OFFSET if the central variant is flagged (|pull| >= 3 or joint X2 at 3 sigma) and so is every
            competitive variant; TENSION if the central one is flagged but some competitive one is not
            (tail-model dependent); PASS otherwise.
    """
    st = structure(dn, ent)
    pts = fit_points(tab, dn, ent, eps_max, eps_min)
    base = dict(name=dn, engine_name=ent.get('engine_name'), K=st['K'], J0=st['J0'], JK=st['JK'], pmin=st['pmin'],
                npts=len(pts), eps_range=[float(pts[0][0]), float(pts[-1][0])] if pts else None,
                settings=dict(eps_max=eps_max, eps_min=eps_min, chi2_max=chi2_max, min_dof=min_dof,
                              noise_min_dof=noise_min_dof, dbic_competitive=dbic_competitive))
    vars_ = []
    for J, P in tail_variants(st, Js, Ps):
        try:
            r = gls_variant(pts, ent, st, J, P)
        except (ZeroDivisionError, ValueError):      # singular design
            r = None
        if r is None or r['dof'] < min_dof:
            continue
        vars_.append(r)
    base['variants'] = vars_
    if not vars_:
        base['verdict'] = 'UNTESTABLE'
        return base
    best = min(vars_, key=lambda v: v['chi2_dof'])
    for v in vars_:
        v['acceptable'] = bool(v['chi2_dof'] <= chi2_max)
    if not best['acceptable']:
        base.update(verdict='MODEL-FAIL', central=best, noise_s2=None)
        return base
    pool = [v['chi2_dof'] for v in vars_ if v['dof'] >= noise_min_dof] or [best['chi2_dof']]
    s2 = min(mp.mpf(1), min(pool))
    if s2 <= 0:
        s2 = mp.mpf('1e-30')
    base['noise_s2'] = s2
    lnn = mp.log(len(pts))
    for v in vars_:
        v['bic'] = (v['chi2_data'] + v['chi2_prior']) / s2 + v['nfree'] * lnn
    cand = [v for v in vars_ if v['acceptable']]
    bmin = min(v['bic'] for v in cand)
    for v in vars_:
        v['dbic'] = v['bic'] - bmin
    cen = min(cand, key=lambda v: (v['bic'], v['nfree']))

    def flagged(v):
        f = False
        for c in ('0', '1'):
            p = v.get('pull' + c)
            if p is not None and abs(p) >= 3:
                f = True
        if v.get('joint_X2') is not None and v['joint_X2'] >= (JOINT_3SIGMA_2DOF if v['joint_ndof'] == 2 else 9):
            f = True
        return f

    for v in vars_:
        v['flagged'] = flagged(v)
    comp = [v for v in cand if v is not cen and v['dbic'] <= dbic_competitive]
    if not cen['flagged']:
        verdict = 'PASS'
    elif all(v['flagged'] for v in comp):
        verdict = 'OFFSET'
    else:
        verdict = 'TENSION'      # flagged, but a competitive tail variant is not: tail-model dependent
    if cen['n_free_missing'] > 0:
        # the engine series omits structural coefficients (negative eps powers, low logs): they are free
        # parameters here and can mimic the tail; the selected tail is then unreliable (demonstrated false
        # 3-7 sigma flags on pilot5 series whose complete counterparts PASS), so no verdict is drawn.
        base['verdict_raw'] = verdict
        verdict = 'INCONCLUSIVE'
    base.update(verdict=verdict, central=cen, n_competitive=len(comp),
                competitive=[dict(J=v['J'], P=v['P'], dbic=v['dbic'], flagged=v['flagged'],
                                  pull0=v.get('pull0'), pull1=v.get('pull1')) for v in comp],
                d0_range_competitive=[min(v['d0'] for v in comp + [cen]), max(v['d0'] for v in comp + [cen])]
                if 'd0' in cen else None,
                d1_range_competitive=[min(v['d1'] for v in comp + [cen]), max(v['d1'] for v in comp + [cen])]
                if 'd1' in cen else None)
    return base


def _f(x):
    if x is None:
        return None
    if isinstance(x, (list, tuple)):
        return [_f(y) for y in x]
    if isinstance(x, dict):
        return {k: _f(v) for k, v in x.items()}
    if isinstance(x, (mp.mpf,)):
        return float(x)
    return x


def summary_line(r):
    c = r.get('central')
    if not c:
        return '%-10s %-10s npts=%d (no variant with enough dof)' % (r['name'], r['verdict'], r['npts'])

    def fmt(t):
        if 'd' + t not in c:
            return '%-46s' % '-'
        if not c['quoted' + t]:
            return '%-46s' % ('%.2e +- %.1e (not quoted: untested)' % (c['d' + t], c['u' + t]))
        return '%-46s' % ('%+.2e +- %.1e e=%.1e p=%+.2f' % (c['d' + t], c['u' + t], c['e' + t], c['pull' + t]))
    return '%-10s %-2d %-2d %-2d %-2d %-4d %-3d %-3d %-46s %-46s %-8.2g %-8s %s%s' % (
        r['name'], r['K'], c['J'], c['P'], c['dof'], r['npts'], c['n_nuis'], c['n_free_missing'], fmt('0'), fmt('1'),
        c['chi2_dof'], ('%.3g' % c['joint_X2']) if c.get('joint_X2') is not None else '-', r['verdict'],
        '')


HEADER = '%-10s %-2s %-2s %-2s %-2s %-4s %-3s %-3s %-46s %-46s %-8s %-8s %s' % (
    'moment', 'K', 'J', 'P', 'df', 'npts', 'nui', 'mis', 'd0 +- u0  e00  pull0', 'd1 +- u1  e01  pull1',
    'chi2/dof', 'X2', 'verdict')


def raw_table(tab, eng):
    rows = []
    for nm in sorted(eng):
        st = structure(nm, eng[nm])
        partial = bool(st['S'] - set(eng[nm]['terms']))
        for el in sorted(tab, key=lambda s: -float(s)):
            d = tab[el].get(nm)
            if d is None:
                continue
            val = evaluate(eng[nm]['terms'], el)
            e = mp.mpf(el)
            l = mp.log(e)
            eerr = mp.sqrt(sum(((err * e ** k * l ** j) ** 2 for (k, j), (c, err) in eng[nm]['terms'].items()),
                               mp.mpf(0)))
            last = abs(sum((c * e ** k * l ** j for (k, j), (c, err) in eng[nm]['terms'].items() if k == st['K']),
                           mp.mpf(0)))
            diff = d['value'] - float(val)
            rows.append(dict(name=nm, eps=el, direct=d['value'], direct_err=d['err'], engine=mp.nstr(val, 25),
                             engine_err_naive=float(eerr), diff=diff,
                             rel_diff=diff / abs(d['value']) if d['value'] else None, trunc_scale=float(last),
                             kmax=st['K'], partial=partial, engine_source=eng[nm]['source']))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('engine', nargs='+', help='engine JSON file(s) or directories')
    ap.add_argument('--dps', type=int, default=50)
    ap.add_argument('--out', default=os.path.join(RES, 'engine_comparison.json'))
    ap.add_argument('--offset-fit', action='store_true', help='GLS test of [eps^0 l^0], [eps^0 l^1]')
    ap.add_argument('--fit-eps-max', type=float, default=0.021)
    ap.add_argument('--fit-eps-min', type=float, default=0.0)
    ap.add_argument('--chi2-max', type=float, default=2.5, help='acceptance: chi2/dof <= this (default 2.5)')
    ap.add_argument('--min-dof', type=int, default=3)
    ap.add_argument('--dbic', type=float, default=6.0, help='BIC window of competitive tail variants (default 6)')
    ap.add_argument('--only', default=None, help='comma-separated direct names to test')
    ap.add_argument('--merge', action='store_true',
                    help='merge the coefficients of a moment over all given files (smaller error wins), e.g. to '
                         'complete a partial production series with the negative powers of a validation file')
    ap.add_argument('--quiet-raw', action='store_true', help='do not print the per-cutoff table')
    a = ap.parse_args()
    mp.mp.dps = a.dps
    tab = json.load(open(os.path.join(RES, 'direct_table.json')))
    eng = load_engine(a.engine, merge=a.merge)
    if a.only:
        keep = set(a.only.split(','))
        eng = {k: v for k, v in eng.items() if k in keep}
    eng = {k: v for k, v in eng.items() if any(k in tab[el] for el in tab)}
    rows = raw_table(tab, eng)
    if not a.quiet_raw:
        print('%-10s %-7s %-24s %-24s %-11s %-9s %s' % ('moment', 'eps', 'direct', 'engine', 'diff', 'trunc', 'partial'))
        for r in rows:
            print('%-10s %-7s %-24.16g %-24s %-11.3e %-9.2e %s' % (r['name'], r['eps'], r['direct'], r['engine'][:22],
                                                                 r['diff'], r['trunc_scale'], r['partial']))
    json.dump(rows, open(a.out, 'w'), indent=1)
    print('wrote', a.out, len(rows), 'comparisons;', len(eng), 'engine moments')
    if a.offset_fit:
        out = []
        print('\nGLS offset test (eps <= %g; direct-only weights; engine errors as priors; chi2/dof <= %g; dof >= %d)'
              % (a.fit_eps_max, a.chi2_max, a.min_dof))
        print('nui = engine nuisance coefficients with priors, mis = structural coefficients the engine does not quote '
              '(free)\n' + HEADER)
        for nm in sorted(eng):
            r = offset_test(tab, nm, eng[nm], a.fit_eps_max, a.fit_eps_min, a.chi2_max, a.min_dof,
                            dbic_competitive=a.dbic)
            print(summary_line(r), flush=True)
            r['engine_source'] = eng[nm]['source']
            out.append(_f(r))
        p = a.out.replace('.json', '_offsets.json')
        json.dump(out, open(p, 'w'), indent=1, default=str)
        tally = {}
        for r in out:
            tally[r['verdict']] = tally.get(r['verdict'], 0) + 1
        print('verdicts:', tally)
        print('wrote', p)


if __name__ == '__main__':
    main()
