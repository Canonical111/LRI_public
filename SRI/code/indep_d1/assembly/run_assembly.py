#!/usr/bin/env python3
"""Assembly phase, steps 1-2 (archive-free).  Writes ../RESULTS_independent.json and out/assembly_*.json.

Step 1  the engine's production replicates (tier 1 + top-up, runs/prod_6digit/framework_input_final.json; tier 1
        alone as a cross-check) through the framework in strict mode, per-replicate assembly:
        all 25 beta inputs, D2, T2, D3, T3, D4, C3..C7 with
          sigma_cov   linear propagation with the per-job replicate covariance (+ precision floors),
          sigma_rep   standard error of the R = 6 per-replicate assemblies (+ floors),
          sigma_pool  sector-pooled projection (statistical, pooled_errors.py) (+ floors in quadrature);
        quoted error = max of the three.  The three-kink inputs are compared with the framework's semi-analytic
        values (framework/validate_low_order.py, computed here again at 40 digits).
Step 2  checks without the archive:
  (i)   closed forms the note proves: a, p, A, E, c, b, f; D2, T2, C3, C4; the periods P4, S5, R4 (two routes
        each for S5 and R4);
  (ii)  cancellation of the eps^{<0} terms of the normalized responses (production data, completed by the engine's
        own validation-run negative powers where production did not compute them);
  (iii) the note's higher-log predictions (l.719-731, 1051-1063) and every other higher-log / endpoint target of
        spec/out/validation_targets.json, plus an RG second-log check derived here (Callan-Symanzik at b0 = 1,
        delta = 0, see README) for C3, C5, C7, K4, K6, K8;
  (iv)  read from out/direct_summary.json (direct_check.py, run first).
Run time ~2 min locally.
"""
import json
import math
import os
import sys
import time

import mpmath as mp
import sympy as sp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as CM  # noqa: E402
from common import L, nstr  # noqa: E402
import pooled_errors as PE  # noqa: E402

DPS = 50
REPLACED = ['Q6_E', 'A7_v', 'A7_base', 'A5_vE']      # groups taken from the top-up run (results_final.json 'merged')
LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def f(x, d=4):
    return None if x is None else float(x) if abs(x) < 1e300 else None


# ======================================================================================================
# step 1
# ======================================================================================================
def stats_of(rr, o):
    st = rr.stats[o]
    if 'missing' in st:
        raise RuntimeError(f'{o} missing: {st["missing"]}')
    return st


