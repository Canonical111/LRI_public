#!/usr/bin/env python3
"""Assembly phase, step 3: comparison with the archive and with the claimed closed forms.

Runs ONLY after ../RESULTS_independent.json exists (steps 1-2, run_assembly.py); it refuses otherwise and
records that file's SHA-256, so the archive-free results provably predate this comparison.  Our values are
read from RESULTS_independent.json (they are not recomputed here, except the few comparison-only quantities
listed below).  Archive numbers come only from the sealed spec/comparison/archive_comparison.json and
spec/comparison/archive_raw_coefficients.json.  Writes ../RESULTS_archive_comparison.json and
out/compare_archive.log.

Compared:
  * the 25 beta inputs, and D2, T2, D3, T3, D4, C3..C7, with the archive's 100-digit values: pull with the
    quoted error (max of sigma_cov, sigma_rep, sigma_pool) and with each estimator;
  * C5 (D3), C6 (T3), D4, C7 with the claimed closed forms, and the period combination
    calR = 2G + k + 2q - 2b - f (note l.632-634) with its closed form;
  * every engine raw coefficient (all 439 of results_final.json) with the archive's raw series where it has
    one (comparison of the integrations themselves);
  * the archive-derived higher-log predictions (sealed): [l^7], [l^3] of C7, [l^7], [l^3], [l^2] of d_delta C5,
    [l^2..l^8] of the Taylor [delta^2] coefficient of K4.
"""
import hashlib
import json
import math
import os
import sys
import time

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as CM  # noqa: E402
from common import L  # noqa: E402
import pooled_errors as PE  # noqa: E402

RES_IND = os.path.join(CM.ROOT, 'RESULTS_independent.json')
ARCH = os.path.join(CM.SPEC_DIR, 'comparison', 'archive_comparison.json')
ARCH_RAW = os.path.join(CM.SPEC_DIR, 'comparison', 'archive_raw_coefficients.json')
LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def f(x):
    return None if x is None else float(x)


