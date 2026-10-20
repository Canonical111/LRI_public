#!/usr/bin/env python3
"""TIER-A VERSION (kept for the record; renamed 2026-10-07 from run_assembly_C8.py, which is now the tier A+B+C assembly).
C8 assembly (phase 4, 2026-10-04), steps 1-2: archive-free.  Writes ../RESULTS_C8_independent_tierA.json (+ .sha256).

C8 = 8 T4 = B_old + 4W + 2S + 3/4 U + 1/4 J9 + 3/32 L3 - 1/4 M21 + 1/2 M12 - 1/16 N2 + 1/8 Ndelta + 1/32 Kv
(note eq:C8assembly; the framework derives it, framework/derive_C8.py).

Step 1  framework (strict for every quantity reported, per-replicate assembly at order C8, dps 50) on
          engine/runs/prod_6digit/framework_input_final.json   (the 116 order-D4 scalars, phase 2)
        + engine/runs/c8tierA/framework_input_final.json       (tier A + the A3_ddE top-up: 26 scalars)
        merged as independent runs (blocks renamed; both R = 6).  Outputs: the seven tier-A inputs W, S, L3, M21,
        M12, N2, Ndelta; B_old; B_done = B_old + the six inherited terms; C8_partial = B_old + the seven tier-A
        terms (U, J9, Kv are MISSING: tiers B and C were not run).  Each with the three error estimators of
        phase 2 (sigma_cov, sigma_rep, sigma_pool; quoted = max).  Strictness: every raw scalar each reported
        quantity needs is supplied (Framework.check_inputs on exactly those outputs); U, J9, Kv, C8 are reported
        MISSING with the raw scalars they lack, never zero.
        Also: W three ways (engine A3_ddd; framework semi-analytic 1D boundary integral; spec three-kink code),
        tier A alone vs tier A + top-up, tier A vs the earlier independent pilot runs at the INPUT level (same
        production data, so only the 26 tier-A scalars differ), the note's raw-structure coefficients of the
        framework gradients, error budgets by input and by job.
Step 2  archive-free checks of the C8 data, read from tools run first (all local, archive-free):
          out/C8/validate_C8_final.{json,txt}  engine/tests/validate_C8.py with tier A first (raw targets incl. the
                                               leading log of d_delta A7, pole cancellation of 74 jets, below-bound
                                               zeros, C3/K4 higher logs incl. the closed forms in L3/M21/M12, RG logs)
          out/C8/direct_C8_final*              engine/tests/direct_C8.py with tier A first (direct finite-cutoff
                                               GLS comparison of the new moments)
          engine/runs/c8tierA/tier_vs_pilot.json (raw-level tier vs pilot, engine tool)
No archive file is read.  Run time a few minutes (local).
"""
import hashlib
import json
import math
import os
import re
import sys
import time

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as CM  # noqa: E402
from common import L  # noqa: E402
import pooled_errors as PE  # noqa: E402

DPS = 50
OUT8 = os.path.join(CM.OUT, 'C8')
REPLACED = ['Q6_E', 'A7_v', 'A7_base', 'A5_vE']          # phase-2 top-up groups (production)
C8A = os.path.join(CM.ENG_DIR, 'runs', 'c8tierA')
C8A_TOP = os.path.join(CM.ENG_DIR, 'runs', 'c8tierA_topup1')
C8A_FINAL = os.path.join(C8A, 'framework_input_final.json')  # tier A + A3_ddE top-up
C8A_ALONE = os.path.join(C8A, 'framework_input.json')         # tier A as collected (no top-up)
TOPUP_A = ['A3_ddE']
PILOT_RUNS = [os.path.join(CM.ENG_DIR, 'runs', x) for x in ('c8val', 'c8conv', 'c8kplus1', 'poles1', 'kplus1')]
NEW_A = ['W', 'S', 'L3', 'M21', 'M12', 'N2', 'Ndelta']
NEW_BC = ['U', 'J9', 'Kv']
PARTS = ['B_old8', 'B_done8', 'C8_partial']
RESULTS = os.path.join(CM.ROOT, 'RESULTS_C8_independent_tierA.json')
LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def fl(x):
    return None if x is None else float(x)


def sha256(path):
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def frac(c):
    return mp.mpf(c.numerator) / c.denominator


# ======================================================================================================
# step 1
# ======================================================================================================
def tier_jobs():
    """per-sector replicate data of every job of the final input: production (tier 1 + its top-up groups),
    tier A (A3_ddE from the tier-A top-up run)"""
    jobs = dict(PE.final_jobs(CM.PROD, CM.TOPUP, REPLACED))
    ta = PE.job_sector_values(C8A, tag='c8tierA:')
    jobs.update({k: v for k, v in ta.items() if k[1] not in TOPUP_A})
    jobs.update(PE.job_sector_values(C8A_TOP, groups=set(TOPUP_A), tag='c8tierA_topup1:'))
    return jobs


