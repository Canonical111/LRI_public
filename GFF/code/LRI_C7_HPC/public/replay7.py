#!/usr/bin/env python3
"""Public replay of C7(1), Tier 1 (`make -f public.mk replay`): works from the git checkout alone.

Recomputes every quoted number of the C7(1) row that the published records determine, and checks the rest against
the recorded values. Inputs (all shipped in git):

  ../../results/C7_1/C7_final.json            final 399-batch + direct-primitive combination (tools/combine.py, 7320afc)
  ../../results/C7_1/combined_assembly.json   its configuration (sources, weights, batches, primitive cross-check)
  ../../results/C7_1/{design_v1.json, inclusion.txt, production_run.json, resubmitted_elements.txt, REPORT.md}
  ../../results/C7_1/v1_46batches/C7_final.json   the earlier 46-batch combination (only for "Result v1: z = 0.11")
  reference/verification/full_affine_assembly.json   the frozen affine map (its SHA-256 is recorded in C7_final.json)
  reference/inputs, reference/verification, reference/SHA256SUMS   the inherited September 2026 archive

What is recomputed (from the per-source component summaries, i.e. the projected replicate means and covariances that
C7_final.json stores for each of the 9577 sources, plus the affine map's constant K):
  the estimator and its covariance, every level (free, primitive, coarse, refine3/5/6, the refine7 check), the
  telescoped resolution sequence, the lower-order checks and their z-scores, the allowance candidates and the
  allowance, the systematic-tension flag, the campaign aggregates and the A/B agreement, the 399 per-batch values and
  standard errors, the inter-batch chi^2, the primitive cross-check, the post hoc truncation-aware estimate and the
  lower-order step/tail table, the archive and v1 comparisons, the archived reassembly (tools/assemble.py --original,
  about 1 s), and the inventory counts of the note (from reference/inputs).
What is only checked as recorded (marked RECORDED; Tier 2, `make -f public.mk replay-full`, recomputes them from the
hosted merged replicate streams): the replicate bootstrap SE, the two half-split estimates, the spurious-pole means,
the zero-pole control terms and the uncontrolled estimator. Their internal arithmetic (z = mean/SE, totals = sums
over L, applied control = uncontrolled - controlled, half-split displacement) is recomputed.

Tolerances: integers, strings and SHA-256 values exactly; re-summations in the production order 1e-12 relative (they
are bitwise identical on IEEE-754 platforms and the script reports when they are); per-batch values, which rescale
the stored components by K=399, 1e-12 relative (C7) and 1e-10 relative (SE); quoted decimals must equal the recomputed
value rounded (or rounded up, for allowances and error bounds) to the quoted number of digits.
Writes <work>/replay7_tier1.txt and .json; exit status 1 if any check FAILs.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, subprocess, sys
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP
from pathlib import Path

sys.dont_write_bytecode = True
PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / 'tools'))

C6_EXACT = 14331.68703277          # C6(1) of LRI_C6_1D_HPC (GFF/results/C6_1/C6_final.json, headline.C6), allowance 4.9e-7
C6_OLD_SE = 0.14344                # SE of the superseded numerical C6 reference 14331.77074705 (LRI_C6_1D_HPC/reference/C6_result_original.json)
K_EXPECTED = 399
BATCH_SEED = 'C7-expanse-2026-09:batch:{k}'
PRIMITIVE_SEED = b'C7-expanse-2026-09:primitive'
CAMPAIGNS = (['tprodA_L5', 'tprodA_L6', 'tprodA_L7', 'tprodB_L5', 'tprodB_L6', 'tprodB_L7']
             + [f'power_coarse{x}_L{L}' for x in 'AB' for L in (5, 6, 7)]
             + ['power_refine3_L5', 'power_refine3_L6', 'power_refine3B_L7']
             + [f'power_refine{d}_L{L}' for d in (5, 6, 7) for L in (5, 6, 7)])
# Replicates per campaign quoted in the note (Sec. "Production results and refinement"): power-free 128; coarse A 128,
# B 64; refinements 1->3 128, 3->5 128, 5->6 64; check 6->7 64.
REPLICATES = {**{f'tprod{x}_L{L}': 128 for x in 'AB' for L in (5, 6, 7)},
              **{f'power_coarseA_L{L}': 128 for L in (5, 6, 7)}, **{f'power_coarseB_L{L}': 64 for L in (5, 6, 7)},
              'power_refine3_L5': 128, 'power_refine3_L6': 128, 'power_refine3B_L7': 128,
              **{f'power_refine5_L{L}': 128 for L in (5, 6, 7)}, **{f'power_refine6_L{L}': 64 for L in (5, 6, 7)},
              **{f'power_refine7_L{L}': 64 for L in (5, 6, 7)}}
# Root SHA256SUMS lines whose files are hash-bound or production code: a mismatch is a FAIL. Any other listed file
# (docs, README, benchmark/provenance JSON, REPORT, production_run.json ...) may have been scrubbed by the public
# export; a mismatch there is reported as WARN.
BOUND_PREFIXES = ('src/', 'tools/', 'cluster/', 'tests/', 'reference/', 'inputs_extra/cw_', 'Makefile', 'requirements.txt')
BOUND_RESULTS = ('C7_final.json', 'combined_assembly.json', 'design_v1.json', 'inclusion.txt')
# TeX notes of reference/ (and their build logs), merged into the condensed note GFF/note (author rule 2026-10-16: one
# TeX note per direction) or superseded, and not shipped. Their reference/SHA256SUMS lines stay; only these may be absent.
MERGED_NOTES = ('C7_1d_full_calculation.tex', 'C7_1d_full_calculation.pdf', 'C7_full_appendix.tex',
                'long_range_ising_complete.tex', 'long_range_ising_complete.pdf', 'note/C7_appendix_template.tex',
                'retained/previous_note.tex', 'verification/build_logs/C7_1d_full_calculation.log',
                'verification/build_logs/long_range_ising_complete.log')

ROWS: list[dict] = []


def add(group, name, status, got='', ref='', tol='', note=''):
    ROWS.append({'group': group, 'check': name, 'status': status, 'recomputed': str(got), 'reference': str(ref),
                 'tolerance': tol, 'note': note})


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def load(p: Path):
    return json.loads(Path(p).read_text())


def rel_ok(a, b, rtol, atol=0.0):
    return abs(a - b) <= max(atol, rtol * max(abs(a), abs(b)))


def close(group, name, got, ref, rtol=1e-12, atol=0.0, note=''):
    """Float or vector agreement; reports bitwise identity in the note."""
    import numpy as np
    g = np.asarray(got, dtype=float); r = np.asarray(ref, dtype=float)
    if g.shape != r.shape:
        add(group, name, 'FAIL', g.shape, r.shape, 'shape', note); return False
    bit = bool(np.array_equal(g, r))
    scale = float(np.max(np.abs(r))) if r.size else 0.0
    ok = bool(np.all(np.abs(g - r) <= np.maximum(atol, rtol * np.maximum(np.abs(g), np.abs(r)))))
    if not ok and r.ndim:  # vectors with zero entries: compare against the largest entry
        ok = bool(np.max(np.abs(g - r)) <= max(atol, rtol * scale))
    show = (lambda x: f'{float(x):.12g}') if g.ndim == 0 else (lambda x: f'max|d|={float(np.max(np.abs(g - r))):.3g}')
    add(group, name, 'PASS' if ok else 'FAIL', show(g), (f'{float(r):.12g}' if r.ndim == 0 else f'scale {scale:.6g}'),
        f'rel {rtol:g}' + (f', abs {atol:g}' if atol else ''), ('bitwise' if bit else 'not bitwise') + ('; ' + note if note else ''))
    return ok


def exact(group, name, got, ref, note=''):
    ok = got == ref
    add(group, name, 'PASS' if ok else 'FAIL', got if len(str(got)) < 80 else str(got)[:77] + '...',
        ref if len(str(ref)) < 80 else str(ref)[:77] + '...', 'exact', note)
    return ok


def rounds_to(value: float, quoted: str, mode: str = 'round') -> bool:
    """True if value, rounded (or rounded up in magnitude, mode 'ceil') to the quoted digits, gives the quoted string."""
    s = quoted.replace('−', '-').replace(',', '').replace('+', '').strip()
    q = Decimal(s); v = Decimal(repr(float(value)))
    e = Decimal(1).scaleb(q.as_tuple().exponent)
    if mode == 'ceil':
        r = abs(v).quantize(e, rounding=ROUND_CEILING).copy_sign(v)
        return r == q
    if mode == 'floor':
        return abs(v).quantize(e, rounding=ROUND_FLOOR).copy_sign(v) == q
    return v.quantize(e, rounding=ROUND_HALF_EVEN) == q or v.quantize(e, rounding=ROUND_HALF_UP) == q


def quoted(name, value, text, where, mode='round', lenient=''):
    """lenient: a known last-digit slip of the source text; within one unit of the last quoted digit it is a WARN."""
    ok = rounds_to(value, text, mode)
    st = 'PASS' if ok else 'FAIL'
    if not ok and lenient:
        qd = Decimal(text.replace('+', '')); unit = Decimal(1).scaleb(qd.as_tuple().exponent)
        if abs(Decimal(repr(float(value))) - qd) <= unit:
            st = 'WARN'; where = where + '; ' + lenient
    add('quoted', name, st, repr(float(value)), text, mode + ' to quoted digits', where)
    return ok


def summary(m, c):
    import numpy as np
    return {'mean': list(map(float, m)), 'sampling_se': np.sqrt(np.maximum(0, np.diag(c))).tolist(), 'covariance': c.tolist()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--results', type=Path, default=Path('../../results/C7_1'))
    ap.add_argument('--v1', type=Path, default=None, help='default: <results>/v1_46batches')
    ap.add_argument('--c6', type=Path, default=Path('../../results/C6_1/C6_final.json'),
                    help='optional C6(1) record for the cross-check constant (SKIP if absent)')
    ap.add_argument('--work', type=Path, default=Path('.work'))
    a = ap.parse_args()
    import numpy as np
    from assemble import REFS, ceil_2sf
    from production import specs
    from campaign import inventory
    R = a.results.resolve(); V1 = (a.v1 or a.results / 'v1_46batches').resolve(); W = a.work.resolve(); W.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- A. integrity
    G = 'A integrity'
    sums = [l.split(None, 1) for l in (PKG / 'SHA256SUMS').read_text().splitlines() if l.strip()]
    ok = bad = miss = warn = 0; bad_list = []; warn_list = []
    for h, p in sums:
        p = p.strip().lstrip('*'); p = p[2:] if p.startswith('./') else p
        if p.startswith('results/2026-09_expanse_v2/'):
            f = R / p.split('/', 2)[2]; bound = f.name in BOUND_RESULTS
        elif p.startswith('results/2026-09_expanse/'):
            f = V1 / p.split('/', 2)[2]; bound = f.name in ('C7_final.json', 'pilot_C7_result.json', 'archive_original.json')
            if not f.is_file() and f.name in ('design_v1.json', 'design_v1_meta.json'):
                f = R / f.name  # byte-identical to the final folder's copies (same sha256 in SHA256SUMS)
        else:
            f = PKG / p; bound = p.startswith(BOUND_PREFIXES)
        if not f.is_file():
            miss += 1; continue
        if sha(f) == h:
            ok += 1
        elif bound:
            bad += 1; bad_list.append(p)
        else:
            warn += 1; warn_list.append(p)
    add(G, 'package SHA256SUMS (results lines mapped to results/C7_1)', 'FAIL' if bad else ('WARN' if warn else 'PASS'),
        f'{ok} OK, {miss} not shipped, {warn} scrub-eligible differ, {bad} bound differ', f'{len(sums)} lines', 'sha256 exact',
        '; '.join(bad_list[:5] + warn_list[:5]))
    ref_lines = [l.split(None, 1) for l in (PKG / 'reference/SHA256SUMS').read_text().splitlines() if l.strip()]
    rgone = [p.strip().lstrip('*') for h, p in ref_lines if p.strip().lstrip('*') in MERGED_NOTES
             and not (PKG / 'reference' / p.strip().lstrip('*')).is_file()]
    rbad = [p.strip() for h, p in ref_lines if p.strip().lstrip('*') not in rgone and
            (not (PKG / 'reference' / p.strip().lstrip('*')).is_file() or sha(PKG / 'reference' / p.strip().lstrip('*')) != h)]
    add(G, 'reference/SHA256SUMS (authenticated archive used by tools/assemble.py)', 'FAIL' if rbad else 'PASS',
        f'{len(ref_lines) - len(rbad) - len(rgone)} OK, {len(rgone)} merged notes not shipped', f'{len(ref_lines)} lines',
        'sha256 exact; absent allowed only for MERGED_NOTES', '; '.join(rbad[:5]))
    fin = load(R / 'C7_final.json'); ca = load(R / 'combined_assembly.json')
    amap_p = PKG / 'reference/verification/full_affine_assembly.json'
    exact(G, 'affine map sha256 = C7_final.affine_map.sha256', sha(amap_p), fin['affine_map']['sha256'],
          'the batches carry byte-identical copies (production.py copies this file)')
    inv_p = PKG / 'reference/inputs/L7_coord.txt'
    exact(G, 'L7 inventory sha256 = C7_final.primitive_guard.sha256', sha(inv_p), fin['primitive_guard']['sha256'])
    rows7 = inventory(PKG / 'reference/inputs', 7)
    exact(G, 'primitive classes (primitive && !power) in L7 inventory', sum(1 for r in rows7 if r['primitive'] and not r['power']),
          fin['primitive_guard']['primitive_classes'])
    pr = (R / 'production_run.json').read_text()
    dsha = sha(R / 'design_v1.json')
    exact(G, 'design_v1.json sha256 prefix as recorded in production_run.json', dsha[:8] in pr and dsha.startswith('fd356a15'), True,
          'full: ' + dsha)
    meta = load(R / 'design_v1_meta.json')
    exact(G, 'design_v1_meta.json names its pilot result and archive reassembly by sha256 (shipped in v1_46batches/)',
          (meta['pilot_result_sha256'], meta['archive_sha256']),
          tuple(sha(V1 / f) if (V1 / f).is_file() else 'missing' for f in ('pilot_C7_result.json', 'archive_original.json')))

    # ---------------------------------------------------------------- B. structure of the combination
    G = 'B structure'
    labels = [b['label'] for b in ca['batches']]
    want = [f'b{i:03d}' for i in range(1, 401) if i != 215]
    exact(G, 'included batches: b001-b400 except b215 (inclusion.txt)', labels, want)
    exact(G, 'inclusion.txt names b215 as the only exclusion', 'excluded: b215' in (R / 'inclusion.txt').read_text(), True)
    exact(G, 'batch count in C7_final', fin['batches']['count'], K_EXPECTED)
    seeds = [int.from_bytes(hashlib.sha256(BATCH_SEED.format(k=int(l[1:])).encode()).digest()[:8], 'little') for l in labels]
    exact(G, 'batch seeds = first 8 bytes (LE) of sha256("C7-expanse-2026-09:batch:k")', [b['seed'] for b in ca['batches']], seeds)
    comps = fin['components']; names = [s['name'] for s in fin['sources']]
    exact(G, 'sources = 399 x 24 campaigns + primitive/P1', names,
          [f'{l}/{c}' for l in labels for c in CAMPAIGNS] + ['primitive/P1'])
    exact(G, 'components and sources list the same names', list(comps), names)
    exact(G, 'source paths/sha256 equal in sources and components',
          all({k: comps[s['name']].get(k) for k in s if k != 'name'} == {k: v for k, v in s.items() if k != 'name'} for s in fin['sources']), True)
    sp = {s['name']: s for s in specs(True)}
    wexp = {f'{l}/{c}': sp[c]['weight'] / K_EXPECTED for l in labels for c in CAMPAIGNS}; wexp['primitive/P1'] = 1
    exact(G, 'combined weights = production.specs weight / 399 (primitive 1)', {s['name']: s['weight'] for s in ca['sources']}, wexp)
    lvl = {f'{l}/{c}': (sp[c]['level'], sp[c]['role'], sp[c]['L']) for l in labels for c in CAMPAIGNS}; lvl['primitive/P1'] = ('primitive', 'estimator', 7)
    exact(G, 'levels, roles and loop orders = production.specs', {n: (comps[n]['level'], comps[n]['role'], comps[n]['L']) for n in names}, lvl)
    exact(G, 'combined_assembly paths = C7_final paths', [(s['name'], s['path'], s.get('subtract')) for s in ca['sources']],
          [(s['name'], s['path'], s.get('subtract')) for s in fin['sources']])
    rep = {}
    for n in names[:-1]:
        rep.setdefault(n.split('/', 1)[1], set()).add(comps[n]['replicates'])
    exact(G, 'replicates per campaign (note: 128; 128/64; 128,128,64; check 64)', {c: sorted(v) for c, v in rep.items()},
          {c: [REPLICATES[c]] for c in CAMPAIGNS})
    exact(G, 'direct primitive: 64 replicates, unit weight, free kind', (comps['primitive/P1']['replicates'], comps['primitive/P1']['weight'],
          comps['primitive/P1']['kind']), (64, 1, 'free'))
    exact(G, 'retained primitive replaced (retained_primitive = null)', fin['retained_primitive'], None)
    se_ok = all(np.array_equal(np.sqrt(np.maximum(0, np.diag(np.array(comps[n]['covariance'])))), np.array(comps[n]['sampling_se'])) for n in names)
    exact(G, 'component sampling_se = sqrt(diag covariance) (bitwise)', se_ok, True)
    nres = len([l for l in (R / 'resubmitted_elements.txt').read_text().splitlines() if l.strip()])
    exact(G, 'transient element failures resubmitted (REPORT: 17)', nres, 17)

    # ---------------------------------------------------------------- C. estimator from the components (assemble.py order)
    G = 'C estimator'
    K = np.array(load(amap_p)['K'], dtype=float)
    mean = K.copy(); cov = np.zeros((8, 8)); levels: dict = {}; checks: dict = {}
    for n in names:
        c = comps[n]; m = np.array(c['mean'], dtype=float); C = np.array(c['covariance'], dtype=float)
        if c['role'] == 'check':
            checks.setdefault(c['level'], []).append((m, C)); continue
        mean += m; cov += C; levels.setdefault(c['level'], []).append((m, C))
    prim = fin['retained_primitive']; pm = prim['mean'] if prim else 0.; pse = prim['sampling_se'] if prim else 0.
    mean[7] += pm; cov[7, 7] += pse ** 2
    SE = float(np.sqrt(cov[7, 7]))
    close(G, 'C7_full', mean[7], fin['C7_full'])
    close(G, 'sampling_se', SE, fin['sampling_se'])
    close(G, 'coefficients C0..C7', mean, fin['coefficients'])
    close(G, 'covariance (8x8)', cov, fin['covariance'])
    lv = {k: summary(sum(x[0] for x in v), sum(x[1] for x in v)) for k, v in levels.items()}
    ck = {k: summary(sum(x[0] for x in v), sum(x[1] for x in v)) for k, v in checks.items()}
    for k in ('coarse', 'refine3', 'refine5', 'refine6'):
        close(G, f'power level {k} (mean, SE)', lv[k]['mean'] + lv[k]['sampling_se'], fin['power_levels'][k]['mean'] + fin['power_levels'][k]['sampling_se'])
    close(G, 'free level (mean, SE)', lv['free']['mean'] + lv['free']['sampling_se'], fin['free_level']['mean'] + fin['free_level']['sampling_se'])
    close(G, 'check level refine7 (mean, SE)', ck['refine7']['mean'] + ck['refine7']['sampling_se'],
          fin['check_levels']['refine7']['mean'] + fin['check_levels']['refine7']['sampling_se'])
    close(G, 'primitive source (mean, SE)', [lv['primitive']['mean'][7], lv['primitive']['sampling_se'][7]],
          [fin['primitive_source']['mean_C7'], fin['primitive_source']['sampling_se_C7']])
    prefix = K.copy(); prefix[7] += pm; pc = np.zeros((8, 8)); pc[7, 7] = pse ** 2
    for k in ('free', 'primitive'):
        prefix += np.array(lv[k]['mean']); pc += np.array(lv[k]['covariance'])
    res = []
    for k, N in (('coarse', 1), ('refine3', 3), ('refine5', 5), ('refine6', 6)):
        prefix += np.array(lv[k]['mean']); pc += np.array(lv[k]['covariance']); res.append((N, summary(prefix, pc)))
    for (N, s), r in zip(res, fin['resolution_sequence']):
        close(G, f'resolution sequence, degree {N} (mean, SE)', s['mean'] + s['sampling_se'], r['mean'] + r['sampling_se'])
    lo = []
    for n in (3, 4, 5, 6):
        se = float(np.sqrt(cov[n, n])); lo.append((n, float(mean[n]), se, (float(mean[n]) - REFS[n]) / se if se > 0 else None))
    for (n, v, se, z), r in zip(lo, fin['lower_order_checks']):
        exact(G, f'lower-order check C{n}: reference', REFS[n], r['reference'])
        close(G, f'lower-order check C{n}: value, SE' + (', z' if z is not None else ''), [v, se] + ([z] if z is not None else []),
              [r['value'], r['sampling_se']] + ([r['difference_over_sampling_se']] if z is not None else []))
    halves = fin['half_splits']
    half_shift = max(abs(h[7] - mean[7]) for h in halves)
    cand = {'4SE': 4 * SE, 'half_split_shift': half_shift,
            'refine6': 2 * abs(lv['refine6']['mean'][7]) + 4 * lv['refine6']['sampling_se'][7],
            'refine7': 2 * abs(ck['refine7']['mean'][7]) + 4 * ck['refine7']['sampling_se'][7]}
    for k, v in cand.items():
        close(G, f'allowance candidate {k}', v, fin['allowance']['candidates'][k], note='half-split values RECORDED' if k == 'half_split_shift' else '')
    head = ceil_2sf(max(cand.values()) + .01); arch = float(math.ceil((max(cand[k] for k in ('4SE', 'refine6', 'half_split_shift')) + .01) / 1000) * 1000)
    exact(G, 'allowance headline_2sf (pre-registered policy)', head, fin['allowance']['headline_2sf'])
    exact(G, 'allowance archived_ceil1000', arch, fin['allowance']['archived_ceil1000'])
    flags = [f'systematic tension: C{n} differs from its reference by {z:.2f} SE' for n, v, se, z in lo if n in (5, 6) and z is not None and abs(z) > 3]
    exact(G, 'flags', flags, fin['flags'])
    rc = ca['retained_primitive_crosscheck']
    zprim = (lv['primitive']['mean'][7] - rc['mean']) / math.hypot(lv['primitive']['sampling_se'][7], rc['sampling_se'])
    close(G, 'direct vs retained primitive z', zprim, fin['retained_primitive_crosscheck']['z'])
    exact(G, 'retained primitive = archive C7_assembled_result.json', (rc['mean'], rc['sampling_se']),
          tuple((lambda p: (p['mean_C7'], p['sampling_se']))(load(PKG / 'reference/verification/C7_assembled_result.json')['components']['retained_primitive'])))
    agg = {}
    for n in names:
        v = comps[n]; g = agg.setdefault(v['campaign'], {'n': 0, 'm': np.zeros(8), 'c': np.zeros((8, 8))})
        g['n'] += 1; g['m'] = g['m'] + np.array(v['mean']); g['c'] = g['c'] + np.array(v['covariance'])
    close(G, 'campaign aggregates (mean_C7, SE_C7, 25 campaigns)', [x for k in agg for x in (agg[k]['m'][7], math.sqrt(max(0, agg[k]['c'][7, 7])))],
          [x for k in agg for x in (fin['campaign_aggregates'][k]['mean_C7'], fin['campaign_aggregates'][k]['sampling_se_C7'])])
    exact(G, 'campaign aggregate source counts', {k: g['n'] for k, g in agg.items()}, {k: g['sources'] for k, g in fin['campaign_aggregates'].items()})
    zab = max(abs(agg[f'tprodA_L{L}']['m'][7] - agg[f'tprodB_L{L}']['m'][7]) / math.sqrt(agg[f'tprodA_L{L}']['c'][7, 7] + agg[f'tprodB_L{L}']['c'][7, 7]) for L in (5, 6, 7))

    # per-batch values (combine.py: assemble() of each batch's own assembly.json, with the retained primitive)
    per = fin['batches']['per_batch']
    exact(G, 'per-batch labels', [x['label'] for x in per], labels)
    rm, rs = rc['mean'], rc['sampling_se']
    pb = []
    for l in labels:
        mb = K.copy(); cb = 0.0
        for c in CAMPAIGNS:
            v = comps[f'{l}/{c}']
            if v['role'] != 'estimator':
                continue
            mb = mb + K_EXPECTED * np.array(v['mean']); cb += K_EXPECTED ** 2 * v['covariance'][7][7]
        pb.append((float(mb[7] + rm), math.sqrt(cb + rs ** 2)))
    close(G, 'per-batch C7 (399 values, from components x 399 + retained primitive)', [x[0] for x in pb], [x['C7_full'] for x in per], rtol=1e-12)
    close(G, 'per-batch SE (399 values)', [x[1] for x in pb], [x['sampling_se'] for x in per], rtol=1e-10)
    centre = mean[7] - (lv['primitive']['mean'][7] - rm)
    close(G, 'chi2 centre (C7 with the retained primitive)', centre, fin['batches']['chi2_centre'])
    chi2_rec = sum((x['C7_full'] - centre) ** 2 / (x['sampling_se'] ** 2 - rs ** 2) for x in per)
    chi2_new = sum((x[0] - centre) ** 2 / (x[1] ** 2 - rs ** 2) for x in pb)
    close(G, 'inter-batch chi2 from the recorded per-batch values', chi2_rec, fin['batches']['chi2_about_combined'])
    close(G, 'inter-batch chi2 from the recomputed per-batch values', chi2_new, fin['batches']['chi2_about_combined'], rtol=1e-9)
    exact(G, 'chi2 degrees of freedom', fin['batches']['dof'], K_EXPECTED - 1)

    # ---------------------------------------------------------------- D. recorded only (Tier 2 recomputes from raw streams)
    G = 'D recorded'
    add(G, 'bootstrap SE (4096 replicate resamples within every source stream, seed 718395)', 'RECORDED',
        fin['bootstrap_se'], '', '', 'Tier 2 recomputes; note: it is a replicate bootstrap, not a bootstrap over batches')
    add(G, 'half-split estimates (first/second half of the replicates of every stream)', 'RECORDED', [round(h[7], 2) for h in halves], '', '', 'Tier 2 recomputes')
    poles = fin['spurious_pole_checks']
    exact(G, 'spurious-pole columns monitored', len(poles), 24)
    close(G, 'spurious-pole z = mean/SE (24 values)', [p['mean'] / p['sampling_se'] for p in poles], [p['z_score'] for p in poles], note='means RECORDED')
    zp = fin['zero_pole_control']
    tm = sum(np.array(v['mean']) for v in zp['per_L'].values()); tc = sum(np.array(v['covariance']) for v in zp['per_L'].values())
    close(G, 'zero-pole control total = sum over L (mean, SE)', list(tm) + list(np.sqrt(np.maximum(0, np.diag(tc)))),
          zp['total']['mean'] + zp['total']['sampling_se'], note='per-L terms RECORDED')
    close(G, 'applied control = raw uncontrolled - C7_full', fin['raw_uncontrolled_C7'] - fin['C7_full'], fin['applied_zero_pole_control_C7'])
    close(G, 'applied control = control total (C7 slot)', zp['total']['mean'][7], fin['applied_zero_pole_control_C7'], rtol=0, atol=1e-6)
    exact(G, 'raw_uncontrolled.coefficients[7] = raw_uncontrolled_C7', fin['raw_uncontrolled']['coefficients'][7], fin['raw_uncontrolled_C7'])

    # ---------------------------------------------------------------- E. post hoc truncation analysis (REPORT, note Sec. C7(1))
    R6, S6 = np.array(lv['refine6']['mean']), np.array(lv['refine6']['sampling_se'])
    R7, S7 = np.array(ck['refine7']['mean']), np.array(ck['refine7']['sampling_se'])
    tail = {}; E7 = {}; Einf = {}; ratio = {}
    for n in (5, 6, 7):
        ratio[n] = R7[n] / R6[n]; tail[n] = R7[n] * ratio[n] / (1 - ratio[n]); E7[n] = mean[n] + R7[n]; Einf[n] = E7[n] + tail[n]
    sig = math.sqrt(SE ** 2 + S7[7] ** 2 + tail[7] ** 2)
    se5, se6 = math.sqrt(cov[5, 5]), math.sqrt(cov[6, 6])
    z5 = [(x - REFS[5]) / se5 for x in (mean[5], E7[5], Einf[5])]
    z6new = [(x - C6_EXACT) / se6 for x in (mean[6], E7[6], Einf[6])]
    z6old = [(x - REFS[6]) / se6 for x in (mean[6], E7[6], Einf[6])]
    z6oldc = [(x - REFS[6]) / math.hypot(se6, C6_OLD_SE) for x in (mean[6], E7[6], Einf[6])]
    c6p = a.c6
    if c6p.is_file():
        exact('E post hoc', 'C6(1) reference constant = results/C6_1/C6_final.json headline.C6', str(C6_EXACT), load(c6p)['headline']['C6'])
    else:
        add('E post hoc', 'C6(1) reference constant 14331.68703277', 'SKIP', '', str(c6p), '', 'C6_1 record absent; pinned value used')

    # ---------------------------------------------------------------- F. archive (assemble.py --original) and v1
    G = 'F archive, v1'
    out = W / 'archived_C7.json'
    if out.exists():
        out.unlink()
    env = {**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
    pr_ = subprocess.run([sys.executable, str(PKG / 'tools/assemble.py'), '--original', '--output', str(out)], capture_output=True, text=True, env=env)
    if pr_.returncode or not out.is_file():
        add(G, 'tools/assemble.py --original', 'FAIL', pr_.returncode, 0, '', pr_.stderr[-300:]); arc = None
    else:
        arc = load(out); acc = load(PKG / 'reference/verification/C7_assembled_result.json')
        close(G, 'archived reassembly C7_full, SE vs reference/verification/C7_assembled_result.json',
              [arc['C7_full'], arc['sampling_se']], [acc['C7_full'], acc['sampling_se']])
        exact(G, 'archived allowance (ceil to 1000)', arc['allowance']['archived_ceil1000'], acc['empirical_allowance'])
        fx = load(PKG / 'tests/fixtures/assemble_original_0227dc5.json')
        keys = [k for k in fx if k not in ('primitive_guard',)]
        same = {k: arc.get(k) == fx[k] for k in keys}
        diff = [k for k, v in same.items() if not v]
        flo = []

        def walk(x, y, at):
            if isinstance(x, dict) and isinstance(y, dict):
                if set(x) != set(y): flo.append((at, 'keys'))
                for k in set(x) & set(y): walk(x[k], y[k], at + '.' + k)
            elif isinstance(x, list) and isinstance(y, list):
                if len(x) != len(y): flo.append((at, 'len'))
                for i, (p, q) in enumerate(zip(x, y)): walk(p, q, at)
            elif isinstance(x, float) or isinstance(y, float):
                if not rel_ok(float(x), float(y), 1e-12, 1e-12 * 0): flo.append((at, x, y))
            elif x != y:
                flo.append((at, x, y))
        for k in diff:
            walk(arc[k], fx[k], k)
        boot_only = all(at in ('bootstrap_se',) for at, *_ in flo)
        st = 'PASS' if not diff else ('PASS' if not flo else ('WARN' if boot_only else 'FAIL'))
        add(G, 'archived reassembly = committed fixture (0227dc5) apart from the PLAN2 keys', st, f'{len(keys) - len(diff)}/{len(keys)} keys identical',
            'tests/fixtures/assemble_original_0227dc5.json', 'exact; floats rel 1e-12', 'new keys primitive_source, retained_primitive_crosscheck; primitive_classes 64 -> 44'
            + ('; differing: ' + ', '.join(sorted({f[0] for f in flo}))[:200] if flo else ''))
        exact(G, 'archived primitive_guard.primitive_classes (PLAN2: 44)', arc['primitive_guard']['primitive_classes'], 44)
    v1 = load(V1 / 'C7_final.json') if (V1 / 'C7_final.json').is_file() else None
    if v1 is None:
        add(G, 'v1 (46 batches) record', 'FAIL', 'missing', str(V1 / 'C7_final.json'))

    # ---------------------------------------------------------------- G. inherited construction checks (reference/)
    G = 'G inherited'
    inv = {}
    for L in (5, 6, 7):
        rows = rows7 if L == 7 else inventory(PKG / 'reference/inputs', L)
        zf = PKG / f'reference/inputs/exact_zero_L{L}.txt'
        zz = set(list(map(int, zf.read_text().split()))[1:]) if zf.exists() else set()
        pw = [r for r in rows if r['power']]
        nz = [r for r in pw if abs(3 * Decimal(r['wb']) - Decimal(r['wa'])) >= Decimal('1e-17')] if L == 7 else pw
        inv[L] = {'classes': len(rows), 'power': len(pw), 'primitive': sum(1 for r in rows if r['primitive'] and not r['power']),
                  'zeros': len(zz), 'power_nonzero_channel': len(nz), 'power_nonzero_exact_zero': sum(1 for r in nz if r['id'] in zz),
                  'power_integrated': sum(1 for r in nz if r['id'] not in zz)}
    exact(G, 'L7 inventory: classes, power, nonzero 3c7-b7, of them exact zeros, integrated, all exact zeros, primitive',
          [inv[7][k] for k in ('classes', 'power', 'power_nonzero_channel', 'power_nonzero_exact_zero', 'power_integrated', 'zeros', 'primitive')],
          [3986, 1091, 845, 151, 694, 691, 44])
    exact(G, 'L5, L6 power classes remaining after the exact-zero test', [inv[5]['power_integrated'], inv[6]['power_integrated']], [24, 132])
    li = (PKG / 'reference/inputs/L7_inventory.txt').read_text().splitlines(); n7 = int(li[0].split()[1])
    hdr = [list(map(int, li[1 + 3 * i].split())) for i in range(n7)]
    exact(G, 'labelled 1PI graphs = sum 8!/|Aut| over the 3986 classes', (sum(h[3] for h in hdr), all(h[2] * h[3] == 40320 for h in hdr)), (125894580, True))
    fe = load(PKG / 'reference/verification/forest_exact_checks_new.json')['checks']
    exact(G, 'forest identities: coupling/mass monomials L=1..7, zero differences',
          [(c['L'], c['beta_monomials'], c['gamma_monomials'], c['beta_difference_zero'] and c['gamma_difference_zero']) for c in fe],
          [(1, 1, 1, True), (2, 2, 2, True), (3, 8, 6, True), (4, 29, 25, True), (5, 134, 103, True), (6, 696, 525, True), (7, 4164, 2935, True)])
    pc_ = load(PKG / 'reference/verification/primitive_coverage_new.json')
    exact(G, 'primitive coverage: 44 classes matched to 14 periods, weights equal', (pc_['primitive_classes'], pc_['completed_periods'],
          pc_['all_period_weights_match_exactly']), (44, 14, True))
    at = load(PKG / 'reference/verification/affine_and_tree_exact_checks.json')
    exact(G, 'exact rational tests: 32 fixed-point/affine trials, 84 Jacobians, Z=(L+1)!L for L=1..7',
          (sum(1 for t in at['assembly'] if t['fixed_equals_lagrange'] and t['high_loop_affine']), sum(1 for j in at['jacobians'] if j['jacobian_exact']),
           [int(z['Z']) == z['factorial_times_L'] == math.factorial(z['vertices']) * (z['vertices'] - 1) for z in at['constant_measure_normalization']]),
          (32, 84, [True] * 7))
    tp = load(PKG / 'reference/verification/tree_point_checks.json')
    exact(G, 'tree point checks: 650 digits, 60 cases', (tp['working_digits'], len(tp['checks'])), (650, 60))
    lr = load(PKG / 'reference/verification/lower_resolution_check.json')
    d16 = [r for r in lr['rows'] if r['N'] == 16][0]['difference_from_tree_N20_C0_to_C7'][7]
    exact(G, 'four-loop degree 16 -> 20 moves C7 by less than 0.001', abs(d16) < 1e-3, True, f'{d16:.3g}')
    # The superseded C6(1) numbers cited by the REPORT (degree-6 and hybrid span values, the hybrid estimate and its SE)
    # were quoted from reference/long_range_ising_complete.tex, which is merged into the condensed note and not shipped.
    # Their records are in the sibling package LRI_C6_1D_HPC/reference/.
    c6ref = PKG.parent / 'LRI_C6_1D_HPC/reference'
    c6o = load(c6ref / 'C6_result_original.json'); c6s = load(c6ref / 'C6_stratified_analysis.json')
    exact(G, 'cited superseded C6 numbers (degree 6 span, hybrid span, hybrid estimate, its SE) in LRI_C6_1D_HPC/reference',
          (f"{c6s['C6_baseline_N6'][1]:.5f}", f"{c6o['raw_cutoff_estimates']['span']:.5f}",
           f"{c6o['underlying_control_estimate']:.8f}", f"{c6o['estimated_sampling_standard_error']:.5f}"),
          ('14332.55449', '14331.75512', '14331.77074705', '0.14344'))
    nm = (PKG / 'docs/NUMERICS.md').read_text()
    exact(G, 'per-element binary128 replay (112 elements) as recorded in docs/NUMERICS.md',
          all(s in nm for s in ('112 elements', '2.8e-12', '1.9e-11', '4.2e-14')), True, 'cited; rerun: tests/check_quad.py on a cluster node')

    # ---------------------------------------------------------------- quoted numbers (note at fa71533, REPORT.md at 68dc6be)
    N = 'note'; P = 'REPORT'
    q = quoted
    q('C7 rounded', mean[7], '-322550', f'{N} abstract, Sec 1, eq c7f:answer; {P}')
    q('allowance', head, '41', f'{N} abstract, Sec 1, eq c7f:answer; {P}')
    q('estimator (16 digits)', mean[7], '-322549.8888129889', f'{N} Sec 1 table')
    q('sampling SE (10 digits)', SE, '10.08791295', f'{N} Sec 1 table')
    q('estimator', mean[7], '-322549.889', f'{N} c7f')
    q('sampling SE', SE, '10.088', f'{N} c7f')
    q('sampling SE (4 s.f.)', SE, '10.09', f'{N} c7f; {P}')
    q('estimator (1 decimal)', mean[7], '-322549.9', f'{P}; {N} Sec 30 table')
    q('SE (1 decimal)', SE, '10.1', f'{N} Sec 30 table')
    q('bootstrap SE (recorded)', fin['bootstrap_se'], '10.111', f'{N} c7f')
    q('bootstrap SE 2 decimals (recorded)', fin['bootstrap_se'], '10.11', f'{N} c7f; {P}')
    q('step 6->7', R7[7], '10.40', f'{N} c7f; {P}'); q('step 6->7 SE', S7[7], '0.43', f'{N}; {P}')
    q('step 6->7 (3 decimals)', R7[7], '10.395', P); q('step 5->6 (3 decimals)', R6[7], '17.329', P)
    q('tail beyond 7', tail[7], '15.59', f'{N} c7f; {P}'); q('tail ratio C7', ratio[7], '0.600', f'{N}; {P}')
    q('truncation-aware estimate', Einf[7], '-322524', f'{N} Sec 1, eq c7f:truncationAware; {P}')
    q('truncation-aware value (1 decimal)', Einf[7], '-322523.9', f'{N} c7f:checks table; {P}')
    q('E7 = estimate + step', E7[7], '-322539.5', f'{N}; {P}')
    q('combined 1-sigma 10.09+0.43+15.59 in quadrature', sig, '18.6', f'{N}; {P}')
    q('truncation-aware allowance 2 x 18.6, rounded up', ceil_2sf(2 * sig), '38', f'{N} Sec 1, c7f:truncationAware; {P}', 'ceil')
    q('modelled shift step + tail', R7[7] + tail[7], '26', P)
    q('shift + 2 SE', R7[7] + tail[7] + 2 * SE, '46', P)
    q('pre-registered interval low', mean[7] - head, '-322591', P); q('pre-registered interval high', mean[7] + head, '-322509', P)
    q('truncation-aware interval low', Einf[7] - 38, '-322562', P); q('truncation-aware interval high', Einf[7] + 38, '-322486', P)
    q('direct primitive', lv['primitive']['mean'][7], '-696179.472', N); q('direct primitive SE', lv['primitive']['sampling_se'][7], '0.867', N)
    q('direct primitive (2 decimals)', lv['primitive']['mean'][7], '-696179.47', P); q('direct primitive SE (2 decimals)', lv['primitive']['sampling_se'][7], '0.87', P)
    q('direct primitive variance SE', lv['primitive']['sampling_se'][7], '0.8667', f'{N} assembly')
    q('retained primitive', rm, '-696147.446', N); q('retained primitive SE', rs, '25.368', N); q('retained primitive SE (2 dec.)', rs, '25.37', P)
    q('primitive agreement |z|', abs(zprim), '1.26', f'{N}; {P} (z = -1.26)')
    for (N_, s), txt, stx, t2, s2 in zip(res, ('-331309.98', '-322614.21', '-322567.22', '-322549.89'), ('6.14', '9.21', '10.01', '10.09'),
                                         ('-331310.0', '-322614.2', '-322567.2', '-322549.9'), ('6.1', '9.2', '10.0', '10.1')):
        q(f'resolution degree {N_}', s['mean'][7], txt, f'{N} table'); q(f'resolution degree {N_} SE', s['sampling_se'][7], stx, f'{N} table')
        q(f'resolution degree {N_} (REPORT)', s['mean'][7], t2, P); q(f'resolution degree {N_} SE (REPORT)', s['sampling_se'][7], s2, P)
    for k, txt, stx in (('refine3', '8695.78', '6.86'), ('refine5', '46.99', '3.93'), ('refine6', '17.33', '1.21')):
        q(f'correction {k}', lv[k]['mean'][7], txt, f'{N} table'); q(f'correction {k} SE', lv[k]['sampling_se'][7], stx, f'{N} table')
    q('step ratio 5->6 / 3->5', R6[7] / lv['refine5']['mean'][7], '0.37', N); q('step ratio 6->7 / 5->6', ratio[7], '0.60', f'{N}; {P}')
    for k, txt in (('4SE', '40.35'), ('refine6', '39.50'), ('refine7', '22.49'), ('half_split_shift', '12.58')):
        q(f'allowance candidate {k}', cand[k], txt, N)
    for k, txt in (('4SE', '40.4'), ('refine6', '39.5'), ('refine7', '22.5'), ('half_split_shift', '12.6')):
        q(f'allowance candidate {k} (REPORT)', cand[k], txt, P)
    q('archived-policy allowance', arch, '1000', P)
    q('chi2', chi2_new, '348.9', f'{N}; {P}')
    q('half split 1 (recorded)', halves[0][7], '-322537.30', N); q('half split 2 (recorded)', halves[1][7], '-322562.47', N)
    q('A/B power-free agreement, max over L (in combined SE)', zab, '0.42', N + ' ("to within 0.42"; the maximum is 0.422, rounded)')
    q('max |z| spurious poles (recorded means)', max(abs(p['z_score']) for p in poles), '2.31', f'{N}; {P}')
    q('zero-pole control, uncontrolled minus controlled (recorded; the note: estimate 71.6 above the uncontrolled)', zp['total']['mean'][7], '-71.6', f'{N}; {P}'); q('zero-pole control SE (recorded)', zp['total']['sampling_se'][7], '41.0', f'{N}; {P}')
    q('uncontrolled estimator (recorded)', fin['raw_uncontrolled_C7'], '-322621.5', f'{N}; {P}')
    q('uncontrolled SE (recorded)', fin['raw_uncontrolled']['sampling_se'], '41.1', f'{N}; {P}')
    q('C5 degree 6', mean[5], '-731.174185', N); q('C5 SE', se5, '0.008355', N); q('C5 reference (exact)', REFS[5], '-731.139477', N)
    q('C6 degree 6', mean[6], '14332.435930', N); q('C6 SE', se6, '0.305002', N); q('C6 reference (deterministic)', C6_EXACT, '14331.687033', N)
    q('C5 degree 6 (REPORT)', mean[5], '-731.17419', P); q('C5 SE (REPORT)', se5, '0.00836', P)
    q('C6 degree 6 (5 decimals)', mean[6], '14332.43593', f'{N} Sec 22; {P}'); q('C6 SE (5 decimals)', se6, '0.30500', f'{N} Sec 22; {P}')
    for lab, zs, txts in (('C5 z vs exact', z5, ('-4.15', '-1.88', '-0.30')), ('C6 z vs new exact C6', z6new, ('2.46', '0.97', '-0.22')),
                          ('C6 z vs old reference, own SE', z6old, ('2.18', '0.69', '-0.49')), ('C6 z vs old reference, combined SE', z6oldc, ('1.97', '0.63', '-0.45'))):
        for stage, z, t in zip(('degree 6', '+ step', '+ tail'), zs, txts):
            q(f'{lab}, {stage}', z, t, f'{N} c7f:checks, Sec 22; {P}' if 'new' in lab or 'C5' in lab else P)
    for n, t7, ti in ((5, '-731.15515', '-731.14201'), (6, '14331.98210', '14331.62055')):
        q(f'C{n} + step', E7[n], t7, f'{P}; {N} Sec 22' if n == 6 else P); q(f'C{n} + tail', Einf[n], ti, f'{P}; {N} Sec 22' if n == 6 else P)
    q('tail ratio C5', ratio[5], '0.408', f'{N}; {P}'); q('tail ratio C6', ratio[6], '0.443', f'{N}; {P}')
    q('C6 truncation correction', Einf[6] - mean[6], '-0.815', P)
    q('reference C6 degree-6 -> hybrid change, span, then -0.007', (14331.75512 - 14332.55449) - 0.007, '-0.81', P + ' (cited from reference tex)')
    q('C6 degree 6 minus new exact C6', mean[6] - C6_EXACT, '0.74890', f'{P} addendum'); q('C6 + step minus new exact C6', E7[6] - C6_EXACT, '0.29507', f'{P} addendum')
    q('C6 + tail minus new exact C6', Einf[6] - C6_EXACT, '-0.06648', f'{P} addendum', lenient='REPORT truncates -0.066486 to -0.06648 (rounded: -0.06649)')
    q('C3 deterministic', mean[3], '-3.71985632290349', N); q('C4 deterministic', mean[4], '45.4248801371166', N)
    q('C3 discrepancy from retained value', abs(mean[3] - REFS[3]), '1.5e-12', N); q('C4 discrepancy', abs(mean[4] - REFS[4]), '3.4e-8', N)
    q('tree points: max normalized discrepancy (rounded up)', float(Decimal(tp['maximum_normalized_error'])), '1.18e-14', N, 'ceil')
    q('tree points: extreme-endpoint subset (rounded up)', float(Decimal(tp['extreme_max_error'])), '3.45e-18', N, 'ceil')
    if arc is not None:
        q('archive estimator', arc['C7_full'], '-323405.3', f'{N} README; {P} (-323405)'); q('archive SE', arc['sampling_se'], '5861.8', f'{N} README')
        q('archive SE (integer)', arc['sampling_se'], '5862', P); q('archive allowance', arc['allowance']['archived_ceil1000'], '24000', P)
        q('archive z = (new - archive)/hypot(SE, SE_archive)', (mean[7] - arc['C7_full']) / math.hypot(SE, arc['sampling_se']), '0.15', f'{P}; {N} README')
    if v1 is not None:
        q('v1 (46 batches) estimator', v1['C7_full'], '-322554', P); q('v1 SE', v1['sampling_se'], '39', P)
        q('v1 allowance', v1['allowance']['headline_2sf'], '160', P)
        q('v1 z = (v2 - v1)/hypot(SE, SE_v1)', (mean[7] - v1['C7_full']) / math.hypot(SE, v1['sampling_se']), '0.11', P + ' (v1 batches are a subset of v2)')
    exact('quoted', 'primitive campaign seed = first 8 bytes (LE) of sha256("C7-expanse-2026-09:primitive")', int.from_bytes(hashlib.sha256(PRIMITIVE_SEED).digest()[:8], 'little'),
          3929792552365635731, 'review log; Tier 2 checks it against the hosted P1 manifest')

    # ---------------------------------------------------------------- report
    nf = sum(r['status'] == 'FAIL' for r in ROWS)
    w = [max(len(r[k]) for r in ROWS) for k in ('group', 'check', 'status')]
    lines = [f"{r['status']:<8} {r['group']:<14} {r['check'][:92]:<92} {r['recomputed'][:26]:>26} | {r['reference'][:26]:<26} [{r['tolerance']}] {r['note']}" for r in ROWS]
    counts = {s: sum(r['status'] == s for r in ROWS) for s in ('PASS', 'FAIL', 'WARN', 'RECORDED', 'SKIP')}
    tail_line = f"C7(1) Tier 1 replay: {len(ROWS)} checks: " + ', '.join(f'{k} {v}' for k, v in counts.items() if v)
    text = '\n'.join(lines + ['', tail_line]) + '\n'
    print(text, end='')
    (W / 'replay7_tier1.txt').write_text(text)
    (W / 'replay7_tier1.json').write_text(json.dumps({'summary': counts, 'rows': ROWS}, indent=1) + '\n')
    return 1 if nf else 0


if __name__ == '__main__':
    sys.exit(main())
