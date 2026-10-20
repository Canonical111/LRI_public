#!/usr/bin/env python3
"""Heavy-tail N-trend check with the production as the third sample length (C62d's discriminator, PLAN-REVIEW-LOG
2026-10-08 "Tail N-trend check"). Fixed-k (16) Hill xi-hat falls with the per-replicate length N for bounded, peaked
weights (C62d: about N^-0.30 for certified-bounded d=2 weights) and stays constant for a true heavy tail.

Inputs: the pilot report (xi at 4,096 = PF and 32,768 = PC points per replicate, per campaign, for the 710 PC graphs),
prod_tails.csv (prod_tails.py: the production's replicate-mean xi per L8 graph and campaign, with its per-replicate
points) and the production C8_result.json (tail monitor; cross-check of prod_tails.csv on its listed graphs).

  ntrend.py PILOT_REPORT.json PROD_TAILS.csv C8_RESULT.json OUT.json
"""
import csv, json, math, random, statistics as st, sys

REPEATED = {4096, 32768}   # the pilot's sample lengths (PF, PC)
CANDIDATES = [10091, 14810, 20760, 3974, 5008, 6987, 9992, 10044, 11017, 11840, 14775, 14792, 19545, 21810, 26175, 26482]


def q(v):
    v = sorted(v)
    return None if not v else {'n': len(v), 'median': st.median(v), 'q25': v[len(v) // 4], 'q75': v[(3 * len(v)) // 4]}


def main(pilot_path, prod_path, result_path, out_path):
    pr = json.load(open(pilot_path))
    conf = pr['action2_confirm']['confirmations']
    piv = {(r['sector'], r['graph']) for r in pr['action2_confirm']['possible_infinite_variance']}
    prod = {}
    for r in csv.DictReader(open(prod_path)):
        prod[(r['campaign'], r['sector'], int(r['graph']))] = (float(r['xi']) if r['xi'] else None, int(r['points_min']),
                                                               int(r['points_max']), int(r['replicates']))
    # cross-check against the production tail monitor (exact recomputation of the listed rows)
    tm = json.load(open(result_path))['tail_monitor']
    worst = 0.0
    for row in tm['listed']:
        for c in ('a', 'b'):
            x = prod[(c, row['sector'], row['graph'])][0]
            worst = max(worst, abs(x - row[f'xi_{c}']))
    check = {'listed_rows': len(tm['listed']), 'max_abs_diff_xi': worst, 'pass': worst < 1e-12}

    rows = []
    for r in conf:
        s, g = r['sector'], r['graph']
        for c in ('a', 'b'):
            sup = (r.get('supporting') or {}).get(c)
            p = prod.get((c, s, g))
            if not sup or p is None or p[0] is None or sup.get('xi_4096') is None or sup.get('xi_32768') is None:
                continue
            x1, x2, x3 = sup['xi_4096'], sup['xi_32768'], p[0]
            n3 = p[1]
            row = {'sector': s, 'graph': g, 'campaign': c, 'piv': (s, g) in piv, 'xi_4096': x1, 'xi_32768': x2,
                   'xi_prod': x3, 'n_prod': n3, 'n_prod_max': p[2], 'replicates_prod': p[3]}
            if x1 > 0 and x2 > 0:
                b12 = math.log(x2 / x1) / math.log(8)
                row['beta_pf_pc'] = b12
                if n3 in REPEATED:
                    # a pilot length repeated with fresh seeds: a reproducibility check, not a trend test (C8D3-R3)
                    row['kind'] = 'repeat'
                    row['ratio_to_same_n_pilot'] = x3 / (x1 if n3 == 4096 else x2)
                elif x3 > 0:
                    row['kind'] = 'new_n'
                    row['beta_pf_prod'] = math.log(x3 / x1) / math.log(n3 / 4096)
                    # predictions at the production length: bounded trend (PF->PC exponent) vs constant (true tail)
                    row['pred_trend'] = x1 * (n3 / 4096) ** b12
                    row['pred_const'] = x2
                    if abs(row['pred_trend'] - x2) <= 1e-9 * max(abs(x2), 1e-300):
                        row['closer_to'] = 'tie'   # coincident predictions do not discriminate (C8D3-R3)
                    else:
                        row['closer_to'] = 'trend' if abs(x3 - row['pred_trend']) < abs(x3 - x2) else 'constant'
            rows.append(row)

    def boot_median(vals, reps=2000, seed=20261012):
        """Median with a 68% bootstrap interval over the listed values (graphs resampled with replacement)."""
        if not vals:
            return None
        rng = random.Random(seed); n = len(vals); meds = []
        for _ in range(reps):
            meds.append(st.median(vals[rng.randrange(n)] for _ in range(n)))
        meds.sort()
        return {'n': n, 'median': st.median(vals), 'band68': [meds[int(0.16 * reps)], meds[int(0.84 * reps)]]}

    def summary(sel):
        out = {'graph_campaigns': len(sel)}
        out['n_prod'] = q([r['n_prod'] for r in sel])
        out['n_prod_counts'] = {str(n): sum(1 for r in sel if r['n_prod'] == n) for n in sorted({r['n_prod'] for r in sel})}
        out['xi_4096'] = q([r['xi_4096'] for r in sel]); out['xi_32768'] = q([r['xi_32768'] for r in sel])
        out['xi_prod'] = q([r['xi_prod'] for r in sel])
        out['beta_pf_pc'] = q([r['beta_pf_pc'] for r in sel if 'beta_pf_pc' in r])
        new = [r for r in sel if r.get('kind') == 'new_n']
        out['new_n'] = {'graph_campaigns': len(new),
                        'beta_pf_prod': q([r['beta_pf_prod'] for r in new]),
                        'ratio_to_trend': boot_median([r['xi_prod'] / r['pred_trend'] for r in new]),
                        'ratio_to_constant': boot_median([r['xi_prod'] / r['pred_const'] for r in new])}
        cl = [r['closer_to'] for r in new]
        out['new_n']['closer_to_trend'] = cl.count('trend'); out['new_n']['closer_to_constant'] = cl.count('constant')
        out['new_n']['ties'] = cl.count('tie')
        # inside the pilot's range (8,192, 16,384: interpolation) or beyond it (65,536: extrapolation)
        out['new_n']['by_n'] = {str(n): {'graph_campaigns': len(v), 'role': 'interpolation' if n < 32768 else 'extrapolation',
                                         'ratio_to_trend': boot_median([r['xi_prod'] / r['pred_trend'] for r in v]),
                                         'ratio_to_xi_32768': boot_median([r['xi_prod'] / r['pred_const'] for r in v]),
                                         'closer_to_trend': sum(r['closer_to'] == 'trend' for r in v)}
                                for n in sorted({r['n_prod'] for r in new}) for v in [[r for r in new if r['n_prod'] == n]]}
        rep = [r for r in sel if r.get('kind') == 'repeat']
        out['repeat_n'] = {'graph_campaigns': len(rep), 'ratio_to_same_n_pilot': boot_median([r['ratio_to_same_n_pilot'] for r in rep])}
        out['xi_prod_gt_0.44'] = sum(1 for r in sel if r['xi_prod'] > 0.44)
        return out

    res = {'cross_check_vs_tail_monitor': check}
    for s in ('free', 'power'):
        for c in ('a', 'b'):
            sel = [r for r in rows if r['sector'] == s and r['campaign'] == c and r['piv']]
            res[f'piv_{s}_{c}'] = summary(sel)
    # a/b shift of xi over the possible-infinite-variance graphs, only for pairs at matched sample length (C8D3-R2):
    # production pairs grouped by their common N, and the pilot's equal-N pairs at 4,096 and 32,768; the face model
    # (rate-limited tail) predicts xi_b - xi_a = -(1 - xi_a)/7
    sup = {(r['sector'], r['graph']): r.get('supporting') or {} for r in conf}
    for s in ('free', 'power'):
        out = {}
        groups = {}
        for (ss, g) in sorted(piv):
            if ss != s:
                continue
            pa, pb = prod.get(('a', s, g)), prod.get(('b', s, g))
            if pa and pb and pa[0] is not None and pb[0] is not None:
                key = f'prod_N{pa[1]}' if (pa[1] == pb[1] and pa[1] == pa[2] and pb[1] == pb[2]) else 'prod_unmatched'
                groups.setdefault(key, []).append((pa[0], pb[0]))
            sa, sb = sup.get((s, g), {}).get('a'), sup.get((s, g), {}).get('b')
            if sa and sb:
                for n, k in ((4096, 'xi_4096'), (32768, 'xi_32768')):
                    if sa.get(k) is not None and sb.get(k) is not None:
                        groups.setdefault(f'pilot_N{n}', []).append((sa[k], sb[k]))
        for key in sorted(groups):
            pairs = groups[key]
            if key == 'prod_unmatched':
                out[key] = {'n': len(pairs), 'note': 'unequal sample lengths: not compared'}
                continue
            out[key] = {'observed_xi_b_minus_a': boot_median([b - a for a, b in pairs]),
                        'face_model_median': st.median(-(1 - a) / 7 for a, _ in pairs)}
        res[f'ab_shift_{s}'] = out
    res['candidates'] = [r for r in rows if r['graph'] in CANDIDATES and r['sector'] == 'power']
    # production-wide context from the tail monitor
    res['tail_monitor'] = {'listed': len(tm['listed']), 'flags_over_3pct': len(tm['flags']), 'undefined': len(tm['undefined']),
                           'max_share': max((v for row in tm['listed'] for v in row['share'].values() if v is not None), default=None),
                           'sum_share_listed': {f'{c}_{s}': sum((row['share'][c] or 0) for row in tm['listed'] if row['sector'] == s)
                                                for c in ('a', 'b') for s in ('free', 'power')}}
    json.dump({'rows': rows, 'summary': res}, open(out_path, 'w'), indent=1)
    print(json.dumps(res, indent=1, default=str)[:6000])


if __name__ == '__main__':
    main(*sys.argv[1:5])
