#!/usr/bin/env python3
"""Before the Stage-6 inspection (Mac, seconds): the F11 fix on J-DES-5's four freezes and the refined cost table with
symmetry's own dd+mp256 factors.

  pre6_tables.py --package PKG --out FILE.json [--markdown FILE.md]

Inputs (all committed records):
  benchmarks/symmetry_2026-10-c8/stage5/des5/s5des5.570114.0/design_<T>.json, design_meta_<T>.json: J-DES-5's four
      test-only freezes on symmetry's J-SWEEP-2 (every stratum's V1, C1 and s, the replicates r, eta_node 0.306 of the
      sweep, the target SE);
  benchmarks/symmetry_2026-10-c8/stage5/des5/aperf4.json: the lane eta_node 0.915 (J-SMK-4), Expanse's per-(sector, L)
      re-costing ratio of each bundle (base counts x kappa_Expanse / kappa_symmetry; the base counts do not depend on
      the split into r and s, so the ratio holds for the F11-fixed design too) and the Expanse-measured profile factors
      k (Stage-4c gate, dd+mp256+exp1, Expanse job 54673902);
  benchmarks/symmetry_2026-10-c8/stage5/close/clflag.570210.0/jflag_dd+mp256/numerics_flags.json: the dd+mp256 J-FLAG
      gate of the exact dd+mp256 build on symmetry (job 570210): symmetry's own k per (sector, L) by the rule of
      benchmarks/expanse_2026-10-c8/stage4c/gate/scripts/aflag7_table.py speedups() (F4 per sector at L8, F2's pooled
      task seconds at L <= 7);
  tools/design.py of PKG (its sha256 is recorded): optimize() with the F11-fixed split().

1. F11: for each target, optimize() of the frozen strata (V1, C1) at the frozen target with (a) the Stage-5 rule (r from
   the LARGEST multiplier of each (sector, L), reimplemented here) must reproduce the frozen r and s exactly, and (b)
   the package's current rule (r from the SMALLEST multiplier). Only 1e-3 changes: the free L8 group goes from r = 128
   to r = 32 and the primitives take s = 8.
2. The cost table per design (Stage-5 freeze and F11-fixed): allocated core-hours sum_k r s C1 / 3600 at the sweep's
   eta_node (the freeze), at the lane eta_node (symmetry: x eta_sweep / eta_lane), Expanse (x the bundle's ratio per
   (sector, L)), the continuous Neyman bound, and dd+mp256 per site: each stratum's core-hours divided by k, with
   symmetry's own k (gate 570210) on symmetry and Expanse's k on Expanse; the allocation is kept (A-FLAG-7's "same
   allocation" rule; route (b) re-costs and so can only do better). sigma^2 is still the sweep's projection (2 x 512
   points per graph), with the margin 1.5, until the pilot measures it.
3. A-PERF-5's dd+mp256 column on symmetry (benchmarks/symmetry_2026-10-c8/stage5/close/aperf5.json): the final default
   binary's factor over Stage 3 on symmetry times symmetry's own k (gate 570210), in place of Expanse's k.
"""
import argparse, hashlib, importlib.util, json, math, sys
from pathlib import Path

TARGETS = ('1e-3', '5e-4', '2.5e-4', '1.35e-4')
MARGIN = 1.5


def load(p):
    return json.loads(Path(p).read_text())