def step1():  # noqa: C901
    log('=' * 110)
    log('STEP 1: framework at order C8 (strict on every reported quantity, per-replicate) on production + tier A')
    log('=' * 110)
    # input integrity: the engine recorded the SHA-256 of its deliverables before any comparison
    sums = {}
    for line in open(os.path.join(C8A, 'SHA256SUMS_results.txt')):
        h, p = line.split()
        sums[p] = h
    for p, h in sums.items():
        full = os.path.join(CM.ENG_DIR, p)
        assert sha256(full) == h, f'{p}: SHA-256 differs from the engine record'
    log(f'  engine SHA256SUMS_results.txt: all {len(sums)} files verified')
    prod = L.load_inputs(CM.FINAL_CANON)
    ta = L.load_inputs(C8A_FINAL)
    names_A = sorted(L.canonical_raw_name(k) for k in ta['scalars'])
    merged = L.merge_inputs([prod, ta], independent=True)
    fw = L.Framework('C8', dps=DPS)
    strict_outputs = NEW_A + ['B_old8', 'B_done8'] + CM.BETA_D4 + CM.CS
    t0 = time.time()
    rr = fw.from_replicates(merged, strict=True, outputs=strict_outputs)
    log(f'  per-replicate assembly at order C8: {time.time() - t0:.1f} s; R = {rr.meta["n_replicates"]}, '
        f'{rr.meta["n_inputs"]} inputs ({rr.meta["n_replicated"]} replicated in {rr.meta["replicate_blocks"]} blocks), '
        f'exact {rr.meta["exact_inputs"]}; strict outputs {len(strict_outputs)}; warnings {rr.warnings}')
    assert rr.meta['strict'] and rr.meta['n_inputs'] == 142 and rr.meta['n_replicates'] == 6
    # strictness of the C8_partial: its value is B_old + the seven tier-A terms, each of which passed the strict check
    need = fw.required_inputs()
    for o in NEW_A + ['B_old8', 'B_done8']:
        miss = set(need[o]) - {L.canonical_raw_name(x) for x in merged['scalars']}
        assert not miss, (o, miss)
    cen = rr.central
    inp, _ = fw._parse(merged, 'raw', None, None, None)
    t0 = time.time()
    jobs = tier_jobs()
    names_jobs = {nm for d in jobs.values() for sec in d['sectors'].values() for nm in sec}
    rep_names = set(inp.reps)
    assert rep_names <= names_jobs, sorted(rep_names - names_jobs)[:5]
    log(f'  sector-pooled data: {len(jobs)} jobs ({sum(1 for k in jobs if k[0].startswith("c8tierA"))} tier A), '
        f'every replicated scalar covered; {time.time() - t0:.1f} s')
    outs = NEW_A + PARTS
    res = {}
    grads = {}
    for o in outs + NEW_BC + ['C8_asm', 'C8']:
        st = rr.stats.get(o)
        if st is None or 'missing' in st:
            x = cen.get(o) if o in cen.outputs() else None
            miss = sorted(x.miss) if (x is not None and x.is_missing) else (st or {}).get('missing')
            res[o] = {'status': 'MISSING', 'missing_raw_scalars': [m for m in (miss or []) if '[' in m],
                      'missing_tags': [m for m in (miss or []) if '[' not in m]}
            continue
        x = cen.get(o)
        g = PE.input_gradient(x, inp)
        grads[o] = g
        r_stat, p_stat, per_job = PE.pooled_projection(jobs, g)
        floor = st['sigma_extra']
        s_pool = mp.sqrt(mp.mpf(p_stat) ** 2 + floor ** 2)
        s_cov, s_rep = st['sigma_linear'], st['sigma_rep_total']
        quoted = max(s_cov, s_rep, s_pool)
        # the part carried by the 26 tier-A scalars alone (full replicate covariance; and pooled over tier-A jobs)
        sA = mp.sqrt(inp.errmodel.restricted(keep_sig=set(names_A), keep_blocks=set(names_A),
                                             keep_reps=set(names_A)).variance(x.g))
        _, pA, _ = PE.pooled_projection({k: v for k, v in jobs.items() if k[0].startswith('c8tierA')}, g)
        res[o] = {'value': mp.nstr(st['value'], 30), 'rep_mean': mp.nstr(st['rep_mean'], 30),
                  'sigma_tierA_part_cov': fl(sA), 'sigma_tierA_part_pool_stat': pA,
                  'sigma_cov': fl(s_cov), 'sigma_rep': fl(s_rep), 'rep_se_stat': fl(st['rep_se']),
                  'sigma_pool': fl(s_pool), 'sigma_pool_stat': p_stat, 'sigma_rep_stat_projection': r_stat,
                  'sigma_floor': fl(floor), 'sigma': fl(quoted), 'nonlinearity': fl(st['nonlinearity']),
                  'rel_sigma': fl(quoted / abs(st['value'])) if st['value'] != 0 else None,
                  'per_replicate': [mp.nstr(v, 25) for v in rr.per_rep[o]],
                  'top_jobs_pooled': [{'job': j['job'], 'pool': j['pool'], 'rep': j['rep'], 'nsec': j['nsec']}
                                      for j in per_job[:6]]}
    log('\n  %-10s %34s %10s %10s %10s %10s %9s | %10s %10s' % ('output', 'value (central)', 'sig_cov', 'sig_rep',
                                                               'sig_pool', 'sigma', 'rel', 'tierA cov', 'tierA pool'))
    for o in outs:
        e = res[o]
        log('  %-10s %34s %10.3e %10.3e %10.3e %10.3e %9.1e | %10.3e %10.3e' % (
            o, mp.nstr(mp.mpf(e['value']), 24), e['sigma_cov'], e['sigma_rep'], e['sigma_pool'], e['sigma'],
            e['rel_sigma'], e['sigma_tierA_part_cov'], e['sigma_tierA_part_pool_stat']))
    for o in NEW_BC + ['C8_asm', 'C8']:
        log(f'  {o:10s} MISSING ({len(res[o]["missing_raw_scalars"])} raw scalars absent, e.g. '
            f'{res[o]["missing_raw_scalars"][:3]}{res[o]["missing_tags"][:2]})')
    # ---- B_old: same as phase 3 (framework/out/C8_production.json, order D4) and C3..C7 unchanged from phase 2
    p3 = json.load(open(os.path.join(CM.FW_DIR, 'out', 'C8_production.json')))
    d_bold = mp.mpf(res['B_old8']['value']) - mp.mpf(p3['B_old']['value'])
    assert abs(d_bold) < mp.mpf(10) ** -20, d_bold
    ind = json.load(open(os.path.join(CM.ROOT, 'RESULTS_independent.json')))['step1']['outputs']
    d_old = {o: fl(cen.get(o).v - mp.mpf(ind[o]['value'])) for o in CM.CS}
    assert all(abs(v) < 1e-20 * (1 + abs(float(ind[o]['value']))) for o, v in d_old.items()), d_old
    log(f'  B_old equals the phase-3 value (order D4) to {mp.nstr(d_bold, 2)}; C3..C7 equal phase 2 '
        f'(max |diff| {max(abs(v) for v in d_old.values()):.1e})')
    # ---- composition of C8_partial: the terms of eq:C8assembly
    terms = {}
    for nm in list(L.C8_LINEAR):
        c = L.C8_LINEAR[nm]
        if res.get(nm, {}).get('status') == 'MISSING' or nm in NEW_BC:
            terms[nm] = {'coefficient': str(c), 'status': 'MISSING (tier ' + ('B' if nm in ('U', 'Kv') else 'C') + ')'}
            continue
        v = mp.mpf(res[nm]['value'])
        terms[nm] = {'coefficient': str(c), 'input': res[nm]['value'], 'contribution': mp.nstr(v * frac(c), 25),
                     'sigma_contribution': abs(float(frac(c))) * res[nm]['sigma']}
    s = mp.mpf(res['B_old8']['value']) + sum(mp.mpf(t['contribution']) for nm, t in terms.items() if 'contribution' in t)
    assert abs(s - mp.mpf(res["C8_partial"]["value"])) < mp.mpf(10) ** -18
    s2 = mp.mpf(res['B_old8']['value']) + sum(mp.mpf(terms[nm]['contribution']) for nm in L.C8_INHERITED)
    assert abs(s2 - mp.mpf(res["B_done8"]["value"])) < mp.mpf(10) ** -18
    log('  C8_partial = B_old + ' + ' + '.join(f'({terms[nm]["coefficient"]}) {nm}' for nm in NEW_A) +
        '   [U, J9, Kv absent]')
    for nm in NEW_A:
        t = terms[nm]
        log(f'    {nm:7s} x {t["coefficient"]:>5s} = {mp.nstr(mp.mpf(t["contribution"]), 20):>26s}  '
            f'+- {t["sigma_contribution"]:.2e}')
    # ---- error budget of B_done, C8_partial by group of raw scalars (linear, own error model)
    budget = {}
    for o in ('B_done8', 'C8_partial'):
        g = cen.get(o).g
        by = {}
        for nm in set(g):
            pref = nm.split('[')[0]
            src = 'tierA' if nm in names_A else 'production'
            sub = inp.errmodel.restricted(keep_sig={nm}, keep_blocks={nm}, keep_reps={nm})
            by.setdefault((src, pref), mp.mpf(0))
            by[(src, pref)] += sub.variance({nm: g[nm]})
        tot_A = math.sqrt(sum(float(v) for (s_, _), v in by.items() if s_ == 'tierA'))
        tot_P = math.sqrt(sum(float(v) for (s_, _), v in by.items() if s_ == 'production'))
        top = sorted(by.items(), key=lambda kv: -kv[1])[:8]
        budget[o] = {'sigma_from_tierA_scalars_diag': tot_A, 'sigma_from_production_scalars_diag': tot_P,
                     'largest_groups_diag': [{'source': s_, 'atom': p, 'sigma': math.sqrt(float(v))} for (s_, p), v in top],
                     'note': 'diagonal per-scalar decomposition (within-job correlations dropped); for orientation'}
        log(f'  {o}: sigma from the tier-A scalars {tot_A:.2e}, from the production scalars {tot_P:.2e} (diagonal); '
            'largest: ' + ', '.join(f'{p} ({s_}) {math.sqrt(float(v)):.1e}' for (s_, p), v in top[:5]))
    meta = {'framework': 'framework/lri_framework.py Framework("C8", dps=50).from_replicates(strict=True, '
                         'outputs=W,S,L3,M21,M12,N2,Ndelta,B_old8,B_done8 + the 25 old inputs + C3..C7)',
            'inputs': {'production': {'path': os.path.relpath(CM.FINAL_CANON, CM.ROOT), 'sha256': sha256(CM.FINAL_CANON)},
                       'tierA_final': {'path': os.path.relpath(C8A_FINAL, CM.ROOT), 'sha256': sha256(C8A_FINAL),
                                       'note': 'tier A (engine runs/c8tierA) with the A3_ddE group from the top-up run '
                                               'runs/c8tierA_topup1 (engine merge_runs.py)'}},
            'n_inputs': rr.meta['n_inputs'], 'R': rr.meta['n_replicates'],
            'replicate_blocks': rr.meta['replicate_blocks'], 'exact_inputs': rr.meta['exact_inputs'],
            'tierA_scalars': names_A, 'warnings': rr.warnings,
            'pooled_jobs': len(jobs),
            'B_old_minus_phase3': fl(d_bold), 'C3_C7_minus_phase2': d_old,
            'sigma_definitions': {
                'sigma_cov': 'linear propagation with the per-job replicate sample covariance / R, plus precision '
                             'floors (framework sigma_linear)',
                'sigma_rep': 'sd of the R=6 per-replicate assemblies / sqrt(R), plus floors (framework sigma_rep_total)',
                'sigma_pool': 'sector-pooled projection of every job on the output gradient (pooled_errors.py), plus '
                              'floors in quadrature',
                'sigma': 'max(sigma_cov, sigma_rep, sigma_pool): quoted error'}}
    return res, terms, budget, meta, fw, merged, inp, cen, names_A, prod


