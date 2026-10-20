#!/usr/bin/env python3
"""Injected-error calibration of the GLS engine comparison (compare_engine.py) for every 5-8 kink moment
of the spec (spec/out/raw_requirements.json, kinks >= 5: A5_*, EA5_*, Z6_*, Q6_*, EQ6_base, A7_*, Q8_base).

Engine configurations (all existing engine output; the engine's production series did not exist yet):
  * pilot5        engine/runs/pilot5/results.json: the engine's production FORMAT (only the coefficients the
                  framework needs; most 5-8 kink moments lack the negative eps powers and some lack c00):
                  the REAL sensitivity of the direct comparison for the engine's production output;
  * merged        pilot5 + validation_d + validation_c merged per moment (compare_engine --merge: the
                  validation runs supply the negative powers): complete series for A5, A5_v, A5_d, Z6, Z6_v, Q6;
  * validation_d / validation_c   the complete validation series alone.
For every (moment, configuration) the baseline test is run; if it is PASS or TENSION, an error delta is
injected into the engine's [eps^0 l^0] and [eps^0 l^1] (when quoted) on the ladder delta = +-m D,
D = 3 sqrt(u^2 + e^2) of the baseline central variant, m = 0.25 ... 100; verdict, shift of d (must be
exactly -delta) and pulls are recorded.  Thresholds (both signs, every larger step too):
  nonpass  smallest |delta| giving a non-PASS verdict (only meaningful if the baseline is PASS);
  offset   smallest |delta| giving a robust OFFSET (all competitive tail variants flag it).
The next log coefficient [eps^0 l^2] is also corrupted (relative 1e-9 ... 1e-1) to show what the gates catch.
INCONCLUSIVE / UNTESTABLE baselines (partial series) get one gross injection (1e3 |c|) to show that no
conclusion is drawn.

Projection (design only, no values): 3-sigma sizes 3 sqrt(u^2 + e^2) if the engine delivered COMPLETE series
(every structural coefficient with k <= K, negative powers exact; c00, c01 errors as in pilot5), for K = 0
(tail k = 1, 2) and K = 1 (tail k = 2, 3), tail log degree J0 - 1 (conservative) and J0 - 2.

Output: results/injection_calibration.json, results/injection_calibration.txt (about 1 minute, local).
"""
import copy
import json
import os
import sys

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_engine as ce  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ENGINE = os.path.join(ROOT, 'engine')
P5 = os.path.join(ENGINE, 'runs', 'pilot5', 'results.json')
VD = os.path.join(ENGINE, 'results', 'validation_d_inputs.json')
VC = os.path.join(ENGINE, 'results', 'validation_c.json')
CONFIGS = [('pilot5', [P5], False), ('merged', [P5, VD, VC], True), ('validation_d', [VD], False),
           ('validation_c', [VC], False)]
LADDER = [0.25, 0.5, 1.0, 2.0, 4.0, 10.0, 100.0]
REL_CORRUPT = [1e-9, 1e-7, 1e-5, 1e-3, 1e-1]


def spec_moments():
    r = json.load(open(os.path.join(ROOT, 'spec', 'out', 'raw_requirements.json')))
    return sorted(nm for nm, v in r['total_safe'].items() if v['kinks'] >= 5)


def inject(ent, coef, delta):
    e2 = copy.copy(ent)
    e2['terms'] = dict(ent['terms'])
    c, err = e2['terms'][coef]
    e2['terms'][coef] = (c + delta, err)
    return e2


def summ(r):
    c = r.get('central') or {}
    return dict(verdict=r['verdict'], verdict_raw=r.get('verdict_raw'), J=c.get('J'), P=c.get('P'),
                dof=c.get('dof'), chi2_dof=c.get('chi2_dof'), n_free_missing=c.get('n_free_missing'),
                d0=c.get('d0'), u0=c.get('u0'), e0=c.get('e0'), pull0=c.get('pull0'),
                d1=c.get('d1'), u1=c.get('u1'), e1=c.get('e1'), pull1=c.get('pull1'), X2=c.get('joint_X2'))


def thresholds(rows):
    out = {}
    mags = sorted({abs(r['delta']) for r in rows})
    for tag, test in (('nonpass', lambda v: v != 'PASS'), ('offset', lambda v: v == 'OFFSET')):
        det = {m: all(test(r['verdict']) for r in rows if abs(r['delta']) == m) for m in mags}
        hit = next((m for i, m in enumerate(mags) if all(det[mm] for mm in mags[i:])), None)
        if hit is None:
            out[tag] = dict(threshold=None, largest_not_detected=mags[-1])
        else:
            i = mags.index(hit)
            out[tag] = dict(threshold=hit, largest_not_detected=mags[i - 1] if i > 0 else None)
    return out


