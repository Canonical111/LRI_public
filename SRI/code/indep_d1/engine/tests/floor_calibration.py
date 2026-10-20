#!/usr/bin/env python3
"""Calibrate the relative error floor (py/lri_moments.py FLOOR_REL) without archive data.

The floor models errors that the shift-replicate scatter cannot see.  It is expressed relative to the L1 scale
of each assembled coefficient, l1 = sum_{channel,order} |w| * (1/N) sum_points |f| (summed over sectors), i.e.
relative to the size of the terms that cancel, which is what double-precision accumulation and the
tail/cancellation tolerances act on.

  1. numerical systematic: default vs strict tolerances (errTarget, tailTol 1e-16, maxJet 2e6, tailMax 0.05) on
     the same lattice and shifts (runs/regress_v2/strict vs replay5): QMC noise cancels, |delta|/l1 is what the
     tolerances do.
  2. independent runs: replay5 (seed 1234567) vs new (hashed seeds), same N: pulls (x1-x2)/sqrt(s1^2+s2^2+floors)
     in two regimes of relative precision sigma/l1 (< 1e-12 and >= 1e-12); f_data = smallest value on a 1-2-5
     grid with rms pull <= 1.2, <= 5% of |z| > 2 and <= 2% of |z| > 3 in both (Student t with 7 dof per run).
  3. FLOOR_REL = max(10 x f_data, 1e-15 a-priori double-rounding floor, 3 x the largest |delta|/l1 of 1):
     systematic rounding (prefactor weights, pole factors) is identical in every run and invisible to 1 and 2.
usage: floor_calibration.py [--out results/floor_calibration.txt]
"""
import argparse, json, math, os, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RG = os.path.join(ROOT, 'runs', 'regress_v2')
GRID = [0.0] + [m * 10.0 ** e for e in range(-18, -10) for m in (1, 2, 5)]
lines = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    lines.append(s)


def load(d):
    return json.load(open(os.path.join(RG, d, 'results.json')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'results', 'floor_calibration.txt'))
    a = ap.parse_args()
    R5, S, NW = load('replay5'), load('strict'), load('new')
    # ---- 1. strict vs default
    P('=== 1. default vs strict numerical tolerances (same lattice, same shifts)')
    rs = []
    for g, co in S['results'].items():
        for key, (vs, _) in co.items():
            if key not in R5['results'].get(g, {}):
                continue
            vd = R5['results'][g][key][0]
            ex = R5['errors'][g][key]
            if ex['l1'] == 0:
                continue
            r = abs(vd - vs) / ex['l1']
            rs.append((r, g, key, vd - vs, ex['stat'], ex['l1']))
    rs.sort(reverse=True)
    P(f'  {len(rs)} coefficients; |delta|/l1: max {rs[0][0]:.2e}, median {st.median(x[0] for x in rs):.2e}; '
      f'|delta|/sigma_stat: max {max(abs(x[3]) / x[4] for x in rs if x[4] > 0):.2e}')
    for r, g, key, d, s, l1 in rs[:6]:
        P(f'    {g}[{key}] delta {d:.2e} l1 {l1:.2e} -> {r:.2e} (sigma_stat {s:.1e})')
    f_num = rs[0][0]
    # ---- 2. independent runs
    P('=== 2. replay5 (seed 1234567) vs new (hashed seeds), same N: pulls vs relative precision')
    pts = []
    for g, co in NW['results'].items():
        if g not in R5['results']:
            continue
        for key, (v1, _) in co.items():
            if key not in R5['results'][g]:
                continue
            e1, e2 = NW['errors'][g][key], R5['errors'][g][key]
            if NW['costs'][g]['N'] != R5['costs'][g]['N']:
                continue
            v2 = R5['results'][g][key][0]
            if e1['l1'] == 0 and e2['l1'] == 0:
                continue
            s0 = math.hypot(e1['stat'], e2['stat'])
            if s0 == 0 and v1 == v2:
                continue          # exact (pole-only) coefficient, identical in both runs
            pts.append((v1 - v2, e1['stat'], e2['stat'], e1['l1'], e2['l1'], g, key))
    def regime_stats(f, cond):
        zs = []
        for d, s1, s2, l1, l2, g, key in pts:
            rel = math.hypot(s1, s2) / max((l1 + l2) / 2, 1e-300)
            if not cond(rel):
                continue
            s = math.sqrt(s1 * s1 + s2 * s2 + (f * l1) ** 2 + (f * l2) ** 2)
            zs.append(d / s if s > 0 else (0.0 if d == 0 else 1e3))
        n = len(zs)
        rms = math.sqrt(sum(min(z * z, 1e6) for z in zs) / n) if n else 0.0
        return n, rms, sum(abs(z) > 2 for z in zs), sum(abs(z) > 3 for z in zs)

    regimes = (('precise (sigma/l1 < 1e-12)', lambda r: r < 1e-12), ('coarse  (sigma/l1 >= 1e-12)', lambda r: r >= 1e-12))
    f_pull = None
    for f in GRID[:16]:
        row = []
        good = True
        for lab, cond in regimes:
            n, rms, n2, n3 = regime_stats(f, cond)
            row.append(f'{lab}: n={n} rms {rms:.2f} |z|>2 {n2} |z|>3 {n3}')
            # Student t (7 dof per run): rms ~1.2, P(|t|>2) ~ 8%, P(|t|>3) ~ 2%
            good &= (rms <= 1.2 and n2 <= 0.05 * n + 1 and n3 <= 0.02 * n + 1)
        P(f'  f={f:<7g} ' + ' | '.join(row) + ('   <- consistent' if good and f_pull is None else ''))
        if good and f_pull is None:
            f_pull = f
    worst = sorted(pts, key=lambda p: -abs(p[0]) / max(math.hypot(p[1], p[2]), 1e-300))[:8]
    P('  largest stat-only pulls:')
    for d, s1, s2, l1, l2, g, key in worst:
        P(f'    {g}[{key}] delta {d:.2e} sigma_stat {math.hypot(s1, s2):.1e} (pull {d / max(math.hypot(s1, s2), 1e-300):.1f}) '
          f'l1 {l1:.1e} -> delta/l1 {abs(d) / l1:.1e}')
    # ---- 3. choice
    F_APRIORI = 1e-15   # systematic double rounding identical in every run (prefactor weights, pole factors,
    #                     per-point dd->double): ~10 ulp of the L1 scale; invisible to replicate and run comparisons
    f_final = max(10 * (f_pull or 0.0), F_APRIORI, 3 * f_num)
    P(f'=== 3. FLOOR_REL = max(10 x f_data = {10 * (f_pull or 0):.1e}, a-priori rounding floor {F_APRIORI:.0e}, '
      f'3 x f_num = {3 * f_num:.1e}) = {f_final:g}')
    open(a.out, 'w').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