def w_three_ways(res):
    log('\n  W three ways (engine A3_ddd; framework semi-analytic 1D boundary integral; spec three-kink code)')
    sys.path.insert(0, CM.FW_DIR)
    import c8_production as C8P
    W50 = C8P.semi_analytic_W(50)
    W40 = C8P.semi_analytic_W(40)
    vt = json.load(open(os.path.join(CM.SPEC_DIR, 'out', 'C8', 'validation_targets_C8.json')))
    Wsp = next(t for t in vt['independent_values'] if t['id'] == 'input.W')
    We, sW = mp.mpf(res['W']['value']), res['W']['sigma']
    out = {'engine': res['W']['value'], 'engine_sigma': sW,
           'framework_semi_analytic_50digit': mp.nstr(W50, 40), 'framework_40_vs_50_digits': fl(W50 - W40),
           'spec_three_kink': Wsp['value'], 'spec_abs_accuracy': Wsp['abs_accuracy'],
           'engine_minus_semi_analytic': fl(We - W50), 'pull_engine_vs_semi_analytic': fl((We - W50) / sW),
           'spec_minus_semi_analytic': fl(mp.mpf(Wsp['value']) - W50)}
    log(f'    engine {mp.nstr(We, 22)} +- {sW:.1e};  semi-analytic {mp.nstr(W50, 34)};  spec {Wsp["value"]}')
    log(f'    engine - semi-analytic {out["engine_minus_semi_analytic"]:+.2e} (pull {out["pull_engine_vs_semi_analytic"]:+.2f}); '
        f'spec - semi-analytic {out["spec_minus_semi_analytic"]:+.1e}')
    # B_done / C8_partial with the semi-analytic W in place of the engine W (variant)
    dW = 4 * (W50 - We)
    out['B_done_with_semi_analytic_W'] = mp.nstr(mp.mpf(res['B_done8']['value']) + dW, 25)
    out['C8_partial_with_semi_analytic_W'] = mp.nstr(mp.mpf(res['C8_partial']['value']) + dW, 25)
    return out