def main():
    if not os.path.exists(RES_IND):
        sys.exit('RESULTS_independent.json does not exist: run run_assembly.py first (archive-free steps 1-2)')
    sha = hashlib.sha256(open(RES_IND, 'rb').read()).hexdigest()
    ind = json.load(open(RES_IND))
    assert ind.get('archive_free') is True
    mp.mp.dps = 50
    arch = json.load(open(ARCH))
    out = {'title': 'Independent C6/C7 re-derivation: comparison with the archive and with the claimed closed forms',
           'date': time.strftime('%Y-%m-%d %H:%M %Z'),
           'results_independent_sha256': sha,
           'results_independent_mtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(RES_IND))),
           'archive_files': [ARCH, ARCH_RAW]}
    s1 = ind['step1']['outputs']
    # ------------------------------------------------------------------ inputs and invariants vs archive
    log('=' * 100)
    log('STEP 3: comparison with the archive (spec/comparison, sealed) -- after RESULTS_independent.json '
        f'(sha256 {sha[:16]}...)')
    log('=' * 100)
    ai = arch['archive_inputs']
    ad = arch['archive_derived_values']
    inv_arch = {k: v['from_archive_inputs'] for k, v in arch['comparisons']['invariants_from_archive_inputs'].items()}
    rows = []
    log('  %-6s %28s %28s %11s %9s %8s %8s %8s' % ('name', 'ours', 'archive', 'ours-arch', 'sigma', 'pull',
                                                   'pull_cov', 'pull_rep'))
    for o in CM.OUTPUTS:
        e = s1[o]
        if o in ai:
            ref, src = mp.mpf(ai[o]['value']), 'archive_inputs (' + ai[o]['source'].split(' ')[0] + ')'
        elif o in ad:
            ref, src = mp.mpf(ad[o]['value']), 'archive_derived_values'
        elif o in inv_arch:
            ref, src = mp.mpf(inv_arch[o]), 'invariants_from_archive_inputs (our algebra on archived 100-digit inputs)'
        else:
            continue
        d = mp.mpf(e['value']) - ref
        r = {'name': o, 'ours': e['value'], 'archive': mp.nstr(ref, 30), 'diff': f(d), 'sigma': e['sigma'],
             'pull': f(d / e['sigma']) if e['sigma'] else None,
             'pull_cov': f(d / e['sigma_cov']) if e['sigma_cov'] else None,
             'pull_rep': f(d / e['sigma_rep']) if e['sigma_rep'] else None,
             'pull_pool': f(d / e['sigma_pool']) if e['sigma_pool'] else None, 'archive_source': src}
        rows.append(r)
        log('  %-6s %28s %28s %+11.3e %9.2e %+8.2f %+8.2f %+8.2f' % (
            o, mp.nstr(mp.mpf(e['value']), 20), mp.nstr(ref, 20), d, e['sigma'], r['pull'], r['pull_cov'],
            r['pull_rep']))
    pulls = [r['pull'] for r in rows if r['pull'] is not None]
    inp_pulls = [r['pull'] for r in rows if r['name'] in CM.BETA_D4 and r['pull'] is not None]
    summ = {'n': len(pulls), 'max_abs_pull': max(abs(x) for x in pulls),
            'rms_pull_inputs': math.sqrt(sum(x * x for x in inp_pulls) / len(inp_pulls)),
            'n_inputs_abs_pull_gt_2': sum(abs(x) > 2 for x in inp_pulls),
            'n_inputs_abs_pull_gt_3': sum(abs(x) > 3 for x in inp_pulls)}
    log(f"  inputs: rms pull {summ['rms_pull_inputs']:.2f}, |pull|>2: {summ['n_inputs_abs_pull_gt_2']}, "
        f"|pull|>3: {summ['n_inputs_abs_pull_gt_3']}; max |pull| over all rows {summ['max_abs_pull']:.2f}")
    out['inputs_and_invariants_vs_archive'] = {'rows': rows, 'summary': summ}
    # ------------------------------------------------------------------ claims (closed forms)
    log('\n  claimed closed forms (note eq:C6exact, D4, C7 = 4D4 - T3 - T2^2 + C3C5/2; C5 and D3 from eq:D3assembly)')
    _, tgt = L.closed_forms(50)
    claims = []
    for o in ('D3', 'C5', 'T3', 'C6', 'D4', 'C7'):
        e = s1[o]
        d = mp.mpf(e['value']) - tgt[o]
        c = {'name': o, 'ours': e['value'], 'closed_form_value': mp.nstr(tgt[o], 30), 'diff': f(d),
             'sigma': e['sigma'], 'sigma_cov': e['sigma_cov'], 'sigma_rep': e['sigma_rep'],
             'sigma_pool': e['sigma_pool'], 'pull': f(d / e['sigma']),
             'pull_cov': f(d / e['sigma_cov']), 'pull_rep': f(d / e['sigma_rep']),
             'pull_pool': f(d / e['sigma_pool']), 'rel_diff': f(d / tgt[o])}
        claims.append(c)
        log('  %-3s ours %26s  claim %26s  diff %+.3e  sigma %.2e  pull %+.2f (cov %+.2f, rep %+.2f, pool %+.2f)' % (
            o, mp.nstr(mp.mpf(e['value']), 18), mp.nstr(tgt[o], 18), d, e['sigma'], c['pull'], c['pull_cov'],
            c['pull_rep'], c['pull_pool']))
    # calR = 2G + k + 2q - 2b - f (needs the correlated combination: recomputed from the strict assembly)
    fw = L.Framework('D4', dps=50)
    rr = fw.from_replicates(CM.FINAL_CANON)
    cen = rr.central
    B = cen.beta
    calR = 2 * B['G'] + B['k'] + 2 * B['q'] - 2 * B['b'] - B['f']
    reps = [2 * rr.per_rep['G'][r] + rr.per_rep['k'][r] + 2 * rr.per_rep['q'][r] - 2 * rr.per_rep['b'][r]
            - rr.per_rep['f'][r] for r in range(6)]
    m = sum(reps) / 6
    se = mp.sqrt(sum((x - m) ** 2 for x in reps) / 5 / 6)
    fixed = rr.central.sig.restricted(keep_sig=rr.central.sig.sig, keep_blocks=set(), keep_reps=None)
    srep = mp.sqrt(se ** 2 + fixed.variance(calR.g))
    slin = calR.sigma(rr.central.sig)
    jobs = PE.final_jobs(CM.PROD, CM.TOPUP, ['Q6_E', 'A7_v', 'A7_base', 'A5_vE'])
    gin = {k: float(v) for k, v in cen.gradient(calR).items()}
    _, pst, _ = PE.pooled_projection(jobs, gin)
    spool = mp.sqrt(mp.mpf(pst) ** 2 + fixed.variance(calR.g))
    sig = max(slin, srep, spool)
    ex = CM.eval_closed(next(t['exact'] for t in CM.spec_targets() if t['id'] == 'input.calR'))
    d = calR.v - ex
    claims.append({'name': 'calR = 2G+k+2q-2b-f', 'ours': mp.nstr(calR.v, 30), 'closed_form_value': mp.nstr(ex, 30),
                   'diff': f(d), 'sigma': f(sig), 'sigma_cov': f(slin), 'sigma_rep': f(srep), 'sigma_pool': f(spool),
                   'pull': f(d / sig)})
    log('  calR ours %26s  claim %26s  diff %+.3e  sigma %.2e  pull %+.2f' % (
        mp.nstr(calR.v, 18), mp.nstr(ex, 18), d, sig, d / sig))
    out['claims_vs_closed_forms'] = claims
    # ------------------------------------------------------------------ raw coefficients vs archive raw series
    log('\n  raw coefficients (engine results_final.json, all 439) vs the archived raw series')
    raw = json.load(open(ARCH_RAW))['raw']
    eng = json.load(open(CM.FINAL_RESULTS))
    jobs_all = PE.final_jobs(CM.PROD, CM.TOPUP, ['Q6_E', 'A7_v', 'A7_base', 'A5_vE'], all_coeffs=True)
    rrows = []
    need = set(json.load(open(CM.FINAL_CANON))['scalars'])
    for grp, ser in eng['results'].items():
        atom = grp
        pref = L.group_to_prefix(grp)
        M, n, i, j, e, _, _ = L.parse_raw_name(f'{pref}[eps^0 l^0]')
        satom = L.prefix_to_spec_atom(M, n, i, j, e)
        if satom not in raw:
            continue
        for kj, (v, err) in ser.items():
            k, jj = (int(x) for x in kj.split(','))
            rec = raw[satom].get(str(k), {}).get('coefficients_by_log_power', {}).get(str(jj))
            try:
                mp.mpf(rec)
            except (TypeError, ValueError):
                continue                    # not archived, or archived without a numerical value
            errs = eng['errors'][grp][kj]
            if errs.get('zero'):
                continue
            nm = f'{pref}[eps^{k} l^{jj}]'
            _, pst, _ = PE.pooled_projection(jobs_all, {nm: 1.0})
            sig = max(err, math.hypot(pst, errs.get('floor', 0.0)))
            dd = float(mp.mpf(v) - mp.mpf(rec))
            rrows.append({'coef': nm, 'needed': nm in need, 'engine': v, 'archive': rec[:30], 'diff': dd,
                          'sigma_rep': err, 'sigma_pool': math.hypot(pst, errs.get('floor', 0.0)), 'sigma': sig,
                          'pull': dd / sig if sig > 0 else None, 'rel_sigma': sig / abs(float(mp.mpf(rec)))
                          if float(mp.mpf(rec)) != 0 else None})
    rp = [r['pull'] for r in rrows if r['pull'] is not None]
    rpn = [r['pull'] for r in rrows if r['pull'] is not None and r['needed']]

    def st(xs):
        return {'n': len(xs), 'rms': math.sqrt(sum(x * x for x in xs) / len(xs)),
                'n_gt_2': sum(abs(x) > 2 for x in xs), 'n_gt_3': sum(abs(x) > 3 for x in xs),
                'max_abs': max(abs(x) for x in xs)}
    rsum = {'all': st(rp), 'needed': st(rpn)}
    log(f"    all compared: {rsum['all']}")
    log(f"    needed only:  {rsum['needed']}")
    for r in sorted(rrows, key=lambda r: -abs(r['pull'] or 0))[:10]:
        log('    %-22s needed=%-5s diff %+.2e sigma %.1e pull %+.2f' % (r['coef'], r['needed'], r['diff'], r['sigma'],
                                                                     r['pull']))
    out['raw_coefficients_vs_archive'] = {'summary': rsum, 'rows': rrows}
    # ------------------------------------------------------------------ archive-derived higher-log predictions
    log('\n  archive-derived higher-log predictions (sealed)')
    dat, _ = CM.extended_input(12)
    NA = CM.NormAssembler(dat, 12, jobs=jobs_all)
    prow = []
    for p in arch['archive_derived_validation_predictions']:
        ser, k = p['series'], p['log_power']
        if ser.startswith('C7[v0d0]'):
            fn = lambda a, k=k: a['C'][7][(0, 0, 0)].coef(0, k)
            fac = 1
        elif ser.startswith('C5[v0d1]'):
            fn = lambda a, k=k: a['C'][5][(0, 1, 0)].coef(0, k)
            fac = 1
        elif ser.startswith('K4[v0d2]/2'):
            fn = lambda a, k=k: a['K'][4][(0, 2, 0)].coef(0, k)       # Taylor [delta^2] = d^2/2
            fac = 1
        else:
            continue
        stt = NA.stats(fn)
        if 'missing' in stt:
            prow.append({'series': ser, 'log': k, 'missing': stt['missing']})
            continue
        ref = mp.mpf(p['value'])
        d = stt['value'] * fac - ref
        prow.append({'series': ser, 'log': k, 'ours': mp.nstr(stt['value'], 20), 'archive_prediction': p['value'][:25],
                     'diff': f(d), 'sigma': f(stt['sigma']), 'pull': f(d / stt['sigma']) if stt['sigma'] else None})
        log('    %-36s l^%d ours %22s pred %22s diff %+.2e sigma %.1e pull %s' % (
            ser[:36], k, mp.nstr(stt['value'], 15), mp.nstr(ref, 15), d, stt['sigma'],
            'n/a' if not stt['sigma'] else '%+.2f' % (d / stt['sigma'])))
    out['archive_derived_higher_logs'] = prow
    CM.write_json(os.path.join(CM.ROOT, 'RESULTS_archive_comparison.json'), out)
    with open(os.path.join(CM.OUT, 'compare_archive.log'), 'w') as fh:
        fh.write('\n'.join(LOG) + '\n')
    log(f"\nwrote {os.path.join(CM.ROOT, 'RESULTS_archive_comparison.json')}")


if __name__ == '__main__':
    main()
