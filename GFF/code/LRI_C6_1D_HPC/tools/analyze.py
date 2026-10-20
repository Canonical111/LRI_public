"""Pre-registered C6 estimate, allowance and stopping rule (PLAN.md section 4.5).

Usage: python analyze.py ASSEMBLED.json ROUNDING.json OUT.json [--provisional]
ASSEMBLED.json from tools/assemble.py, ROUNDING.json from tools/rounding.py. Both must reference the same production
L6 records (SHA256 of each level file) and the same weights manifest.
Without --provisional the program refuses to produce a headline or a stopping decision unless every mandatory input
exists: L6 degrees 6,8,...,N* (N* >= 16), each with light and hard levels and both rounding replicates; the
calibration runs at N = 6, 8, 10; L5 configurations M = 12,16,...,40 and the perturbed replicate at M = 40.
--provisional reports the table and a provisional value without an allowance.
"""
import sys, json, math, argparse
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
import mpmath as mp

mp.mp.dps = 40
CUTS = ('maxgap', 'span')
ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / 'reference'
OLD_C6, OLD_SE = mp.mpf('14331.77074704865'), mp.mpf('0.1434434494122894')
RHO_FLOOR = mp.mpf('1e-12')


def ceil_2sf(x):
    x = Decimal(str(mp.nstr(x, 30)))
    if x <= 0:
        return Decimal(0)
    e = x.adjusted() - 1
    q = Decimal(1).scaleb(e)
    return (x / q).to_integral_value(rounding=ROUND_CEILING) * q


