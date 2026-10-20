#!/usr/bin/env python3
"""A-PERF-4: the refined table of cost against target (docs/PERFORMANCE.md), from the J-DES-5 freezes. Mac, seconds.

  aperf4_table.py --des5 DIR --bundles DIR --package PKG --out FILE.json [--markdown FILE.md]

  DIR (--des5) is the job's evidence folder (s5des5.570114.0/); --bundles is its bundles.tgz unpacked (the four
  bundles' counts/ files are read for the Expanse re-costing).

Base (measured kappa, sigma^2 still projected until the pilot): the four test-only freezes of J-DES-5 on symmetry's
J-SWEEP-2 (all 24,173 graphs, 2 x 512 points, final default binary 2cc5e88e, AMD EPYC 7543). Each design.json stratum
carries s, V1, C1 (allocated core-seconds per replicate at s = 1, with the sweep's own eta_node) and the replicates r
of its (sector, L): allocated core-hours = sum r s C1 / 3600 (checked against the freeze's total).

Columns (each a fixed allocation: the frozen counts x s and r are kept; only the cost per point or the efficiency
changes):
  literal      the freeze as frozen: eta_node of the sweep's own accounting (a 17-minute job: plan, tail and merge
               inside the allocation);
  symmetry     the same allocation at the lane-mode eta_node of the J-SMK-4 campaign (accounting.py on smk4-20261005,
               one amdq node, 8 x 8 lanes, 1.4 h): core-hours x eta_sweep / eta_lane;
  expanse      the same allocation re-costed with the Expanse cost model of the final binary (J-SWEEP-2E, EPYC 7742,
               cost_models/gmp_expanse_amd_c8.json) per graph and campaign, with symmetry's per-group OpenMP efficiency
               and the same lane eta_node (assumed: Expanse's lane campaigns J-EXP-3/4 lasted 4 minutes, too short for
               an eta_node; Expanse SU = core-hours on compute/shared):
               C1_E = C1 x [sum_g b_g kappa_E(g) / eta_omp,g] / [sum_g b_g kappa_S(g) / eta_omp,g] per (sector, L), the
               sums over both campaigns with the base counts b_g of the bundle (both free L8 strata get the ratio of
               their (sector, L): the count files do not mark the primitives);
  continuous   the continuous Neyman optimum at the target (m_k = lambda sqrt(V1/C1), no powers of two, no shared r):
               a lower bound for any integer design. At 1e-3 the frozen design is far above it (finding F11 below);
  profiles     each opt-in profile at each site: every stratum's core-hours divided by the profile's measured speedup k
               over the final default binary (Stage 4c gate, Expanse: F4 per sector for the L8 strata, F2's pooled
               task seconds for L <= 7; benchmarks/expanse_2026-10-c8/stage4c/gate/scripts/aflag7_table.py
               speedups()), the frozen allocation kept (A-FLAG-7's "same allocation" rule). The APPROVED profile
               dd+mp256 (user check-in 2026-10-05: production after the pilot, pending its own J-FLAG build gate) was
               measured as the dd+mp256+exp1 build: exp1 changes no value and no shifted point exists under the
               planned sampling, so it acted only as code layout (its F4 x1.007, the all-stub layout control x1.005).
               On symmetry the Expanse-measured k are assumed (not measured there; F10: GCC 11.4's binary128 tier is
               slower, so the split between tiers differs).
  R7           the measured ratio of A-FLAG-7 (fresh-under-map freezes against exact freezes, J-SWEEP-1 stand-in pilot);
               quoted, not recomputed. Not approved.

F11 (found here, design.py split()): the replicates r of a (sector, L) follow the LARGEST stratum multiplier of the
group. At free L8 the cheap primitive stratum (248 graphs) has a multiplier about 5x that of the other free L8 graphs
at 1e-3 (176.8 against 35.1), so the dominant stratum gets r = 128 at s = 1 where 32 would do: the 1e-3 freeze costs
about 3x the continuous optimum and overshoots the target (SE 32.6 against 46). 5e-4 and tighter are within 1.10x.
"""
import argparse, importlib.util, json, math
from pathlib import Path

TARGETS = ('1e-3', '5e-4', '2.5e-4', '1.35e-4')
# profile: (gate record, approval status)
PROFILES = {
    'dd+mp256': ('s4cgate.54673902.0/jflag_dd_mp256_exp1',
                 'APPROVED for production after the pilot (user check-in 2026-10-05), pending its own J-FLAG gate of the exact dd+mp256 build; '
                 'k measured on the dd+mp256+exp1 build (exp1 inert)'),
    'dd': ('s4cgate.54673900.0/jflag_dd', 'measured alone; production use is the approved dd+mp256 combination'),
    'mp256': ('s4cgate.54673901.0/jflag_mp256', 'measured alone; production use is the approved dd+mp256 combination'),
    'exp1': ('s4cgate.54673904.0/jflag_exp1', 'NOT approved (inert: no shifted point under the planned sampling; code layout only)'),
}
R7_STATUS = 'NOT approved (needs a real pilot under its map, R14)'
MARGIN = 1.5