def step1():
    log('=' * 100)
    log('STEP 1: framework (strict, per-replicate) on the engine production data')
    log('=' * 100)
    fw = L.Framework('D4', dps=DPS)
    t0 = time.time()
    rr = fw.from_replicates(CM.FINAL_CANON)
    rr1 = fw.from_replicates(CM.TIER1_CANON)
    log(f'  per-replicate assemblies done in {time.time() - t0:.1f} s; R = {rr.meta["n_replicates"]}, '
        f'{rr.meta["n_replicated"]} replicated scalars in {rr.meta["replicate_blocks"]} blocks, '
        f'exact inputs {rr.meta["exact_inputs"]}; warnings {rr.warnings}')
    assert rr.meta['strict'] and rr.meta['n_required'] == 116 and rr.meta['n_inputs'] == 116
    # gradients (input convention) at the final central point, for the pooled projections
    cen = rr.central
    grads = {o: {k: float(v) for k, v in cen.gradient(cen.get(o)).items()} for o in CM.OUTPUTS}
    # sector-pooled errors (statistical) for every output; final = tier-1 jobs with the replaced groups
    # taken from the top-up run
    t0 = time.time()
    jobs_final = PE.final_jobs(CM.PROD, CM.TOPUP, REPLACED)
    jobs_t1 = PE.job_sector_values(CM.PROD)
    pooled, pooled_t1 = {}, {}
    for o in CM.OUTPUTS:
        r, p, per = PE.pooled_projection(jobs_final, grads[o])
        pooled[o] = {'rep_stat': r, 'pool_stat': p, 'top_jobs': per[:4]}
        r1, p1, _ = PE.pooled_projection(jobs_t1, grads[o])
        pooled_t1[o] = {'rep_stat': r1, 'pool_stat': p1}
    log(f'  sector-pooled projections done in {time.time() - t0:.1f} s '
        f'({len(jobs_final)} jobs final, {len(jobs_t1)} tier 1)')
    # tier-1 vs final: the difference comes only from the four replaced groups (independent seeds)
    inp_f, _ = fw._parse(CM.FINAL_CANON, 'raw', None, None, None)
    inp_1, _ = fw._parse(CM.TIER1_CANON, 'raw', None, None, None)

    def repl_names(inp):
        out = set()
        for nm in inp.values:
            pref = nm.split('[')[0]
            grp = pref if '_' in pref else pref + '_base'
            if grp in REPLACED:
                out.add(nm)
        return out
    rf, r1n = repl_names(inp_f), repl_names(inp_1)
    em_f = inp_f.errmodel.restricted(keep_sig=rf, keep_blocks=rf, keep_reps=rf)
    em_1 = inp_1.errmodel.restricted(keep_sig=r1n, keep_blocks=r1n, keep_reps=r1n)
    out = {}
    for o in CM.OUTPUTS:
        st, st1 = stats_of(rr, o), stats_of(rr1, o)
        xf, x1 = rr.central.get(o), rr1.central.get(o)
        sd = mp.sqrt(em_f.variance(xf.g) + em_1.variance(x1.g))
        floor = st['sigma_extra']
        pool_tot = mp.sqrt(mp.mpf(pooled[o]['pool_stat']) ** 2 + floor ** 2)
        e = {'value': nstr(st['value'], 30), 'rep_mean': nstr(st['rep_mean'], 30),
             'sigma_cov': f(st['sigma_linear']), 'sigma_rep': f(st['sigma_rep_total']),
             'rep_se_stat': f(st['rep_se']), 'sigma_floor': f(floor),
             'sigma_pool': f(pool_tot), 'sigma_pool_stat': pooled[o]['pool_stat'],
             'sigma_rep_stat_projection': pooled[o]['rep_stat'],
             'nonlinearity': f(st['nonlinearity']),
             'top_jobs_pooled': [{'job': x['job'], 'pool': x['pool'], 'rep': x['rep']} for x in pooled[o]['top_jobs']],
             'tier1': {'value': nstr(st1['value'], 30), 'sigma_cov': f(st1['sigma_linear']),
                       'sigma_rep': f(st1['sigma_rep_total']),
                       'sigma_pool': f(mp.sqrt(mp.mpf(pooled_t1[o]['pool_stat']) ** 2 + st1['sigma_extra'] ** 2)),
                       'final_minus_tier1': f(xf.v - x1.v), 'sigma_diff_replaced_groups': f(sd),
                       'pull': f((xf.v - x1.v) / sd) if sd > 0 else None}}
        e['sigma'] = max(e['sigma_cov'], e['sigma_rep'], e['sigma_pool'])
        out[o] = e
    log('\n  %-6s %32s %10s %10s %10s %10s %9s | tier1-final pull' % ('output', 'value (central)', 'sig_cov',
                                                                       'sig_rep', 'sig_pool', 'sigma', 'nonlin'))
    for o in CM.OUTPUTS:
        e = out[o]
        log('  %-6s %32s %10.3e %10.3e %10.3e %10.3e %9.1e | %s' % (
            o, mp.nstr(mp.mpf(e['value']), 22), e['sigma_cov'], e['sigma_rep'], e['sigma_pool'], e['sigma'],
            e['nonlinearity'], 'n/a' if e['tier1']['pull'] is None else '%+.2f' % e['tier1']['pull']))
    # linear effect of the convergence re-check engine/runs/conv1 (Z4_E k=-1,0; A3_vdE, A5_vv k=0 at 4-16x N),
    # had its values replaced the production ones (the production input is NOT changed)
    conv_path = os.path.join(CM.ENG_DIR, 'runs', 'conv1', 'results.json')
    conv_effect = None
    if os.path.exists(conv_path):
        cr = json.load(open(conv_path))['results']
        pr = json.load(open(CM.FINAL_RESULTS))['results']
        dx = {}
        for grp, ser in cr.items():
            pref = L.group_to_prefix(grp)
            for kj, (v, e) in ser.items():
                if kj in pr.get(grp, {}):
                    k, j = (int(x) for x in kj.split(','))
                    dx[f'{pref}[eps^{k} l^{j}]'] = v - pr[grp][kj][0]
        conv_effect = {}
        for o in ('C5', 'C6', 'D4', 'C7'):
            d = sum(grads[o].get(nm, 0.0) * x for nm, x in dx.items())
            conv_effect[o] = {'shift': d, 'shift_over_sigma': d / out[o]['sigma']}
        log('  effect of replacing Z4_E (k=-1,0), A3_vdE, A5_vv (k=0) by the conv1 re-check values: ' +
            ', '.join(f"{o} {v['shift']:+.2e} ({v['shift_over_sigma']:+.2f} sigma)" for o, v in conv_effect.items()))
    meta = {'framework': 'framework/lri_framework.py Framework("D4", dps=50).from_replicates (strict)',
            'input_final': CM.FINAL_CANON, 'input_tier1': CM.TIER1_CANON, 'replaced_by_topup': REPLACED,
            'n_required': rr.meta['n_required'], 'n_inputs': rr.meta['n_inputs'], 'R': rr.meta['n_replicates'],
            'replicate_blocks': rr.meta['replicate_blocks'], 'exact_inputs': rr.meta['exact_inputs'],
            'warnings': rr.warnings, 'conv1_replacement_effect': conv_effect,
            'sigma_definitions': {
                'sigma_cov': 'g^T Sigma g: per-job replicate sample covariance / R, plus precision floors (framework '
                             'sigma_linear)',
                'sigma_rep': 'sd of the R=6 per-replicate assemblies / sqrt(R), plus floors (framework '
                             'sigma_rep_total)',
                'sigma_pool': 'sector-pooled projection of every job on the output gradient (statistical, '
                              'pooled_errors.py), plus floors in quadrature',
                'sigma': 'max(sigma_cov, sigma_rep, sigma_pool) -- quoted error'}}
    return out, meta, rr, cen