def projection(tab, dn, ent, K, dJ):
    st = ce.structure(dn, ent)
    J0 = st['J0']
    S = set()
    for k in range(st['pmin'], K + 1):
        jm = max(0, J0 + 2 * k + 1) if k < 0 else (J0 if k == 0 else max(0, J0 - k))
        if k == 0:
            jm = max([jm] + [j for (kk, j) in ent['terms'] if kk == 0])
        S |= {(k, j) for j in range(jm + 1)}
    terms = {t: (mp.mpf(0), mp.mpf(0)) for t in S}
    for t in ((0, 0), (0, 1)):
        if t in terms:
            terms[t] = (mp.mpf(0), ent['terms'].get(t, (0, mp.mpf(0)))[1])
    fake = dict(terms=terms, cov=None, kmax=K, source='projection')
    stf = dict(S=S, K=K, J0=J0, JK=J0, pmin=st['pmin'])
    pts = [(x, mp.mpf(0), sg, el) for (x, r, sg, el) in ce.fit_points(tab, dn, ent, 0.021)]
    v = ce.gls_variant(pts, fake, stf, max(0, J0 - dJ), 2)
    if v is None or v['dof'] < 3:
        return None
    return dict(J=max(0, J0 - dJ), P=2, dof=v['dof'], npts=len(pts), detect3_0=v.get('detect3_0'),
                detect3_1=v.get('detect3_1'), u0=v.get('u0'), u1=v.get('u1'), e0=v.get('e0'), e1=v.get('e1'))


def fmt_th(th, key):
    x = th[key]['threshold']
    if x is None:
        return 'none<=100D'
    return '%.1e (rel %.0e)' % (x, x / abs(th['coef_value'])) if th['coef_value'] else '%.1e' % x


