#!/usr/bin/env python3
"""Post-pilot analysis of the C8(2) L8 pilot (2026-10-06): the numbers the design report and the freezes do not print.

  pa_analysis.py --package PKG --run PILOT --sweep SWEEP2 --accounting ACC.json --bundles DIR [DIR ...] --out OUT.json

Runs inside the analysis job (pa.slurm) with the export's tools on sys.path; reads only (the pilot, the sweep, the
bundles, the cost models). Nothing it computes changes a bundle.

1. Per index: the plan's estimate (manifest est_core_seconds; lane-wall estimate est / (8 x 0.9)) against the measured
   lane wall of the lane logs ("index N done in X s"), and per group the plan's core-hours against the merged
   row and thread seconds (merged.json).
2. Pilot efficiencies: eta_node (accounting.py: busy thread-seconds / allocated lane core-seconds), the lane occupancy
   (sum of index lane walls x 8 / allocated lane core-seconds) and the in-index efficiency (busy / (sum of index lane
   walls x 8)); eta_node = occupancy x in-index efficiency.
3. Per bundle (frozen by pa.slurm): points, tasks, checkpoints and indices (production.plan's index sizing:
   nshards = ceil(secs / (1.5 h x 8 x 0.9)) per group, secs = sum of r x count x s x c_g with the design's own c_g:
   the pilot's measured costs on the exact path, the profile cost model's under route (b)), and the wall on N = 4, 8,
   16 amdq nodes of 8 x 8 lanes: the indices heaviest first, each onto the lane that frees first, at
   (secs / nshards) / (8 x eta_omp,g x E) per index, for two efficiency models E:
     - "design": E = the pilot's eta_node (the index walls then sum to the design's lane core-hours / 8; the pilot's
       own tail idle is inside eta_node, so this double-counts a tail and is the pessimistic wall);
     - "steady": E = the pilot's in-index efficiency (no idle inside an index; the tail is the schedule's own), whose
       allocation is wall x 64 x N (an upper bound: a worker exits when its lanes find nothing left).
   Expanse: the ratio of the bundle's work under the Expanse exact cost model to the same work under the symmetry
   exact cost model (same counts, r, s; seconds per point per graph), i.e. Expanse SU per symmetry core-hour at equal
   node efficiency (exact path only: dd+mp256 is gated on symmetry only).
4. The stand-in comparison: the per-graph continuous Neyman bound
   cost(SE) = margin^2 (sum_g 0.5 sigma_g sqrt(c_g / eta_omp,g))^2 / (SE^2 eta_node) of the J-SWEEP-2 sweep (the
   stand-in of J-DES-5: 2 replicates x 512 points) and of the pilot (8 x 4,096), with the chain stand-in -> pilot
   costs (c_g / eta_omp,g of the pilot, sigma of the sweep) -> pilot sigma, so that the cost ratio splits into a
   cost-model factor and a variance factor; per stratum also sum_g sigma_g^2 (an unbiased variance sum at any number of
   replicates) and sum_g sigma_g sqrt(c_g) (biased low by E[sqrt(chi2_nu / nu)]: 0.798 at nu = 1, 0.965 at nu = 7).
"""
from __future__ import annotations
import argparse, glob, hashlib, heapq, json, math, re, sys
from pathlib import Path


def lpt(durations, lanes):
    h = [(0., k) for k in range(lanes)]; heapq.heapify(h); end = 0.
    for d in sorted(durations, reverse=True):
        t, k = heapq.heappop(h); t += d; end = max(end, t); heapq.heappush(h, (t, k))
    return end


