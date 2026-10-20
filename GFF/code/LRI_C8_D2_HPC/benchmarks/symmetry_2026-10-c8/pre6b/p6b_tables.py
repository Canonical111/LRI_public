#!/usr/bin/env python3
"""pre-Stage-6b symmetry run (Mac, seconds): the fixed tools/design.py of 77fab71 on J-DES-5's real data, against the
pre-Stage-6 freezes of the 23540b2 tool (job 570241) and the Mac recomputation that came with the fix.

  p6b_tables.py --package PKG --des DIR --out FILE.json [--markdown FILE.md]

Inputs (committed records):
  --des DIR   this run's evidence folder (p6bdes.<job>.0: design_<R>_<T>.json, design_meta_<R>_<T>.json,
              compare_<R>_<T>.json, measure_<R>_<T>.json, route_<R>_<T>.json, identity.json); R = x (exact path),
              b (route (b), dd+mp256)
  benchmarks/symmetry_2026-10-c8/pre6/p6_tables.json   the 570241 freezes (exact F11 greedy; route (b) re-optimized
              by the greedy loop; the exact allocation kept and re-costed with the profile model)
  benchmarks/mac_2026-10-c8/f13fix/test_pipeline.json  the fix's Mac recomputation from 570241's committed strata
              (tests/test_pipeline.py, F13_J-DES-5_records_...: the new optimizer's exact and route-(b) designs)

Core-hours: each freeze's own (eta_node 0.306 of the J-SWEEP-2 sweep, which design.py takes from its ledger) and at
J-SMK-4's lane eta_node 0.9146 (x 0.306 / 0.9146; the allocation does not depend on eta_node, a uniform cost scale).
route_b_choice's two branches are converted the same way.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

TARGETS = ['1e-3', '5e-4', '2.5e-4', '1.35e-4']
ETA_LANE = 0.9146050173698389   # J-SMK-4, accounting.py (stage5/des5)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--package', type=Path, default=Path('.')); ap.add_argument('--des', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True); ap.add_argument('--markdown', type=Path)
    a = ap.parse_args(); P = a.package; E = a.des
    p6 = json.loads((P / 'benchmarks/symmetry_2026-10-c8/pre6/p6_tables.json').read_bytes())['freezes']
    mac = next(t for t in json.loads((P / 'benchmarks/mac_2026-10-c8/f13fix/test_pipeline.json').read_bytes())['tests']
               if t.get('test', '').startswith('F13_J-DES-5_records'))
    assert abs(mac['lane_eta'] - ETA_LANE) < 1e-15
    mt = mac['table']
    rec = {'schema': 'c8-d2-pre6b-symmetry-tables-1', 'rule': __doc__, 'evidence': str(E), 'identity': json.loads((E / 'identity.json').read_bytes()),
           'targets': {}}
    lane = lambda ch, eta: ch * eta / ETA_LANE
    for T in TARGETS:
        row = {}
        for R in ('x', 'b'):
            N = f'{R}_{T}'
            d = json.loads((E / f'design_{N}.json').read_bytes()); m = json.loads((E / f'design_meta_{N}.json').read_bytes())
            cmp_ = json.loads((E / f'compare_{N}.json').read_bytes()); me = json.loads((E / f'measure_{N}.json').read_bytes())
            ro = json.loads((E / f'route_{N}.json').read_bytes()); eta = d['eta_node']; opt = m['optimizer']
            v = {'numerics': m['numerics'], 'target_se': m['target']['se'], 'predicted_se': d['predicted']['se_total'],
                 'meets_target': d['predicted']['se_total'] <= m['target']['se'] * (1 + 1e-12),
                 'core_hours_freeze': d['predicted']['cost_total_core_hours'], 'eta_node': eta,
                 'core_hours_lane': lane(d['predicted']['cost_total_core_hours'], eta), 'K': d['batches'], 'K_min': d['batches_minimum'],
                 'r': d['replicates'], 's': {k: x['s'] for k, x in d['strata'].items()},
                 'bundle_caps': d['caps'], 'bundle_caps_ok': bool(d['caps']['ok'] and d['caps']['task_ok']),
                 'optimizer_kept': opt['kept'],
                 'optimizer_starts': {rule: {'greedy_core_hours_lane': lane(st['greedy']['cost_total_core_hours'], eta), 'greedy_se': st['greedy']['se_total'],
                                             'final_core_hours_lane': lane(st['final']['cost_total_core_hours'], eta), 'final_se': st['final']['se_total'],
                                             'caps_ok': st['caps_ok'], 'prune_steps': st['prune_steps'], 'lattice_boxes': st['lattice_boxes'],
                                             'lattice_moves': st['lattice_moves']} for rule, st in opt['starts'].items()},
                 'vs_pre6_570241': {k: cmp_['refs']['pre6_570241'][k] for k in ('counts_equal', 'replicates_equal', 's_equal', 'cost_ratio_new_over_ref', 'se_ratio_new_over_ref')},
                 'plan': {k: me.get(k) for k in ('seed', 'tasks', 'tasks_per_campaign', 'checkpoints', 'indices', 'task_files', 'manifest_bytes', 'plan_wall_seconds',
                                                 'plan_peak_rss_bytes', 'estimated_task_core_hours', 'max_index_wall_seconds', 'predicted_max_task_seconds',
                                                 'merge_passes_max', 'merge_projected_max_seconds', 'projected_files', 'plan_dir_files', 'plan_dir_bytes',
                                                 'caps', 'all_caps_hold', 'executable_sha256', 'cost_model_sha256', 'numerics')},
                 'plan_numerics_route': None if not ro.get('numerics_route') else
                 {k: ro['numerics_route'].get(k) for k in ('route', 'profile', 'executable_sha256', 'executable_gated', 'bundle_approval', 'plan_approval')}}
            if R == 'x':
                v['vs_jdes5_570114'] = {k: cmp_['refs']['jdes5_570114'][k] for k in ('counts_equal', 'replicates_equal', 's_equal', 'cost_ratio_new_over_ref', 'se_ratio_new_over_ref')}
                v['pre6_570241_lane'] = p6[T]['x']['core_hours_lane']; v['pre6_570241_se'] = p6[T]['x']['predicted_se']
                v['mac_prediction_lane'] = mt[T]['exact_new']; v['mac_prediction_se'] = mt[T]['exact_new_se']
                v['matches_mac'] = {'r': d['replicates'] == mt[T]['exact_r'], 's': v['s'] == mt[T]['exact_s'],
                                    'core_hours_rel_diff': v['core_hours_lane'] / mt[T]['exact_new'] - 1, 'se_rel_diff': v['predicted_se'] / mt[T]['exact_new_se'] - 1,
                                    'start_kept': opt['kept'] == mt[T]['exact_kept_start']}
            else:
                ch = m['route_b_choice']; ro_ = ch['reoptimized']; ke = ch.get('kept_exact_allocation') or {}
                v['route_b'] = {'chosen': ch['chosen'], 'mode': ch['mode'],
                                'reoptimized_lane': lane(ro_['cost_total_core_hours'], eta), 'reoptimized_se': ro_['se_total'], 'reoptimized_optimizer_kept': ro_.get('optimizer_kept'),
                                'kept_exact_lane': lane(ke['cost_total_core_hours'], eta) if 'cost_total_core_hours' in ke else None, 'kept_exact_se': ke.get('se_total'),
                                'kept_exact_feasible': ke.get('feasible'), 'kept_exact_caps_ok': ke.get('caps_ok'),
                                'kept_exact_own_exact_lane': lane(ke['exact_cost_total_core_hours'], eta) if 'exact_cost_total_core_hours' in ke else None}
                v['pre6_570241_lane'] = p6[T]['b']['core_hours_lane']; v['pre6_570241_se'] = p6[T]['b']['predicted_se']
                v['pre6_kept_allocation_lane'] = p6[T]['x_allocation_recost_dd_mp256']['core_hours_lane']
                v['mac_prediction'] = {k: mt[T][k] for k in ('route_b_reoptimized', 'route_b_reoptimized_se', 'route_b_new_allocation_kept', 'route_b_chosen', 'route_b_final')}
                v['matches_mac'] = {'chosen': ch['chosen'] == mt[T]['route_b_chosen'], 'final_rel_diff': v['core_hours_lane'] / mt[T]['route_b_final'] - 1,
                                    'reoptimized_rel_diff': v['route_b']['reoptimized_lane'] / mt[T]['route_b_reoptimized'] - 1,
                                    'kept_rel_diff': (v['route_b']['kept_exact_lane'] / mt[T]['route_b_new_allocation_kept'] - 1) if v['route_b']['kept_exact_lane'] else None}
            row[R] = v
        row['b_over_x'] = row['b']['core_hours_lane'] / row['x']['core_hours_lane']
        rec['targets'][T] = row
    a.out.write_text(json.dumps(rec, indent=1, default=float) + '\n')
    if a.markdown:
        L = []
        L.append('| Target | Route | SE (target) | r: free L8 / power L8 | s: free L8 / prim / power L8 | Start kept | Core-h (freeze, η 0.306) | **Lane core-h** (η 0.915) | 570241 (23540b2) | Mac (77fab71 test) | Plan: tasks / checkpoints / indices | Plan wall, RSS | Caps |')
        L.append('|---|---|---:|---|---|---|---:|---:|---:|---:|---|---|---|')
        for T, row in rec['targets'].items():
            for R, lbl in (('x', 'exact'), ('b', 'route (b) `dd+mp256`')):
                v = row[R]; pl = v['plan']
                macv = v['mac_prediction_lane'] if R == 'x' else v['mac_prediction']['route_b_final']
                br = f" ({v['route_b']['chosen'].replace('_', ' ')})" if R == 'b' else ''
                L.append(f"| {T} | {lbl}{br} | {v['predicted_se']:.2f} ({v['target_se']:.2f}) | {v['r']['free_L8']} / {v['r']['power_L8']} | "
                         f"{v['s']['free_L8']} / {v['s']['free_L8_primitive']} / {v['s']['power_L8']} | {v['optimizer_kept']} | {v['core_hours_freeze']:,.0f} | "
                         f"**{v['core_hours_lane']:,.0f}** | {v['pre6_570241_lane']:,.0f} | {macv:,.0f} | {pl['tasks']:,} / {pl['checkpoints']:,} / {pl['indices']:,} | "
                         f"{pl['plan_wall_seconds']:.0f} s, {pl['plan_peak_rss_bytes'] / 2**30:.2f} GiB | {'all hold' if (v['bundle_caps_ok'] and pl['all_caps_hold']) else 'FAIL'} |")
        L.append('')
        L.append('| Target | Route (b): re-optimized (SE) | Exact design kept, re-costed (SE) | Chosen | 570241 route (b) (SE) | 570241 exact allocation kept | Mac: re-optimized / kept / chosen |')
        L.append('|---|---:|---:|---|---:|---:|---|')
        for T, row in rec['targets'].items():
            b = row['b']; rb = b['route_b']; mp = b['mac_prediction']
            L.append(f"| {T} | {rb['reoptimized_lane']:,.0f} ({rb['reoptimized_se']:.2f}) | {rb['kept_exact_lane']:,.0f} ({rb['kept_exact_se']:.2f}) | {rb['chosen'].replace('_', ' ')} | "
                     f"{b['pre6_570241_lane']:,.0f} ({b['pre6_570241_se']:.2f}) | {b['pre6_kept_allocation_lane']:,.0f} | "
                     f"{mp['route_b_reoptimized']:,.0f} / {mp['route_b_new_allocation_kept']:,.0f} / {mp['route_b_chosen'].replace('_', ' ')} |")
        L.append('')
        L.append('| Target | Route | Start | Greedy: lane core-h (SE) | Final: lane core-h (SE) | Prune steps | Lattice boxes / moves | Caps |')
        L.append('|---|---|---|---:|---:|---:|---|---|')
        for T, row in rec['targets'].items():
            for R, lbl in (('x', 'exact'), ('b', 'route (b), re-optimized')):
                if R == 'b' and row['b']['route_b']['chosen'] != 'reoptimized':
                    continue   # the kept exact design carries the exact search's record (the rows above); route_b_choice holds only the re-optimized branch's cost and SE
                for rule, st in row[R]['optimizer_starts'].items():
                    L.append(f"| {T} | {lbl} | {rule}{' (kept)' if rule == row[R]['optimizer_kept'] else ''} | {st['greedy_core_hours_lane']:,.0f} ({st['greedy_se']:.2f}) | "
                             f"{st['final_core_hours_lane']:,.0f} ({st['final_se']:.2f}) | {st['prune_steps']} | {st['lattice_boxes']} / {st['lattice_moves']} | {'ok' if st['caps_ok'] else 'FAIL'} |")
        L.append('')
        L.append('A route-(b) bundle that keeps the exact design records the exact search (the exact rows of the same target); '
                 'its re-optimized branch is recorded in route_b_choice by cost and SE only (the second table).')
        a.markdown.write_text('\n'.join(L) + '\n')
    print(json.dumps({T: {'x_lane': round(r['x']['core_hours_lane'], 1), 'x_se': round(r['x']['predicted_se'], 3), 'x_mac': r['x']['matches_mac'],
                          'b_lane': round(r['b']['core_hours_lane'], 1), 'b_se': round(r['b']['predicted_se'], 3), 'b_chosen': r['b']['route_b']['chosen'],
                          'b_mac': r['b']['matches_mac']} for T, r in rec['targets'].items()}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