def split_stage5(D, S, m, opts):
    """The Stage-5 rule (before the F11 fix): r from the group's LARGEST multiplier."""
    r = {}; s = {}
    for grp in {D.rgroup(k) for k in S}:
        mm = max([m[k] for k in S if D.rgroup(k) == grp] + [0.]); rr = opts.min_reps
        while 2 * rr <= opts.max_reps and mm / (2 * rr) >= 1:
            rr *= 2
        r[grp] = rr
    for k in S:
        s[k] = D.pow2_round(m[k] / r[D.rgroup(k)]) if m[k] > r[D.rgroup(k)] else 1
    return r, s


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument('--package', type=Path, required=True); ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--markdown', type=Path); a = ap.parse_args(); pkg = a.package.resolve()
    sys.path.insert(0, str(pkg / 'tools')); import design as D
    s5 = pkg / 'benchmarks/symmetry_2026-10-c8/stage5'; des5 = s5 / 'des5/s5des5.570114.0'
    gate_dir = pkg / 'benchmarks/expanse_2026-10-c8/stage4c/gate'
    spec = importlib.util.spec_from_file_location('aflag7_table', gate_dir / 'scripts/aflag7_table.py'); af = importlib.util.module_from_spec(spec); spec.loader.exec_module(af)
    gate_rec = s5 / 'close/clflag.570210.0/jflag_dd+mp256/numerics_flags.json'; g = load(gate_rec)
    assert g['status'] == 'passed' and g['profile_name'] == 'dd+mp256' and not g['development'], 'the 570210 record is not a passed dd+mp256 gate'
    k_sym = af.speedups(g)['used']
    ap4 = load(s5 / 'des5/aperf4.json'); k_exp = ap4['profiles_k']['dd+mp256']; eta_lane = ap4['eta_lane']; eta_sw = ap4['eta_sweep']
    out = {'schema': 'c8-d2-pre6-tables-1', 'rule': __doc__, 'design_py_sha256': hashlib.sha256((pkg / 'tools/design.py').read_bytes()).hexdigest(),
           'gate_570210_sha256': hashlib.sha256(gate_rec.read_bytes()).hexdigest(), 'k_symmetry_dd_mp256': k_sym, 'k_expanse_dd_mp256': k_exp,
           'eta_lane': eta_lane, 'eta_sweep': eta_sw, 'targets': {}}
    opts = D.Opts()
    for t in TARGETS:
        d = load(des5 / f'design_{t}.json'); meta = load(des5 / f'design_meta_{t}.json'); tse = meta['target']['se']
        assert abs(d['eta_node'] - eta_sw) < 1e-12 and d['batches'] == 1
        S = {k: dict(V1=v['V1'], C1=v['C1'], V1_imputed=0., graphs=v['graphs'], piloted=v['piloted']) for k, v in d['strata'].items()}
        new_split = D.split
        try:
            D.split = lambda S_, m_, o_: split_stage5(D, S_, m_, o_); r0, s0, ev0 = D.optimize(S, 1, opts, tse)
        finally:
            D.split = new_split
        assert r0 == d['replicates'] and all(s0[k] == d['strata'][k]['s'] for k in S), f'{t}: the Stage-5 rule does not reproduce the frozen design'
        assert abs(ev0['cost_total_core_hours'] - d['predicted']['cost_total_core_hours']) <= 1e-9 * ev0['cost_total_core_hours']
        r1, s1, ev1 = D.optimize(S, 1, opts, tse)
        ratio = {sl: x['expanse_ratio'] for sl, x in ((v['sector_L'], v) for v in ap4['targets'][t]['strata'].values())}
        act = [x for x in S if S[x]['graphs'] and S[x]['V1'] > 0]; root = sum(math.sqrt(S[x]['V1'] * S[x]['C1']) for x in act)
        lam = MARGIN ** 2 * root / tse ** 2; m = {x: lam * math.sqrt(S[x]['V1'] / S[x]['C1']) for x in act}
        cont = sum(m[x] * S[x]['C1'] for x in act) / 3600

        def table(r, s, ev):
            rows = {'predicted_se_total': ev['se_total'], 'literal_core_hours': 0., 'symmetry_core_hours': 0., 'expanse_su': 0.,
                    'dd_mp256_symmetry_own_k': 0., 'dd_mp256_symmetry_expanse_k': 0., 'dd_mp256_expanse': 0., 'r': dict(r), 's': dict(s)}
            for k, v in d['strata'].items():
                if not v['graphs']:
                    continue
                sl = f'{v["sector"]}_L{v["L"]}'; lit = r[sl] * s[k] * S[k]['C1'] / 3600; sym = lit * eta_sw / eta_lane; exp = sym * ratio[sl]
                rows['literal_core_hours'] += lit; rows['symmetry_core_hours'] += sym; rows['expanse_su'] += exp
                rows['dd_mp256_symmetry_own_k'] += sym / k_sym[sl]; rows['dd_mp256_symmetry_expanse_k'] += sym / k_exp[sl]; rows['dd_mp256_expanse'] += exp / k_exp[sl]
            assert abs(rows['literal_core_hours'] - ev['cost_total_core_hours']) <= 1e-9 * rows['literal_core_hours']
            rows['ratio_dd_mp256_symmetry_own_k'] = rows['dd_mp256_symmetry_own_k'] / rows['symmetry_core_hours']
            rows['ratio_dd_mp256_expanse'] = rows['dd_mp256_expanse'] / rows['expanse_su']
            rows['over_continuous'] = rows['literal_core_hours'] / cont
            return rows

        out['targets'][t] = {'target_se': tse, 'continuous_literal_core_hours': cont, 'continuous_symmetry_core_hours': cont * eta_sw / eta_lane,
                             'stage5_freeze': table(r0, s0, ev0), 'f11_fixed': table(r1, s1, ev1),
                             'changed': {'r': {k: [r0[k], r1[k]] for k in r0 if r0[k] != r1[k]}, 's': {k: [s0[k], s1[k]] for k in s0 if s0[k] != s1[k]}}}
    a5 = load(s5 / 'close/aperf5.json')['rows']
    out['aperf5_dd_mp256_symmetry'] = {n: {'default_symmetry': r['default_symmetry'], 'k_symmetry': k_sym[n], 'dd_mp256_symmetry_own_k': r['default_symmetry'] * k_sym[n],
                                           'dd_mp256_symmetry_expanse_k': r['dd+mp256_symmetry']} for n, r in a5.items()}
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    T = out['targets']; f = lambda v: f'{v:,.0f}'
    L = ['| Design | Row | ' + ' | '.join(TARGETS) + ' |', '|---|---|' + '---:|' * len(TARGETS)]
    for key, name in (('stage5_freeze', 'J-DES-5 freeze (Stage-5 rule)'), ('f11_fixed', 'F11 fixed')):
        L.append(f'| {name} | predicted SE (target) | ' + ' | '.join(f'{T[t][key]["predicted_se_total"]:.2f} ({T[t]["target_se"]:.2f})' for t in TARGETS) + ' |')
        L.append(f'| {name} | default, symmetry (η_node 0.915) | ' + ' | '.join(f(T[t][key]['symmetry_core_hours']) + f' (×{T[t][key]["over_continuous"]:.2f} cont.)' for t in TARGETS) + ' |')
        L.append(f'| {name} | default, Expanse SU | ' + ' | '.join(f(T[t][key]['expanse_su']) for t in TARGETS) + ' |')
        L.append(f'| {name} | dd+mp256, symmetry (own k, gate 570210) | ' + ' | '.join(f'{f(T[t][key]["dd_mp256_symmetry_own_k"])} (×{T[t][key]["ratio_dd_mp256_symmetry_own_k"]:.3f})' for t in TARGETS) + ' |')
        L.append(f'| {name} | dd+mp256, Expanse (Expanse k) | ' + ' | '.join(f'{f(T[t][key]["dd_mp256_expanse"])} (×{T[t][key]["ratio_dd_mp256_expanse"]:.3f})' for t in TARGETS) + ' |')
    L.append('| continuous Neyman bound | default, symmetry | ' + ' | '.join(f(T[t]['continuous_symmetry_core_hours']) for t in TARGETS) + ' |')
    L += ['', '| Sector, L | default: symmetry | k (gate 570210) | `dd+mp256`: symmetry (own k) | (with Expanse k) |', '|---|---:|---:|---:|---:|']
    for n, x in out['aperf5_dd_mp256_symmetry'].items():
        L.append(f'| {n.replace("_L", " L")} | ×{x["default_symmetry"]:.3f} | ×{x["k_symmetry"]:.3f} | ×{x["dd_mp256_symmetry_own_k"]:.2f} | ×{x["dd_mp256_symmetry_expanse_k"]:.2f} |')
    md = '\n'.join(L) + '\n'
    if a.markdown:
        a.markdown.write_text(md)
    print(md)
    for t in TARGETS:
        print(t, 'changed', T[t]['changed'])
    print('k symmetry (570210)', {k: round(v, 3) for k, v in k_sym.items()})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