def note_structure(cen):
    """the note's raw structure of the new inputs, from our framework gradients (exact rational coefficients)"""
    checks = [('Ndelta', 'Q6_vd[eps^0 l^1]', -4, 'eq:NdP6 l.1328: Ndelta = -4 P6 + ...'),
              ('Ndelta', 'Q4_vvd[eps^0 l^0]', 16, 'l.1319-1321 (lambda4)_vd'),
              ('Ndelta', 'Q4_vdE[eps^0 l^0]', -8, 'l.1319-1321 (lambda4)_vd'),
              ('N2', 'Q6_vv[eps^0 l^1]', None, ''), ('L3', 'Q4_vvv[eps^0 l^1]', None, ''),
              ('M21', 'Q4_vvd[eps^0 l^1]', None, ''), ('M12', 'Q4_vdd[eps^0 l^1]', None, ''),
              ('S', 'A5_dd[eps^0 l^1]', None, ''), ('W', 'A3_ddd[eps^0 l^1]', None, '')]
    rows = []
    for o, nm, exp, note in checks:
        g = cen.gradient(o)
        v = g.get(L.canonical_raw_name(nm), mp.mpf(0))
        r = {'input': o, 'raw': nm, 'd_input_d_raw': mp.nstr(v, 20)}
        if exp is not None:
            r.update(expected=exp, agree=bool(abs(v - exp) < mp.mpf(10) ** -30), note=note)
        rows.append(r)
    log('  raw structure (d input / d raw, derivative convention): ' +
        ', '.join(f'd{r["input"]}/d{r["raw"]} = {mp.nstr(mp.mpf(r["d_input_d_raw"]), 8)}'
                  + (f' (note {r["expected"]}: {"ok" if r["agree"] else "DIFFERS"})' if 'expected' in r else '')
                  for r in rows))
    return rows


def alt_assembly(fw, items, outs):
    """central values (and gradients/error model) of an alternative input, linear errors only"""
    merged = L.merge_inputs(items, independent=True)
    r = fw.from_raw(merged, strict=False)
    inp, _ = fw._parse(merged, 'raw', None, None, None)
    return {o: r.get(o) for o in outs}, inp