def three_kink(step1_out):
    log('\n  three-kink sector: engine vs the framework semi-analytic 1D boundary integrals '
        '(validate_low_order.three_kink_single_log, 40 digits)')
    import validate_low_order as V
    need = {'v': (1, 0), 'd': (0, 1), 'vv': (2, 0), 'vd': (1, 1), 'dd': (0, 2), 'vvv': (3, 0), 'vvd': (2, 1),
            'vdd': (1, 2)}
    C31 = {}
    with mp.workdps(40):
        for nm, (i, j) in need.items():
            C31[nm] = V.three_kink_single_log(i, j)[0]
        sa = {'a': C31['v'] - 4, 'p': C31['d'] + 4, 'A': C31['vv'] / 2, 'E': C31['vd'] + 4, 'V': C31['dd'] / 2 - 4,
              'alpha': C31['vvv'] / 6, 'beta': C31['vvd'] / 2, 'gamma': C31['vdd'] / 2 - 4}
    res = {}
    for k, v in sa.items():
        e = step1_out[k]
        d = mp.mpf(e['value']) - v
        res[k] = {'semi_analytic_40digit': mp.nstr(v, 32), 'engine': e['value'], 'engine_sigma': e['sigma'],
                  'engine_minus_semi_analytic': f(d), 'pull': f(d / e['sigma'])}
        log('    %-6s semi-analytic %36s  engine-sa %+.2e  sigma %.1e  pull %+.2f' % (
            k, mp.nstr(v, 30), d, e['sigma'], d / e['sigma']))
    return res


# ======================================================================================================
# step 2 (i): closed forms
# ======================================================================================================
def mellin_relations():
    """Q4[eps^0 l^0](P) and Q4_v[eps^0 l^1](P, R4) from the note's angular Laurent data (eq. lo:eq:AQ,
    lo:eq:AQv) and the radial Mellin factor 1/(q(q+k)(q+k+1)), k = 4-4v (as in framework/validate_low_order.py,
    part B).  Returns sympy expressions in P, R, zeta2."""
    q, P, R, zt = sp.symbols('q P R zeta2')
    Aq = 8 / q ** 2 - 6 / q - 6 - 4 * zt + P * q
    Apq = 32 / q ** 3 - 4 / q ** 2 + (4 + 16 * zt) / q + R
    M0 = Aq / (q ** 2 * (q + 1))
    dM = Apq / (q ** 2 * (q + 1)) + 4 * (2 * q + 1) * Aq / (q ** 3 * (q + 1) ** 2)
    s0 = sp.expand(sp.series(M0, q, 0, 0).removeO())
    s1 = sp.expand(sp.series(dM, q, 0, 0).removeO())
    # c / q^(n+1)  <->  c (-1)^n l^n / n!
    Q4_l = {n: sp.expand(s0.coeff(q, -(n + 1)) * (-1) ** n / sp.factorial(n)) for n in range(4)}
    Q4v_l = {n: sp.expand(s1.coeff(q, -(n + 1)) * (-1) ** n / sp.factorial(n)) for n in range(5)}
    return Q4_l, Q4v_l, (P, R, zt)


