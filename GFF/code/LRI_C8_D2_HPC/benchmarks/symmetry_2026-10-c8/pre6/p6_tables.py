#!/usr/bin/env python3
"""Pre-Stage-6 symmetry run (Mac, seconds): the dd+mp256 profile cost model against the exact symmetry model, and the
J-DES-5 re-check (F11-fixed exact freezes and route-(b) dd+mp256 freezes at the four targets, their test-only plans).

  p6_tables.py --package PKG --sweep DIR --des DIR --out FILE.json [--markdown FILE.md]

Inputs (committed records):
  cost_models/gmp_symmetry_amd_c8.json            the exact symmetry model (J-SWEEP-2, job 570032, <NODE>)
  cost_models/gmp_symmetry_amd_c8_dd+mp256.json   the profile model (this run's sweep; numerics identity dd+mp256)
  inputs/inventory.json                           graphs per (sector, L), the free L8 primitive flag
  --sweep DIR   the profile sweep's evidence folder (p6sweep.<job>.0: manifest.json, binaries.sha256, node.txt)
  --des DIR     the J-DES-5 re-check's evidence folder (p6des.<job>.0: design_<N>.json, design_meta_<N>.json,
                measure_<N>.json, route_<N>.json, compare_des5_<T>.json, accounting_sweepdd.json, bundles.tgz)
  benchmarks/symmetry_2026-10-c8/stage5/pre6/pre6_tables.json   the Mac projections before this run (F11 fix
                applied to J-DES-5's strata; dd+mp256 by the gate 570210's factors k at a fixed allocation)
  benchmarks/symmetry_2026-10-c8/stage5/des5/s5des5.570114.0/design_<T>.json   J-DES-5's four freezes (Stage-5 rule)

Speedups: per (sector, L) and stratum, sum over the graphs of both campaigns of the exact seconds per point over the
profile's (equal points per graph, as A-PERF-5), the per-graph ratio's median and P10-P90, and the ratio at the 1e-3
exact bundle's allocation (counts x s x r per graph). Core-hours: each freeze's own (eta_node 0.306 of the J-SWEEP-2
sweep, which design.py takes from its ledger) and at J-SMK-4's lane eta_node 0.9146 (x 0.306 / 0.9146; the allocation
does not depend on eta_node, a uniform cost scale).
"""
from __future__ import annotations
import argparse, json, math, statistics, sys, tarfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))

TARGETS = ['1e-3', '5e-4', '2.5e-4', '1.35e-4']
SECTORS = ['free', 'power']; LOOPS = [3, 4, 5, 6, 7, 8]
ETA_LANE = 0.9146050173698389   # J-SMK-4, accounting.py (stage5/des5)


def strata_of(inv):
    """(campaign-free) stratum name of every (sector, L, graph)."""
    out = {}
    for s in SECTORS:
        for L in LOOPS:
            for r in inv[s][str(L)]:
                out[(s, L, r['id'])] = f'{s}_L{L}' + ('_primitive' if (s == 'free' and L == 8 and r.get('primitive')) else '')
    return out


def pct(xs, q):
    xs = sorted(xs); k = (len(xs) - 1) * q; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def bundle_counts(tgz: Path, name: str) -> dict:
    out = {}
    with tarfile.open(tgz) as t:
        for m in t.getmembers():
            p = Path(m.name)
            if len(p.parts) >= 4 and p.parts[1] == name and p.parts[2] == 'counts' and m.isfile():
                c, s, L = p.stem.split('_'); L = int(L[1:])
                for ln in t.extractfile(m).read().decode().splitlines():
                    if ln.strip():
                        g, n = ln.split(); out[(c, s, L, int(g))] = int(n)
    return out