def restricted_var(inp, names, val):
    em = inp.errmodel.restricted(keep_sig=names, keep_blocks=names, keep_reps=names)
    return em.variance(val.g)


def tier_checks(fw, cen, inp, prod, names_A, res):
    outs = NEW_A + ['B_done8', 'C8_partial']
    out = {}
    # (a) tier A alone (no A3_ddE top-up) vs final: the difference is A3_ddE[eps^0 l^0] only (independent seeds)
    alone, inpa = alt_assembly(fw, [prod, L.load_inputs(C8A_ALONE)], outs)
    nmE = {L.canonical_raw_name('A3_ddE[eps^0 l^0]')}
    rows = {}
    for o in outs:
        xf, xa = cen.get(o), alone[o]
        d = xf.v - xa.v
        sd = mp.sqrt(restricted_var(inp, nmE, xf) + restricted_var(inpa, nmE, xa))
        rows[o] = {'final_minus_tierA_alone': fl(d), 'sigma_diff': fl(sd), 'pull': fl(d / sd) if sd > 0 else None}
    out['tierA_alone_vs_final'] = {'what': 'final (A3_ddE from the 2N top-up, fresh seeds) minus tier A as collected; '
                                           'the difference comes only from A3_ddE[eps^0 l^0]', 'rows': rows}
    log('\n  tier A alone vs final (A3_ddE top-up): ' + ', '.join(
        f'{o} {r["final_minus_tierA_alone"]:+.2e} (pull {r["pull"]:+.2f})' for o, r in rows.items()
        if r['pull'] is not None and abs(r['final_minus_tierA_alone']) > 0))
    # (b) tier A vs the earlier independent pilot runs, INPUT level: same production data, the 26 tier-A scalars
    #     replaced by their pilot values (all-sector entries, smallest replicate error; c8val, c8conv, c8kplus1,
    #     poles1, kplus1); the difference only carries the errors of the 26 scalars of both runs
    sys.path.insert(0, os.path.join(CM.ENG_DIR, 'tests'))
    from preview_C8 import pilot_scalars
    best = pilot_scalars(PILOT_RUNS, set(names_A))
    missing = sorted(set(names_A) - set(best))
    pil = L.load_inputs({'format': 'lri-framework-raw/1', 'convention': 'derivative', 'sources': ['c8pilot'],
                         'scalars': {nm: ent for nm, (_, ent, _) in best.items()}})
    rows = {}
    if not missing:
        pv, inpp = alt_assembly(fw, [prod, pil], outs)
        nA = set(names_A)
        for o in outs:
            xf, xp = cen.get(o), pv[o]
            d = xf.v - xp.v
            sA, sP = mp.sqrt(restricted_var(inp, nA, xf)), mp.sqrt(restricted_var(inpp, nA, xp))
            sd = mp.sqrt(sA ** 2 + sP ** 2)
            rows[o] = {'tierA': mp.nstr(xf.v, 22), 'pilot': mp.nstr(xp.v, 22), 'diff': fl(d), 'sigma_tierA_part': fl(sA),
                       'sigma_pilot_part': fl(sP), 'sigma_diff': fl(sd), 'pull': fl(d / sd) if sd > 0 else None}
        pulls = [r['pull'] for r in rows.values() if r['pull'] is not None]
        log('  tier A vs pilots (input level, 26 scalars swapped): ' + ', '.join(
            f'{o} {r["diff"]:+.2e} +- {r["sigma_diff"]:.1e} ({r["pull"]:+.2f})' for o, r in rows.items()))
    out['tierA_vs_pilot_inputs'] = {
        'what': 'C8 inputs from production + tier A minus production + the same 26 scalars from the independent pilot '
                'runs (all-sector entries; c8val, c8conv, c8kplus1, poles1, kplus1; disjoint seeds); sigma = the 26 '
                'scalars of both runs (linear, replicate covariance + floors)',
        'pilot_sources': {nm: src for nm, (_, _, src) in best.items()}, 'not_in_pilots': missing, 'rows': rows}
    # (c) raw level: the engine's tier_vs_pilot_C8.py output
    tvp = json.load(open(os.path.join(C8A, 'tier_vs_pilot.json')))
    pt = [r['pull_tot'] for r in tvp['rows'] if r.get('pull_tot') is not None]
    out['tierA_vs_pilot_raw'] = {'source': 'engine/runs/c8tierA/tier_vs_pilot.json (engine tests/tier_vs_pilot_C8.py)',
                                 'n': len(pt), 'rms_pull': math.sqrt(sum(p * p for p in pt) / len(pt)),
                                 'max_abs_pull': max(abs(p) for p in pt)}
    log(f'  tier A vs pilots (raw, engine tool): {len(pt)} comparisons, rms pull {out["tierA_vs_pilot_raw"]["rms_pull"]:.2f}, '
        f'max {out["tierA_vs_pilot_raw"]["max_abs_pull"]:.2f}')
    # (d) the engine's pilot-level preview (results/preview_C8.json; archive-free), for reference only
    pv = json.load(open(os.path.join(CM.ENG_DIR, 'results', 'preview_C8.json')))['outputs']
    out['engine_pilot_preview'] = {k: v for k, v in pv.items()
                                   if k in NEW_A + NEW_BC + ['B_old8', 'B_done8', 'C8_partial']}
    return out