def e_sqrt_chi(nu):  # E[sqrt(chi2_nu / nu)]
    return math.sqrt(2. / nu) * math.exp(math.lgamma((nu + 1) / 2) - math.lgamma(nu / 2))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--package', type=Path, required=True); ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--sweep', type=Path, required=True); ap.add_argument('--accounting', type=Path, required=True)
    ap.add_argument('--bundles', type=Path, nargs='+', required=True); ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--margin', type=float, default=1.5); ap.add_argument('--c8', type=float, default=4.6e4)
    a = ap.parse_args()
    sys.path.insert(0, str(a.package / 'tools'))
    import design
    RUN = a.run.resolve(); out = {'schema': 'c8-d2-pilot-analysis-1', 'rule': __doc__, 'run': str(RUN)}
    m = json.loads((RUN / 'manifest.json').read_bytes()); acc = json.loads(a.accounting.read_bytes())

    # 1. per index and per group
    done = {}
    for f in sorted(glob.glob(str(RUN / 'slurm_logs/lane-*.log'))):
        job = re.search(r'lane-(\d+)\.log', f).group(1)
        for line in open(f):
            x = re.match(r'lane (\d+): index (\d+) done in (\d+) s \(estimate (\d+) s, class factor ([\d.]+)\)', line)
            if x: done[int(x.group(2))] = dict(job=job, lane=int(x.group(1)), wall_s=int(x.group(3)), lane_estimate_s=int(x.group(4)), class_factor=float(x.group(5)))
    idx = []
    for j in m['jobs']:
        d = done.get(j['id'], {}); est = j['est_core_seconds']
        idx.append(dict(index=j['id'], group=j['group'], L=j['L'], tasks=j['tasks'], est_core_seconds=est, est_lane_wall_s=est / (8 * 0.9),
                        measured_lane_wall_s=d.get('wall_s'), job=d.get('job'), lane=d.get('lane'),
                        ratio_measured_over_est_wall=(d['wall_s'] / (est / (8 * 0.9)) if d.get('wall_s') and est > 1 else None)))
    grp = {}
    for g in m['groups']:
        md = json.loads((RUN / 'groups' / g['name'] / 'merged.json').read_bytes())
        e = m['estimates']['groups'][g['name']]['core_hours']
        grp[g['name']] = dict(est_core_hours=e, row_core_hours=md['row_seconds_sum'] / 3600, thread_core_hours=md['thread_seconds_sum'] / 3600,
                              eta_omp=md['row_seconds_sum'] / md['thread_seconds_sum'] if md['thread_seconds_sum'] else None,
                              ratio_thread_over_est=(md['thread_seconds_sum'] / 3600 / e if e > 1e-3 else None))
    lane_wall_sum = sum(d['wall_s'] for d in done.values())
    byL = {}
    for x in idx:
        r = byL.setdefault(f'L{x["L"]}', dict(indices=0, est_lane_wall_h=0., measured_lane_wall_h=0.))
        r['indices'] += 1; r['est_lane_wall_h'] += x['est_lane_wall_s'] / 3600; r['measured_lane_wall_h'] += (x['measured_lane_wall_s'] or 0) / 3600
    for v in byL.values(): v['ratio'] = v['measured_lane_wall_h'] / v['est_lane_wall_h'] if v['est_lane_wall_h'] > 0 else None
    busy = acc['busy_thread_core_hours'] * 3600; work = acc['work_core_hours'] * 3600
    eff = dict(eta_node=acc['eta_node'], busy_thread_core_hours=busy / 3600, work_core_hours=work / 3600, allocated_core_hours=acc['allocated_core_hours'],
               lane_wall_core_hours=lane_wall_sum * 8 / 3600, lane_occupancy=lane_wall_sum * 8 / work, in_index_efficiency=busy / (lane_wall_sum * 8),
               plan_estimate_core_hours=m['estimates']['total_core_hours'],
               busy_over_estimate=busy / 3600 / m['estimates']['total_core_hours'],
               lane_wall_over_estimate=(lane_wall_sum * 8 / 3600) / (m['estimates']['total_core_hours'] / 0.9))
    out['per_index'] = idx; out['per_group'] = grp; out['by_L'] = byL; out['efficiency'] = eff
    print('efficiency', json.dumps(eff))

    # 2. per bundle
    P = design.load_pilot(RUN); T_exact = design.graph_table(P)
    cm_sym = json.loads((a.package / 'cost_models/gmp_symmetry_amd_c8.json').read_bytes())['seconds_per_point']
    cm_exp = json.loads((a.package / 'cost_models/gmp_expanse_amd_c8.json').read_bytes())['seconds_per_point']
    cm_dd = json.loads((a.package / 'cost_models/gmp_symmetry_amd_c8_dd+mp256.json').read_bytes())['seconds_per_point']
    T_dd = design.graph_table(P, costs={(c, s, L, g): cm_dd[f'{c}:{s}:{L}:{g}'] for (c, s, L) in P.groups for g in (r['id'] for r in P.inventory[s][str(L)])})
    prim = {(s, L): {r['id']: bool(r.get('primitive')) for r in P.inventory[s][str(L)]} for s in design.SECTORS for L in design.LOOPS}
    E_design = acc['eta_node']; E_steady = eff['in_index_efficiency']
    bundles = {}
    for B in a.bundles:
        B = B.resolve(); d = json.loads((B / 'design.json').read_bytes()); meta = json.loads((B / 'design_meta.json').read_bytes())
        T = T_dd if meta['numerics'] != 'exact' else T_exact
        r = d['replicates']; s = {k: v['s'] for k, v in d['strata'].items()}
        points = 0; durs = {'design': [], 'steady': []}; nidx = 0; groups = {}; w_sym = w_exp = w_des = 0.
        for (c, sec, L), G in sorted(P.groups.items()):
            name = f'{c}_{sec}_L{L}'; cnt = {}
            for line in (B / 'counts' / f'{name}.txt').read_text().splitlines():
                g, n = line.split(); cnt[int(g)] = int(n)
            rr = r[f'{sec}_L{L}']; secs = 0.; pts = 0
            for g, n in cnt.items():
                st = design.stratum_of(sec, L, prim[(sec, L)].get(g, False)); npts = rr * n * s[st]; pts += npts
                secs += npts * T[(c, sec, L)][g]['cost']
                w_sym += npts * cm_sym[f'{c}:{sec}:{L}:{g}']; w_exp += npts * cm_exp[f'{c}:{sec}:{L}:{g}']
            ns = max(1, math.ceil(secs / (1.5 * 3600 * 8 * 0.9))); nidx += ns; points += pts
            w_des += secs / (G.eta_omp * E_design)
            for k, E in (('design', E_design), ('steady', E_steady)):
                durs[k] += [secs / ns / (8 * G.eta_omp * E)] * ns
            groups[name] = dict(points=pts, task_core_hours=secs / 3600, indices=ns, index_lane_wall_h=secs / ns / (8 * G.eta_omp * E_steady) / 3600)
        cost = d['predicted']['cost_total_core_hours']
        walls = {}
        for N in (4, 8, 16):
            wd = lpt(durs['design'], 8 * N); ws = lpt(durs['steady'], 8 * N)
            walls[str(N)] = dict(wall_h_design_eta=wd / 3600, wall_h_steady=ws / 3600, ideal_h_design_eta=cost / (64 * N),
                                 allocated_core_hours_steady=ws * 64 * N / 3600, steady_lane_occupancy=sum(durs['steady']) / (ws * 8 * N))
        tgt = meta['target']
        bundles[B.name] = dict(path=str(B), design_meta_sha256=hashlib.sha256((B / 'design_meta.json').read_bytes()).hexdigest(),
                               numerics=meta['numerics'], target_rel=tgt['rel'], target_se=tgt['se'], predicted_se=d['predicted']['se_total'],
                               predicted_se_raw=d['predicted']['se_raw_total'], relative_se=d['predicted']['se_total'] / a.c8,
                               core_hours=cost, check_lane_core_hours=w_des / 3600, batches=d['batches'], batches_minimum=d['batches_minimum'],
                               replicates=r, s=s, points=points, indices=nidx, tasks_per_campaign=d['caps']['tasks_per_campaign'],
                               checkpoints=d['caps']['checkpoints'], predicted_max_index_wall_seconds=d['caps']['predicted_max_index_wall_seconds'],
                               work_core_hours_steady=sum(durs['steady']) * 8 / 3600, walls=walls,
                               expanse_over_symmetry_cost_model=w_exp / w_sym,
                               route_b_choice=(meta.get('route_b_choice') or {}).get('chosen'), optimizer_kept=meta['optimizer']['kept'],
                               spent_core_hours=meta['spent_core_hours'], total_cap=meta['total_cap'], eta_node=meta['eta_node'])
        print(B.name, json.dumps({k: bundles[B.name][k] for k in ('core_hours', 'predicted_se', 'batches', 'points', 'indices', 'expanse_over_symmetry_cost_model')}),
              json.dumps({N: round(w['wall_h_design_eta'], 2) for N, w in walls.items()}), json.dumps({N: round(w['wall_h_steady'], 2) for N, w in walls.items()}))
    out['bundles'] = bundles

    # 3. stand-in comparison
    SW = design.load_pilot(a.sweep.resolve()); T_sw = design.graph_table(SW)
    reps = {'pilot': sorted({G.reps for G in P.groups.values()}), 'sweep': sorted({G.reps for G in SW.groups.values()})}
    pts = {'pilot': sorted({n for G in P.groups.values() for n in G.points.values()}), 'sweep': sorted({n for G in SW.groups.values() for n in G.points.values()})}
    strata = {st: dict(S0=0., S1=0., S2=0., U_pilot=0., U_sweep=0., N_pilot=0., N_sweep=0., c_pilot=0., c_sweep=0., graphs=0) for st in design.strata_names()}
    for key, TT in T_exact.items():
        Gp = P.groups[key]; Gs = SW.groups[key]; Ts = T_sw[key]
        for g, x in TT.items():
            y = Ts[g]; o = strata[x['stratum']]; o['graphs'] += 1
            o['S0'] += .5 * y['sigma'] * math.sqrt(y['cost'] / Gs.eta_omp); o['S1'] += .5 * y['sigma'] * math.sqrt(x['cost'] / Gp.eta_omp)
            o['S2'] += .5 * x['sigma'] * math.sqrt(x['cost'] / Gp.eta_omp)
            o['U_pilot'] += x['sigma'] ** 2; o['U_sweep'] += y['sigma'] ** 2
            o['N_pilot'] += x['sigma'] * math.sqrt(x['cost']); o['N_sweep'] += y['sigma'] * math.sqrt(y['cost'])
            o['c_pilot'] += x['cost']; o['c_sweep'] += y['cost']
    tot = {k: sum(v[k] for v in strata.values()) for k in ('S0', 'S1', 'S2')}
    eta_ref = 0.9146050173698389  # J-SMK-4 lane eta_node, used by every stand-in lane table
    bound = lambda S, se, eta: a.margin ** 2 * S ** 2 / (se ** 2 * eta) / 3600
    targets = {}
    for rel in (1e-3, 5e-4, 2.5e-4, 1.35e-4):
        se = rel * a.c8
        targets[f'{rel:g}'] = dict(standin_bound_lane=bound(tot['S0'], se, eta_ref), pilot_costs_standin_sigma_lane=bound(tot['S1'], se, eta_ref),
                                   pilot_bound_lane_eta_ref=bound(tot['S2'], se, eta_ref), pilot_bound_pilot_eta=bound(tot['S2'], se, E_design))
    out['standin'] = dict(sweep=str(a.sweep.resolve()), replicates=reps, points_per_replicate=pts, eta_ref=eta_ref, eta_pilot=E_design,
                          factors=dict(cost_model=(tot['S1'] / tot['S0']) ** 2, variance=(tot['S2'] / tot['S1']) ** 2, eta_node=eta_ref / E_design,
                                       total=(tot['S2'] / tot['S0']) ** 2 * eta_ref / E_design),
                          jensen=dict(nu_sweep=reps['sweep'][0] - 1, nu_pilot=reps['pilot'][0] - 1, e_sqrt_sweep=e_sqrt_chi(reps['sweep'][0] - 1),
                                      e_sqrt_pilot=e_sqrt_chi(reps['pilot'][0] - 1),
                                      expected_variance_factor_from_bias=(e_sqrt_chi(reps['pilot'][0] - 1) / e_sqrt_chi(reps['sweep'][0] - 1)) ** 2),
                          strata={st: dict(v, variance_factor=(v['S2'] / v['S1']) ** 2 if v['S1'] else None, cost_factor=(v['S1'] / v['S0']) ** 2 if v['S0'] else None,
                                           U_ratio=v['U_pilot'] / v['U_sweep'] if v['U_sweep'] else None,
                                           share_pilot=v['S2'] / tot['S2'], share_standin=v['S0'] / tot['S0']) for st, v in strata.items()},
                          targets=targets)
    print('standin factors', json.dumps(out['standin']['factors']), json.dumps(out['standin']['jensen']))
    for st, v in out['standin']['strata'].items():
        print(f'  {st:18s} share pilot {v["share_pilot"]:.3f} stand-in {v["share_standin"]:.3f} variance x{(v["variance_factor"] or 0):.3f} cost x{(v["cost_factor"] or 0):.3f} '
              f'U ratio {(v["U_ratio"] or 0):.3f}')
    a.out.write_text(json.dumps(out, indent=1, default=float) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
