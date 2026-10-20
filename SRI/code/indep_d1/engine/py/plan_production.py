#!/usr/bin/env python3
"""Production planner (v2, 2026-10-03): replicate-based error model.

Inputs
  specs/production_D4.json        46 moment groups / 116 raw coefficients (framework list)
  --grad FILE                     SIGNED gradients dC6/dx, dC7/dx (tests/e2e_framework.py --grad-out), evaluated
                                  at the engine's own data point (not the archive)
  --src RUNDIR [--src RUNDIR ...] v2 run directories with results.json (campaign.py collect): per-replicate
                                  coefficients, error floors, cpu seconds; sector-sampled benchmarks allowed
Model (per group g, reference = the source with the largest N for g)
  var_g(C) at the reference = sum over its jobs (g,k) of  sum_r D_r^2 / (R (R-1)),
        D_r = sum_{i in job} dC/dx_i (x_{i,r} - mean_i)      (exact correlations between channels, Laurent
                                                              orders and coefficients of one job)
  scaled to all sectors (x stride), to the production shift count (x R_ref/R_prod) and to N:
        sigma_g(C; N)^2 = var_g * stride * (R_ref/R_prod) * (N/N_ref)^(-2 alpha_d)
  plus the N-independent error floor  sum_i (dC/dx_i * floor_i * stride)^2.
  alpha_d = conservative rate per integration dimension (6D 2.4, 5D 2.8, 4D 2.3, <=3D 3.0), lowered to the
  measured replicate-error rate between two benchmark sizes when that is slower.
  Lattice sizes: greedy (largest reduction of max(sigma(C6), sigma(C7))^2 per added core-hour) on the prime
  ladder until sigma(C6), sigma(C7) <= T.  Cost = measured us/point (symmetry amdq) x N x shifts x sectors.
Output
  results/production_plan.md, specs/production_<tier>.json (campaign specs with tier names for the seeds)
usage: plan_production.py --grad specs/gradients_C6_C7_D4.json --src runs/pilot4v2 --src runs/regress
"""
import argparse, json, math, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LADDER = [16001, 32003, 64007, 131071, 262139, 524287, 1048573, 2097143, 4194301]
TIERS = {'6digit': 5e-5, '8digit': 5e-7}
SHIFTS = 6
CORES_PER_NODE = 64
ALPHA = {6: 2.4, 5: 2.8, 4: 2.3}