# ======================================================================================================
# step 2
# ======================================================================================================
RELEVANT = {  # jets through which the tier-A inputs enter (normalized responses; derivative order v, delta)
    'W': ['C3[v0d3]', 'C3[ddd]'], 'S': ['C5[v0d2]', 'C5_2[v0d2]', 'EC3[v0d2]', 'C3[dd]'],
    'L3': ['K4[v3d0]', 'K4[vvv]'], 'M21': ['K4[v2d1]', 'K4[vvd]'], 'M12': ['K4[v1d2]', 'K4[vdd]'],
    'N2': ['K6[v2d0]', 'K6_2[v2d0]', 'EK4[v2d0]', 'K4[vv]'], 'Ndelta': ['K6[v1d1]', 'K6_2[v1d1]', 'EK4[v1d1]', 'K4[vd]']}


def summarize(rows):
    p = [r['pull'] for r in rows if r.get('pull') is not None]
    if not p:
        return {'n': 0}
    w = max(rows, key=lambda r: abs(r['pull']) if r.get('pull') is not None else -1)
    return {'n': len(p), 'max_abs_pull': max(abs(x) for x in p), 'rms_pull': math.sqrt(sum(x * x for x in p) / len(p)),
            'n_above_3': sum(1 for x in p if abs(x) > 3), 'worst': w['check'],
            'n_missing': sum(1 for r in rows if r.get('status') == 'MISSING')}


def explicit_new_input_checks(V):
    """checks whose closed form / RG prediction contains a new C8 input explicitly: the input (computed from one
    engine job's single log) is then tested against a higher log of ANOTHER engine job"""
    import sympy as sp
    rg = json.load(open(os.path.join(CM.SPEC_DIR, 'out', 'C8', 'rg_logs_C8.json')))
    forms = {k + ' (second log)': v['prediction'] for k, v in rg['second_log_formulas']['formulas'].items()}
    for key, jet in rg['higher_log_formulas']['jets'].items():
        for k, r in jet['logs'].items():
            forms[f'{key} l^{k}'] = r['prediction']
    new = set(NEW_A + NEW_BC)
    rows = []
    for cat in ('targets', 'rg'):
        for r in V[cat]['rows']:
            f = r.get('closed_form') if cat == 'targets' else forms.get(r['check'])
            if not f or r.get('pull') is None:
                continue
            g = re.sub(r'([A-Za-z0-9_]+)\[(v\dd\d)\]', r'\1__\2', f)
            ids = set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', g))
            if not ids & new:
                continue
            loc = {t: sp.Symbol(t) for t in ids}
            ex = sp.sympify(g, locals=loc)
            for t in sorted(ids & new):
                c = sp.diff(ex, loc[t])
                cn = float(c) if c.is_number else None
                rows.append({'category': cat, 'check': r['check'], 'input': t, 'coefficient': str(c), 'diff': r['diff'],
                             'sigma': r['sigma'], 'pull': r['pull'],
                             'implied_abs_precision': (r['sigma'] / abs(cn)) if cn else None, 'formula': f})
    return rows


def step2_validate():
    path = os.path.join(OUT8, 'validate_C8_final.json')
    V = json.load(open(path))
    assert os.path.abspath(V['runs'][0]).endswith('c8tierA_topup1') and V['runs'][1].endswith('c8tierA')
    out = {'source': os.path.relpath(path, CM.ROOT), 'sha256': sha256(path), 'runs': [os.path.relpath(r, CM.ROOT) for r in V['runs']],
           'input_info': V['input_info'], 'kmax': V['kmax']}
    for cat in ('raw', 'zeros', 'targets', 'rg'):
        out[cat] = summarize(V[cat]['rows'])
    out['poles'] = {'all': summarize(V['poles']['rows']),
                    'new_for_C8': summarize([r for r in V['poles']['rows'] if r.get('new_for_C8')]),
                    'new_nontrivial': summarize([r for r in V['poles']['rows'] if r.get('new_for_C8') and r.get('nontrivial')]),
                    'jets_not_computable': sorted({r['check'].split('[eps')[0] for r in V['poles']['rows']
                                                   if r.get('status') == 'MISSING'})}
    out['raw_rows'] = [{k: r.get(k) for k in ('check', 'value', 'target', 'diff', 'sigma', 'pull')} for r in V['raw']['rows']]
    # per tier-A input: the checks on the jets it enters through
    per = {}
    for o, jets in RELEVANT.items():
        sel = {}
        for cat in ('poles', 'targets', 'rg'):
            rows = [r for r in V[cat]['rows'] if any(r['check'].startswith(j) for j in jets)]
            sel[cat] = summarize(rows)
            if cat == 'poles':
                sel['poles_nontrivial'] = summarize([r for r in rows if r.get('nontrivial')])
            if cat in ('targets', 'rg'):
                sel[cat + '_rows'] = [{k: r.get(k) for k in ('check', 'diff', 'sigma', 'pull', 'closed_form')}
                                      for r in rows]
        per[o] = sel
    out['by_tierA_input'] = per
    out['explicit_new_input_checks'] = explicit_new_input_checks(V)
    for r in out['explicit_new_input_checks']:
        log(f"    explicit: {r['check']:26s} contains {r['input']} (coefficient {r['coefficient']}): diff {r['diff']:+.2e} "
            f"sigma {r['sigma']:.1e} pull {r['pull']:+.2f} -> tests {r['input']} to {r['implied_abs_precision']:.1e}")
    rg_missing = sorted({r['check'].split(' ')[0] for r in V['rg']['rows'] if r.get('status') == 'MISSING'})
    out['rg_not_computable'] = rg_missing
    log('\n' + '=' * 110)
    log('STEP 2: archive-free checks (validate_C8 with tier A first; direct finite-cutoff; tier consistency)')
    log('=' * 110)
    log(f"  raw targets: {out['raw']}")
    log(f"  poles: all {out['poles']['all']}; new non-trivial {out['poles']['new_nontrivial']}; "
        f"not computable {out['poles']['jets_not_computable']}")
    log(f"  zeros {out['zeros']}; C3/K4 higher-log targets {out['targets']}; RG logs {out['rg']} "
        f"(not computable {rg_missing})")
    for o, s in per.items():
        log(f"    {o:7s} poles n={s['poles'].get('n')} max {s['poles'].get('max_abs_pull', 0):.2f} | "
            f"targets n={s['targets'].get('n')} max {s['targets'].get('max_abs_pull', 0):.2f} | "
            f"RG n={s['rg'].get('n')} max {s['rg'].get('max_abs_pull', 0):.2f}")
    return out


