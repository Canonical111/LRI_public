#!/usr/bin/env python3
"""v2 regression report (runs/regress_v2, job of slurm/regress_symmetry.sbatch).

  A  direct_v1 vs direct_v2: every phase-1 output field bit for bit (same cfg, same node, same compiler)
  B  replay5 vs runs/pilot5, replay4 vs runs/pilot4 (stored phase-1 outputs): bit for bit, or pulls where the
     stored output came from an earlier phase-1 binary
  C  replicate errors vs the phase-1 quadrature errors of the same runs (multi-channel moments)
  D  new (hashed seeds) vs pilot5 values: pulls with replicate errors (statistical consistency)
usage: regress_compare.py [--out results/regress_v2_report.txt]
"""
import argparse, glob, json, math, os, re, statistics as st, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RG = os.path.join(ROOT, 'runs', 'regress_v2')
TOP = ('n', 'type', 'geom', 's0', 'etarget', 'lo', 'kappa', 'dF', 'M', 'N', 'shifts', 'transform', 'prec',
       'sectors_total', 'sector_range')
lines = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    lines.append(s)


def cmp_outputs(a, b):
    """-> (identical: bool, n_values, max_rel, max_pull, detail)"""
    diffs = [k for k in TOP if a.get(k) != b.get(k)]
    if diffs:
        return False, 0, float('inf'), float('inf'), f'header differs: {diffs}'
    nval, mrel, mpull, ident = 0, 0.0, 0.0, True
    for c in a['channels']:
        A, B = a['channels'][c], b['channels'][c]
        if A['orders'] != B['orders']:
            return False, 0, float('inf'), float('inf'), 'orders differ'
        pairs = list(zip(A['value'], B['value'], A['err'], B['err']))
        for sa, sb in zip(A.get('per_sector', []), B.get('per_sector', [])):
            if sa['id'] != sb['id'] or sa['Nsub'] != sb['Nsub'] or sa['ord'] != sb['ord']:
                return False, 0, float('inf'), float('inf'), 'sector structure differs'
            pairs += [(x[0], y[0], x[1], y[1]) for x, y in zip(sa['value'], sb['value'])]
        for va, vb, ea, eb in pairs:
            nval += 1
            if va != vb or ea != eb:
                ident = False
                if va != vb:
                    mrel = max(mrel, abs(va - vb) / max(abs(va), abs(vb), 1e-300))
                    s = math.hypot(ea, eb)
                    if s > 0:
                        mpull = max(mpull, abs(va - vb) / s)
    return ident, nval, mrel, mpull, ''


def rep_consistency(b):
    """v2 output: mean of the per-shift replicates == value, per-sector replicate means == per-sector values"""
    worst = 0.0
    for c, ch in b['channels'].items():
        R = len(ch['rep'])
        for io, v in enumerate(ch['value']):
            m = sum(ch['rep'][r][io] for r in range(R)) / R
            worst = max(worst, abs(m - v) / max(ch['abs'][io], 1e-300))
    return worst


def section_A():
    P('=== A. direct: phase-1 binary vs v2 binary (same cfg, node, compiler, 64 threads)')
    ok = True
    for f in sorted(glob.glob(os.path.join(RG, 'direct_v1', '*.cfg.json'))):
        g = f.replace('direct_v1', 'direct_v2')
        if not os.path.exists(g):
            P('  MISSING', os.path.basename(g)); ok = False; continue
        a, b = json.load(open(f)), json.load(open(g))
        ident, n, mrel, mpull, det = cmp_outputs(a, b)
        ok &= ident
        P(f"  {os.path.basename(f):28s} {'BIT-IDENTICAL' if ident else 'DIFFERENT'} ({n} values; "
          f"v2 tasks: {b['task_shifts']} shift(s)/task, {b['point_blocks']} point block(s); "
          f"cpu v1 {a['cpu_seconds']:.0f}s v2 {b['cpu_seconds']:.0f}s, wall v1 {a['wall_seconds']:.0f}s v2 {b['wall_seconds']:.0f}s)"
          f"{'' if ident else f' max rel {mrel:.1e}, max pull {mpull:.2f} {det}'}; rep-mean vs value {rep_consistency(b):.1e} (rel. to L1)")
    return ok


def section_B(name, ref):
    P(f'=== B. {name} (v2) vs stored phase-1 outputs in runs/{ref}')
    nid, ndif, worst = 0, 0, []
    for f in sorted(glob.glob(os.path.join(RG, name, '*.cfg.json'))):
        r = os.path.join(ROOT, 'runs', ref, os.path.basename(f))
        if not os.path.exists(r):
            continue
        a, b = json.load(open(r)), json.load(open(f))
        ident, n, mrel, mpull, det = cmp_outputs(a, b)
        if ident:
            nid += 1
        else:
            ndif += 1
            worst.append((mpull, os.path.basename(f), mrel, det))
    P(f'  {nid} outputs bit-identical, {ndif} different')
    for mp_, f, mrel, det in sorted(worst, reverse=True)[:15]:
        P(f'    {f:34s} max pull {mp_:.2f}  max rel {mrel:.1e} {det}')
    return nid, ndif


def section_B2():
    P('=== B2. phase1_check: the phase-1 binary (final phase-1 source) on stored-output cfgs that differ (job 569290)')
    for f in sorted(glob.glob(os.path.join(RG, 'phase1_check', '*.cfg.json'))):
        c = os.path.basename(f)
        p1, v2 = json.load(open(f)), json.load(open(os.path.join(RG, 'replay4', c)))
        st_ = json.load(open(os.path.join(ROOT, 'runs', 'pilot4', c)))
        i1 = cmp_outputs(p1, v2)
        i2 = cmp_outputs(st_, p1)
        P(f"  {c:34s} phase-1 binary vs v2: {'BIT-IDENTICAL' if i1[0] else 'DIFFERENT'}; stored pilot4 output vs "
          f"phase-1 binary: {'identical' if i2[0] else f'different (max pull {i2[3]:.2f})'}")


