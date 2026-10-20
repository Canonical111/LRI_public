#!/usr/bin/env python3
"""A-FLAG-7 table of the Stage-4c gate (J-FLAG): per opt-in profile, F1-F5 from its full-scale numerics_flags.json and
the projected core-hours at the four relative targets 1e-3, 5e-4, 2.5e-4 and 1.35e-4 of |C8| (4.6e4).

Cost base (the default binary): the test-only freezes of the fresh exact sweep of R7's validation (final default
binary bin/c8d2_gmp 1d2a2181, all graphs, 2 x 512 points, one eta_node 0.481; Expanse job 54673870,
dev_r7/expanse/r7refreeze.54673870.0/exact_eqeta_<target>_design.json). Each of its 13 strata carries s, C1 (allocated
core-seconds per replicate at s = 1) and the replicates r of its (sector, L); allocated core-hours = sum r s C1 / 3600
(checked against the freeze's total).

A numerics profile changes the cost per point, not the integrand (F2 bounds the difference), so the projection keeps
the variance and divides each stratum's cost by the profile's measured speedup k (exact / profile time):
  L8 strata (free L8, the free L8 primitives, power L8): F4's median lane-thread speedup of the sector on the L8 sweep
      sample (2,000 graphs, rate .8);
  L <= 7: F2's task seconds of that (sector, L), both campaigns pooled (the paired blocks, run back to back).
Two numbers per target: "same allocation" sum r s C1 / k (the frozen counts kept, only cheaper) and "Neyman"
the continuous re-optimized ratio (sum_s w_s / sqrt(k_s))^2 (w_s = sqrt(V1 C1) shares) times the exact total.
F4's lane wall time includes start-up and graph loading of 512-point tasks, so it is the conservative basis; the
record also gives "projection_f2_only", every stratum from F2's integration-only task seconds (closer to production's
long tasks).
R7 (rates) changes the integrand: its row is the measured fresh-under-map freezes against the exact freezes with the
same eta_node (A-FLAG-6, job 54673870), not a speedup projection.

  aflag7_table.py --gate DIR --r7 DIR --out FILE.json [--markdown FILE.md]
DIR (--gate): searched for numerics_flags.json records (the F1-baseline-only record excluded): the full gate runs in
directories named jflag_<profile> (jflag_dd, jflag_mp256, jflag_exp1, jflag_dd_mp256_exp1), and controls (any other
name, e.g. layout_stub_dd, an F4-only run of the framework's all-stub dd executable).
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path

TARGETS = ('1e-3', '5e-4', '2.5e-4', '1.35e-4')
PROFILES = ('dd', 'mp256', 'exp1', 'dd+mp256+exp1')


def load(p: Path):
    return json.loads(p.read_text())


def stratum_key(name: str) -> tuple[str, int]:
    s, l = name.split('_')[:2]
    return s, int(l[1:])


def base_tables(r7: Path) -> dict:
    out = {}
    for t in TARGETS:
        d = load(r7 / f'exact_eqeta_{t}_design.json'); f = load(r7 / f'freeze_exact_eqeta_{t}.json')
        fr = load(r7 / f'freeze_fresh_eqeta_{t}.json')
        R = d['replicates']; strata = {}
        for k, v in d['strata'].items():
            s, L = stratum_key(k); r = R[f'{s}_L{L}']
            strata[k] = {'sector': s, 'L': L, 's': v['s'], 'r': r, 'C1': v['C1'], 'V1': v['V1'],
                         'core_hours': r * v['s'] * v['C1'] / 3600}
        tot = sum(x['core_hours'] for x in strata.values())
        if abs(tot - f['allocated_core_hours_total']) > 1e-6 * tot:
            raise SystemExit(f'{t}: sum r s C1 = {tot} != allocated {f["allocated_core_hours_total"]}')
        out[t] = {'strata': strata, 'core_hours': tot, 'batches': f['batches'], 'predicted_se_total': f['predicted_se_total'],
                  'eta_node': f['eta_node'], 'r7_fresh_core_hours': fr['allocated_core_hours_total'],
                  'r7_fresh_predicted_se_total': fr['predicted_se_total']}
    return out


def speedups(rec: dict) -> dict:
    """k per (sector, L): F4 at L8 (per sector), F2 pooled task seconds at every L (both kept; L8 uses F4)."""
    f2 = {}
    for key, v in (rec.get('F3_counters') or {}).items():
        c, s, l = key.split('_'); L = int(l[1:]); a = f2.setdefault((s, L), [0., 0.])
        a[0] += v['task_seconds_exact']; a[1] += v['task_seconds_profile']
    k_f2 = {f'{s}_L{L}': (e / p if p > 0 else None) for (s, L), (e, p) in f2.items()}
    f4 = (rec.get('F4') or {}).get('speedup_exact_over_profile') or {}
    k = {}
    for s in ('free', 'power'):
        for L in range(3, 9):
            n = f'{s}_L{L}'
            k[n] = f4.get(s) if L == 8 and s in f4 else k_f2.get(n)
    return {'used': k, 'f2_pooled': k_f2, 'f4': f4}


def project(base: dict, k: dict) -> dict:
    out = {}
    for t, b in base.items():
        same = 0.; num = 0.; den = 0.
        for name, x in b['strata'].items():
            kk = k[f'{x["sector"]}_L{x["L"]}'] or 1.0
            same += x['core_hours'] / kk
            w = math.sqrt(x['V1'] * x['C1']); num += w / math.sqrt(kk); den += w
        ney = (num / den) ** 2
        out[t] = {'core_hours_same_allocation': same, 'ratio_same_allocation': same / b['core_hours'],
                  'ratio_neyman': ney, 'core_hours_neyman': ney * b['core_hours']}
    return out


def gate_summary(rec: dict) -> dict:
    F1, F2, F4, F5 = rec.get('F1') or {}, rec.get('F2') or {}, rec.get('F4') or {}, rec.get('F5') or {}
    tiers = (rec.get('F3_tiers') or {})
    g = F2.get('gates') or {}
    return {
        'status': rec.get('status'), 'verdicts': rec.get('verdicts'), 'development': rec.get('development'),
        'profile_sha256': (rec.get('profile') or {}).get('sha256'), 'exact_sha256': (rec.get('exact') or {}).get('sha256'),
        'F1': {'passed': (F1.get('verdict') or {}).get('passed'), 'points': (F1.get('total') or {}).get('points'),
               'violations': (F1.get('verdict') or {}).get('violations'), 'failed_profile_checks': (F1.get('verdict') or {}).get('failed_profile_checks'),
               'max_relative_error': {t: v.get('max_relative_error') for t, v in ((F1.get('total') or {}).get('tiers') or {}).items() if v.get('points')},
               'identical_to_exact': ((F1.get('total') or {}).get('paired') or {}).get('identical'),
               'max_paired_relative_difference': ((F1.get('total') or {}).get('paired') or {}).get('max_relative_difference'),
               'profile_checks': (F1.get('total') or {}).get('profile_checks')},
        'F2': {'passed': F2.get('passed'), 'replicates': F2.get('replicates'), 'doublings': F2.get('doublings'),
               'gates': {n: {'dC8': v['dC8'], 'se': v['se'], 'bound': v['bound'], 'passed': v['passed']} for n, v in g.items()},
               'nonlinear_dC8': (F2.get('nonlinear') or {}).get('dC8'),
               'per_task_max_normalized': (F2.get('per_task') or {}).get('max_normalized'),
               'per_task_over_bound': (F2.get('per_task') or {}).get('over_bound'),
               'per_task_zero': ((F2.get('per_task') or {}).get('normalized') or {}).get('zero'),
               'per_task_n': ((F2.get('per_task') or {}).get('normalized') or {}).get('n'),
               'projection_2097152': ((F2.get('projection') or {}).get('by_points') or {}).get('2097152', {}).get('total'),
               'wall_seconds': F2.get('wall_seconds')},
        'F3': {'tiers_profile': {t: v['points'] for t, v in (tiers.get('profile') or {}).items()},
               'tiers_exact': tiers.get('exact'), 'transitions': tiers.get('transitions'),
               'mp_change': {k: v['mp_change'] for k, v in (rec.get('F3_counters') or {}).items() if k.endswith(('L7', 'L8'))},
               'quad_change': {k: v['quad_change'] for k, v in (rec.get('F3_counters') or {}).items() if k.endswith(('L7', 'L8'))}},
        'F4': {'speedup': F4.get('speedup_exact_over_profile'), 'medians': F4.get('medians'), 'rows_repeatable': F4.get('rows_repeatable'),
               'rows_identical_between_binaries': F4.get('rows_identical_between_binaries'), 'shape': F4.get('shape')},
        'F5': {'passed': F5.get('passed'), 'threads': F5.get('threads'), 'lanes': F5.get('lanes')},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--gate', type=Path, required=True); ap.add_argument('--r7', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True); ap.add_argument('--markdown', type=Path)
    a = ap.parse_args()
    base = base_tables(a.r7)
    res = {'schema': 'c8-d2-aflag7-1', 'targets': list(TARGETS), 'c8_magnitude': 4.6e4,
           'default': {t: {'core_hours': b['core_hours'], 'predicted_se_total': b['predicted_se_total'], 'batches': b['batches'], 'eta_node': b['eta_node'],
                           'strata_core_hours': {n: x['core_hours'] for n, x in b['strata'].items()}} for t, b in base.items()},
           'r7': {t: {'core_hours': b['r7_fresh_core_hours'], 'ratio': b['r7_fresh_core_hours'] / b['core_hours'],
                      'predicted_se_total': b['r7_fresh_predicted_se_total']} for t, b in base.items()},
           'profiles': {}, 'controls': {}}
    for d in sorted({f.parent for f in a.gate.rglob('numerics_flags.json')} - {f.parent for f in a.gate.rglob('f1_baseline/baseline.json')} - {f.parent.parent for f in a.gate.rglob('f1_baseline/baseline.json')}):
        rec = load(d / 'numerics_flags.json'); name = rec.get('profile_name')
        entry = {'record': str(d / 'numerics_flags.json'), **gate_summary(rec)}
        if d.name.startswith('jflag_') and name in PROFILES and set(rec.get('parts') or []) >= {'F1', 'F2', 'F4', 'F5'}:
            sp = speedups(rec); entry['speedups'] = sp; entry['projection'] = project(base, sp['used'])
            entry['projection_f2_only'] = project(base, {n: sp['f2_pooled'].get(n) for n in sp['used']})
            res['profiles'][name] = entry
        else:
            res['controls'][d.name] = entry
    a.out.write_text(json.dumps(res, indent=1) + '\n')
    if a.markdown:
        L = ['| Profile | F1 | F2 | F5 | F4 total (free / power) | ' + ' | '.join(f'{t}: core-h (×)' for t in TARGETS) + ' |',
             '|---|---|---|---|---|' + '---:|' * len(TARGETS)]
        L.append('| default (exact) | — | — | — | ×1 | ' + ' | '.join(f'{res["default"][t]["core_hours"]:,.0f}' for t in TARGETS) + ' |')
        for p in PROFILES:
            e = res['profiles'].get(p)
            if not e: continue
            ok = lambda x: 'pass' if x else 'FAIL'
            s = e['F4']['speedup'] or {}
            L.append(f'| `{p}` | {ok(e["F1"]["passed"])} | {ok(e["F2"]["passed"])} | {ok(e["F5"]["passed"])} | '
                     f'×{s.get("total", float("nan")):.3f} ({s.get("free", float("nan")):.3f} / {s.get("power", float("nan")):.3f}) | '
                     + ' | '.join(f'{e["projection"][t]["core_hours_same_allocation"]:,.0f} (×{e["projection"][t]["ratio_same_allocation"]:.3f})' for t in TARGETS) + ' |')
        L.append('| R7 map `98a215a8…` (A-FLAG-6) | — | — | — | — | ' + ' | '.join(f'{res["r7"][t]["core_hours"]:,.0f} (×{res["r7"][t]["ratio"]:.3f})' for t in TARGETS) + ' |')
        a.markdown.write_text('\n'.join(L) + '\n')
    print(json.dumps({p: {t: round(e['projection'][t]['ratio_same_allocation'], 4) for t in TARGETS} for p, e in res['profiles'].items()}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