DIRECT_TIER_A = ['A3_dd', 'A3_ddd', 'A3_vdd', 'EA3_dd', 'Q4_vvv', 'Q4_vvd', 'Q4_vdd', 'EQ4_vv', 'EQ4_vd', 'Q4_vv',
                 'Q4_vd', 'Q4_d', 'Z4_dd', 'Z4_vd', 'Z4_vv', 'Z4_d', 'A5_dd', 'Q6_vv', 'Q6_vd']


def step2_direct():
    base = os.path.join(OUT8, 'direct_C8_final')
    rows = json.load(open(base + '_offsets.json'))
    eng = json.load(open(base + '_engine.json'))
    tally = {}
    for r in rows:
        tally[r['verdict']] = tally.get(r['verdict'], 0) + 1
    sel = []
    for r in rows:
        c = r.get('central') or {}
        e = {'moment': r['name'], 'engine_name': r.get('engine_name'), 'verdict': r['verdict'],
             'verdict_raw': r.get('verdict_raw'), 'K': r.get('K'), 'npts': r.get('npts'),
             'n_competitive': r.get('n_competitive')}
        for i in ('0', '1'):
            e[f'd{i}'], e[f'u{i}'], e[f'pull{i}'], e[f'detect3_{i}'], e[f'quoted{i}'] = (
                c.get(f'd{i}'), c.get(f'u{i}'), c.get(f'pull{i}'), c.get(f'detect3_{i}'), c.get(f'quoted{i}'))
        e['tierA_moment'] = r['name'] in DIRECT_TIER_A
        sel.append(e)
    log(f'  direct finite-cutoff comparison (tier A first): {tally}')
    for e in sel:
        if e['tierA_moment']:
            q = lambda i: ('%+.2e +- %.1e (%+.2f)' % (e[f'd{i}'], e[f'u{i}'], e[f'pull{i}'])
                           if e.get(f'quoted{i}') and e.get(f'pull{i}') is not None else 'not quoted')
            log(f"    {e['moment']:9s} {e['verdict']:12s} K={e['K']}  c00 {q('0'):30s} c01 {q('1')}")
    nonpass = [{k: e[k] for k in ('moment', 'verdict', 'verdict_raw', 'pull0', 'pull1')}
               for e in sel if e['verdict'] != 'PASS']
    return {'source': os.path.relpath(base + '_offsets.json', CM.ROOT), 'sha256': sha256(base + '_offsets.json'),
            'tally': tally, 'non_pass': nonpass, 'rows': sel, 'engine_series_note': eng.get('note'),
            'completion_counts': {k: len(v) for k, v in eng.get('added', {}).items()}}


def res_missing(nm):
    fw = L.Framework('C8', dps=20)
    req = set(fw.required_inputs()[nm])
    have = {L.canonical_raw_name(k) for f_ in (CM.FINAL_CANON, C8A_FINAL) for k in json.load(open(f_))['scalars']}
    return sorted(req - have)