def load(p):
    return json.loads(Path(p).read_text())


def counts(bdir: Path) -> dict:
    out = {}
    for f in sorted((bdir / 'counts').iterdir()):
        c, s, l = f.stem.split('_'); L = int(l[1:])
        for line in f.read_text().split('\n'):
            if line.strip():
                g, n = line.split(); out[(c, s, L, int(g))] = int(n)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument('--des5', type=Path, required=True); ap.add_argument('--bundles', type=Path, required=True)
    ap.add_argument('--package', type=Path, required=True); ap.add_argument('--out', type=Path, required=True); ap.add_argument('--markdown', type=Path)
    a = ap.parse_args(); pkg = a.package.resolve()
    gate = pkg / 'benchmarks/expanse_2026-10-c8/stage4c/gate'
    spec = importlib.util.spec_from_file_location('aflag7_table', gate / 'scripts/aflag7_table.py'); af = importlib.util.module_from_spec(spec); spec.loader.exec_module(af)
    k = {p: af.speedups(load(gate / d / 'numerics_flags.json'))['used'] for p, (d, _) in PROFILES.items()}
    r7 = load(gate / 'aflag7.json')['r7']
    kS = load(pkg / 'cost_models/gmp_symmetry_amd_c8.json')['seconds_per_point']; kE = load(pkg / 'cost_models/gmp_expanse_amd_c8.json')['seconds_per_point']
    eta_lane = load(a.des5 / 'accounting_smk4-20261005.json')['eta_node']; acc_sw = load(a.des5 / 'accounting_sweep2-5d7586e9f1ab.json')
    out = {'schema': 'c8-d2-aperf4-1', 'rule': __doc__, 'eta_lane': eta_lane, 'eta_lane_source': 'tools/accounting.py on smk4-20261005 (J-SMK-4)',
           'eta_sweep': acc_sw['eta_node'], 'profiles_k': k, 'profiles_status': {p: s for p, (_, s) in PROFILES.items()},
           'r7_status': R7_STATUS, 'targets': {}}
    for t in TARGETS:
        d = load(a.des5 / f'design_{t}.json')
        b = counts(a.bundles / f'des5_{t}'); eta_sw = d['eta_node']; R = d['replicates']; eo = d['eta_omp']
        assert abs(eta_sw - acc_sw['eta_node']) < 1e-12, (eta_sw, acc_sw['eta_node'])
        assert d['batches'] == 1, d['batches']
        num = {}; den = {}
        for (c, s, L, g), n in b.items():
            key = f'{c}:{s}:{L}:{g}'
            sl = f'{s}_L{L}'; w = n / eo[f'{c}_{s}_L{L}']
            num[sl] = num.get(sl, 0.) + w * kE[key]; den[sl] = den.get(sl, 0.) + w * kS[key]
        rho = {sl: num[sl] / den[sl] for sl in num}
        # the continuous Neyman optimum at this target (design.py optimize() before the split into r and s)
        S = d['strata']; act = [x for x in S if S[x]['graphs'] and S[x]['V1'] > 0]
        tse = float(t) * 46000.; root = sum(math.sqrt(S[x]['V1'] * S[x]['C1']) for x in act); lam = MARGIN ** 2 * root / tse ** 2
        m = {x: lam * math.sqrt(S[x]['V1'] / S[x]['C1']) for x in act}
        cont_se = MARGIN * math.sqrt(sum(S[x]['V1'] / m[x] for x in act))
        assert abs(cont_se - tse) <= 1e-9 * tse, (cont_se, tse)
        strata = {}
        for st, v in S.items():
            if not v['graphs']:
                continue
            sl = f'{v["sector"]}_L{v["L"]}'; r = R[sl]; ch = r * v['s'] * v['C1'] / 3600
            cont = (m.get(st, 0.) * v['C1'] / 3600)
            strata[st] = {'sector_L': sl, 'r': r, 's': v['s'], 'C1': v['C1'], 'V1': v['V1'], 'core_hours_literal': ch,
                          'core_hours_symmetry': ch * eta_sw / eta_lane, 'expanse_ratio': rho[sl], 'core_hours_expanse': ch * eta_sw / eta_lane * rho[sl],
                          'continuous_multiplier': m.get(st), 'continuous_core_hours_literal': cont}
        lit = sum(x['core_hours_literal'] for x in strata.values())
        assert abs(lit - d['predicted']['cost_total_core_hours']) <= 1e-6 * lit, (t, lit, d['predicted']['cost_total_core_hours'])
        cont_lit = sum(x['continuous_core_hours_literal'] for x in strata.values())
        row = {'batches': d['batches'], 'predicted_se_total': d['predicted']['se_total'], 'target_se': tse,
               'literal_core_hours': lit, 'eta_sweep': eta_sw,
               'symmetry_core_hours': sum(x['core_hours_symmetry'] for x in strata.values()),
               'expanse_su': sum(x['core_hours_expanse'] for x in strata.values()),
               'continuous': {'literal_core_hours': cont_lit, 'symmetry_core_hours': cont_lit * eta_sw / eta_lane,
                              'expanse_su': sum(x['continuous_core_hours_literal'] * x['expanse_ratio'] for x in strata.values()) * eta_sw / eta_lane,
                              'frozen_over_continuous': lit / cont_lit},
               'strata': strata, 'profiles': {}}
        for p, kk in k.items():
            sym = sum(x['core_hours_symmetry'] / (kk[x['sector_L']] or 1.) for x in strata.values())
            exp = sum(x['core_hours_expanse'] / (kk[x['sector_L']] or 1.) for x in strata.values())
            row['profiles'][p] = {'symmetry_core_hours': sym, 'expanse_su': exp, 'ratio_symmetry': sym / row['symmetry_core_hours'],
                                  'ratio_expanse': exp / row['expanse_su'], 'status': PROFILES[p][1]}
        row['profiles']['R7'] = {'ratio': r7[t]['ratio'], 'symmetry_core_hours': r7[t]['ratio'] * row['symmetry_core_hours'],
                                 'expanse_su': r7[t]['ratio'] * row['expanse_su'], 'status': R7_STATUS}
        row['l8_share_literal'] = sum(x['core_hours_literal'] for st, x in strata.items() if st.startswith(('free_L8', 'power_L8'))) / lit
        out['targets'][t] = row
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    T = out['targets']
    lines = ['| Numerics | Site | 1e-3 | 5e-4 | 2.5e-4 | 1.35e-4 |', '|---|---|---:|---:|---:|---:|']
    lines.append('| predicted SE of the freeze (target) | | ' + ' | '.join(f'{T[t]["predicted_se_total"]:.2f} ({T[t]["target_se"]:.2f})' for t in TARGETS) + ' |')
    lines.append('| default, the freeze as frozen (η_node %.3f of the sweep) | symmetry | ' % out['eta_sweep'] + ' | '.join(f'{T[t]["literal_core_hours"]:,.0f}' for t in TARGETS) + ' |')
    lines.append('| **default (exact path)** | **symmetry** | ' + ' | '.join(f'**{T[t]["symmetry_core_hours"]:,.0f}**' for t in TARGETS) + ' |')
    lines.append('| **default (exact path)** | **Expanse** | ' + ' | '.join(f'**{T[t]["expanse_su"]:,.0f}**' for t in TARGETS) + ' |')
    lines.append('| default, continuous Neyman bound (F11) | symmetry | ' + ' | '.join(f'{T[t]["continuous"]["symmetry_core_hours"]:,.0f} (frozen ×{T[t]["continuous"]["frozen_over_continuous"]:.2f})' for t in TARGETS) + ' |')
    lines.append('| default, continuous Neyman bound (F11) | Expanse | ' + ' | '.join(f'{T[t]["continuous"]["expanse_su"]:,.0f}' for t in TARGETS) + ' |')
    names = {'dd+mp256': '**`dd+mp256`: APPROVED after the pilot** (build gate pending)', 'dd': '`dd` (alone)', 'mp256': '`mp256` (alone)', 'exp1': '`exp1`: not approved'}
    for p in PROFILES:
        for site, key, rk in (('symmetry', 'symmetry_core_hours', 'ratio_symmetry'), ('Expanse', 'expanse_su', 'ratio_expanse')):
            lines.append(f'| {names[p]} | {site} | ' + ' | '.join(f'{T[t]["profiles"][p][key]:,.0f} (×{T[t]["profiles"][p][rk]:.3f})' for t in TARGETS) + ' |')
    for site, key in (('symmetry', 'symmetry_core_hours'), ('Expanse', 'expanse_su')):
        lines.append(f'| R7 map (A-FLAG-7 ratio): not approved | {site} | ' + ' | '.join(f'{T[t]["profiles"]["R7"][key]:,.0f} (×{T[t]["profiles"]["R7"]["ratio"]:.3f})' for t in TARGETS) + ' |')
    md = '\n'.join(lines) + '\n'
    if a.markdown:
        a.markdown.write_text(md)
    print(md)
    for t in TARGETS:
        print(t, 'L8 share', round(T[t]['l8_share_literal'], 4), 'Expanse/symmetry', round(T[t]['expanse_su'] / T[t]['symmetry_core_hours'], 4),
              'frozen/continuous', round(T[t]['continuous']['frozen_over_continuous'], 3), 'batches', T[t]['batches'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