def check_closed_forms(step1_out, NA, targets):
    log('\n' + '=' * 100)
    log('STEP 2(i): closed forms proved in the note')
    log('=' * 100)
    rows = []
    tmap = {t['id']: t for t in targets}

    def add(name, val, sig, exact_str, source, extra=None):
        ex = CM.eval_closed(exact_str)
        d = val - ex
        row = {'quantity': name, 'value': mp.nstr(val, 25), 'closed_form': exact_str, 'closed_value': mp.nstr(ex, 25),
               'diff': f(d), 'sigma': f(sig), 'pull': f(d / sig) if sig else None, 'source': source}
        if extra:
            row.update(extra)
        rows.append(row)
        log('  %-28s %26s  diff %+.2e  sigma %.1e  pull %s' % (name, mp.nstr(val, 20), d, sig,
                                                               'n/a' if not sig else '%+.2f' % (d / sig)))
    for nm in ('a', 'p', 'A', 'E', 'c', 'b', 'f'):
        e = step1_out[nm]
        add(f'input {nm}', mp.mpf(e['value']), e['sigma'], tmap[f'input.{nm}']['exact'], tmap[f'input.{nm}']['source'])
    for nm in ('D2', 'T2', 'C3', 'C4'):
        e = step1_out[nm]
        add(f'invariant {nm}', mp.mpf(e['value']), e['sigma'], tmap[f'invariant.{nm}']['exact'],
            tmap[f'invariant.{nm}']['source'])
    # periods ------------------------------------------------------------------------------------------
    z2, z3 = mp.zeta(2), mp.zeta(3)
    L2 = mp.log(2)

    def per(fn, label, exact_id, extra=None):
        st = NA.stats(fn)
        sig = st['sigma']
        ex = dict(extra or {})
        ex['sigma_parts'] = {k: f(st[k]) for k in ('sigma_lin', 'sigma_rep', 'sigma_pool_tot') if k in st}
        add(label, st['value'], sig, tmap[exact_id]['exact'], tmap[exact_id]['source'], ex)
    # P4 = K4[l^0] - 4 z2 + 10  (lo:eq:K4)
    per(lambda a: a['K'][4][(0, 0, 0)].coef(0, 0) - 4 * z2 + 10, 'period P4 (K4[l^0])', 'period.P4')
    # S5 = 96 - 40 z2 - C5[l^1]  (lo:eq:C5)
    per(lambda a: 96 - 40 * z2 - a['C'][5][(0, 0, 0)].coef(0, 1), 'period S5 (C5[l^1])', 'period.S5')
    # S5 from b: b = -21 + 38 z2 + 60 z3 + 32 log2 - S  (lo:eq:bperiod)
    per(lambda a: -21 + 38 * z2 + 60 * z3 + 32 * L2 - CM.beta_of(a, 'b'), 'period S5 (from b)', 'period.S5')
    # R4 from f: f = 16 P + 4 R4 - 32 + 16 z2 + 32 z3 (lo:eq:fperiod), P from K4[l^0]
    per(lambda a: (CM.beta_of(a, 'f') - 16 * (a['K'][4][(0, 0, 0)].coef(0, 0) - 4 * z2 + 10) + 32 - 16 * z2
                   - 32 * z3) / 4, 'period R4 (from f, P4)', 'period.R4')
    # R4 from the raw charge derivative d_v Q4 (Mellin, lo:eq:AQv), P from raw Q4[l^0] (lo:eq:AQ)
    Q4_l, Q4v_l, (P, R, zt) = mellin_relations()
    zsub = {zt: sp.Float(mp.nstr(z2, 60), 60)}
    q0 = Q4_l[0].subs(zsub)
    a0 = mp.mpf(str(sp.N(q0.coeff(P), 60)))
    b0 = mp.mpf(str(sp.N(q0.subs(P, 0), 60)))
    q1 = sp.expand(Q4v_l[1].subs(zsub))
    aR = mp.mpf(str(sp.N(q1.coeff(R), 60)))
    aP = mp.mpf(str(sp.N(q1.coeff(P), 60)))
    c1 = mp.mpf(str(sp.N(q1.subs({P: 0, R: 0}), 60)))
    # consistency of the Mellin map with the P-independent engine logs (no free parameter)
    mel_logs = []
    for n in (1, 2, 3):
        ex = mp.mpf(str(sp.N(Q4_l[n].subs(zsub), 60)))
        st = NA.stats(CM.raw_coef(f'Q4[eps^0 l^{n}]'))
        mel_logs.append({'coef': f'Q4[eps^0 l^{n}]', 'engine': mp.nstr(st['value'], 20), 'mellin': mp.nstr(ex, 20),
                         'diff': f(st['value'] - ex), 'sigma': f(st['sigma'])})
    for n in (2, 3, 4):
        exs = Q4v_l[n].subs(zsub)
        ex = mp.mpf(str(sp.N(exs, 60)))
        st = NA.stats(CM.raw_coef(f'Q4_v[eps^0 l^{n}]'))
        mel_logs.append({'coef': f'Q4_v[eps^0 l^{n}]', 'engine': mp.nstr(st['value'], 20), 'mellin': mp.nstr(ex, 20),
                         'diff': f(st['value'] - ex), 'sigma': f(st['sigma'])})
    log('    Mellin map check on the P-, R4-independent logs: ' +
        ', '.join('%s diff %.1e' % (m['coef'], m['diff']) for m in mel_logs))

    def r4raw(a):
        Pv = (a['raw']['Q4[eps^0 l^0]'] - b0) / a0
        return (a['raw']['Q4_v[eps^0 l^1]'] - c1 - aP * Pv) / aR
    per(lambda a: (a['raw']['Q4[eps^0 l^0]'] - b0) / a0, 'period P4 (raw Q4[l^0], Mellin)', 'period.P4')
    per(r4raw, 'period R4 (raw Q4_v[l^1], Mellin)', 'period.R4',
        {'mellin_map_checks': mel_logs})
    return rows