def raw_name(group, key):
    k, j = key.split(',')
    return f"{group.replace('_base', '')}[eps^{k} l^{j}]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grad', default=os.path.join(ROOT, 'specs', 'gradients_C6_C7_D4.json'))
    ap.add_argument('--src', action='append', required=True)
    ap.add_argument('--shifts', type=int, default=SHIFTS)
    ap.add_argument('--node-hours-per-cfg', type=float, default=3.0)
    a = ap.parse_args()
    prod = json.load(open(os.path.join(ROOT, 'specs', 'production_D4.json')))
    G = json.load(open(a.grad))['gradients']
    # ---- gather per-group candidate references from all sources
    cand = {}
    for src in a.src:
        R = json.load(open(os.path.join(src, 'results.json')))
        man = json.load(open(os.path.join(src, 'manifest.json')))
        for name, coeffs in R['results'].items():
            g = re.sub(r'_N\d+$', '', name)
            gp = next((x for x in prod if x['name'] == g), None)
            if gp is None:
                continue
            needed = {f'{p},{j}' for p, js in gp['coeffs'].items() for j in js}
            # sample size per k (sectors actually integrated) and cpu
            nsamp, cpu, N, sh = {}, 0.0, None, None
            for m in man:
                if m['moment'] != name:
                    continue
                for c in m['cfgs']:
                    r = json.load(open(os.path.join(src, c + '.json')))
                    k = m['job']['k']
                    nsamp[k] = nsamp.get(k, 0) + r['sector_range'][1] - r['sector_range'][0]
                    cpu += r['cpu_seconds']
                    N, sh = r['N'], r['shifts']
            if not nsamp:
                continue
            stride = gp['sectors'] / (sum(nsamp.values()) / len(nsamp))
            pts = N * sh * sum(nsamp.values())
            # replicate projections per job block
            var = {'C6': 0.0, 'C7': 0.0}
            fl = {'C6': 0.0, 'C7': 0.0}
            blocks = {}
            for key in coeffs:
                if key not in needed:
                    continue
                ex = R['errors'][name][key]
                if ex.get('zero'):
                    continue
                blocks.setdefault(ex['block'], []).append(key)
                nm = raw_name(g, key)
                for o in var:
                    fl[o] += (G[o].get(nm, 0.0) * ex['floor'] * stride) ** 2
            Rref = None
            for b, keys in blocks.items():
                reps = {kk: R['replicates'][name][kk] for kk in keys}
                Rb = len(next(iter(reps.values())))
                Rref = Rb
                if Rb < 2:
                    continue
                for o in var:
                    mean = {kk: sum(v) / Rb for kk, v in reps.items()}
                    D = [sum(G[o].get(raw_name(g, kk), 0.0) * (reps[kk][r] - mean[kk]) for kk in keys)
                         for r in range(Rb)]
                    var[o] += sum(x * x for x in D) / (Rb * (Rb - 1))
            cand.setdefault(g, []).append({'src': src, 'N': N, 'shifts': sh, 'R': Rref, 'stride': stride,
                                           'us_pt': 1e6 * cpu / pts, 'var': var, 'floor2': fl,
                                           'nk': len(nsamp)})
    rows, model = [], {}
    for gp in prod:
        g = gp['name']
        cs = sorted(cand.get(g, []), key=lambda c: (c['N'], -c['stride']))
        row = {'name': g, 'geom': gp['geom'], 'dim': gp['dim'], 'sectors': gp['sectors'], 'powers': gp['powers']}
        if not cs:
            print(f'WARNING: no replicate data for {g}; it is NOT in the error budget', file=sys.stderr)
            row['nodata'] = True
            rows.append(row)
            continue
        ref = cs[-1]
        alpha = ALPHA.get(gp['dim'], 3.0)
        meas = None
        others = [c for c in cs if c['N'] < ref['N'] and abs(c['stride'] - ref['stride']) < 1e-9]
        if others:
            lo = others[-1]
            for o in ('C7', 'C6'):
                v0 = lo['var'][o] * lo['R'] / ref['R'] if lo['R'] and ref['R'] else lo['var'][o]
                if v0 > 0 and ref['var'][o] > 0:
                    meas = 0.5 * math.log(v0 / ref['var'][o]) / math.log(ref['N'] / lo['N'])
                    break
        if meas is not None and meas < alpha - 0.3:
            alpha = max(meas, 1.0)
        row.update({'ref': ref, 'alpha': alpha, 'alpha_meas': meas, 'us_pt': ref['us_pt']})
        model[g] = row
        rows.append(row)

    def sig2(Nsel, o):
        tot = 0.0
        for g, r in model.items():
            ref = r['ref']
            scale = ref['stride'] * (ref['R'] / a.shifts if ref['R'] else 1.0)
            tot += ref['var'][o] * scale * (Nsel[g] / ref['N']) ** (-2 * r['alpha']) + ref['floor2'][o]
        return tot

    def cost(g, N):
        r = model[g]
        gp = next(x for x in prod if x['name'] == g)
        return r['us_pt'] * 1e-6 * N * a.shifts * gp['sectors'] * r['ref']['nk'] / 3600.0

    alloc = {}
    for t, T in TIERS.items():
        # start: cheap 1D/2D groups at N=1048573 (negligible cost), all others at the bottom of the ladder
        Nsel = {g: (1048573 if r['dim'] <= 2 else LADDER[0]) for g, r in model.items()}
        while max(sig2(Nsel, 'C6'), sig2(Nsel, 'C7')) > T * T:
            cur = max(sig2(Nsel, 'C6'), sig2(Nsel, 'C7'))
            best, bestv = None, -1.0
            for g in model:
                i = LADDER.index(Nsel[g]) if Nsel[g] in LADDER else None
                if i is None or i + 1 >= len(LADDER):
                    continue
                trial = dict(Nsel)
                trial[g] = LADDER[i + 1]
                gain = cur - max(sig2(trial, 'C6'), sig2(trial, 'C7'))
                v = gain / max(cost(g, LADDER[i + 1]) - cost(g, Nsel[g]), 1e-9)
                if v > bestv:
                    best, bestv = g, v
            if best is None or bestv <= 0:
                print(f'WARNING: tier {t} target {T} not reachable on the ladder', file=sys.stderr)
                break
            Nsel[best] = LADDER[LADDER.index(Nsel[best]) + 1]
        alloc[t] = (Nsel, math.sqrt(sig2(Nsel, 'C6')), math.sqrt(sig2(Nsel, 'C7')))

    specs = {t: [] for t in TIERS}
    tot = {t: 0.0 for t in TIERS}
    for r in rows:
        gp = next(x for x in prod if x['name'] == r['name'])
        for t in TIERS:
            if 'nodata' in r:
                N, ch = 1048573, 1
                cpuh = None
            else:
                N = alloc[t][0][r['name']]
                cpuh = cost(r['name'], N)
                tot[t] += cpuh
                ch = max(1, min(gp['sectors'], math.ceil(cpuh / CORES_PER_NODE / a.node_hours_per_cfg / len(gp['powers']))))
                ref = r['ref']
                scale = ref['stride'] * (ref['R'] / a.shifts if ref['R'] else 1.0)
                for o in ('C6', 'C7'):
                    r[f'sig_{o}_{t}'] = math.sqrt(ref['var'][o] * scale * (N / ref['N']) ** (-2 * r['alpha'])
                                                  + ref['floor2'][o])
            r[f'N_{t}'], r[f'cpuh_{t}'], r[f'chunks_{t}'] = N, cpuh, ch
            specs[t].append({'name': r['name'], 'kind': gp['kind'], 'n': gp['n'], 'nv': gp['nv'], 'nd': gp['nd'],
                             'ne': gp['ne'], 'powers': gp['powers'], 'jmin': gp['jmin'], 'coeffs': gp['coeffs'],
                             'N': N, 'shifts': a.shifts, 'chunks': ch})
    for t in TIERS:
        json.dump({'tier': t, 'defaults': {'transform': 3, 'prec': 'auto'}, 'moments': specs[t]},
                  open(os.path.join(ROOT, 'specs', f'production_{t}.json'), 'w'), indent=1)
    lines = ['# Production plan (generated by py/plan_production.py, v2 replicate-based error model)', '',
             f'Sources: {", ".join(a.src)}; gradients: {os.path.relpath(a.grad, ROOT)}. '
             f'Error of each group = replicate projection of its coefficients on dC6/dx, dC7/dx (exact '
             f'correlations), scaled by stride, shifts ({a.shifts} in production) and (N/N_ref)^-alpha, plus the '
             f'calibrated floor. Greedy cost/benefit lattice allocation until sigma(C6), sigma(C7) <= T; tiers {TIERS}. '
             'Cost: measured us/point on symmetry amdq (64 cores/node).', '',
             '| group | d | sectors | eps powers | ref N (src) | stride | alpha (meas.) | us/pt | sigma_C6 @ref | sigma_C7 @ref '
             '| N (6-digit) | core-h | sigma_C7 | N (8-digit) | core-h | sigma_C7 |',
             '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    key = lambda r: -(r.get('cpuh_6digit') or 0)
    for r in sorted(rows, key=key):
        if 'nodata' in r:
            lines.append(f"| {r['name']} | {r['dim']} | {r['sectors']} | {r['powers']} | (no data) |||||||||||")
            continue
        ref = r['ref']
        sc = ref['stride'] * (ref['R'] / a.shifts if ref['R'] else 1.0)
        lines.append(
            f"| {r['name']} | {r['dim']} | {r['sectors']} | {r['powers']} | {ref['N']} ({os.path.basename(ref['src'])}) | "
            f"{ref['stride']:.0f} | {r['alpha']:.2f} ({'-' if r['alpha_meas'] is None else '%.2f' % r['alpha_meas']}) | "
            f"{r['us_pt']:.0f} | {math.sqrt(ref['var']['C6'] * sc):.1e} | {math.sqrt(ref['var']['C7'] * sc):.1e} | "
            f"{r['N_6digit']} | {r['cpuh_6digit']:.1f} | {r['sig_C7_6digit']:.1e} | "
            f"{r['N_8digit']} | {r['cpuh_8digit']:.1f} | {r['sig_C7_8digit']:.1e} |")
    lines += ['', f"**Tier 1 (6 digits, T=5e-5): {tot['6digit']:.0f} core-hours, predicted sigma(C6) = "
                  f"{alloc['6digit'][1]:.1e}, sigma(C7) = {alloc['6digit'][2]:.1e}.**  ",
              f"Tier 2 (8 digits, T=5e-7, to be re-planned from the tier-1 data): {tot['8digit']:.0f} core-hours, "
              f"sigma(C6) = {alloc['8digit'][1]:.1e}, sigma(C7) = {alloc['8digit'][2]:.1e}."]
    open(os.path.join(ROOT, 'results', 'production_plan.md'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