def main():
    mp.mp.dps = 50
    tab = json.load(open(os.path.join(HERE, '..', 'results', 'direct_table.json')))
    names = spec_moments()
    engines = {cfg: ce.load_engine(paths, merge=mg) for cfg, paths, mg in CONFIGS}
    res = dict(moments=names, configs={c: p for c, p, m in CONFIGS}, ladder=LADDER, rel_corrupt=REL_CORRUPT,
               results=[])
    lines = ['Injected-error calibration of compare_engine.py --offset-fit (5-8 kink spec moments).',
             'D3 = baseline 3-sigma size; nonPASS = smallest injection with a non-PASS verdict (baseline PASS only);',
             'OFFSET = smallest injection giving a robust OFFSET; rel = relative to |c|.', '']
    for nm in names:
        for cfg, _, _ in CONFIGS:
            ent = engines[cfg].get(nm)
            if ent is None:
                continue
            base = ce.offset_test(tab, nm, ent)
            st = ce.structure(nm, ent)
            missing = sorted('%d,%d' % t for t in st['S'] - set(ent['terms']) if t not in ((0, 0), (0, 1)))
            rec = dict(name=nm, config=cfg, engine_name=ent['engine_name'], K=base['K'], J0=base['J0'],
                       npts=base['npts'], baseline=summ(base), structure_missing=missing,
                       quoted=sorted('%d,%d' % t for t in ent['terms']), injections={}, thresholds={})
            v = base['verdict']
            if v in ('UNTESTABLE', 'INCONCLUSIVE', 'MODEL-FAIL'):
                for coef in ((0, 0), (0, 1)):
                    if coef in ent['terms']:
                        big = 1e3 * max(1.0, abs(float(ent['terms'][coef][0])))
                        r = ce.offset_test(tab, nm, inject(ent, coef, big))
                        rec['injections']['%d,%d' % coef] = [dict(delta=big, verdict=r['verdict'],
                                                                  verdict_raw=r.get('verdict_raw'))]
                res['results'].append(ce._f(rec))
                lines.append('%-9s %-12s K=%d %-12s (raw %s) npts=%d; %d structural coefficients not quoted: %s%s' % (
                    nm, cfg, base['K'], v, base.get('verdict_raw') or '-', base['npts'], len(missing),
                    ' '.join(missing[:6]), ' ...' if len(missing) > 6 else ''))
                continue
            c = base['central']
            for coef in ((0, 0), (0, 1)):
                t = 'd%d' % coef[1]
                if coef not in ent['terms'] or t not in c:
                    continue
                D = float(c['detect3_%d' % coef[1]])
                rows = []
                for m in LADDER:
                    for sgn in (+1, -1):
                        delta = sgn * m * D
                        r = ce.offset_test(tab, nm, inject(ent, coef, delta))
                        cc = r.get('central') or {}
                        shift = (cc.get(t) - c[t]) if cc.get(t) is not None else None
                        rows.append(dict(m=m, delta=delta, verdict=r['verdict'], shift=shift,
                                         shift_plus_delta=(shift + delta) if shift is not None else None,
                                         pull=cc.get('pull%d' % coef[1]), X2=cc.get('joint_X2'),
                                         J=cc.get('J'), P=cc.get('P')))
                rec['injections']['%d,%d' % coef] = rows
                th = thresholds(rows)
                th['coef_value'] = float(ent['terms'][coef][0])
                th['D3'] = D
                th['max_abs_shift_plus_delta'] = max(abs(float(q['shift_plus_delta'])) for q in rows
                                                     if q['shift_plus_delta'] is not None)
                if v != 'PASS':
                    th['nonpass'] = dict(threshold=None, largest_not_detected=None,
                                         note='baseline is %s: not meaningful' % v)
                rec['thresholds']['%d,%d' % coef] = th
            c2 = (0, 2)
            if c2 in ent['terms'] and ent['terms'][c2][0] != 0:
                v2 = abs(float(ent['terms'][c2][0]))
                rows = []
                for rel in REL_CORRUPT:
                    r = ce.offset_test(tab, nm, inject(ent, c2, rel * v2))
                    rows.append(dict(rel=rel, delta=rel * v2, verdict=r['verdict'],
                                     chi2_dof=(r.get('central') or {}).get('chi2_dof')))
                rec['injections']['0,2'] = rows
            rec = ce._f(rec)
            res['results'].append(rec)
            msg = '%-9s %-12s K=%d %-7s J=%s P=%s dof=%s chi2/dof=%.2g' % (
                nm, cfg, base['K'], v, c['J'], c['P'], c['dof'], float(c['chi2_dof']))
            for key in ('0,0', '0,1'):
                th = rec['thresholds'].get(key)
                if not th:
                    msg += ' | c%s not quoted' % key.replace(',', '')
                    continue
                np_ = fmt_th(th, 'nonpass') if th['nonpass'].get('threshold') or v == 'PASS' else 'n/a'
                msg += ' | c%s: D3=%.1e nonPASS>=%s OFFSET>=%s' % (key.replace(',', ''), th['D3'], np_,
                                                                   fmt_th(th, 'offset'))
            if '0,2' in rec['injections']:
                first = next((q['rel'] for q in rec['injections']['0,2'] if q['verdict'] != v), None)
                msg += ' | c02 corrupted: verdict changes at rel %s' % ('%.0e' % first if first else '>1e-1')
            lines.append(msg)
    lines.append('')
    lines.append('Projection: 3-sigma sizes if the engine delivered COMPLETE series (all structural coefficients with '
                 'k <= K, negative powers exact; c00, c01 errors as in pilot5); tail k = K+1, K+2 with log degree '
                 'J0-1 / J0-2 ("-": fewer than 3 dof):')
    proj = []
    p5 = engines['pilot5']
    for nm in names:
        ent = p5.get(nm)
        if ent is None:
            continue
        row = dict(name=nm, J0=ce.structure(nm, ent)['J0'], npts=len(ce.fit_points(tab, nm, ent, 0.021)),
                   c00=ent['terms'].get((0, 0), (None,))[0], c01=ent['terms'].get((0, 1), (None,))[0])
        for K in (0, 1):
            for dJ in (1, 2):
                row['K%d_dJ%d' % (K, dJ)] = projection(tab, nm, ent, K, dJ)
        row = ce._f(row)
        proj.append(row)

        def g(K, dJ, i):
            q = row['K%d_dJ%d' % (K, dJ)]
            return ('%.1e' % q['detect3_%d' % i]) if q and q.get('detect3_%d' % i) is not None else '-'
        lines.append('%-9s J0=%d npts=%2d  c00: K=0 %s / %s   K=1 %s / %s    c01: K=0 %s / %s   K=1 %s / %s   '
                     '(|c00| = %s, |c01| = %s)' % (
                         nm, row['J0'], row['npts'], g(0, 1, 0), g(0, 2, 0), g(1, 1, 0), g(1, 2, 0), g(0, 1, 1),
                         g(0, 2, 1), g(1, 1, 1), g(1, 2, 1),
                         '%.3g' % abs(row['c00']) if row['c00'] is not None else '-',
                         '%.3g' % abs(row['c01']) if row['c01'] is not None else '-'))
    res['projection_complete'] = proj
    out = os.path.join(HERE, '..', 'results', 'injection_calibration.json')
    json.dump(res, open(out, 'w'), indent=1)
    open(out.replace('.json', '.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print('wrote', out)


if __name__ == '__main__':
    main()