# ======================================================================================================
# step 2 (ii): pole cancellation
# ======================================================================================================
def check_poles(NA, label):
    log('\n' + '=' * 100)
    log(f'STEP 2(ii): cancellation of eps^(<0) terms in the normalized responses [{label}]')
    log('=' * 100)
    cen = NA.central
    tested, untested = [], []
    for X, src in (('C', cen['C']), ('K', cen['K'])):
        for n, jet in sorted(src.items()):
            if (X == 'C' and n == 1) or (X == 'K' and n == 2):
                continue
            for m, s in sorted(jet.items()):
                # is this jet entry used (its eps^0 l^0 or l^1 coefficient computable)?
                used = any(not s.coef(0, k).is_missing for k in (0, 1))
                if not used:
                    continue
                i, j, e = m
                nm = f'{X}{n}' + ('_' + L.deriv_str(i, j, e) if (i or j or e) else '')
                pmin = -((n - 1) // 2) if X == 'C' else -(n // 2 - 1)
                pmin = min(pmin, -(n // 2))
                miss_here = []
                for p in range(pmin - 1, 0):
                    for k in range(0, NA.fw.kmax + 1):
                        x = s.coef(p, k)
                        if x.is_missing:
                            miss_here.append(f'[eps^{p} l^{k}]')
                            continue
                        if x.is_exact_zero:
                            continue
                        fac = math.factorial(i) * math.factorial(j)
                        st = NA.stats(lambda a, X=X, n=n, m=m, p=p, k=k: (a['C'] if X == 'C' else a['K'])[n][m].coef(p, k))
                        # double-double rounding floor: the engine leaves residues of ~1e-34 (with replicate
                        # errors of ~1e-36) in coefficients that vanish identically; |x| < 1e-25 is zero at
                        # that precision for these O(1)-O(1e4) responses
                        sig = mp.sqrt(st['sigma'] ** 2 + mp.mpf('1e-25') ** 2)
                        rel = abs(st['value']) / st['l1'] if st['l1'] > 0 else mp.mpf(0)
                        tested.append({'response': nm, 'eps': p, 'log': k, 'value': f(st['value'] * fac),
                                       'sigma': f(sig * fac), 'pull': f(st['value'] / sig) if sig > 0 else None,
                                       'sigma_parts': {kk: f(st[kk] * fac) for kk in
                                                       ('sigma_lin', 'sigma_rep', 'sigma_pool_tot') if kk in st},
                                       'l1_scale': f(st['l1'] * fac), 'rel_to_l1': f(rel)})
                if miss_here:
                    untested.append({'response': nm, 'missing_coefficients': len(miss_here)})
    for t in tested:
        t['nontrivial'] = t['l1_scale'] > 1e-12      # the cancelling terms are not themselves (near) zero
    nt = [t for t in tested if t['nontrivial']]
    pulls = [abs(t['pull']) for t in tested if t['pull'] is not None]
    rels = [t['rel_to_l1'] for t in nt]
    worst = sorted(tested, key=lambda t: -(abs(t['pull']) if t['pull'] is not None else 0))[:8]
    log(f'  tested {len(tested)} coefficients [eps^p l^k], p<0, that depend on inputs, in '
        f'{len({t["response"] for t in tested})} normalized jet entries; {len(nt)} of them non-trivial '
        f'(L1 size of the cancelling terms > 1e-12)')
    if pulls:
        log(f'  max |pull| {max(pulls):.2f}, rms pull {math.sqrt(sum(x * x for x in pulls) / len(pulls)):.2f}, '
            f'max |value|/L1 {max(rels):.1e}')
    for t in worst:
        log('    worst: %-10s eps^%d l^%d  value %+.2e  sigma %.1e  pull %s  |value|/L1 %.1e' % (
            t['response'], t['eps'], t['log'], t['value'], t['sigma'],
            'n/a' if t['pull'] is None else '%+.2f' % t['pull'], t['rel_to_l1']))
    log(f'  jet entries with at least one negative-power coefficient not computable from these data: '
        f'{len(untested)}: ' + ', '.join(u['response'] for u in untested))
    pn = [abs(t['pull']) for t in nt if t['pull'] is not None]
    log(f'  non-trivial ones: max |pull| {max(pn) if pn else 0:.2f}, '
        f'rms {math.sqrt(sum(x * x for x in pn) / len(pn)) if pn else 0:.2f}')
    return {'tested': tested, 'untested_entries': untested, 'n_tested': len(tested), 'n_nontrivial': len(nt),
            'max_abs_pull_nontrivial': max(pn) if pn else None,
            'rms_pull_nontrivial': math.sqrt(sum(x * x for x in pn) / len(pn)) if pn else None,
            'rounding_floor_abs': 1e-25,
            'max_abs_pull': max(pulls) if pulls else None,
            'rms_pull': math.sqrt(sum(x * x for x in pulls) / len(pulls)) if pulls else None,
            'max_rel_to_l1': max(rels) if rels else None,
            'responses_tested': sorted({t['response'] for t in tested})}


# ======================================================================================================
# step 2 (iii): higher logs
# ======================================================================================================
def norm_getter(series):
    """'C7[v1d0]' -> (X, n, (i, j, 0)), derivative factor"""
    import re
    m = re.match(r'^([CK])(\d+)\[v(\d)d(\d)\]$', series)
    X, n, i, j = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
    return X, n, (i, j, 0), math.factorial(i) * math.factorial(j)


RAW_SERIES = {'EQ4_base': 'Q4_E', 'EA3_v': 'A3_vE', 'EA3_base': 'A3_E'}
NOTE_HIGHER_LOG_IDS = {'C7.l6', 'C7.l5', 'C7.l4', 'C5d.l6', 'C5d.l5', 'C5d.l4', 'C7v.l8', 'C7v.l7', 'C7v.l6',
                       'C7v.l5', 'K8.l7', 'K8.l6', 'K8.l5'}


def check_higher_logs(NA, targets):
    log('\n' + '=' * 100)
    log('STEP 2(iii): higher logarithms and endpoint constants (spec/out/validation_targets.json)')
    log('=' * 100)
    rows = []
    for t in targets:
        if t['kind'] == 'normalized':
            X, n, m, fac = norm_getter(t['series'])
            fn = (lambda a, X=X, n=n, m=m, k=t['log_power']: (a['C'] if X == 'C' else a['K'])[n][m].coef(0, k))
        elif t['kind'] == 'raw' and (t['series'] in RAW_SERIES or t['series'] == 'A3_dd/2'):
            if t['series'] == 'A3_dd/2':
                name, fac = f"A3_dd[eps^{t['eps_power']} l^{t['log_power']}]", 1    # internal = Taylor = dd/2
            else:
                name, fac = f"{RAW_SERIES[t['series']]}[eps^{t['eps_power']} l^{t['log_power']}]", 1
            fn = CM.raw_coef(name)
        else:
            continue          # exact two-kink entries (framework internal), inputs, invariants, periods: elsewhere
        st = NA.stats(fn)
        if 'missing' in st:
            log(f"  {t['id']:14s} MISSING {st['missing'][:2]}")
            rows.append({'id': t['id'], 'missing': st['missing']})
            continue
        ex = CM.eval_closed(t['exact'])
        val = st['value'] * fac
        sig = st['sigma'] * fac
        d = val - ex
        row = {'id': t['id'], 'quantity': t['quantity'], 'series': t['series'], 'eps': t['eps_power'],
               'log': t['log_power'], 'value': mp.nstr(val, 20), 'closed_form': t['exact'],
               'closed_value': mp.nstr(ex, 20), 'diff': f(d), 'sigma': f(sig),
               'pull': f(d / sig) if sig > 0 else None,
               'sigma_parts': {k: f(st[k] * fac) for k in ('sigma_lin', 'sigma_rep', 'sigma_pool_tot') if k in st},
               'provenance': t['provenance'], 'source': t['source'],
               'note_l719_731_or_l1051_1063': t['id'] in NOTE_HIGHER_LOG_IDS}
        rows.append(row)
        log('  %-14s %-34s %24s  diff %+.2e  sigma %.1e  pull %s' % (
            t['id'], t['exact'][:34], mp.nstr(val, 16), d, sig, 'n/a' if sig == 0 else '%+.2f' % (d / sig)))
    return rows


def rg_second_log(NA):
    """C_{n,2}, K_{n,2} at (v, delta) = (1, 0) predicted from the l^0, l^1 data by the Callan-Symanzik equation
    of the auxiliary couplings at b0 = 1:  F_2 = (1/2) beta . grad F_1  (derivation in README.md).
       C_{n,2} = 1/2 [ sum_m m b_{n-m+1} C_{m,1} + 2 sum_m h_{n-m} (-2m C_{m,0} - 2 d_v C_{m,1} + E C_{m,1}) ]
       K_{n,2} = 1/2 [ sum_m m b_{n-m+1} K_{m,1} + sum_m h_{n-m} (-2K_{m,1} + 2(-2m K_{m,0} - 2 d_v K_{m,1} + E K_{m,1})) ]
    Valid only at (v, delta) = (1, 0): away from it the matching (eq:fugmatch) adds explicit logs."""
    log('\n  RG second-log check (Callan-Symanzik, b0 = 1, delta = 0), engine [l^2] vs prediction from l^0, l^1:')
    rows = []

    def pred(a, X, n):
        c = a['c'] if X == 'C' else a['kk']
        bh = a['bh']
        b = {k: bh[f'b{k}'][(0, 0)] for k in (3, 5, 7)}
        h = {k: bh[f'h{k}'][(0, 0)] for k in (2, 4, 6, 8)}
        acc = L.Val(mp.mpf(0))
        ms = range(1, n, 2) if X == 'C' else range(2, n, 2)
        for m in ms:
            k = n - m + 1
            if k in b:
                acc = acc + m * b[k] * c[m][1][(0, 0, 0)]
            hk = n - m
            if hk in h:
                inner = (-2 * m) * c[m][0][(0, 0, 0)] - 2 * c[m][1][(1, 0, 0)] + c[m][1][(0, 0, 1)]
                if X == 'C':
                    acc = acc + 2 * h[hk] * inner
                else:
                    acc = acc + h[hk] * (-2 * c[m][1][(0, 0, 0)] + 2 * inner)
        return acc * mp.mpf('0.5')
    for X, n in (('C', 3), ('C', 5), ('C', 7), ('K', 4), ('K', 6), ('K', 8)):
        eng = NA.stats(lambda a, X=X, n=n: (a['c'] if X == 'C' else a['kk'])[n][2][(0, 0, 0)])
        prd = NA.stats(lambda a, X=X, n=n: pred(a, X, n))
        dif = NA.stats(lambda a, X=X, n=n: (a['c'] if X == 'C' else a['kk'])[n][2][(0, 0, 0)] - pred(a, X, n))
        sig = dif['sigma']
        rows.append({'response': f'{X}{n}[l^2] at v=1, delta=0', 'engine': mp.nstr(eng['value'], 20),
                     'rg_prediction': mp.nstr(prd['value'], 20), 'diff': f(dif['value']), 'sigma_diff': f(sig),
                     'pull': f(dif['value'] / sig) if sig > 0 else None, 'rel_diff': f(dif['value'] / eng['value']),
                     'sigma_parts': {k: f(dif[k]) for k in ('sigma_lin', 'sigma_rep', 'sigma_pool_tot') if k in dif}})
        log('    %-4s engine %24s  RG %24s  diff %+.2e  sigma %.1e  pull %s' % (
            f'{X}{n}', mp.nstr(eng['value'], 18), mp.nstr(prd['value'], 18), dif['value'], sig,
            'n/a' if sig == 0 else '%+.2f' % (dif['value'] / sig)))
    return rows


# ======================================================================================================
def main():
    os.makedirs(CM.OUT, exist_ok=True)
    t_all = time.time()
    s1, meta, rr, cen = step1()
    tk = three_kink(s1)
    targets = CM.spec_targets()
    # extended data (all engine coefficients, all logs) for the normalized-response checks
    KMAX = 12
    jobs_prod = PE.final_jobs(CM.PROD, CM.TOPUP, REPLACED, all_coeffs=True)
    dat_p, info_p = CM.extended_input(KMAX)
    t0 = time.time()
    NA = CM.NormAssembler(dat_p, KMAX, jobs=jobs_prod)
    log(f'\n  extended assembly (production only, {info_p["n_scalars"]} scalars incl. {len(info_p["log_zeros"])} '
        f'structural log zeros, kmax {KMAX}): {time.time() - t0:.1f} s, R = {NA.R}')
    # consistency of the extended assembly with step 1 (same needed inputs)
    for nm in ('b', 'f', 'k', 'K'):
        st = NA.stats(lambda a, nm=nm: CM.beta_of(a, nm))
        d = st['value'] - mp.mpf(s1[nm]['value'])
        assert abs(d) < mp.mpf(10) ** -20 * (1 + abs(st['value'])), (nm, d)
    cf = check_closed_forms(s1, NA, targets)
    poles_p = check_poles(NA, 'production data only')
    hl = check_higher_logs(NA, targets)
    rg = rg_second_log(NA)
    have_poles = os.path.exists(CM.POLES_RESULTS)
    dat_v, info_v = CM.extended_input(KMAX, with_validation=True, with_poles=have_poles)
    jobs_v = dict(jobs_prod)
    if have_poles:
        jobs_v.update(PE.job_sector_values(CM.POLES, all_coeffs=True, keep=set(info_v['poles1_coefficients']),
                                           tag='poles1:'))
    t0 = time.time()
    NAv = CM.NormAssembler(dat_v, KMAX, jobs=jobs_v)
    log(f'\n  extended assembly (production + {len(info_v["poles1_coefficients"])} coefficients of the poles1 run + '
        f'{len(info_v["validation_coefficients"])} validation-run coefficients): {time.time() - t0:.1f} s')
    poles_v = check_poles(NAv, 'production + poles1 run' + (' + validation runs' if info_v['validation_coefficients']
                                                             else ''))
    # (iv) direct comparison summary (direct_check.py)
    dpath = os.path.join(CM.OUT, 'direct_summary.json')
    direct = json.load(open(dpath)) if os.path.exists(dpath) else None
    if direct:
        log('\n' + '=' * 100)
        log('STEP 2(iv): direct finite-cutoff GLS comparison (out/direct_summary.json): '
            f"prod {direct['prod']['tally']}; prod+val {direct['prod_plus_val']['tally']}")
    res = {
        'title': 'Independent C6/C7 re-derivation: assembly of the engine production data (archive-free part)',
        'date': '2026-10-03',
        'archive_free': True,
        'note': 'Every number here comes from the project\'s own engine, framework, direct and spec components. '
                'No archive number was read or used. Closed forms quoted are the note\'s proved results '
                '(a,p,A,E,c,b,f, D2, T2, C3, C4, P4, R4, S5, higher logs); the claims under test (C5/D3, C6/T3, '
                'D4, C7) are NOT compared here (RESULTS_archive_comparison.json).',
        'step1': {'meta': meta, 'outputs': s1, 'three_kink_semi_analytic': tk},
        'step2': {'i_closed_forms': cf,
                  'ii_pole_cancellation': {'production_only': poles_p, 'complete': poles_v,
                                           'poles1_run_used': have_poles,
                                           'n_poles1_coefficients': len(info_v['poles1_coefficients']),
                                           'validation_coefficients_used': info_v['validation_coefficients']},
                  'iii_higher_logs': {'note_and_spec_targets': hl, 'rg_second_log': rg},
                  'iv_direct': direct},
        'extended_input_info': {'kmax': KMAX, 'structural_log_zeros': len(info_p['log_zeros']),
                                'n_scalars_production': info_p['n_scalars'], 'n_scalars_complete':
                                info_v['n_scalars']},
    }
    CM.write_json(os.path.join(CM.ROOT, 'RESULTS_independent.json'), res)
    with open(os.path.join(CM.OUT, 'run_assembly.log'), 'w') as fh:
        fh.write('\n'.join(LOG) + '\n')
    log(f'\nwrote {os.path.join(CM.ROOT, "RESULTS_independent.json")}  ({time.time() - t_all:.0f} s)')


if __name__ == '__main__':
    main()
