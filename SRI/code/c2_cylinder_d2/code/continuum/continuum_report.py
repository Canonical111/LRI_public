"""REPORT.md for the arbitrary-N continuum analysis (tables only; every number comes from the JSON outputs)."""
from __future__ import annotations

from pathlib import Path

LAMBDA_N_MINIMUM = {1: 50, 2: 60, 3: 75}       # = continuum_analysis.LAMBDA_N_MINIMUM (display only)


IN_E = ('eps_prop', 'eps_mix', 'eps_tailcut', 'eps_coll', 'eps_grid', 'eps_round', 'eps_model')


def ca_min(order: int) -> float:
    return LAMBDA_N_MINIMUM[order]


def g(x, fmt='.3e'):
    if x is None:
        return '-'
    if isinstance(x, bool):
        return 'yes' if x else 'no'
    if isinstance(x, int):
        return str(x)
    return format(x, fmt)


def count(flags: dict) -> str:
    """'k of n files' for a {file: bool} map."""
    return f"{sum(1 for v in flags.values() if v is True)} of {len(flags)} files" if flags else 'not available'


def cell(x) -> str:
    """A Markdown table cell: literal pipes escaped, line breaks removed (R007)."""
    return str(x).replace('\\|', '|').replace('|', '\\|').replace('\n', ' ')


def table(head: list[str], rows: list[list]) -> str:
    for r in rows:
        if len(r) != len(head):
            raise ValueError(f'table row with {len(r)} cells under {len(head)} headers: {r}')
    out = ['| ' + ' | '.join(cell(h) for h in head) + ' |', '|' + '|'.join('---' for _ in head) + '|']
    out += ['| ' + ' | '.join(cell(c) for c in r) + ' |' for r in rows]
    return '\n'.join(out)