# ======================================================================================================
def main():
    os.makedirs(OUT8, exist_ok=True)
    t_all = time.time()
    with mp.workdps(DPS):
        res, terms, budget, meta, fw, merged, inp, cen, names_A, prod = step1()
        W3 = w_three_ways(res)
        struct = note_structure(cen)
        tiers = tier_checks(fw, cen, inp, prod, names_A, res)
    val = step2_validate()
    direct = step2_direct()
    prodc8 = os.path.join(CM.ENG_DIR, 'PRODUCTION_C8.md')
    # what C8 still needs: the engine plan (results/plan_C8.json; amdq core-hours, own error model)
    planp = os.path.join(CM.ENG_DIR, 'results', 'plan_C8.json')
    plan = json.load(open(planp))
    remaining = {
        'missing_inputs': {nm: {'coefficient_in_C8': str(L.C8_LINEAR[nm]), 'tier': 'B' if nm in ('U', 'Kv') else 'C',
                                'raw_scalars_not_in_production_or_tierA': res_missing(nm)} for nm in NEW_BC},
        'plan_source': {'path': os.path.relpath(planp, CM.ROOT), 'sha256': sha256(planp),
                        'units': 'amdq core-hours (personal-desktop pilot timings x 0.667)'},
        'tiers': plan['tiers'], 'tierB_alternatives': plan['tierB']['alternatives'],
        'tierC_by_total_sigma_C8': {k: {kk: v[kk] for kk in ('sigma_B', 'sigma_C', 'cost_B', 'cost_C', 'reached')}
                                    for k, v in plan['tierC_by_target'].items()},
        'predicted_input_sigmas_main_plan': plan['sigma_inputs_main_plan'],
        'specs': {'B': 'engine/specs/production_C8_tierB.json', 'B_sigma0.01': 'engine/specs/production_C8_tierB_sigma0.01.json',
                  'C': 'engine/specs/production_C8_tierC.json', 'C_sigma0.3': 'engine/specs/production_C8_tierC_sigma0.3.json'}}
    out = {
        'title': 'Independent C8 re-derivation, tier A: assembly of the engine data (archive-free part)',
        'date': time.strftime('%Y-%m-%d %H:%M:%S %Z'),
        'archive_free': True,
        'note': 'Every number here comes from the project\'s own engine, framework, direct and spec components. No '
                'archive number was read or used by this script. The claims under test (C8, B_done, the six inherited '
                'records, the closed-form candidate) are compared only afterwards (compare_archive_C8.py, '
                '../RESULTS_C8_archive_comparison.json).',
        'definition': 'C8 = 8 T4 = B_old + 4W + 2S + 3/4 U + 1/4 J9 + 3/32 L3 - 1/4 M21 + 1/2 M12 - 1/16 N2 + 1/8 Ndelta '
                      '+ 1/32 Kv (eq:C8assembly, derived in framework/derive_C8.py); B_done = B_old + 4W + 2S + 3/32 L3 '
                      '- 1/4 M21 + 1/2 M12 - 1/16 N2; C8_partial = B_done + 1/8 Ndelta = C8 - (3/4 U + 1/4 J9 + 1/32 Kv)',
        'status': {'tiers_run': ['A'], 'available_new_inputs': NEW_A, 'missing_new_inputs': NEW_BC,
                   'C8_complete': False,
                   'reason': 'tiers B (U, Kv) and C (J9) of the engine plan were not run'},
        'step1': {'meta': meta, 'outputs': res, 'C8_assembly_terms': terms, 'error_budget': budget,
                  'W_three_ways': W3, 'note_raw_structure': struct, 'tier_consistency': tiers},
        'step2': {'validate_C8': val, 'direct': direct},
        'remaining_for_complete_C8': remaining,
        'independence': {
            'code': 'no archive integration or evaluation code imported, called or copied (engine, framework, direct, '
                    'spec and assembly are the project\'s own); no archived raw data (*_negative.json, *_audit.json, '
                    '*.expr, P6/P8/U/J9/Kv expression files) used as input',
            'this_script': 'reads only the project\'s engine runs, framework, spec/out (archive-free part; the '
                           'archive_derived_targets_sealed entries are never read) and direct table',
            'disclosure': [
                'The task brief that started this phase quotes archive numbers (C8, B_done, the closed-form candidate, '
                'and the magnitudes J9 ~ -273.72, U ~ -1296.7, Kv ~ -1487, A9_1, D9_lower, A7_d_1, P8). They were '
                'visible while this script was written; none of them enters any computation here.',
                'During tier-A development the engine agent compared its PILOT preview (results/preview_C8.json, '
                'B_done and U) with the B_done and U quoted in that brief (tests/compare_brief_C8.py, after hashing the '
                'preview). The tier-A production spec had already been planned from the archive-free error model, and '
                'nothing in the tier-A run or this assembly depends on that comparison.',
                'Phase 3: the note\'s printed B_old and W were compared (framework/compare_c8_production.py) after '
                'framework/out/C8_production.json was hashed.']},
        'compute': {'engine_tierA': 'engine/PRODUCTION_C8.md: the personal desktop (symmetry down), 183.1 allocated the personal desktop '
                                    'core-h = 122.2 amdq-equivalent (production + top-up 154.5 personal-desktop; strict '
                                    're-checks 28.6, 23.8 of them in two cancelled jobs)',
                    'engine_tierA_log_sha256': sha256(prodc8),
                    'this_assembly': 'local Mac only (framework assembly, validate_C8.py, direct_C8.py)',
                    'assembly_runtime_s': None},
    }
    out['compute']['assembly_runtime_s'] = round(time.time() - t_all, 1)
    CM.write_json(RESULTS, out)
    h = sha256(RESULTS)
    with open(RESULTS + '.sha256', 'w') as fh:
        fh.write(f'{h}  RESULTS_C8_independent_tierA.json  {out["date"]}\n')
    with open(os.path.join(OUT8, 'run_assembly_C8.log'), 'w') as fh:
        fh.write('\n'.join(LOG) + '\n')
    log(f'\nwrote {RESULTS}  sha256 {h}  ({time.time() - t_all:.0f} s)')


if __name__ == '__main__':
    main()
