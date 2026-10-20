#!/usr/bin/env python3
"""TIER-A VERSION (kept for the record; renamed 2026-10-07; reads/writes the *_tierA result files).
C8 assembly, step 3: comparison with the archive (COMPARISON ONLY).

Runs only after ../RESULTS_C8_independent.json exists with its .sha256 record (run_assembly_C8.py); it refuses
otherwise, checks that the file still has the recorded hash, verifies spec/comparison_C8/SHA256SUMS, and records
both.  Our values are read from RESULTS_C8_independent.json and never recomputed, except the raw-coefficient errors
of four comparison-only rows (read from the engine outputs).  Archive numbers come only from the sealed
spec/comparison_C8/archive_C8_values.json.  Writes ../RESULTS_C8_archive_comparison.json and
out/C8/compare_archive_C8.log.

Compared:
  * the seven tier-A inputs W, S, L3, M21, M12, N2 (100-digit inherited records) and Ndelta (archive F1_known - 4 P6),
    with the quoted error (max of sigma_cov, sigma_rep, sigma_pool) and with each estimator; also the note's printed
    15-digit values of the six inherited inputs;
  * B_old, B_done; C8_partial = B_done + Ndelta/8 against the same combination of archive numbers;
  * C8: ours is not complete (U, J9, Kv absent).  Reported: (a) the remainder the claim requires,
    C8_claim - C8_partial(ours), against the archive's 3/4 U + 1/4 J9 + 1/32 Kv; (b) the hybrid
    C8_partial(ours) + archive (3/4 U + 1/4 J9 + 1/32 Kv) against the claimed C8 and against the candidate closed
    form (evaluated here with mpmath);
  * raw single coefficients the note quotes: P6 = Q6_vd[eps^0 l^1] (eq:P6full), X_vv = Q6_vv[eps^0 l^0],
    (Q4_vvd)_0, (EE Q4_vd)_0;
  * the A3_ddE[eps^0 l^0] coefficient behind S: our three independent runs and the value the archive S implies.
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
import pooled_errors as PE  # noqa: E402

RES = os.path.join(CM.ROOT, 'RESULTS_C8_independent_tierA.json')
SEALDIR = os.path.join(CM.SPEC_DIR, 'comparison_C8')
ARCH = os.path.join(SEALDIR, 'archive_C8_values.json')
OUTP = os.path.join(CM.ROOT, 'RESULTS_C8_archive_comparison_tierA.json')
LOG = []
NEW_A = ['W', 'S', 'L3', 'M21', 'M12', 'N2', 'Ndelta']
COEF = {'W': mp.mpf(4), 'S': mp.mpf(2), 'L3': mp.mpf(3) / 32, 'M21': -mp.mpf(1) / 4, 'M12': mp.mpf(1) / 2,
        'N2': -mp.mpf(1) / 16, 'Ndelta': mp.mpf(1) / 8, 'U': mp.mpf(3) / 4, 'J9': mp.mpf(1) / 4, 'Kv': mp.mpf(1) / 32}


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def sha256(path):
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def fl(x):
    return None if x is None else float(x)


def pulls(e, d):
    return {k: fl(d / e[s]) if e.get(s) else None for k, s in (('pull', 'sigma'), ('pull_cov', 'sigma_cov'),
                                                              ('pull_rep', 'sigma_rep'), ('pull_pool', 'sigma_pool'))}


def candidate(dps=60):
    with mp.workdps(dps):
        z = {n: mp.zeta(n) for n in range(2, 8)}
        return +(88 - 178 * z[2] + 110 * z[3] + 113 * z[4] + 4892 * z[5] - 2376 * z[2] * z[3]
                 - mp.mpf(8630) / 3 * z[6] + 1872 * z[3] ** 2 - 12168 * z[7] + 6048 * z[2] * z[5]
                 + 1536 * z[3] * z[4])


def raw_error(rundir, group, kj, name):
    """our error of a single raw coefficient: max(replicate, sector-pooled) (+) floor, as in the assembly"""
    R = json.load(open(os.path.join(rundir, 'results.json')))
    v, e = R['results'][group][kj]
    ex = R['errors'][group][kj]
    jobs = PE.job_sector_values(rundir, groups={group}, all_coeffs=True, keep={name})
    jobs = {k: j for k, j in jobs.items() if k[2] == int(kj.split(',')[0])}
    _, pool, _ = PE.pooled_projection(jobs, {name: 1.0})
    stat = max(ex['stat'], pool)
    return mp.mpf(repr(v)), ex['stat'], pool, math.sqrt(stat ** 2 + ex['floor'] ** 2)


def main():
    mp.mp.dps = 50
    if not (os.path.exists(RES) and os.path.exists(RES + '.sha256')):
        sys.exit('RESULTS_C8_independent.json (+ .sha256) missing: run run_assembly_C8.py first (archive-free part)')
    sha = sha256(RES)
    rec = open(RES + '.sha256').read().split()
    if rec[0] != sha:
        sys.exit('RESULTS_C8_independent.json differs from its recorded SHA-256: refusing to compare')
    # the sealed directory: verify its SHA256SUMS before reading anything numeric from it
    sums = {}
    for line in open(os.path.join(SEALDIR, 'SHA256SUMS')):
        h, p = line.split()
        sums[p] = h
    bad = [p for p, h in sums.items() if sha256(os.path.join(SEALDIR, p)) != h]
    if bad:
        sys.exit(f'spec/comparison_C8/SHA256SUMS mismatch: {bad}')
    ind = json.load(open(RES))
    assert ind.get('archive_free') is True
    A = json.load(open(ARCH))
    rec100, nq = A['records_100_digit'], A['note_quoted_decimals']
    av = lambda k: mp.mpf(rec100[k]['value'])  # noqa: E731
    o = ind['step1']['outputs']
    out = {'title': 'Independent C8 re-derivation (tier A): comparison with the archive and the claims (COMPARISON ONLY)',
           'date': time.strftime('%Y-%m-%d %H:%M:%S %Z'),
           'results_C8_independent_sha256': sha, 'results_C8_independent_recorded': ' '.join(rec[2:]),
           'sealed_dir_sha256sums_verified': sorted(sums), 'archive_file': os.path.relpath(ARCH, CM.ROOT),
           'archive_file_sha256': sha256(ARCH)}
    log('=' * 110)
    log(f'STEP 3 (C8): comparison with the sealed archive values, after RESULTS_C8_independent.json '
        f'(sha256 {sha[:16]}..., written {" ".join(rec[2:])}); comparison_C8/SHA256SUMS verified ({len(sums)} files)')
    log('=' * 110)
    # ------------------------------------------------------------------ the seven tier-A inputs
    rows = {}
    notep = {'W': 'W (note table l.1243)', 'S': 'S (note)', 'L3': 'L3 (note)', 'M21': 'M21 (note)', 'M12': 'M12 (note)',
             'N2': 'N2 (note)'}
    log('  %-7s %26s %26s %11s %9s %7s %7s %7s %7s %9s' % ('input', 'ours', 'archive', 'ours-arch', 'sigma', 'pull',
                                                          'p_cov', 'p_rep', 'p_pool', 'rel diff'))
    for nm in NEW_A:
        e = o[nm]
        ours = mp.mpf(e['value'])
        ref = av(nm)
        d = ours - ref
        r = {'ours': e['value'], 'sigma': e['sigma'], 'archive': rec100[nm]['value'][:40],
             'archive_source': rec100[nm].get('source'), 'archive_note': rec100[nm].get('note'),
             'diff': fl(d), 'rel_diff': fl(d / ref)}
        r.update(pulls(e, d))
        if nm in notep:
            pn = mp.mpf(nq[notep[nm]])
            r['note_printed'] = nq[notep[nm]]
            r['diff_to_note_printed'] = fl(ours - pn)
        r['contribution_to_C8_of_diff'] = fl(COEF[nm] * d)
        rows[nm] = r
        log('  %-7s %26s %26s %+11.2e %9.2e %+7.2f %+7.2f %+7.2f %+7.2f %9.1e' % (
            nm, mp.nstr(ours, 20), mp.nstr(ref, 20), d, e['sigma'], r['pull'], r['pull_cov'], r['pull_rep'],
            r['pull_pool'], d / ref))
    pl = [rows[n]['pull'] for n in NEW_A]
    pl6 = [rows[n]['pull'] for n in NEW_A if n != 'Ndelta']
    out['inputs'] = {'rows': rows, 'rms_pull_7': math.sqrt(sum(p * p for p in pl) / len(pl)),
                     'rms_pull_six_inherited': math.sqrt(sum(p * p for p in pl6) / len(pl6)),
                     'max_abs_pull': max(abs(p) for p in pl)}
    log(f"  seven inputs: rms pull {out['inputs']['rms_pull_7']:.2f}; six inherited records: rms "
        f"{out['inputs']['rms_pull_six_inherited']:.2f}; max |pull| {out['inputs']['max_abs_pull']:.2f}")
    # S: tier A alone and the A3_ddE coefficient behind it
    tA = ind['step1']['tier_consistency']['tierA_alone_vs_final']['rows']['S']
    S_alone = mp.mpf(o['S']['value']) - mp.mpf(tA['final_minus_tierA_alone'])
    eng = CM.ENG_DIR
    a3 = {}
    for tag, rd in (('c8val (N=64007)', 'c8val'), ('tier A (N=262139)', 'c8tierA'),
                    ('top-up (N=524287)', 'c8tierA_topup1')):
        v, srep, spool, stot = raw_error(os.path.join(eng, 'runs', rd), 'A3_ddE', '0,0', 'A3_ddE[eps^0 l^0]')
        a3[tag] = {'value': mp.nstr(v, 17), 'sigma_rep': srep, 'sigma_pool': spool, 'sigma': stot}
    # dS/dA3_ddE from our own tier-A-alone vs final difference (only A3_ddE differs)
    xf = mp.mpf(a3['top-up (N=524287)']['value'])
    xa = mp.mpf(a3['tier A (N=262139)']['value'])
    dSdx = mp.mpf(tA['final_minus_tierA_alone']) / (xf - xa)
    implied = xf - (mp.mpf(o['S']['value']) - av('S')) / dSdx
    for tag, e in a3.items():
        e['minus_archive_implied'] = fl(mp.mpf(e['value']) - implied)
        e['pull_vs_archive_implied'] = fl((mp.mpf(e['value']) - implied) / e['sigma'])
    out['S_detail'] = {'S_tierA_alone': mp.nstr(S_alone, 22), 'S_tierA_alone_minus_archive': fl(S_alone - av('S')),
                       'dS_dA3_ddE': fl(dSdx), 'A3_ddE_implied_by_archive_S': mp.nstr(implied, 17),
                       'A3_ddE_runs': a3,
                       'S_error_budget': {'pooled_by_job': o['S']['top_jobs_pooled'][:3],
                                          'floors_total': o['S']['sigma_floor'], 'sigma_pool_stat': o['S']['sigma_pool_stat']},
                       'what': 'the largest statistical part of sigma(S) is the endpoint coefficient A3_ddE[eps^0 l^0] '
                               '(then A5_dd[eps^0 l^1] and the precision floors); our three independent runs of A3_ddE '
                               'and the value the archive S would imply if the whole difference were in A3_ddE'}
    log(f"  S detail: tier A alone (before the A3_ddE top-up) minus archive {fl(S_alone - av('S')):+.2e}; "
        f"dS/dA3_ddE = {fl(dSdx):.4f}; A3_ddE implied by the archive S = {mp.nstr(implied, 17)}")
    for tag, e in a3.items():
        log(f"    A3_ddE[eps^0 l^0] {tag:18s} {e['value']:>20s}  rep {e['sigma_rep']:.1e} pool {e['sigma_pool']:.1e}  "
            f"minus implied {e['minus_archive_implied']:+.2e} ({e['pull_vs_archive_implied']:+.2f} sigma)")
    # ------------------------------------------------------------------ B_old, B_done, C8_partial
    agg = {}
    for nm, ref in (('B_old8', av('B_old')), ('B_done8', av('B_done'))):
        e = o[nm]
        d = mp.mpf(e['value']) - ref
        agg[nm] = {'ours': e['value'], 'sigma': e['sigma'], 'archive': mp.nstr(ref, 30), 'diff': fl(d),
                   'rel_diff': fl(d / ref)}
        agg[nm].update(pulls(e, d))
    ref_part = av('B_done') + av('Ndelta') / 8
    e = o['C8_partial']
    d = mp.mpf(e['value']) - ref_part
    agg['C8_partial'] = {'ours': e['value'], 'sigma': e['sigma'], 'archive': mp.nstr(ref_part, 30),
                         'archive_definition': 'archive B_done + archive Ndelta/8 (our algebra)', 'diff': fl(d),
                         'rel_diff': fl(d / ref_part)}
    agg['C8_partial'].update(pulls(e, d))
    # B_done - B_old: the six inherited terms alone (our B_old error cancels)
    ours_6 = mp.mpf(o['B_done8']['value']) - mp.mpf(o['B_old8']['value'])
    arch_6 = av('B_done') - av('B_old')
    sig6 = math.sqrt(sum((float(COEF[n]) * o[n]['sigma']) ** 2 for n in ('W', 'S', 'L3', 'M21', 'M12')) +
                     (float(COEF['N2']) * ind['step1']['outputs']['N2']['sigma']) ** 2)
    agg['six_inherited_terms'] = {'ours': mp.nstr(ours_6, 22), 'archive': mp.nstr(arch_6, 22), 'diff': fl(ours_6 - arch_6),
                                  'sigma_conservative': sig6, 'pull': fl((ours_6 - arch_6) / sig6),
                                  'note': 'B_done - B_old = 4W + 2S + 3/32 L3 - 1/4 M21 + 1/2 M12 - 1/16 N2; sigma: the '
                                          'six input sigmas in quadrature (conservative: N2 includes production errors '
                                          'shared with B_old)'}
    out['aggregates'] = agg
    log('')
    for nm, r in agg.items():
        log(f"  {nm:20s} ours {mp.nstr(mp.mpf(r['ours']), 22):>26s}  archive {mp.nstr(mp.mpf(r['archive']), 22):>26s}  "
            f"diff {r['diff']:+.3e}  sigma {r.get('sigma', r.get('sigma_conservative')):.2e}  pull {r['pull']:+.2f}")
    # ------------------------------------------------------------------ C8
    C8c = av('C8')
    cand = candidate()
    rem_arch = COEF['U'] * av('U') + COEF['J9'] * av('J9') + COEF['Kv'] * av('Kv')
    part = mp.mpf(o['C8_partial']['value'])
    sp = o['C8_partial']['sigma']
    rem_needed = C8c - part
    hybrid = part + rem_arch
    c8 = {'status': 'our C8 is INCOMPLETE: U, J9, Kv (tiers B, C) were not computed',
          'claim_C8': mp.nstr(C8c, 35), 'candidate_closed_form': ('88 - 178 z2 + 110 z3 + 113 z4 + 4892 z5 - 2376 z2 z3 - '
                                                                  '8630/3 z6 + 1872 z3^2 - 12168 z7 + 6048 z2 z5 + 1536 z3 z4'),
          'candidate_value_ours': mp.nstr(cand, 40), 'candidate_minus_claim': fl(cand - C8c),
          'C8_partial_ours': o['C8_partial']['value'], 'C8_partial_sigma': sp,
          'remainder_required_by_claim': {'value': mp.nstr(rem_needed, 22), 'sigma': sp,
                                          'archive_3U/4+J9/4+Kv/32': mp.nstr(rem_arch, 22),
                                          'diff': fl(rem_needed - rem_arch), 'pull': fl((rem_needed - rem_arch) / sp),
                                          'archive_terms': {'3/4 U': mp.nstr(COEF['U'] * av('U'), 18),
                                                            '1/4 J9': mp.nstr(COEF['J9'] * av('J9'), 18),
                                                            '1/32 Kv': mp.nstr(COEF['Kv'] * av('Kv'), 18)}},
          'hybrid_C8': {'definition': 'C8_partial (ours: B_old + W, S, L3, M21, M12, N2, Ndelta terms) + archive '
                                      '(3/4 U + 1/4 J9 + 1/32 Kv)',
                        'value': mp.nstr(hybrid, 22), 'sigma_ours_part': sp,
                        'minus_claim': fl(hybrid - C8c), 'pull_vs_claim': fl((hybrid - C8c) / sp),
                        'minus_candidate': fl(hybrid - cand), 'pull_vs_candidate': fl((hybrid - cand) / sp),
                        'rel_minus_claim': fl((hybrid - C8c) / C8c)},
          'what_is_not_tested': 'U, J9, Kv (the four-package terms F2-F4 except Ndelta) are not computed by us; the '
                                'hybrid tests only B_old and the seven tier-A terms (1334.8 of C8, against a '
                                'remainder of -1087.4)'}
    pv = ind['step1']['tier_consistency']['engine_pilot_preview'].get('U', {})
    if 'value' in pv:
        su = max(mp.mpf(pv['sigma_linear']), mp.mpf(pv['rep_se']))
        du = mp.mpf(pv['value']) - av('U')
        c8['U_pilot_level'] = {'ours_pilot': pv['value'], 'sigma': fl(su), 'archive': mp.nstr(av('U'), 20),
                               'diff': fl(du), 'pull': fl(du / su),
                               'note': 'engine PILOT preview (N = 1009 all-sector A7_d), NOT production; it was '
                                       'already compared with the U quoted in the brief during development '
                                       '(engine tests/compare_brief_C8.py)'}
        log(f"  U at pilot level (preview, not production; compared before in development): {pv['value'][:12]} +- "
            f"{fl(su):.0f} vs archive {mp.nstr(av('U'), 10)}: pull {fl(du / su):+.2f}")
    out['C8'] = c8
    log('')
    log(f"  C8 claim {mp.nstr(C8c, 25)}; candidate closed form (our evaluation) - claim = {fl(cand - C8c):+.1e}")
    log(f"  remainder the claim requires: C8_claim - C8_partial(ours) = {mp.nstr(rem_needed, 18)} +- {sp:.2e};  "
        f"archive 3/4 U + 1/4 J9 + 1/32 Kv = {mp.nstr(rem_arch, 18)};  diff {fl(rem_needed - rem_arch):+.2e} "
        f"(pull {fl((rem_needed - rem_arch) / sp):+.2f})")
    log(f"  hybrid C8 = ours + archive (U, J9, Kv) = {mp.nstr(hybrid, 18)} +- {sp:.1e} (our part); minus claim "
        f"{fl(hybrid - C8c):+.2e} (pull {fl((hybrid - C8c) / sp):+.2f}, rel {fl((hybrid - C8c) / C8c):+.1e})")
    # ------------------------------------------------------------------ raw coefficients the note quotes
    raw = {}
    for lab, rd, g, kj, nm, ref, src in (
            ('P6 = Q6_vd[eps^0 l^1]', 'c8tierA', 'Q6_vd', '0,1', 'Q6_vd[eps^0 l^1]', av('P6'), 'records_100_digit P6 (eq:P6full)'),
            ('X_vv = Q6_vv[eps^0 l^0]', 'c8tierA', 'Q6_vv', '0,0', 'Q6_vv[eps^0 l^0]', mp.mpf(nq['X_vv (note l.1366)']), 'note l.1366'),
            ('(Q4_vvd)_0 = Q4_vvd[eps^0 l^0]', 'c8tierA', 'Q4_vvd', '0,0', 'Q4_vvd[eps^0 l^0]',
             mp.mpf(nq['(Q4_vvd)_0 (note l.1323)']), 'note l.1323'),
            ('(EE Q4_vd)_0 = Q4_vdE[eps^0 l^0]', 'c8tierA', 'Q4_vdE', '0,0', 'Q4_vdE[eps^0 l^0]',
             mp.mpf(nq['(EE Q4_vd)_0 (note l.1324)']), 'note l.1324')):
        v, srep, spool, stot = raw_error(os.path.join(eng, 'runs', rd), g, kj, nm)
        d = v - ref
        raw[lab] = {'ours': mp.nstr(v, 20), 'sigma_rep': srep, 'sigma_pool': spool, 'sigma': stot,
                    'archive': mp.nstr(ref, 25), 'archive_source': src, 'diff': fl(d), 'pull': fl(d / stot),
                    'rel_diff': fl(d / ref)}
        log(f"  raw {lab:32s} ours {mp.nstr(v, 20):>24s}  archive {mp.nstr(ref, 20):>24s}  diff {fl(d):+.2e}  "
            f"sigma {stot:.1e}  pull {fl(d / stot):+.2f}")
    sup = {k: rec100[k]['value'][:30] for k in rec100 if k.startswith('superseded_P6')}
    raw['P6 = Q6_vd[eps^0 l^1]']['superseded_archive_P6_runs'] = {
        k: {'value': v, 'ours_minus': fl(mp.mpf(raw['P6 = Q6_vd[eps^0 l^1]']['ours']) - mp.mpf(v))} for k, v in sup.items()}
    out['raw_coefficients'] = raw
    # ------------------------------------------------------------------ write
    CM.write_json(OUTP, out)
    with open(os.path.join(CM.OUT, 'C8', 'compare_archive_C8.log'), 'w') as fh:
        fh.write('\n'.join(LOG) + '\n')
    log(f'\nwrote {OUTP}')


if __name__ == '__main__':
    main()