def write_report(out: Path, points, others, order_results, regs, joint, outcome, final, budget, estimate, replaced,
                 measured, meta) -> None:
    L = []
    L.append('# Arbitrary-N continuum analysis of the 2D LRI C2 Hamiltonian records\n')
    L.append(f"Generation `{meta.get('generation', '-')}` (results are published as immutable generations under "
             '`generations/`; the file `CURRENT` names the current one, and the top-level files are copies of it).\n')
    L.append(f"Generated {meta['generated_utc']} by `code/continuum/continuum_driver.py run` "
             f"(python {meta['python'].split()[0]}, numpy {meta['numpy']}, {meta['platform']}). "
             f"Plan: `{meta['rules']['plan']['file']}` rev {meta['rules']['plan']['revision']} "
             f"(sha256 {meta['rules']['plan']['sha256'][:12]}...). "
             'All selection rules are fixed in `continuum_analysis.RULES` and copied into every JSON output. '
             'No proposed closed form of C2 is an input, a prior or a selection criterion. '
             'All uncertainties are linear sums of systematic numerical diagnostics, '
             '**not rigorous bounds and not standard deviations**.\n')
    L.append('Files: `continuum_points.json` (every point, all M1-M4 diagnostics), `regulator_fits.json` '
             '(every deduplicated regulator fit with its admissibility), `C2_estimate.json` (per-order and joint '
             'results, error budget, outcome branch, rules, input hashes), `evidence/` (cluster job receipts, logs, '
             'legacy reproduction).\n')

    # ---- outcome
    cov = estimate['extraction_coverage']
    if estimate.get('deviations'):
        L.append('Approved deviations from the plan (operational; no rule changed): '
                 + '; '.join(f"{d['title']} ({d['file']})" for d in estimate['deviations']) + '.\n')
    L.append('## Result\n')
    L.append(f"Extraction coverage: **{cov['label']}** ({cov['n_measured']} of {cov['n_points']} primary points "
             'have a direct full-coverage extraction comparison).\n')
    if cov['exceptions']:
        L.append('Rev-4 exceptions (R6-002; flagged "extraction comparison missing: rev-4 exception"; their frozen '
                 'rev-4 epsilon_grid is used):\n')
        L.append(table(['r', 'lambda', 'N', 'frozen rev-4 eps_grid', 'rev-4 status', 'rev-4 flags', 'rev-4 donor'],
                       [[x['order'], x['lam'], x['N'], g(x['frozen_rev4']['eps_grid']), x['frozen_rev4']['status'],
                         '; '.join(x['frozen_rev4'].get('flags') or []) or '-', x['frozen_rev4'].get('donor') or '-']
                        for x in cov['exceptions']]) + '\n')
    L.append(f"Outcome-table branch **{outcome['branch']}**: {outcome['label']}"
             + ('' if cov['complete'] else ' (extraction coverage incomplete)') + '.\n')
    if final:
        L.append(f"- h0 = {final['h0']:.6f} +- {final['E_h0']:.6f}")
        L.append(f"- **C2 = {final['C2']:.5f} +- {final['dC2']:.5f}** "
                 f"(C2 = -pi^2/(4 b0) + h0/b0^2, b0 = {float(final['b0']):.15f}; dC2 = dh0/b0^2 = "
                 f"{final['dC2_per_dh0']:.5f} dh0)\n")
    else:
        L.append('- no estimate\n')
    rows = []
    for k, v in sorted(order_results.items()):
        status = 'retained' if v['validated'] else f"EXCLUDED: {v.get('exclusion_reason') or v['validation_status']}"
        if 'h0' in v:
            rows.append([k, v['selection_status'], v['validation_status'], f"{v['h0']:.6f}", f"{v['E']:.6f}",
                         f"{v['C2']['C2']:.5f}", f"{v['C2']['dC2']:.5f}", status])
        else:
            rows.append([k, v['selection_status'], v['validation_status'], '-', '-', '-', '-', status])
    L.append(table(['order', 'S_r', 'validation', 'h0_r', 'E_r', 'C2_r', 'dC2_r', 'status'], rows) + '\n')
    unavailable = [(k, v['preferred']) for k, v in sorted(order_results.items())
                   if v.get('preferred') and not v['preferred'].get('available', True)]
    for k, pv in unavailable:
        L.append(f"Order {k}: the preferred fit is unavailable ({'; '.join(pv.get('rejection_reasons') or [])}); "
                 'the fallback and validation rules were applied.\n')
    if final is None:
        L.append(f"**No estimate** (outcome branch {outcome['branch']}: {outcome['label']}): no regulator order is "
                 'retained; the exclusion reasons are listed in the table above.\n')
    if outcome.get('pairs'):
        L.append('Order consistency (|h0_r - h0_r\'| <= E_r + E_r\'):\n')
        L.append(table(['orders', '|difference|', 'E_r + E_r\'', 'consistent'],
                       [[f"{p['orders'][0]}-{p['orders'][1]}", g(p['difference']), g(p['limit']), g(p['consistent'])]
                        for p in outcome['pairs']]) + '\n')
        e = outcome['envelope']
        L.append(f"Envelope of the retained orders: [{e['low']:.6f}, {e['high']:.6f}] = {e['midpoint']:.6f} +- "
                 f"{e['half_width']:.6f} in h0.\n")
    if estimate.get('joint'):
        j = estimate['joint']
        L.append(f"Joint fit (shared h0, each order with its S_r): h0 = {j['h0']:.6f}, accepted = {g(j['accepted'])}, "
                 f"condition {j['condition']:.3g}, {j['n_admissible_distinct']} distinct admissible joint variants "
                 f"of {j['n_variants']}, eps_model,joint = {j['eps_model_joint']:.3e}, E_joint = {j['E']:.3e}; "
                 f"C2 = {j['C2']['C2']:.5f} +- {j['C2']['dC2']:.5f}.\n")
        L.append(table(['block (order)', 'points', 'terms', 'weighted', 'block dof', 'max |res|', 'limit', 'passed'],
                       [[b['order'], b['points'], ','.join(b['terms']), g(b['weighted']), b['block_dof'],
                         g(b['max_residual']), g(b['residual_limit']), g(b['passed'])] for b in j['blocks']]) + '\n')

    sup = estimate.get('superseded_rev4')
    if sup:
        L.append(f"Superseded rev-4 result (evidence/rev4/, L1 extraction rule with inheritance): branch "
                 f"{sup['outcome_branch']}, h0 = {sup['h0']:.6f} +- {sup['E_h0']:.4g}, C2 = {sup['C2']:.5f} +- "
                 f"{sup['dC2']:.4g}; E_r = " + ', '.join(f"{v['E']:.4g} (r={k})" for k, v in sorted(sup['per_order'].items()))
                 + '. The central values are unchanged by construction; only epsilon_grid changed.\n')

    # ---- caveats (computed from the outputs)
    L.append('## Caveats\n')
    L.append('- Limitation (M4d): a difference between two Cauchy grids measures extraction sensitivity. It does '
             'not bound an extraction error that both grids share.')
    meas = [c for m in measured.values() for c in m['comparisons']]
    if meas:
        L.append(f"- Extraction (M4d, rev 6/7): epsilon_grid = |v.s| + sum|v||rho| on each selected window (cubic "
                 f"smooth part with its measured sign, rough residual at worst-case signs), the maximum over the "
                 f"selected fits and over every full-coverage comparison of the point. Over the {len(meas)} "
                 f"full-coverage comparisons, max|rho| is {min(c['max_abs_rho'] for c in meas):.2e} to "
                 f"{max(c['max_abs_rho'] for c in meas):.2e} against max|delta| {min(c['max_delta'] for c in meas):.2e} "
                 f"to {max(c['max_delta'] for c in meas):.2e}. The superseded rev-4 L1 sum|v||delta| on the same "
                 f"profiles is reported per point and in the budget (not in E).")
    groups: dict[float, list] = {}
    for m in measured.values():
        for c in m['comparisons']:
            if c.get('check_grid'):
                groups.setdefault(c['check_grid']['radius_cost'], []).append(c['max_delta'])
    if len(groups) > 1:
        L.append('- The M4d comparisons differ in size by check grid: ' + '; '.join(
            f'radius_cost {r:g}: max |delta_n| {min(v):.2e} to {max(v):.2e}' for r, v in sorted(groups.items()))
                 + '. A difference between two grids does not say which grid carries it; the variant grid '
                   '(radius_cost 4.0) has a larger Cauchy radius and so more aliasing than the production '
                   'grid (4.5).')
    partial = [(k, c) for k, m in measured.items() for c in m.get('partial', [])]
    if partial:
        L.append('- Partial overlaps reported but never used for epsilon_grid: ' + '; '.join(
            f"{k} vs {c['check_record']} ({c['coverage']}, max |delta| {c['max_delta']:.2e})" for k, c in partial) + '.')
    low = [p for p in points if p['lambda_N'] < ca_min(p['order'])]
    if low:
        L.append('- Points below the lambda*N science minimum (flag only, M4c): '
                 + ', '.join(f"({p['order']}, {p['lam']}, N={p['N']}, lambda N={p['lambda_N']:.1f})" for p in low) + '.')
    lv = estimate.get('legacy_validation') or {}
    if not lv.get('performed'):
        L.append('- Legacy mode (A1): legacy validation was not performed for this run (no legacy receipt given).')
    elif lv.get('status') == 'INCOMPLETE':
        L.append(f"- Legacy mode (A1): **INCOMPLETE** receipt `{lv['file']}` (sha256 {str(lv.get('sha256'))[:12]}...): "
                 + '; '.join(lv.get('problems') or []) + '. No A1 result is stated.')
    else:
        pl = lv.get('platform') or {}
        L.append(f"- Legacy mode (A1), from the inspected receipt `{lv['file']}` (sha256 {lv['sha256'][:12]}...; "
                 f"platform {pl.get('platform', '?')}, python {str(pl.get('python', '?')).split()[0]}, numpy "
                 f"{pl.get('numpy', 'not recorded')}): **{lv['status']}**. Same-machine byte "
                 f"identity with the pristine {lv.get('pristine_commit')} run: "
                 f"{count(lv['same_platform_pristine_bytes_identical'])}; cross-platform category checks against the "
                 f"shipped reference passed: {count(lv['cross_platform_passed'])} (largest value difference "
                 f"{g(max((lv.get('max_abs_value_difference') or {}).values(), default=None))}, representative C2 "
                 f"{g(lv.get('max_abs_representative_C2_difference'))}, condition numbers "
                 f"{g(max((lv.get('max_rel_condition_difference') or {}).values(), default=None))} relative); byte "
                 f"identity with the shipped reference: {count(lv.get('bytes_identical_to_reference') or {})}.")
    L.append('')

    # ---- error budget
    L.append('## Error budget (M8)\n')
    L.append('Each component is sum_i |w_i| eps_i through the influence row of the quoted fit (L1, worst-case '
             'signs). The "of which" lines under eps_prop split it by the parts of eps_spec = max(half-spread, '
             'prefix drift, cross-N) and are not additive; those under eps_grid give its smooth and rough parts '
             '(for rev-4 exceptions both are counted as 0 there). The rows "rev-4 L1 (superseded)" and "signed '
             'shift" are reported through the same weights and are NOT in E.\n')
    if not budget['per_order']:
        L.append('No regulator order has a selected fit, so there is no error budget (no estimate).\n')
    cols = ['component'] + [f'order {k} (h0)' for k in sorted(budget['per_order'])]
    if 'joint' in budget:
        cols += ['joint (h0)', 'joint (C2)']
    first = next(iter(budget['per_order'].values()), None) or budget.get('joint')
    names = [r['component'] for r in first['table']] if first else []
    descr = {r['component']: r['description'] for r in first['table']} if first else {}
    rows = []
    for nme in names:
        row = [descr[nme]]
        for k in sorted(budget['per_order']):
            row.append(g([r for r in budget['per_order'][k]['table'] if r['component'] == nme][0]['h0']))
        if 'joint' in budget:
            jr = [r for r in budget['joint']['table'] if r['component'] == nme][0]
            row += [g(jr['h0']), g(jr['C2'])]
        rows.append(row)
    if first:
        tot = ['**total E (linear sum)**'] + [g(budget['per_order'][k]['E']) for k in sorted(budget['per_order'])]
        if 'joint' in budget:
            tot += [g(budget['joint']['E']), g(budget['joint']['E_C2'])]
        rows.append(tot)
        L.append(table(cols, rows) + '\n')
    quoted = budget.get('joint') if outcome['branch'] == 4 else None
    if quoted:
        shares = [(r['description'].strip(), r['h0'] / quoted['E']) for r in quoted['table']
                  if r['h0'] is not None and r['component'] in IN_E]
        L.append('Share of the quoted E_joint by component: ' + '; '.join(f'{d}: {100 * s:.3g}%' for d, s in shares) + '.\n')
    for k in sorted(budget['per_order']):
        t = budget['per_order'][k]
        shares = [(r['component'], r['h0'] / t['E']) for r in t['table'] if r['h0'] is not None
                  and r['component'] in IN_E]
        L.append(f'Share of E_{k}: ' + ', '.join(f'{c} {100 * s:.3g}%' for c, s in shares) + '.')
    L.append('')
    oc = budget['order_consistency']
    L.append(f"Order consistency: largest pairwise |h0_r - h0_r'| = {g(oc['max_pair_difference'])} "
             f"(C2: {g(oc['max_pair_difference'] * budget['conversion_dC2_per_dh0'])}). "
             f"Quoted: branch {budget['quoted']['branch']}, E(h0) = {g(budget['quoted']['E_h0'])}, "
             f"E(C2) = {g(budget['quoted']['E_C2'])}.\n")

    # ---- points
    L.append('## Fixed-regulator points (PRIMARY pool, M5)\n')
    L.append('h is the median of the accepted selected M3 fits with aligned auxiliary inputs (mixed 16384, '
             'collapsed 800000, tail 8192). eps_spec = max(half-spread, |h(N)-h(3N/4)|, eps_cross).\n')
    rows = []
    for p in points:
        c = p['eps_spec_components']
        e = p['eps']
        rows.append([p['order'], p['lam'], p['N'], f"{p['lambda_N']:.1f}", f"{p['h']:.9f}", g(c['half_spread']),
                     g(c['prefix_d34']), g(c['eps_cross']), g(p['eps_spec']), g(e['eps_mix']), g(e['eps_coll']),
                     g(e['eps_grid']) + (' (rev-4 exc.)' if p['extraction']['status'] == 'rev-4 exception' else ''),
                     g(e['eps_round']), g(e['eps_tailcut']),
                     f"{p['spectral']['n_selected_accepted']}/{p['spectral']['n_selected']}"])
    L.append(table(['r', 'lambda', 'N', 'lambda N', 'h(lambda)', 'half-spread', 'prefix d34', 'eps_cross',
                    'eps_spec', 'eps_mix', 'eps_coll', 'eps_grid', 'eps_round', 'eps_tailcut', 'fits acc.'], rows) + '\n')
    fl = [(p['order'], p['lam'], p['N'], f) for p in points for f in p['flags']]
    if fl:
        L.append('Flags:\n')
        L += [f'- ({k}, {a}, N={n}): {f}' for k, a, n, f in fl]
        L.append('')
    if replaced:
        L.append('Replaced by M5 (kept as cross-N checks):\n')
        L += [f"- ({r['order']}, {r['lam']}): N={r['replaced_N']} -> N={r['by_N']}" for r in replaced]
        L.append('')

    # ---- auxiliary alignment
    L.append('## Auxiliary-cutoff alignment of archived points (M1, M2, M2b)\n')
    rows = []
    for p in points:
        lc = p['legacy_inputs_comparison']
        if lc:
            rows.append([p['order'], p['lam'], p['N'], f"{lc['legacy_inputs']['h']:.9f}", f"{p['h']:.9f}",
                         g(lc['M1_mixed_shift_t_times_delta']), g(lc['M1_mixed_shift_h']),
                         g(lc['M2b_collapsed_shift_h']), g(lc['M2_tail_shift_h']), g(lc['total_shift_h'])])
    if rows:
        L.append(table(['r', 'lambda', 'N', 'h (recorded inputs)', 'h (aligned)', 't x d(mixed)', 'mixed 4096->16384',
                        'collapsed ->800000', 'tail 2048->8192', 'total'], rows) + '\n')
    rows = []
    for p in points:
        a = p['auxiliary']
        rows.append([p['order'], p['lam'], g(a['mixed']['t'], '.3f'), g(a['mixed']['mixed_limit'], '.9f'),
                     g(a['mixed']['mixed_half_spread']), g(a['mixed']['prefix_shift']), g(a['tail']['A_face_8192'], '.6g'),
                     g(a['tail']['A_face_2048'] - a['tail']['A_face_8192']), g(a['collapsed']['Xdisc_shift']),
                     g(a['collapsed']['A_face_shift'])])
    L.append(table(['r', 'lambda', 't', 'mixed limit (16384)', 'mixed half-spread', '|prefix - full|',
                    'A_face (8192)', 'A(2048)-A(8192)', 'Xdisc(800k)-Xdisc(400k)', 'A(800k)-A(400k)'], rows) + '\n')

    # ---- validation
    L.append('## Spectral validation (M4)\n')
    L.append("### Prefix test (M4a): h at N' = N/2, 2N/3, 3N/4, N\n")
    rows = []
    for p in points:
        pr = p['prefix_test']
        rows.append([p['order'], p['lam'], p['N']] + [f"{r['N_prime']}: {r['h']:.9f}" if r['h'] is not None else '-'
                                                      for r in pr['rows']] + [g(pr['drift']), g(pr['d34'])])
    L.append(table(['r', 'lambda', 'N', "N'1", "N'2", "N'3", "N'4", 'drift (max-min)', '|h(N)-h(3N/4)|'], rows) + '\n')
    L.append('### Cross-N (M4b), aligned auxiliary inputs\n')
    rows = []
    for p in points:
        for c in p['cross_N']:
            rows.append([p['order'], p['lam'], p['N'], c['N'], c['pool'], f"{c['lambda_N']:.1f}",
                         g(c['meets_lambda_N_minimum']), f"{c['h']:.9f}" if c['h'] is not None else '-',
                         g(c['abs_difference_to_primary']), g(c['enters_eps_cross']),
                         ','.join(c['configuration_differences_from_primary'])])
    L.append(table(['r', 'lambda', 'N primary', 'N other', 'pool', 'lambda N', 'meets min', 'h other', '|diff|',
                    'enters eps_cross', 'config differences'], rows) + '\n')
    L.append('### Extraction (M4d) and roundoff (M4e)\n')
    L.append('Per primary point (rev 6/7): the A5-1 epsilon_grid (in E) and, NOT in E, the superseded rev-4 L1 '
             'sum|v||delta|, the plain signed shift |sum v delta| and max_W|rho|, each the maximum over the accepted '
             'selected fits and the full-coverage comparisons. eps_round keeps its L1 form (rounding errors have '
             'random signs).\n')
    rows = []
    for p in points:
        x = p['extraction']
        rows.append([p['order'], p['lam'], p['N'], x['status'], x.get('n_full_coverage', 0),
                     g((x.get('measured') or {}).get('comparisons', [{}])[0].get('max_delta')
                       if x['status'] == 'measured' else None),
                     g(x.get('signed_shift')), g(x.get('max_abs_rho')), g(x.get('smooth')), g(x.get('rough')),
                     g(x['eps_grid']), g(x.get('rev4_l1')), g(p['roundoff']['eps_round'])])
    L.append(table(['r', 'lambda', 'N', 'status', 'comparisons', 'max|delta| (first)', 'signed |v.delta|',
                    'max|rho|', 'smooth |v.s|', 'rough sum|v||rho|', 'eps_grid (A5-1, in E)',
                    'rev-4 L1 (superseded, not in E)', 'eps_round'], rows) + '\n')
    L.append('All comparisons (the last three columns are illustrative and in no budget: mean signed delta over '
             'the last quarter, the largest |sum v delta|, and the change of the median when the check chain '
             'replaces the primary chain):\n')
    rows = []
    for ident, m in sorted(measured.items()):
        for c in m['comparisons']:
            il = c.get('illustrative_not_in_budget', {})
            rows.append([ident, c['kind'], c['check_record'], c['coverage'], g(c['max_delta']), g(c['max_abs_rho']),
                         g(c['eps_grid']), g(c['rev4_l1']), g(il.get('constant_shift')),
                         g(il.get('max_abs_signed_fit_shift')), g(il.get('median_shift_by_replacement'))])
        for c in m.get('partial', []):
            rows.append([ident, c['kind'], c['check_record'], c['coverage'], g(c['max_delta']), '-', 'not used',
                         '-', '-', '-', '-'])
    L.append(table(['record', 'kind', 'compared with', 'coverage', 'max|delta|', 'max|rho|', 'eps_grid (A5-1)',
                    'rev-4 L1', 'const. shift (illus.)', 'max signed fit shift (illus.)', 'median shift (illus.)'],
                   rows) + '\n')
    L.append('### Cross-site replicas (A3)\n')
    reps = [(o['record'] if 'record' in o else o, o) for o in list(points) + list(others)]
    rows = []
    for rec, _ in reps:
        for rp in rec.get('replicas') or []:
            rows.append([rec['ident'], rec['site'], rp['site'], g(rp.get('max_abs_raw_chain_difference')),
                         g(rp.get('finite_cutoff_h_difference'))])
    if rows:
        L.append('Records of the same configuration and sources on several sites are one replica (Expanse '
                 'representative); the differences are raw partial sums (max over n) and the sidecar finite-cutoff h.\n')
        L.append(table(['record', 'representative site', 'replica site', 'max |raw chain difference|',
                        'finite-cutoff h difference'], rows) + '\n')
    else:
        L.append('No record has a replica on another site.\n')
    L.append('### Records reported alongside (never estimates)\n')
    rows = [[o['record']['ident'], o['role'], f"{o['lambda_N']:.1f}", g(o['meets_lambda_N_minimum']),
             f"{o['h']:.9f}" if o['h'] is not None else '-', g(o['half_spread'])] for o in others]
    L.append(table(['record', 'role', 'lambda N', 'meets min', 'h (aligned aux)', 'half-spread'], rows) + '\n')

    # ---- regulator fits
    L.append('## Regulator limit per order (M6)\n')
    for k, reg in sorted(regs.items()):
        L.append(f"### Order {k}: {reg['selection_status']}; {reg['validation_status']}\n")
        S = reg['S']
        if S is not None:
            L.append(f"S_{k}: terms {{{','.join(S['terms'])}}}, {'weighted' if S['weighted'] else 'unweighted'}, "
                     f"windows {S['windows']}, lambdas {S['lambdas']}, h0 = {S['h0']:.6f}, dof {S['dof']}, "
                     f"max |res| {S['max_residual']:.2e} (limit {S['residual_limit']:.2e}), condition "
                     f"{S['condition']:.3g}; eps_model = {reg['eps_model']:.3e}.\n")
        rows = []
        for f in sorted(reg['fits'], key=lambda f: (not f['admissible'], f['number_of_parameters'], -f['number_of_points'])):
            rows.append([','.join(f['terms']) + (' (sens.)' if f['sensitivity_variant'] else ''),
                         'w' if f['weighted'] else 'u', '/'.join(f['windows']), f['number_of_points'], f['dof'],
                         f"{f['h0']:.6f}", g(f['max_residual']), g(f['residual_limit']), f"{f['condition']:.2g}",
                         'ADMISSIBLE' if f['admissible'] else ', '.join(f['rejection_reasons']),
                         'S_r' if f.get('selected') else ('preferred' if f.get('preferred') else '')])
        L.append(table(['terms', 'wt', 'windows', 'pts', 'dof', 'h0', 'max |res|', 'limit', 'cond', 'status', 'role'],
                       rows) + '\n')

    # ---- comparison after computation
    cmp = estimate['comparison_after_computation']
    L.append('## Comparison with earlier numbers (made after the computation)\n')
    L.append(cmp['note'] + '\n')
    L.append(table(['order', 'new C2_r', 'new dC2_r', 'historical C2 (representative fit)', 'difference',
                    'difference / dC2_r'],
                   [[r['order'], f"{r['new_C2']:.5f}", f"{r['new_dC2']:.5f}", f"{r['historical_C2']:.5f}",
                     f"{r['difference']:+.5f}", f"{r['in_units_of_new_error']:+.2f}"] for r in cmp['per_order']]) + '\n')
    if final:
        L.append(f"Earlier reviewers: C2 = -4.067 +- 0.004. This analysis: C2 = {final['C2']:.5f} +- {final['dC2']:.5f} "
                 f"(difference {cmp['final_minus_reviewers']:+.5f}).\n")
    (out / 'REPORT.md').write_text('\n'.join(L) + '\n')
