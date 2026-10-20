#!/usr/bin/env python3
"""C8 assembly with tiers A + B + C (2026-10-07), step 3: comparison with the archive (COMPARISON ONLY).
(The tier-A version of 2026-10-04 is compare_archive_C8_tierA.py.)

Runs only after ../RESULTS_C8_independent.json exists with its .sha256 record (run_assembly_C8.py); it refuses otherwise,
checks that the file still has the recorded hash, verifies spec/comparison_C8/SHA256SUMS, and records both.  Our values
are read from RESULTS_C8_independent.json and never recomputed.  Archive numbers come only from the sealed
spec/comparison_C8/archive_C8_values.json.  Writes ../RESULTS_C8_archive_comparison.json and
out/C8_ABC/compare_archive_C8.log.

Compared (pulls with the quoted error = max of sigma_cov, sigma_rep, sigma_pool, and with each estimator):
  * the ten new inputs W, S, U, J9, L3, M21, M12, N2, Ndelta, Kv (archive 100-digit records; Ndelta = F1_known - 4 P6);
  * every sub-piece the archive or the note quotes: A7_d_1, D_known (U package), P8, X_vv, X_E, S3, F3_known (Kv),
    A9_1, Z8_1, (EA7)_0, (EZ6)_0, D9_lower (J9), P6, C_fixed;
  * B_old, B_done; C8 = 8 T4 against the claimed C8 (archive record and the value quoted in the task brief) and against
    the candidate closed form (evaluated here with mpmath); C8 without its J9 term against the archive's same quantity;
    the term-by-term decomposition of C8(ours) - C8(claim).
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

RES = os.path.join(CM.ROOT, 'RESULTS_C8_independent.json')
SEALDIR = os.path.join(CM.SPEC_DIR, 'comparison_C8')
ARCH = os.path.join(SEALDIR, 'archive_C8_values.json')
OUTP = os.path.join(CM.ROOT, 'RESULTS_C8_archive_comparison.json')
LOGF = os.path.join(CM.OUT, 'C8_ABC', 'compare_archive_C8.log')
LOG = []
NEW10 = ['W', 'S', 'U', 'J9', 'L3', 'M21', 'M12', 'N2', 'Ndelta', 'Kv']
COEF = {'W': mp.mpf(4), 'S': mp.mpf(2), 'L3': mp.mpf(3) / 32, 'M21': -mp.mpf(1) / 4, 'M12': mp.mpf(1) / 2,
        'N2': -mp.mpf(1) / 16, 'Ndelta': mp.mpf(1) / 8, 'U': mp.mpf(3) / 4, 'J9': mp.mpf(1) / 4, 'Kv': mp.mpf(1) / 32}
BRIEF_C8 = '247.38120480499354840735507'      # the claim as quoted (truncated) in the task brief of this phase
# our sub-piece -> candidate keys in the sealed file (records_100_digit first, then note_quoted_decimals)
SUBKEYS = {'A7_d_1': ['A7_d_1'], 'D_known': ['D_known'], 'P8': ['P8'], 'F3_known': ['F3_known = 16 X_vv - 8 X_E + S3'],
           'X_vv': ['X_vv', 'X_vv (note l.1366)'], 'X_E': ['X_E', 'X_E (note l.1367)'], 'S3': ['S3', 'S3 (note l.1363)'],
           'A9_1': ['A9_1'], 'Z8_1': ['Z8_1'], 'EA7_0': ['(EA7)_0', 'EA7_0'], 'EZ6_0': ['(EZ6)_0', 'EZ6_0'],
           'D9_lower': ['D9_lower'], 'P6': ['P6'], 'C_fixed': ['C_fixed'], 'F1_known': ['F1_known (Ndelta + 4 P6)']}


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
                                                              ('pull_rep', 'sigma_rep'), ('pull_pool', 'sigma_pool'),
                                                              ('pull_jobmax', 'sigma_jobmax'))}


def candidate(dps=60):
    with mp.workdps(dps):
        z = {n: mp.zeta(n) for n in range(2, 8)}
        return +(88 - 178 * z[2] + 110 * z[3] + 113 * z[4] + 4892 * z[5] - 2376 * z[2] * z[3]
                 - mp.mpf(8630) / 3 * z[6] + 1872 * z[3] ** 2 - 12168 * z[7] + 6048 * z[2] * z[5]
                 + 1536 * z[3] * z[4])


def main():  # noqa: C901
    mp.mp.dps = 50
    if not (os.path.exists(RES) and os.path.exists(RES + '.sha256')):
        sys.exit('RESULTS_C8_independent.json (+ .sha256) missing: run run_assembly_C8.py first (archive-free part)')
    sha = sha256(RES)
    rec = open(RES + '.sha256').read().split()
    if rec[0] != sha:
        sys.exit('RESULTS_C8_independent.json differs from its recorded SHA-256: refusing to compare')
    sums = {}
    for line in open(os.path.join(SEALDIR, 'SHA256SUMS')):
        h, p = line.split()
        sums[p] = h
    bad = [p for p, h in sums.items() if sha256(os.path.join(SEALDIR, p)) != h]
    if bad:
        sys.exit(f'spec/comparison_C8/SHA256SUMS mismatch: {bad}')
    ind = json.load(open(RES))
    assert ind.get('archive_free') is True and ind['status']['C8_complete'] is True
    A = json.load(open(ARCH))
    rec100, nq = A['records_100_digit'], A['note_quoted_decimals']

    def arch(keys):
        for k in keys:
            if k in rec100:
                return mp.mpf(rec100[k]['value']), f'records_100_digit[{k}]', rec100[k].get('source')
        for k in keys:
            if k in nq:
                return mp.mpf(nq[k]), f'note_quoted_decimals[{k}]', 'note'
        return None, None, None

    o = ind['step1']['outputs']
    sp = ind['step1']['sub_pieces']
    out = {'title': 'Independent C8 re-derivation (tiers A + B + C): comparison with the archive and the claims '
                    '(COMPARISON ONLY)',
           'date': time.strftime('%Y-%m-%d %H:%M:%S %Z'),
           'results_C8_independent_sha256': sha, 'results_C8_independent_recorded': ' '.join(rec[2:]),
           'sealed_dir_sha256sums_verified': sorted(sums), 'archive_file': os.path.relpath(ARCH, CM.ROOT),
           'archive_file_sha256': sha256(ARCH)}
    log('=' * 110)
    log(f'STEP 3 (C8, tiers A+B+C): comparison with the sealed archive values, after RESULTS_C8_independent.json '
        f'(sha256 {sha[:16]}..., written {" ".join(rec[2:])}); comparison_C8/SHA256SUMS verified ({len(sums)} files)')
    log('=' * 110)
    # ------------------------------------------------------------------ the ten inputs
    rows = {}
    hdr = '  %-8s %28s %28s %11s %9s %7s %7s %7s %7s %9s %11s'
    log(hdr % ('input', 'ours', 'archive', 'ours-arch', 'sigma', 'pull', 'p_cov', 'p_rep', 'p_pool', 'rel diff', 'in C8'))
    for nm in NEW10:
        e = o[nm]
        ours = mp.mpf(e['value'])
        ref, src, _ = arch([nm])
        d = ours - ref
        r = {'ours': e['value'], 'sigma': e['sigma'], 'quoted_estimator': e['quoted_estimator'], 'archive': mp.nstr(ref, 30),
             'archive_source': src, 'diff': fl(d), 'rel_diff': fl(d / ref), 'coefficient_in_C8': mp.nstr(COEF[nm], 6),
             'diff_in_C8': fl(COEF[nm] * d), 'sigma_in_C8': fl(abs(COEF[nm]) * e['sigma'])}
        r.update(pulls(e, d))
        rows[nm] = r
        log(hdr % (nm, mp.nstr(ours, 20), mp.nstr(ref, 20), '%+.2e' % d, '%.2e' % e['sigma'], '%+.2f' % r['pull'],
                   '%+.2f' % r['pull_cov'], '%+.2f' % r['pull_rep'], '%+.2f' % r['pull_pool'], '%.1e' % (d / ref),
                   '%+.2e' % (COEF[nm] * d)))
    pl = [rows[n]['pull'] for n in NEW10]
    out['inputs'] = {'rows': rows, 'rms_pull_10': math.sqrt(sum(p * p for p in pl) / len(pl)),
                     'max_abs_pull': max(abs(p) for p in pl),
                     'max_abs_pull_input': max(NEW10, key=lambda n: abs(rows[n]['pull']))}
    log(f"  ten inputs: rms pull {out['inputs']['rms_pull_10']:.2f}, max |pull| {out['inputs']['max_abs_pull']:.2f} "
        f"({out['inputs']['max_abs_pull_input']})")
    # ------------------------------------------------------------------ sub-pieces
    srows = {}
    log('')
    for nm, keys in SUBKEYS.items():
        e = sp[nm]
        ref, src, srcnote = arch(keys)
        if ref is None:
            srows[nm] = {'ours': e['value'], 'sigma': e['sigma'], 'archive': None, 'note': 'not in the sealed file'}
            log(f'  {nm:10s} ours {mp.nstr(mp.mpf(e["value"]), 18)} +- {e["sigma"]:.2e}: no archive value in the sealed file')
            continue
        d = mp.mpf(e['value']) - ref
        r = {'ours': e['value'], 'sigma': e['sigma'], 'quoted_estimator': e['quoted_estimator'], 'archive': mp.nstr(ref, 30),
             'archive_source': src, 'archive_source_note': srcnote, 'diff': fl(d),
             'rel_diff': fl(d / ref) if ref != 0 else None, 'definition': e['definition']}
        r.update(pulls(e, d))
        srows[nm] = r
        log(f'  {nm:10s} ours {mp.nstr(mp.mpf(e["value"]), 20):>26s}  archive {mp.nstr(ref, 20):>26s} ({src})  diff '
            f'{fl(d):+.3e}  sigma {e["sigma"]:.2e}  pull {r["pull"]:+.2f} (cov {r["pull_cov"]:+.2f}, rep {r["pull_rep"]:+.2f}, '
            f'pool {r["pull_pool"]:+.2f})')
    out['sub_pieces'] = srows
    # ------------------------------------------------------------------ B_old, B_done
    agg = {}
    for nm, key in (('B_old8', 'B_old'), ('B_done8', 'B_done')):
        e = o[nm]
        ref, src, _ = arch([key])
        d = mp.mpf(e['value']) - ref
        agg[nm] = {'ours': e['value'], 'sigma': e['sigma'], 'archive': mp.nstr(ref, 30), 'archive_source': src,
                   'diff': fl(d), 'rel_diff': fl(d / ref)}
        agg[nm].update(pulls(e, d))
        log(f"  {nm:8s} ours {mp.nstr(mp.mpf(e['value']), 20)}  archive {mp.nstr(ref, 20)}  diff {fl(d):+.3e}  "
            f"sigma {e['sigma']:.2e}  pull {agg[nm]['pull']:+.2f}")
    out['aggregates'] = agg
    # ------------------------------------------------------------------ C8
    C8c, srcC8, _ = arch(['C8'])
    cand = candidate()
    brief = mp.mpf(BRIEF_C8)
    e = o['C8']
    ours = mp.mpf(e['value'])
    d = ours - C8c
    c8 = {'ours_8T4': e['value'], 'sigma': e['sigma'], 'quoted_estimator': e['quoted_estimator'],
          'sigma_cov': e['sigma_cov'], 'sigma_rep': e['sigma_rep'], 'sigma_pool': e['sigma_pool'],
          'sigma_jobmax': e['sigma_jobmax'], 'rel_sigma': e['rel_sigma'],
          'claim_C8_archive': mp.nstr(C8c, 40), 'claim_source': srcC8, 'claim_as_quoted_in_brief': BRIEF_C8,
          'brief_minus_archive_record': fl(brief - C8c),
          'candidate_closed_form': ('88 - 178 z2 + 110 z3 + 113 z4 + 4892 z5 - 2376 z2 z3 - 8630/3 z6 + 1872 z3^2 - '
                                    '12168 z7 + 6048 z2 z5 + 1536 z3 z4'),
          'candidate_value_ours': mp.nstr(cand, 45), 'candidate_minus_claim': fl(cand - C8c),
          'ours_minus_claim': fl(d), 'rel_ours_minus_claim': fl(d / C8c), 'ours_minus_candidate': fl(ours - cand)}
    c8.update({'vs_claim': pulls(e, d), 'vs_candidate': pulls(e, ours - cand)})
    # C8 without its J9 term: ours vs archive C8 - archive J9 / 4 (tests everything but J9 at the tier-B precision)
    nj = sp['C8_without_J9']
    J9a, _, _ = arch(['J9'])
    ref_nj = C8c - J9a / 4
    dnj = mp.mpf(nj['value']) - ref_nj
    c8['C8_without_J9'] = {'ours': nj['value'], 'sigma': nj['sigma'], 'archive_C8_minus_J9_over_4': mp.nstr(ref_nj, 30),
                           'diff': fl(dnj), 'rel_diff': fl(dnj / ref_nj)}
    c8['C8_without_J9'].update(pulls(nj, dnj))
    # hybrid: our C8 with the archive J9 term in place of ours
    hyb = mp.mpf(nj['value']) + J9a / 4
    c8['hybrid_ours_with_archive_J9'] = {'value': mp.nstr(hyb, 25), 'sigma_ours_part': nj['sigma'],
                                         'minus_claim': fl(hyb - C8c), 'pull': fl((hyb - C8c) / nj['sigma'])}
    # term-by-term decomposition of ours - claim (archive inputs, our algebra; B_old from both sides)
    dec = {'B_old': fl(mp.mpf(o['B_old8']['value']) - arch(['B_old'])[0])}
    for nm in NEW10:
        dec[nm] = rows[nm]['diff_in_C8']
    dec_sum = sum(dec.values())
    tree = mp.mpf(o['C8']['value']) - mp.mpf(o['C8_asm']['value'])
    c8['decomposition_of_ours_minus_claim'] = {'terms': dec, 'sum_of_terms': dec_sum,
                                               'ours_8T4_minus_ours_C8asm': fl(tree),
                                               'archive_C8_minus_archive_eq_C8assembly': fl(
                                                   C8c - (arch(['B_old'])[0] + sum(COEF[n] * arch([n])[0] for n in NEW10))),
                                               'residual': fl(d - mp.mpf(dec_sum) - tree)}
    out['C8'] = c8
    log('')
    log(f"  C8 = 8 T4 (ours) = {mp.nstr(ours, 18)} +- {e['sigma']:.3f} ({e['quoted_estimator']}; cov {e['sigma_cov']:.3f}, "
        f"rep {e['sigma_rep']:.3f}, pool {e['sigma_pool']:.3f}, jobmax {e['sigma_jobmax']:.3f})")
    log(f"  claim {mp.nstr(C8c, 30)} ({srcC8}); brief value - record = {fl(brief - C8c):+.1e}; candidate (mpmath) - claim "
        f"= {fl(cand - C8c):+.1e}")
    log(f"  ours - claim = {fl(d):+.4f} ({fl(d / C8c):+.2e} relative): pull {c8['vs_claim']['pull']:+.2f} (cov "
        f"{c8['vs_claim']['pull_cov']:+.2f}, rep {c8['vs_claim']['pull_rep']:+.2f}, pool {c8['vs_claim']['pull_pool']:+.2f}, "
        f"jobmax {c8['vs_claim']['pull_jobmax']:+.2f})")
    log(f"  C8 without J9: ours {mp.nstr(mp.mpf(nj['value']), 20)} +- {nj['sigma']:.2e}; archive C8 - J9/4 = "
        f"{mp.nstr(ref_nj, 20)}; diff {fl(dnj):+.3e} (pull {c8['C8_without_J9']['pull']:+.2f})")
    log(f"  hybrid (ours, archive J9 term) - claim = {fl(hyb - C8c):+.3e} (pull {c8['hybrid_ours_with_archive_J9']['pull']:+.2f})")
    log('  decomposition of ours - claim: ' + ', '.join(f'{k} {v:+.3e}' for k, v in dec.items()) +
        f"; residual {c8['decomposition_of_ours_minus_claim']['residual']:+.1e}")
    CM.write_json(OUTP, out)
    with open(LOGF, 'w') as fh:
        fh.write('\n'.join(LOG) + '\n')
    log(f'\nwrote {OUTP}')


if __name__ == '__main__':
    main()