def section_E():
    P('=== E. refinement round on the new campaign (job 569201): flagged Z4_E sectors at 4 x N, substituted per replicate')
    a = os.path.join(RG, 'new', 'results_before_refine.json')
    if not os.path.exists(a):
        return
    A, B = json.load(open(a)), json.load(open(os.path.join(RG, 'new', 'results.json')))
    for key in ('-1,0', '0,0'):
        va, ea = A['results']['Z4_E'][key]
        vb, eb = B['results']['Z4_E'][key]
        P(f'  Z4_E[{key}]: before {va:.14g} +- {ea:.2g}   after {vb:.14g} +- {eb:.2g}')
    P(f"  refined sectors: {B['costs']['Z4_E'].get('refined_sectors')}")


def section_C():
    P('=== C. replicate-based error / phase-1 quadrature error of the same assembled coefficients (replay5)')
    sys.path.insert(0, os.path.join(ROOT, 'py'))
    from lri_moments import assemble_job, merge_outputs
    from campaign import decode_job
    R5 = json.load(open(os.path.join(RG, 'replay5', 'results.json')))
    man = json.load(open(os.path.join(RG, 'replay5', 'manifest.json')))
    rows = []
    for m in man:
        outs = [json.load(open(os.path.join(ROOT, 'runs', 'pilot5', c + '.json'))) for c in m['cfgs']]
        tmp = {}
        assemble_job(decode_job(m['job']), merge_outputs(outs), tmp)
        for (k, j), (v, e) in tmp.items():
            key = f'{k},{j}'
            if key in R5['errors'].get(m['moment'], {}) and e > 0:
                s = R5['errors'][m['moment']][key]['stat']
                rows.append((m['moment'], key, s / e, s, e, len(m['job']['chans'])))
    for nm in ('A5_vd', 'Q6_v', 'A5_vv', 'A5_d', 'Q4_vd', 'A3_vdE', 'Q6_base', 'Z6_v'):
        sel = [r for r in rows if r[0] == nm]
        if sel:
            P(f'  {nm:7s} ' + '  '.join(f'[{r[1]}] {r[2]:.2f}' for r in sorted(sel, key=lambda r: r[1])))
    multi = [r[2] for r in rows if r[5] > 1]
    single = [r[2] for r in rows if r[5] == 1]
    if multi:
        P(f'  multi-channel: {len(multi)} coefficients, ratio median {st.median(multi):.2f}, min {min(multi):.2f}, max {max(multi):.2f}')
    if single:
        P(f'  single-channel: {len(single)} coefficients, ratio median {st.median(single):.2f}, min {min(single):.2f}, max {max(single):.2f}')


def section_D():
    P('=== D. new campaign (hashed seeds, regress-v2) vs pilot5 / replay5 (seed 1234567): pulls')
    N = json.load(open(os.path.join(RG, 'new', 'results.json')))
    R5 = json.load(open(os.path.join(RG, 'replay5', 'results.json')))
    P5 = json.load(open(os.path.join(ROOT, 'runs', 'pilot5', 'results.json')))
    needed = {}
    for g in json.load(open(os.path.join(ROOT, 'specs', 'production_D4.json'))):
        needed[g['name']] = {f'{p},{j}' for p, js in g['coeffs'].items() for j in js}
    pulls_all, pulls_need, big = [], [], []
    for grp, coeffs in N['results'].items():
        for key, (v, e) in coeffs.items():
            if grp in R5['results'] and key in R5['results'][grp]:
                v2, e2 = R5['results'][grp][key]
                src = 'replay5'
            elif grp in P5['results'] and key in P5['results'][grp]:
                v2, e2 = P5['results'][grp][key]
                src = 'pilot5(quadrature)'
            else:
                continue
            s = math.hypot(e, e2)
            if s == 0:
                if v != v2:
                    big.append((float('inf'), grp, key, v, v2, 0, src))
                continue
            z = (v - v2) / s
            pulls_all.append(z)
            if key in needed.get(grp, ()):
                pulls_need.append(z)
            if abs(z) > 3:
                big.append((abs(z), grp, key, v, v2, s, src))
    for lab, zs in (('all coefficients', pulls_all), ('needed coefficients', pulls_need)):
        if zs:
            n = len(zs)
            P(f'  {lab}: n={n}, rms pull {math.sqrt(sum(z * z for z in zs) / n):.2f}, '
              f'|z|>2: {sum(abs(z) > 2 for z in zs)} ({100 * sum(abs(z) > 2 for z in zs) / n:.1f}%), '
              f'|z|>3: {sum(abs(z) > 3 for z in zs)} ({100 * sum(abs(z) > 3 for z in zs) / n:.1f}%)')
    for z, g, k, v, v2, s, src in sorted(big, reverse=True)[:20]:
        P(f'    |z|={z:.1f} {g}[{k}] new {v:.15g} vs {src} {v2:.15g} (sigma {s:.1e})')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'results', 'regress_v2_report.txt'))
    a = ap.parse_args()
    section_A()
    section_B('replay5', 'pilot5')
    section_B('replay4', 'pilot4')
    if glob.glob(os.path.join(RG, 'phase1_check', '*.cfg.json')):
        section_B2()
    if os.path.exists(os.path.join(RG, 'replay5', 'results.json')):
        section_C()
    if os.path.exists(os.path.join(RG, 'new', 'results.json')):
        section_D()
        section_E()
    open(a.out, 'w').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