def ulow():
    ac = json.loads((REF / 'additional_checks.json').read_text())
    return 2 * max(abs(mp.mpf(ac['lower_order_degree_controls'][c]['N28_minus_N22'])) for c in CUTS)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('assembled'); ap.add_argument('rounding'); ap.add_argument('out')
    ap.add_argument('--provisional', action='store_true')
    ap.add_argument('--resources', help='JSON from cluster/env.sh c6_resources N*: node-hours and next-degree projection')
    ap.add_argument('--decision-dir', help='write decision_N{N*}.json here (consumed by production.sh N=<N*+2>)')
    a = ap.parse_args()
    import hashlib
    A_raw = Path(a.assembled).read_bytes(); R_raw = Path(a.rounding).read_bytes()   # read once: parse and hash the same bytes
    A = json.loads(A_raw); Rn = json.loads(R_raw)
    A_sha, R_sha = hashlib.sha256(A_raw).hexdigest(), hashlib.sha256(R_raw).hexdigest()
    Ms = sorted(int(k[4:]) for k in A['configs'] if k.startswith('L5_M'))
    if not Ms:
        raise SystemExit('no L5 configuration assembled')
    Mstar = Ms[-1]; best = f'L5_M{Mstar}'; prev = f'L5_M{Mstar - 4}'; pertname = f'L5pert_M{Mstar}'
    Ns = sorted(int(n) for n in A['levels'])
    RL = Rn['levels']; cal = mp.mpf(Rn.get('cal', 'nan'))
    missing = []
    if not Ns or Ns[0] != 6 or Ns != list(range(6, Ns[-1] + 1, 2)) or Ns[-1] < 16:
        missing.append(f'L6 degrees must be 6,8,...,N* with N*>=16 (both strata); have {Ns}')
    if [n for n in A.get('incomplete_degrees', []) if Ns and n < Ns[-1]]:
        missing.append(f"degrees with only one stratum below N*: {A['incomplete_degrees']}")
    if Ms != list(range(12, 41, 4)):
        missing.append(f'L5 degrees must be 12,16,...,40; have {Ms}')
    if pertname not in A['configs']:
        missing.append(f'L5 perturbed replicate {pertname} missing')
    if not Rn.get('calibration_complete'):
        missing.append(f"calibration runs incomplete: {Rn.get('calibration')}")
    for n in Ns:
        if 'rho' not in RL.get(str(n), {}):
            missing.append(f'rounding replicates missing at N={n}: {RL.get(str(n))}')
        for f in (f'L6_H_light_N{n}.dbl.json', f'L6_H_hard_N{n}.ld.json'):
            ia, ir = A.get('level_identities', {}).get(f), Rn.get('level_identities', {}).get(f)
            if ia is None or ir is None or ia != ir:
                missing.append(f'{f}: assembly and rounding did not use the same record ({ia} vs {ir})')
    if A.get('weights_manifest_sha256') != Rn.get('weights_manifest_sha256'):
        missing.append('assembly and rounding used different weights manifests')
    if not (mp.isfinite(cal) and cal >= 1):
        missing.append(f'calibration factor not finite and >= 1: {cal}')
    for n, r in RL.items():
        if 'rho' in r and not (mp.isfinite(mp.mpf(r['rho'])) and mp.mpf(r['rho']) >= 0):
            missing.append(f'rho at N={n} not finite and non-negative: {r["rho"]}')
    if missing and not a.provisional:
        raise SystemExit('REFUSED (mandatory inputs missing; use --provisional for a report without allowance):\n  ' + '\n  '.join(missing))
    rho = {N: {'rho': mp.mpf(RL[str(N)]['rho']) if 'rho' in RL.get(str(N), {}) else RHO_FLOOR, 'measured': 'rho' in RL.get(str(N), {})} for N in Ns}
    C = {N: {c: mp.mpf(A['levels'][str(N)]['C6'][best][c]) for c in CUTS} for N in Ns}
    D = {N: {c: C[N][c] - C[N - 2][c] for c in CUTS} for N in Ns if N - 2 in C}
    table = []
    for N in Ns:
        row = {'N': N, 'C6_maxgap': mp.nstr(C[N]['maxgap'], 20), 'C6_span': mp.nstr(C[N]['span'], 20),
               'maxgap_minus_span': mp.nstr(C[N]['maxgap'] - C[N]['span'], 6), 'rho': mp.nstr(rho[N]['rho'], 4),
               'rho_measured': rho[N]['measured']}
        if N in D:
            row.update({'delta_maxgap': mp.nstr(D[N]['maxgap'], 6), 'delta_span': mp.nstr(D[N]['span'], 6)})
            if N - 2 in D:
                row['ratio'] = {c: (mp.nstr(abs(D[N][c] / D[N - 2][c]), 4) if D[N - 2][c] != 0 else None) for c in CUTS}
        if N >= 16 and N in D and not missing and not a.provisional:
            conv = max(abs(D[N][c]) for c in CUTS) <= 2 * rho[N]['rho'] and abs(C[N]['maxgap'] - C[N]['span']) <= 2 * rho[N]['rho']
            row['stop_a_converged_to_floor'] = bool(conv)
            row['stop_b_cap'] = N >= 30
        table.append(row)
    if a.provisional:
        Nstar = Ns[-1] if Ns else None
        prov = {'C6_provisional_mean_of_cutoffs': mp.nstr((C[Nstar]['maxgap'] + C[Nstar]['span']) / 2, 20) if Nstar else None,
                'N_star': Nstar, 'L5_M_star': Mstar, 'missing_for_final': missing,
                'note': 'provisional report: no headline, allowance or stopping decision'}
        Path(a.out).write_text(json.dumps({'headline': None, 'provisional': prov, 'levels': table}, indent=1, default=str))
        print(json.dumps(prov, indent=1)); return
    Nstar = Ns[-1]
    if Nstar not in D or Nstar - 2 not in D:
        raise SystemExit('need at least three consecutive levels for the headline')
    head = (C[Nstar]['maxgap'] + C[Nstar]['span']) / 2
    geo = all(abs(D[Nstar][c]) <= abs(D[Nstar - 2][c]) / 2 or abs(D[Nstar][c]) <= 2 * rho[Nstar]['rho'] for c in CUTS)
    f = 1 if geo else 4
    Uconv = 2 * f * max(abs(D[Nstar][c]) for c in CUTS)
    Ucut = abs(C[Nstar]['maxgap'] - C[Nstar]['span'])
    Uround = 4 * rho[Nstar]['rho']
    if prev in A['configs']:
        Cprev = {c: mp.mpf(A['levels'][str(Nstar)]['C6'][prev][c]) for c in CUTS}
        U5 = 2 * max(abs(C[Nstar][c] - Cprev[c]) for c in CUTS)
    else:
        U5 = None
    Ul = ulow()
    if pertname in A['configs']:
        Cp = {c: mp.mpf(A['levels'][str(Nstar)]['C6'][pertname][c]) for c in CUTS}
        U5round = 4 * cal * max(abs(Cp[c] - C[Nstar][c]) for c in CUTS)
    else:
        U5round = None
    parts = {'U_conv': Uconv, 'U_cut': Ucut, 'U_round': Uround, 'U5': U5, 'U5_round': U5round, 'Ulow': Ul}
    U = ceil_2sf(Uconv + Ucut + Uround + U5 + U5round + Ul)
    # Headline printed to the decimal place of U's second significant figure.
    q = Decimal(1).scaleb(U.adjusted() - 1)
    head_str = str(Decimal(mp.nstr(head, 30)).quantize(q))
    diag = {}
    for c in CUTS:
        d1, d0 = D[Nstar][c], D[Nstar - 2][c]
        r = d1 / d0 if d0 != 0 else mp.mpf(0)
        aitken = C[Nstar][c] - d1 * d1 / (d1 - d0) if d1 != d0 else C[Nstar][c]
        tail = C[Nstar][c] + (d1 * r / (1 - r) if abs(r) < 1 else mp.mpf('nan'))
        diag[c] = {'aitken': mp.nstr(aitken, 20), 'geometric_tail': mp.nstr(tail, 20), 'ratio_last': mp.nstr(r, 6)}
    diag['pole_errors'] = {N: A['levels'][str(N)]['pole_errors'][best] for N in Ns}
    diag['old_result'] = {'old': mp.nstr(OLD_C6, 16), 'old_SE': mp.nstr(OLD_SE, 6), 'z_using_old_SE': mp.nstr((head - OLD_C6) / OLD_SE, 4)}
    diag['C7_package_crosscheck'] = 'see tools/c7_crosscheck.py (labelled degree-6 / +step7 / +tail stages from C7_final.json)'
    diag['retained_pole_config'] = {c: mp.nstr(mp.mpf(A['levels'][str(Nstar)]['C6']['retained_poles_J16ref'][c]) - C[Nstar][c], 6) for c in CUTS}
    diag['L5_sequence_at_Nstar'] = {name: A['levels'][str(Nstar)]['C6'][name] for name in A['configs']}
    reasons = []
    last = [r for r in table if r['N'] == Nstar][0]
    if last.get('stop_a_converged_to_floor'):
        reasons.append('(a) converged to the floating-point floor')
    if last.get('stop_b_cap'):
        reasons.append('(b) N_cap = 30 reached')
    res = json.loads(Path(a.resources).read_text()) if a.resources else None
    res_problem = None
    if res is not None:
        try:
            vals = {k: float(res[k]) for k in ('production_node_hours', 'N_star_node_hours', 'projected_next_hours_on_12_nodes')}
            if int(res.get('N_star', -1)) != Nstar:
                res_problem = f"resources are for N*={res.get('N_star')}, not {Nstar}"
            elif not all(math.isfinite(v) and v >= 0 for v in vals.values()):
                res_problem = f'resource values not finite and non-negative: {vals}'
            elif res.get('coverage_complete') is not True or vals['N_star_node_hours'] <= 0:
                res_problem = f"accounting coverage incomplete: {res.get('coverage')}"
        except (KeyError, TypeError, ValueError) as e:
            res_problem = f'malformed resources: {e}'
        if res_problem is None:
            if vals['production_node_hours'] > 400:
                reasons.append(f"(c) cumulative production {vals['production_node_hours']} node-hours > 400")
            if vals['projected_next_hours_on_12_nodes'] > 36:
                reasons.append(f"(d) projected N={Nstar + 2} wall time {vals['projected_next_hours_on_12_nodes']} h > 36 h on 12 nodes")
    if Nstar < 16:
        decision = 'continue'; reasons = ['N* < 16: degrees 6..16 are unconditional']
    elif reasons:
        decision = 'stop'
    elif res is None or res_problem:
        decision = 'unresolved'; reasons = [res_problem or 'resource guards (c), (d) not evaluated: rerun with --resources']
    else:
        decision = 'continue'
    diag['stopping'] = {'decision': decision, 'reasons': reasons, 'N_star': Nstar, 'next_degree': Nstar + 2 if decision == 'continue' else None, 'resources': res}
    diag['light_stratum_vs_reference_MC'] = light_vs_mc(A)
    diag['hard_double_minus_longdouble_C6'] = A.get('diagnostics', {}).get('hard_dbl_minus_ld_C6')
    if f'L5dbl_M{Mstar}' in A['configs']:
        diag['L5_double_minus_longdouble_C6_at_Nstar'] = {c: mp.nstr(mp.mpf(A['levels'][str(Nstar)]['C6'][f'L5dbl_M{Mstar}'][c]) - C[Nstar][c], 6) for c in CUTS}
    diag['rounding'] = Rn
    prov = {'assembled_sha256': A_sha, 'rounding_sha256': R_sha,
            'assembly_level_identities': A.get('level_identities'), 'rounding_level_identities': Rn.get('level_identities'),
            'weights_manifest_sha256': A.get('weights_manifest_sha256')}
    if a.decision_dir:
        dd = Path(a.decision_dir); dd.mkdir(parents=True, exist_ok=True)
        ids = {f: A['level_identities'][f] for f in (f'L6_H_light_N{Nstar}.dbl.json', f'L6_H_hard_N{Nstar}.ld.json')}
        (dd / f'decision_N{Nstar}.json').write_text(json.dumps({**diag['stopping'], 'levels_at_N_star': ids, **{k: prov[k] for k in ('assembled_sha256', 'rounding_sha256')}}, indent=1))
    out = {'provenance': prov, 'headline': {'C6': head_str, 'allowance_U': str(U), 'N_star': Nstar, 'L5_M_star': Mstar, 'f': f, 'cal': mp.nstr(cal, 4),
                        'components': {k: mp.nstr(v, 6) for k, v in parts.items()}, 'C6_unrounded': mp.nstr(head, 25),
                        'scope': 'Empirical convergence-and-rounding allowance (PLAN.md 4.5); not a rigorous bound.'},
           'levels': table, 'diagnostics': diag}
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out['headline'], indent=1))


