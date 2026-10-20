#!/usr/bin/env python3
"""Post-production diagnostics of the C8(2) production batch prod1-2.5e-4-ddmp256-20261006-ba68f401e46e (2026-10-07).

  pr_result_analysis.py --package PKG --run PROD --pilot PILOT --accounting ACC.json --out OUT.json

Reads only (both campaigns through tools/design.load_pilot, i.e. every merged table verified through merged.json).
1. Variance: per (sector, L) the realized C8 variance of the batch, two ways (replicate group sums, as the assembly
   does; and the sum of per-graph variances 0.25 Var_rep(y_g)/r, y_g = J8[L] . jet of graph g at the batch's means)
   against error_by_loop, and the variance the design predicted from the pilot's per-graph sigma at the batch's points
   (sum 0.25 sigma_pilot,g^2 / (n_g r)); the per-point variance n Var_rep(y_g) of the batch against the pilot's,
   pooled per stratum.
2. Heavy tails (C63d's rule, tools/design.tail_table on both campaigns): the pilot's screened L8 graphs classified at
   production scale as confirmed (both campaigns defined at >= 32,768 points per replicate, two-campaign mean
   xi_hat > 0.44), cleared (the same, mean <= 0.44), below the confirmation points, or undefined; the production-scale
   screen; xi_hat distributions; and for the confirmed graphs: their share of the batch's C8 variance, the growth of
   their per-point variance from 4,096 to >= 32,768 points (an infinite-variance graph grows like n^(2 xi - 1)),
   measured also on a cross split (selected on one campaign's xi_hat, measured on the other's sigma) that is free of
   the selection bias, their replicate-level excess kurtosis against a Gaussian reference, and the SE if their
   variance were k times larger.
3. Cost: busy thread seconds per group (merged.json thread_seconds_sum) against the plan's index estimates
   (manifest jobs est_core_seconds), and the lane logs' per-index wall against its estimate."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np

CONFIRM = 32768


def q(x, ps=(0.1, 0.5, 0.9)):
    x = np.asarray([v for v in x if v is not None and math.isfinite(v)], float)
    if not len(x):
        return None
    return {f'q{int(p * 100)}': float(np.quantile(x, p)) for p in ps} | {'n': int(len(x)), 'max': float(x.max()), 'mean': float(x.mean())}


def per_graph(P, design):
    """{(c, s, L, g): dict(y, n, reps, var, v)}: y the C8-projected replicate values, var = Var_rep(y) (ddof 1),
    v = 0.25 var / reps (the graph's contribution to Var(C8_full) = Var((C8_a + C8_b)/2)), sp2 = n var (per point)."""
    out = {}
    for (c, s, L), G in P.groups.items():
        if not len(G.graphs):
            continue
        y = np.einsum('rgj,j->rg', G.Y, P.J8[L])
        var = np.var(y, axis=0, ddof=1)
        for i, g in enumerate(G.graphs):
            n = G.points[g]
            out[(c, s, L, g)] = dict(y=y[:, i], n=n, reps=G.reps, var=float(var[i]), v=0.25 * float(var[i]) / G.reps, sp2=n * float(var[i]))
    return out


def group_sum_variance(P):
    """Per (sector, L): sum over campaigns of 0.25 J8 cov(replicate group sums) J8^T / reps (the assembly's way)."""
    out = {}
    for (c, s, L), G in P.groups.items():
        y = np.einsum('rgj,j->rg', G.Y, P.J8[L]).sum(1)
        out[(s, L)] = out.get((s, L), 0.) + 0.25 * float(np.var(y, ddof=1)) / G.reps
    return out


def excess_kurtosis(ys):
    """Pooled excess kurtosis of the standardized replicate values (mean 0, ddof-1 sd per graph-campaign)."""
    z = []
    for y in ys:
        sd = np.std(y, ddof=1)
        if sd > 0:
            z.append((y - y.mean()) / sd)
    if not z:
        return None
    z = np.concatenate(z)
    return float(np.mean(z ** 4) - 3.)


def gaussian_kurtosis_reference(reps, m=20000, seed=20261007):
    rng = np.random.default_rng(seed)
    return excess_kurtosis(list(rng.standard_normal((m, reps))))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--package', type=Path, required=True)
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--pilot', type=Path, required=True)
    ap.add_argument('--accounting', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    sys.path.insert(0, str(a.package / 'tools'))
    import design
    t0 = time.time()
    res = json.loads((a.run / 'C8_result.json').read_bytes())
    pres = json.loads((a.pilot / 'C8_result.json').read_bytes())
    out = {'schema': 'c8-d2-production-analysis-1', 'run': str(a.run), 'pilot': str(a.pilot), 'rule': __doc__, 'timing': {}}
    P = design.load_pilot(a.run)
    out['timing']['load_production_s'] = time.time() - t0
    t1 = time.time()
    Q = design.load_pilot(a.pilot)
    out['timing']['load_pilot_s'] = time.time() - t1
    out['production_meta'] = {k: P.meta[k] for k in ('manifest_sha256', 'seed', 'numerics', 'executable_sha256')}
    out['pilot_meta'] = {k: Q.meta[k] for k in ('manifest_sha256', 'seed', 'numerics', 'executable_sha256')}

    # ---------------------------------------------------------------- 0. headline numbers
    se, c8 = res['sampling_standard_error'], res['C8_full']
    pse, pc8 = pres['sampling_standard_error'], pres['C8_full']
    ca, cb = res['campaigns']['a'], res['campaigns']['b']
    out['headline'] = dict(
        C8_full=c8, sampling_se=se, relative_se=se / abs(c8),
        campaigns=dict(a=ca, b=cb, difference=ca['C8'] - cb['C8'], difference_se=math.hypot(ca['sampling_se'], cb['sampling_se']),
                       pull=(ca['C8'] - cb['C8']) / math.hypot(ca['sampling_se'], cb['sampling_se'])),
        half_streams=dict(values=[h[8] for h in res['half_streams']], difference=res['half_streams'][0][8] - res['half_streams'][1][8]),
        bootstrap=dict(se=res['bootstrap']['full_se'][8], bias=res['bootstrap']['bias'][8], ratio_to_sampling_se=res['bootstrap']['full_se'][8] / se),
        pilot=dict(C8_full=pc8, sampling_se=pse, difference=c8 - pc8, combined_se=math.hypot(se, pse), pull=(c8 - pc8) / math.hypot(se, pse)),
        power=dict(power_free_C8=res['power_free_C8'], power_free_se=res['power_free_se'], correction=res['power_correction'],
                   correction_se=res['power_correction_se'], pull=res['power_correction'] / res['power_correction_se']))

    # ---------------------------------------------------------------- 1. variance: realized vs predicted
    t1 = time.time()
    GP, GQ = per_graph(P, design), per_graph(Q, design)
    gsum = group_sum_variance(P)
    prim = {s: {r['id']: bool(r.get('primitive')) for r in P.inventory[s]['8']} for s in design.SECTORS}
    strata = {}
    for s in design.SECTORS:
        for L in design.LOOPS:
            keys = [k for k in GP if k[1] == s and k[2] == L]
            real = sum(GP[k]['v'] for k in keys)
            pred = sum(0.25 * GQ[k]['sp2'] / (GP[k]['n'] * GP[k]['reps']) for k in keys if k in GQ)
            sp_prod = sum(GP[k]['sp2'] for k in keys if k in GQ)
            sp_pil = sum(GQ[k]['sp2'] for k in keys if k in GQ)
            lr = [math.log(GP[k]['sp2'] / GQ[k]['sp2']) for k in keys if k in GQ and GP[k]['sp2'] > 0 and GQ[k]['sp2'] > 0]
            ebl = res['error_by_loop'][s][str(L)]['variance']
            strata[f'{s}_L{L}'] = dict(graph_campaigns=len(keys), realized_variance_group_sums=gsum[(s, L)], realized_variance_sum_of_graphs=real,
                                       error_by_loop_variance=ebl, error_by_loop_share=res['error_by_loop'][s][str(L)]['share'],
                                       predicted_variance_from_pilot_sigma=pred, realized_over_predicted=gsum[(s, L)] / pred if pred else None,
                                       per_point_variance_ratio_pooled=sp_prod / sp_pil if sp_pil else None,
                                       per_point_variance_log_ratio_median=float(np.median(lr)) if lr else None,
                                       points_per_replicate=q([GP[k]['n'] for k in keys], (0.0, 0.5, 1.0)),
                                       replicates=sorted({GP[k]['reps'] for k in keys}))
    tot_real = sum(x['realized_variance_group_sums'] for x in strata.values())
    tot_pred = sum(x['predicted_variance_from_pilot_sigma'] for x in strata.values())
    out['variance'] = dict(strata=strata, total_realized_group_sums=tot_real, total_realized_sum_of_graphs=sum(x['realized_variance_sum_of_graphs'] for x in strata.values()),
                           result_variance=se ** 2, total_predicted_from_pilot_sigma=tot_pred, predicted_se_raw=math.sqrt(tot_pred),
                           realized_over_predicted_variance=tot_real / tot_pred, realized_over_predicted_se=math.sqrt(tot_real / tot_pred),
                           note='predicted = sum over graphs of 0.25 sigma_pilot^2 / (n_batch r_batch), sigma_pilot^2 = n_pilot Var_rep (ddof 1) with the pilot J8; '
                                'no sigma floor and no margin (the design: raw 7.667, with margin 11.50)')
    out['timing']['variance_s'] = time.time() - t1

    # ---------------------------------------------------------------- 2. heavy tails
    t1 = time.time()
    rows_p, flags_p = design.tail_table(P)
    rows_q, flags_q = design.tail_table(Q)
    out['timing']['tail_tables_s'] = time.time() - t1
    tp = {(x['campaign'], x['sector'], x['L'], x['graph']): x for x in rows_p}
    tq = {(x['campaign'], x['sector'], x['L'], x['graph']): x for x in rows_q}
    screened_pilot = {(x['sector'], x['L'], x['graph']) for x in flags_q['screened']}
    confirmed_prod = {(x['sector'], x['L'], x['graph']): x for x in flags_p['confirmed']}
    screened_prod = {(x['sector'], x['L'], x['graph']) for x in flags_p['screened']}
    undefined_prod = {(x['sector'], x['L'], x['graph']) for x in flags_p['undefined']}

    def status(s, L, g):
        d = [tp.get((c, s, L, g)) for c in design.CAMPAIGNS]
        if any(x is None or x['status'] != 'defined' for x in d):
            return 'undefined', None, None
        pts = min(x['points'] or 0 for x in d)
        m = sum(x['xi_hat'] for x in d) / 2
        if pts < CONFIRM:
            return 'below_confirm_points', m, pts
        return ('confirmed' if m > design.XI_CONFIRM_MEAN else 'cleared'), m, pts

    cls = {}
    for (s, L, g) in sorted(screened_pilot):
        st, m, pts = status(s, L, g)
        cls[(s, L, g)] = dict(status=st, xi_mean_production=m, points=pts, primitive=prim[s].get(g, False),
                              xi_mean_pilot=sum(tq[(c, s, L, g)]['xi_hat'] for c in design.CAMPAIGNS) / 2)
    summary = {}
    for s in design.SECTORS:
        for sub in ('all', 'primitive', 'non-primitive'):
            sel = [v for (ss, L, g), v in cls.items() if ss == s and (sub == 'all' or (sub == 'primitive') == v['primitive'])]
            if not sel:
                continue
            summary[f'{s}_L8_{sub}'] = {k: sum(1 for v in sel if v['status'] == k) for k in ('confirmed', 'cleared', 'below_confirm_points', 'undefined')} | {'screened_in_pilot': len(sel)}
    # consistency with the report's own rule (design.tail_table's confirmed list)
    mine = {k for k, v in cls.items() if v['status'] == 'confirmed'}
    out['tails'] = dict(
        pilot_screened=len(screened_pilot), pilot_confirmed=len(flags_q['confirmed']), pilot_undefined=len(flags_q['undefined']),
        followup=summary,
        production_confirmed_total=len(confirmed_prod), production_confirmed_not_screened_in_pilot=len(set(confirmed_prod) - screened_pilot),
        production_confirmed_by_sector={s: sum(1 for k in confirmed_prod if k[0] == s) for s in design.SECTORS},
        consistent_with_report_rule=mine == (set(confirmed_prod) & screened_pilot),
        production_screened_total=len(screened_prod), production_screened_by_sector={s: sum(1 for k in screened_prod if k[0] == s) for s in design.SECTORS},
        production_undefined=len(undefined_prod))
    # xi_hat distributions per stratum (graph-campaigns) and the per-graph change pilot -> production (two-campaign mean)
    dist = {}
    for s in design.SECTORS:
        for L in design.LOOPS:
            xp = [x['xi_hat'] for k, x in tp.items() if k[1] == s and k[2] == L and x['status'] == 'defined']
            xq = [x['xi_hat'] for k, x in tq.items() if k[1] == s and k[2] == L and x['status'] == 'defined']
            sp = [x['largest_share'] for k, x in tp.items() if k[1] == s and k[2] == L and x['status'] == 'defined']
            sq = [x['largest_share'] for k, x in tq.items() if k[1] == s and k[2] == L and x['status'] == 'defined']
            dx = []
            for k, x in tp.items():
                if k[1] == s and k[2] == L and k[0] == 'a':
                    kb = ('b',) + k[1:]
                    if all(tp[kk]['status'] == 'defined' and tq[kk]['status'] == 'defined' for kk in (k, kb)):
                        dx.append((tp[k]['xi_hat'] + tp[kb]['xi_hat']) / 2 - (tq[k]['xi_hat'] + tq[kb]['xi_hat']) / 2)
            dist[f'{s}_L{L}'] = dict(production_xi=q(xp), pilot_xi=q(xq),
                                     production_frac_xi_gt_0_44=float(np.mean(np.asarray(xp) > 0.44)) if xp else None,
                                     pilot_frac_xi_gt_0_44=float(np.mean(np.asarray(xq) > 0.44)) if xq else None,
                                     production_frac_xi_ge_0_5=float(np.mean(np.asarray(xp) >= 0.5)) if xp else None,
                                     production_largest_share=q(sp), pilot_largest_share=q(sq),
                                     per_graph_change_of_two_campaign_mean_xi=q(dx))
    out['tails']['xi_distributions'] = dist

    # ---------------------------------------------------------------- 2b. does a confirmed tail threaten the SE?
    t1 = time.time()
    var_total = tot_real
    conf = set(confirmed_prod)
    threat = {}
    for s in design.SECTORS:
        keys8 = [k for k in GP if k[1] == s and k[2] == 8]
        kc = [k for k in keys8 if (k[1], k[2], k[3]) in conf]
        kclr = [k for k in keys8 if cls.get((k[1], k[2], k[3]), {}).get('status') == 'cleared']
        kun = [k for k in keys8 if (k[1], k[2], k[3]) not in screened_pilot]
        kbelow = [k for k in keys8 if cls.get((k[1], k[2], k[3]), {}).get('status') == 'below_confirm_points']

        def grow(ks):
            a_ = sum(GP[k]['sp2'] for k in ks if k in GQ)
            b_ = sum(GQ[k]['sp2'] for k in ks if k in GQ)
            return a_ / b_ if b_ else None

        vc = sum(GP[k]['v'] for k in kc)
        v8 = sum(GP[k]['v'] for k in keys8)
        xi_c = [confirmed_prod[(k[1], k[2], k[3])]['xi_mean'] for k in kc if k[0] == 'a']
        # cross split: select on campaign c's production xi_hat > 0.44 (>= CONFIRM points), measure the other campaign's growth
        cross = {}
        for c_sel, c_meas in (('a', 'b'), ('b', 'a')):
            sel_hi, sel_lo = [], []
            for k in keys8:
                if k[0] != c_sel:
                    continue
                x = tp.get(k)
                if x is None or x['status'] != 'defined' or (x['points'] or 0) < CONFIRM:
                    continue
                km = (c_meas,) + k[1:]
                (sel_hi if x['xi_hat'] > design.XI_CONFIRM_MEAN else sel_lo).append(km)
            cross[f'select_{c_sel}_measure_{c_meas}'] = dict(n_heavy=len(sel_hi), n_light=len(sel_lo), growth_heavy=grow(sel_hi), growth_light=grow(sel_lo))
        ratio_pts = [GP[k]['n'] / GQ[k]['n'] for k in kc if k in GQ]
        threat[f'{s}_L8'] = dict(
            confirmed_graphs=len({k[3] for k in kc}), confirmed_graph_campaigns=len(kc),
            confirmed_variance=vc, confirmed_share_of_C8_variance=vc / var_total, confirmed_share_of_stratum_variance=vc / v8 if v8 else None,
            confirmed_se_contribution=math.sqrt(vc),
            largest_single_confirmed_graph_campaign_share_of_C8_variance=max((GP[k]['v'] for k in kc), default=0.) / var_total,
            largest_single_graph_campaign_share_of_C8_variance_any_L8=max((GP[k]['v'] for k in keys8), default=0.) / var_total,
            confirmed_xi_mean=q(xi_c),
            per_point_variance_growth_pooled=dict(confirmed=grow(kc), cleared=grow(kclr), below_confirm_points=grow(kbelow),
                                                  not_screened_in_pilot=grow(kun), all=grow(keys8)),
            point_ratio_production_over_pilot_confirmed=q(ratio_pts, (0.0, 0.5, 1.0)),
            expected_growth_if_xi=dict({f'xi_{x}': 8 ** (2 * x - 1) for x in (0.5, 0.55, 0.6, 0.7)}, note='n^(2 xi - 1) at the point ratio 8 (4,096 -> 32,768)'),
            cross_split=cross,
            replicate_excess_kurtosis=dict(confirmed=excess_kurtosis([GP[k]['y'] for k in kc]),
                                           cleared=excess_kurtosis([GP[k]['y'] for k in kclr]),
                                           not_screened_in_pilot=excess_kurtosis([GP[k]['y'] for k in kun]),
                                           all=excess_kurtosis([GP[k]['y'] for k in keys8])),
            se_if_confirmed_variance_times={str(f): math.sqrt(var_total + (f - 1) * vc) for f in (2, 4, 10)})
    reps = sorted({x['reps'] for x in GP.values()})
    out['tails']['threat'] = threat
    out['tails']['gaussian_excess_kurtosis_reference'] = {str(r): gaussian_kurtosis_reference(r) for r in reps}
    out['tails']['confirmed_list'] = sorted(([k[0], k[1], k[2], v['xi_mean'], v['points']] for k, v in confirmed_prod.items()), key=lambda x: -x[3])[:200]
    out['timing']['threat_s'] = time.time() - t1

    # ---------------------------------------------------------------- 3. cost: busy vs the plan's estimate, lane logs
    m = json.loads((a.run / 'manifest.json').read_bytes())
    est = {}
    for j in m['jobs']:
        est[j['group']] = est.get(j['group'], 0.) + j['est_core_seconds']
    busy = {}
    for g in m['groups']:
        md = json.loads((a.run / 'groups' / g['name'] / 'merged.json').read_bytes())
        busy[g['name']] = dict(thread_seconds=md.get('thread_seconds_sum'), row_seconds=md.get('row_seconds_sum'))
    cost = {}
    for name in sorted(est):
        b = busy.get(name, {}).get('thread_seconds')
        cost[name] = dict(estimate_core_h=est[name] / 3600, busy_thread_core_h=b / 3600 if b else None, ratio=b / est[name] if b else None)
    agg = {}
    for name, x in cost.items():
        c, s, L = name.split('_')
        for key in (f'{s}_{L}', 'total'):
            a_ = agg.setdefault(key, dict(estimate_core_h=0., busy_thread_core_h=0.))
            a_['estimate_core_h'] += x['estimate_core_h']
            a_['busy_thread_core_h'] += x['busy_thread_core_h'] or 0.
    for x in agg.values():
        x['ratio'] = x['busy_thread_core_h'] / x['estimate_core_h']
    pat = re.compile(r'lane (\d+): index (\d+) done in (\d+) s \(estimate (\d+) s, class factor ([\d.]+)\)')
    lanes = {}
    seen = {}
    fails = 0
    for f in sorted((a.run / 'slurm_logs').glob('lane-*.log')):
        jid = f.stem.split('-')[1]
        n = sw = se_ = 0
        for line in f.read_text(errors='replace').splitlines():
            mm = pat.search(line)
            if mm:
                n += 1; sw += int(mm.group(3)); se_ += int(mm.group(4))
                seen.setdefault(int(mm.group(2)), []).append(jid)
            if re.search(r'\bFAILED\b|failed\)|refused', line) and 'finished' not in line:
                fails += 1
        lanes[jid] = dict(indices=n, wall_s=sw, estimate_s=se_, ratio=sw / se_ if se_ else None)
    out['cost'] = dict(per_group=cost, aggregate=agg, lanes=lanes,
                       indices_done=len(seen), indices_done_more_than_once={str(k): v for k, v in seen.items() if len(v) > 1},
                       lane_wall_over_estimate=sum(x['wall_s'] for x in lanes.values()) / sum(x['estimate_s'] for x in lanes.values()),
                       lane_log_failure_like_lines=fails)
    if a.accounting:
        acc = json.loads(a.accounting.read_bytes())
        out['accounting'] = {k: acc.get(k) for k in ('complete', 'allocated_core_hours', 'work_core_hours', 'overhead_core_hours', 'busy_thread_core_hours',
                                                      'eta_node', 'core_hours_by_role', 'ledger_jobs', 'sacct_records', 'checkpoints_with_slurm_id')}
        out['accounting']['busy_over_plan_estimate'] = acc['busy_thread_core_hours'] / agg['total']['estimate_core_h']
        out['accounting']['allocated_over_design_14465'] = acc['allocated_core_hours'] / 14465.356021580961
        out['accounting']['allocated_over_plan_12025'] = acc['allocated_core_hours'] / 12025.121924839943
        out['accounting']['lane_occupancy'] = sum(x['wall_s'] for x in lanes.values()) * 8 / 3600 / acc['work_core_hours']
    out['timing']['total_s'] = time.time() - t0
    a.out.write_text(json.dumps(out, indent=1, default=float))
    # short summary on stdout
    h = out['headline']
    print(f"C8 = {h['C8_full']:.4f} +/- {h['sampling_se']:.4f}; a-b pull {h['campaigns']['pull']:+.2f}; pilot pull {h['pilot']['pull']:+.2f}; "
          f"bootstrap/SE {h['bootstrap']['ratio_to_sampling_se']:.3f}")
    v = out['variance']
    print(f"variance: realized {v['total_realized_group_sums']:.3f} (result {v['result_variance']:.3f}), predicted from pilot sigma {v['total_predicted_from_pilot_sigma']:.3f} "
          f"(SE {v['predicted_se_raw']:.3f}); realized/predicted SE {v['realized_over_predicted_se']:.3f}")
    for k, x in v['strata'].items():
        if x['graph_campaigns']:
            print(f"  {k:10s} share {x['error_by_loop_share']:.4f} realized {x['realized_variance_group_sums']:.4g} (graphs {x['realized_variance_sum_of_graphs']:.4g}, "
                  f"ebl {x['error_by_loop_variance']:.4g}) predicted {x['predicted_variance_from_pilot_sigma']:.4g} ratio {x['realized_over_predicted']:.3f} "
                  f"per-point growth {x['per_point_variance_ratio_pooled']:.3f}")
    t = out['tails']
    print(f"tails: pilot screened {t['pilot_screened']}; production confirmed {t['production_confirmed_total']} ({t['production_confirmed_by_sector']}), "
          f"of them not pilot-screened {t['production_confirmed_not_screened_in_pilot']}; production screened {t['production_screened_total']}; undefined {t['production_undefined']}; "
          f"consistent {t['consistent_with_report_rule']}")
    for k, x in t['followup'].items():
        print(f"  {k}: {x}")
    for k, x in t['threat'].items():
        print(f"  threat {k}: {json.dumps({kk: x[kk] for kk in ('confirmed_graphs', 'confirmed_share_of_C8_variance', 'per_point_variance_growth_pooled', 'cross_split', 'replicate_excess_kurtosis', 'se_if_confirmed_variance_times')}, default=float)}")
    print(f"  gaussian kurtosis reference {t['gaussian_excess_kurtosis_reference']}")
    c = out['cost']
    print(f"cost: busy/estimate {c['aggregate']['total']}; lanes wall/estimate {c['lane_wall_over_estimate']:.3f}; indices {c['indices_done']}, repeated {len(c['indices_done_more_than_once'])}")
    if a.accounting:
        print(f"accounting: {out['accounting']}")
    print(f"timing {out['timing']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