def cheapest_last_step(S: dict, target: float, margin: float) -> dict:
    """design.py's optimize() for one batch at a target SE, except that whenever a single doubling of one stratum's s
    meets the target, the cheapest such doubling is taken (the tool takes the most efficient doubling, which may be
    the dominant stratum's; finding F13). Uses the package's own split() and evaluate_design()."""
    import design as D
    o = D.Opts(margin=margin); act = [k for k in S if S[k]['graphs'] and S[k]['V1'] > 0]
    root = sum(math.sqrt(S[k]['V1'] * S[k]['C1']) for k in act); lam = margin ** 2 * root / target ** 2
    m = {k: (lam * math.sqrt(S[k]['V1'] / S[k]['C1']) if k in act else 0.) for k in S}
    r, s = D.split(S, m, o); ev = D.evaluate_design(S, r, s, 1, margin)
    while ev['se_total'] > target * (1 + 1e-12):
        ok = []
        for k in act:
            s2 = dict(s); s2[k] *= 2; e2 = D.evaluate_design(S, r, s2, 1, margin)
            if e2['se_total'] <= target * (1 + 1e-12): ok.append((e2['cost_total_core_hours'], k))
        k = min(ok)[1] if ok else max(act, key=lambda k: (S[k]['V1'] / (2 * r[D.rgroup(k)] * s[k])) / (S[k]['C1'] * r[D.rgroup(k)] * s[k]))
        s[k] *= 2; ev = D.evaluate_design(S, r, s, 1, margin)
    return ev


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--package', type=Path, default=Path('.')); ap.add_argument('--sweep', type=Path, required=True)
    ap.add_argument('--des', type=Path, required=True); ap.add_argument('--out', type=Path, required=True); ap.add_argument('--markdown', type=Path)
    a = ap.parse_args(); P = a.package; E = a.des
    ex = json.loads((P / 'cost_models/gmp_symmetry_amd_c8.json').read_bytes())
    pr = json.loads((P / 'cost_models/gmp_symmetry_amd_c8_dd+mp256.json').read_bytes())
    inv = json.loads((P / 'inputs/inventory.json').read_bytes()); st = strata_of(inv)
    pre = json.loads((P / 'benchmarks/symmetry_2026-10-c8/stage5/pre6/pre6_tables.json').read_bytes())
    ke, kp = ex['seconds_per_point'], pr['seconds_per_point']
    assert set(ke) == set(kp) and len(kp) == 48346, 'the two models must hold the same 48,346 keys'
    rec = {'schema': 'c8-d2-pre6-symmetry-tables-1', 'rule': __doc__,
           'models': {'exact': {k: ex.get(k) for k in ('numerics', 'executable_sha256', 'cpu_models', 'hosts', 'job_ids', 'keys', 'source_campaign')},
                      'dd+mp256': {k: pr.get(k) for k in ('numerics', 'executable_sha256', 'cpu_models', 'hosts', 'job_ids', 'keys', 'source_campaign', 'note')}}}
    # ---- speedups
    x1 = bundle_counts(E / 'bundles.tgz', 'p6x_1e-3'); d1 = json.loads((E / 'design_p6x_1e-3.json').read_bytes())
    def alloc(c, s, L, g):
        sn = st[(s, L, g)]; return x1[(c, s, L, g)] * d1['strata'][sn]['s'] * d1['replicates'][f'{s}_L{L}']
    groups = {}
    for k in ke:
        c, s, L, g = k.split(':'); L = int(L); g = int(g); sn = st[(s, L, g)]
        for key in {f'{s}_L{L}', sn}:
            G = groups.setdefault(key, {'e': 0., 'p': 0., 'we': 0., 'wp': 0., 'r': [], 'n': 0, 'by_c': {}})
            G['e'] += ke[k]; G['p'] += kp[k]; G['r'].append(ke[k] / kp[k]); G['n'] += 1
            w = alloc(c, s, L, g); G['we'] += w * ke[k]; G['wp'] += w * kp[k]
            C = G['by_c'].setdefault(c, [0., 0.]); C[0] += ke[k]; C[1] += kp[k]
    tot = {'e': sum(ke.values()), 'p': sum(kp.values())}
    kgate = pre['k_symmetry_dd_mp256']
    sp = {}
    for key in [f'{s}_L{L}' for s in SECTORS for L in LOOPS] + ['free_L8_primitive', 'free_L8_rest']:
        if key == 'free_L8_rest':
            G0 = groups['free_L8']; Gp = groups['free_L8_primitive']
            G = {'e': G0['e'] - Gp['e'], 'p': G0['p'] - Gp['p'], 'we': G0['we'] - Gp['we'], 'wp': G0['wp'] - Gp['wp'], 'n': G0['n'] - Gp['n'],
                 'r': None, 'by_c': {}}
            prim = {(c, int(g)) for k in ke for c, s_, L_, g in [k.split(':')] if s_ == 'free' and L_ == '8' and st[('free', 8, int(g))] == 'free_L8_primitive'}
            G['r'] = [ke[k] / kp[k] for k in ke if k.split(':')[1:3] == ['free', '8'] and (k.split(':')[0], int(k.split(':')[3])) not in prim]
        else:
            G = groups[key]
        sp[key] = {'keys': G['n'], 'exact_s_per_point_sum': G['e'], 'profile_s_per_point_sum': G['p'], 'speedup_equal_points': G['e'] / G['p'],
                   'speedup_at_1e-3_allocation': G['we'] / G['wp'] if G['wp'] else None,
                   'per_graph_median': statistics.median(G['r']), 'per_graph_p10': pct(G['r'], .1), 'per_graph_p90': pct(G['r'], .9),
                   'by_campaign': {c: v[0] / v[1] for c, v in sorted(G['by_c'].items())},
                   'gate_570210_k': kgate.get(key)}
    rec['speedup'] = {'per_stratum': sp, 'all_equal_points': tot['e'] / tot['p'],
                      'rule': 'exact seconds per point / dd+mp256 seconds per point, summed over the keys (both campaigns); gate k: '
                              'stage5/pre6 (F4 at L8, F2 task seconds at L <= 7, job 570210)'}
    # ---- the profile sweep
    sm = json.loads((a.sweep / 'manifest.json').read_bytes())
    acc = json.loads((E / 'accounting_sweepdd.json').read_bytes())
    rec['sweep'] = {'campaign': pr['source_campaign'], 'evidence': str(a.sweep), 'seed': sm['seed'], 'numerics': sm['numerics'], 'approved_numerics_change': sm.get('approved_numerics_change'),
                    'executable_sha256': sm['executable_sha256'], 'indices': len(sm['jobs']), 'tasks': sum(j['tasks'] for j in sm['jobs']),
                    'accounting': {k: acc.get(k) for k in ('eta_node', 'allocated_core_hours', 'work_core_hours', 'busy_thread_core_hours', 'core_hours_by_role')}}
    # ---- freezes
    lit = lambda d: d['predicted']['cost_total_core_hours']
    fr = {}
    for T in TARGETS:
        row = {}
        for R in ('x', 'b'):
            N = f'p6{R}_{T}'; d = json.loads((E / f'design_{N}.json').read_bytes()); m = json.loads((E / f'design_meta_{N}.json').read_bytes())
            me = json.loads((E / f'measure_{N}.json').read_bytes()); ro = json.loads((E / f'route_{N}.json').read_bytes())
            eta = d['eta_node']
            row[R] = {'numerics': m['numerics'], 'route': (m.get('profile_recost') or {}).get('route'), 'target_se': m['target']['se'],
                      'predicted_se': d['predicted']['se_total'], 'core_hours_freeze': lit(d), 'eta_node': eta,
                      'core_hours_lane': lit(d) * eta / ETA_LANE, 'K': d['batches'], 'K_min': d['batches_minimum'],
                      'r': d['replicates'], 's': {k: v['s'] for k, v in d['strata'].items()}, 'caps_ok': bool(d['caps']['ok'] and d['caps']['task_ok']),
                      'design_meta_sha256': me['bundle_design_meta_sha256'],
                      'cost_model_sha256': ((m.get('profile_recost') or {}).get('cost_model') or {}).get('sha256'),
                      'gates': [{k: g.get(k) for k in ('sha256', 'slurm_job', 'profile_executable_sha256')} for g in (m.get('profile_recost') or {}).get('gates', [])],
                      'plan': {k: me.get(k) for k in ('seed', 'tasks', 'tasks_per_campaign', 'checkpoints', 'indices', 'tasks_sqlite_bytes_total', 'tasks_sqlite_bytes_max_group',
                                                      'task_files', 'task_files_bytes', 'manifest_bytes', 'plan_wall_seconds', 'plan_peak_rss_bytes',
                                                      'estimated_task_core_hours', 'max_index_wall_seconds', 'predicted_max_task_seconds', 'merge_passes_max',
                                                      'merge_projected_max_seconds', 'projected_files', 'plan_dir_files', 'plan_dir_bytes', 'all_caps_hold',
                                                      'executable_sha256', 'cost_model_sha256', 'numerics')},
                      'plan_numerics_route': None if not ro.get('numerics_route') else
                      {k: ro['numerics_route'].get(k) for k in ('route', 'profile', 'executable_sha256', 'executable_gated', 'bundle_approval', 'plan_approval')}}
        row['x']['vs_des5'] = json.loads((E / f'compare_des5_{T}.json').read_bytes())
        p = pre['targets'][T]
        row['projection_stage5_pre6'] = {'f11_fixed_literal': p['f11_fixed']['literal_core_hours'], 'f11_fixed_symmetry_lane': p['f11_fixed']['symmetry_core_hours'],
                                         'f11_fixed_se': p['f11_fixed']['predicted_se_total'], 'dd_mp256_symmetry_own_k': p['f11_fixed']['dd_mp256_symmetry_own_k'],
                                         'stage5_symmetry_lane': p['stage5_freeze']['symmetry_core_hours'], 'continuous_symmetry_lane': p['continuous_symmetry_core_hours']}
        row['x']['matches_projection'] = (row['x']['r'] == p['f11_fixed']['r'] and row['x']['s'] == p['f11_fixed']['s']
                                          and abs(row['x']['core_hours_freeze'] - p['f11_fixed']['literal_core_hours']) < 1e-6 * p['f11_fixed']['literal_core_hours'])
        row['b_over_x'] = row['b']['core_hours_freeze'] / row['x']['core_hours_freeze']
        row['b_over_projection'] = row['b']['core_hours_lane'] / p['f11_fixed']['dd_mp256_symmetry_own_k']
        # F13 analysis: each freeze against its own continuous Neyman bound (from its strata V1, C1), the target loop
        # with a cheapest-sufficient last step (tools/design.py's split and evaluate_design, the same strata), and the
        # exact F11-fixed allocation kept and re-costed with the measured profile model (the stage5/pre6 projection's
        # method with the measured kappa instead of the gate's k; its SE stays the exact design's)
        dx = json.loads((E / f'design_p6x_{T}.json').read_bytes()); xc = bundle_counts(E / 'bundles.tgz', f'p6x_{T}')
        for R in ('x', 'b'):
            d = json.loads((E / f'design_p6{R}_{T}.json').read_bytes()); S = {k: dict(v) for k, v in d['strata'].items()}
            for v in S.values(): v.setdefault('V1_imputed', 0.)
            root = sum(math.sqrt(v['V1'] * v['C1']) for v in S.values() if v['graphs'] and v['V1'] > 0)
            cont = d['predicted']['variance_margin'] ** 2 * root ** 2 / row[R]['target_se'] ** 2 / 3600
            ev = cheapest_last_step(S, row[R]['target_se'], d['predicted']['variance_margin'])
            row[R]['continuous_core_hours_lane'] = cont * d['eta_node'] / ETA_LANE
            row[R]['over_continuous'] = row[R]['core_hours_freeze'] / cont
            row[R]['cheapest_last_step'] = {'core_hours_lane': ev['cost_total_core_hours'] * d['eta_node'] / ETA_LANE, 'se': ev['se_total'],
                                            'over_continuous': ev['cost_total_core_hours'] / cont}
        num = {'e': 0., 'p': 0.}
        for (c, s_, L, g), n in xc.items():
            sn = st[(s_, L, g)]; w = n * dx['strata'][sn]['s'] * dx['replicates'][f'{s_}_L{L}'] / dx['eta_omp'][f'{c}_{s_}_L{L}']
            k = f'{c}:{s_}:{L}:{g}'; num['e'] += w * ke[k]; num['p'] += w * kp[k]
        row['x_allocation_recost_dd_mp256'] = {'ratio': num['p'] / num['e'], 'core_hours_lane': row['x']['core_hours_lane'] * num['p'] / num['e'],
                                               'se': row['x']['predicted_se']}
        fr[T] = row
    rec['freezes'] = fr
    a.out.write_text(json.dumps(rec, indent=1, default=float) + '\n')
    if a.markdown:
        L = []
        L.append('| Sector, L | graphs (a+b) | exact / dd+mp256, equal points | at the 1e-3 allocation | per graph: median (P10-P90) | a / b | gate 570210 k |')
        L.append('|---|---:|---:|---:|---|---|---:|')
        for key, v in sp.items():
            L.append(f"| {key.replace('_', ' ')} | {v['keys']:,} | ×{v['speedup_equal_points']:.3f} | "
                     f"{'×%.3f' % v['speedup_at_1e-3_allocation'] if v['speedup_at_1e-3_allocation'] else ''} | ×{v['per_graph_median']:.2f} ({v['per_graph_p10']:.2f}-{v['per_graph_p90']:.2f}) | "
                     f"{' / '.join('×%.3f' % x for x in v['by_campaign'].values())} | {'×%.3f' % v['gate_570210_k'] if v['gate_570210_k'] else ''} |")
        L.append(f"| all | {len(ke):,} | ×{rec['speedup']['all_equal_points']:.3f} | | | | |")
        L.append('')
        L.append('| Target | Route | SE (target) | K | r free L8 / power L8 | s free L8 / prim / power L8 | Core-h (freeze, η 0.306) | Lane core-h (η 0.915) | Projection (stage5/pre6) | Plan: tasks / checkpoints / indices | Plan wall, RSS | Caps |')
        L.append('|---|---|---:|---:|---|---|---:|---:|---:|---|---|---|')
        for T, row in fr.items():
            for R, lbl, proj in (('x', 'exact (F11 fixed)', row['projection_stage5_pre6']['f11_fixed_symmetry_lane']), ('b', 'route (b) dd+mp256', row['projection_stage5_pre6']['dd_mp256_symmetry_own_k'])):
                v = row[R]; pl = v['plan']
                L.append(f"| {T} | {lbl} | {v['predicted_se']:.2f} ({v['target_se']:.2f}) | {v['K']} | {v['r']['free_L8']} / {v['r']['power_L8']} | "
                         f"{v['s']['free_L8']} / {v['s']['free_L8_primitive']} / {v['s']['power_L8']} | {v['core_hours_freeze']:,.0f} | **{v['core_hours_lane']:,.0f}** | {proj:,.0f} | "
                         f"{pl['tasks']:,} / {pl['checkpoints']:,} / {pl['indices']:,} | {pl['plan_wall_seconds']:.0f} s, {pl['plan_peak_rss_bytes'] / 2**30:.2f} GiB | "
                         f"{'all hold' if (v['caps_ok'] and pl['all_caps_hold']) else 'FAIL'} |")
        L.append('')
        L.append('| Target | Route | Freeze, lane core-h (SE) | Continuous Neyman bound | Freeze / bound | Cheapest-sufficient last step (SE, / bound) | Exact allocation re-costed under dd+mp256 (SE) |')
        L.append('|---|---|---:|---:|---:|---:|---:|')
        for T, row in fr.items():
            for R, lbl in (('x', 'exact (F11 fixed)'), ('b', 'route (b) dd+mp256')):
                v = row[R]; c = v['cheapest_last_step']; xa = row['x_allocation_recost_dd_mp256']
                xs = '{:,.0f} (×{:.3f}; SE {:.2f})'.format(xa['core_hours_lane'], xa['ratio'], xa['se']) if R == 'b' else ''
                L.append(f"| {T} | {lbl} | {v['core_hours_lane']:,.0f} ({v['predicted_se']:.2f}) | {v['continuous_core_hours_lane']:,.0f} | ×{v['over_continuous']:.2f} | "
                         f"{c['core_hours_lane']:,.0f} ({c['se']:.2f}, ×{c['over_continuous']:.2f}) | {xs} |")
        a.markdown.write_text('\n'.join(L) + '\n')
    print(json.dumps({T: {'x_lane': round(fr[T]['x']['core_hours_lane'], 1), 'x_se': round(fr[T]['x']['predicted_se'], 2), 'b_lane': round(fr[T]['b']['core_hours_lane'], 1),
                          'b_se': round(fr[T]['b']['predicted_se'], 2), 'b/x': round(fr[T]['b_over_x'], 4), 'x_matches_projection': fr[T]['x']['matches_projection']} for T in TARGETS}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