def light_vs_mc(A):
    """Exact light-stratum level differences (production light vectors) versus the reference Monte Carlo levels."""
    import numpy as np
    old = json.loads((REF / 'C6_stratified_analysis.json').read_text())
    lv = {n: r for n, r in A['levels'].items() if 'light' in r}; res = {}
    def lightC6(N, i):
        return -mp.mpf(2) / 729 * mp.mpf(lv[str(N)]['light'][i])
    for (hi, lo), key in (((8, 6), '8-6, light'), ((10, 8), '10-8, light')):
        if not all(str(n) in lv for n in (hi, lo)):
            continue
        row = {}
        for j, c in enumerate(CUTS):
            i = 6 * j + 5
            exact = lightC6(hi, i) - lightC6(lo, i)
            mc = mp.mpf(old['levels'][key]['C6_shift'][j]); se = mp.mpf(old['levels'][key]['SE'][j])
            row[c] = {'exact': mp.nstr(exact, 10), 'mc': mp.nstr(mc, 8), 'mc_SE': mp.nstr(se, 6), 'z': mp.nstr((exact - mc) / se, 4)}
        res[key] = row
    if all(str(n) in lv for n in (12, 10)):
        FACTOR = -662287500.
        s12 = np.fromfile(REF / 'samples_H_L6_N12_s135799_M1000.bin').reshape(1000, 12) * FACTOR
        s10 = np.fromfile(REF / 'samples_H_L6_N10_s135799_M3000.bin').reshape(3000, 12)[:1000] * FACTOR
        feat = np.fromfile(REF / 'features_s135799_M3000.bin', np.int32).reshape(3000, 10)[:1000]
        light = (feat[:, 1] < 2) & (feat[:, 2] == 0) & (feat[:, 3] == 0)
        dx = s12 - s10; dl = dx.copy(); dl[~light] = 0
        row = {}
        for j, c in enumerate(CUTS):
            i = 6 * j + 5
            y_all = -2 / 729 * dx[:, i]; y_l = -2 / 729 * dl[:, i]
            mc_all, se_all = mp.mpf(float(y_all.mean())), mp.mpf(float(y_all.std(ddof=1) / 1000 ** .5))
            mc_l, se_l = mp.mpf(float(y_l.mean())), mp.mpf(float(y_l.std(ddof=1) / 1000 ** .5))
            ex_all = -mp.mpf(2) / 729 * (mp.mpf(lv['12']['H6_vector'][i]) - mp.mpf(lv['10']['H6_vector'][i]))
            ex_l = lightC6(12, i) - lightC6(10, i)
            row[c] = {'exact_all': mp.nstr(ex_all, 10), 'mc_all': mp.nstr(mc_all, 8), 'mc_all_SE': mp.nstr(se_all, 6), 'z_all': mp.nstr((ex_all - mc_all) / se_all, 4),
                      'exact_light': mp.nstr(ex_l, 10), 'mc_light': mp.nstr(mc_l, 8), 'mc_light_SE': mp.nstr(se_l, 6), 'z_light': mp.nstr((ex_l - mc_l) / se_l, 4),
                      'note': 'the 1000 reference samples are the first 1000 draws of the 10-8 level (seed 135799)'}
        res['12-10'] = row
    return res


if __name__ == '__main__':
    main()
