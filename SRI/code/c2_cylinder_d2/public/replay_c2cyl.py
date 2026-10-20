#!/usr/bin/env python3
"""Fast replay of c_2 in d = 2 from the cylinder Hamiltonian (new tool, 2026-10-15). Run from code/c2_cylinder_d2/.

Input: the shipped result generation results/continuum_2026-10/generations/<CURRENT>/ (continuum_points.json: the 25
PRIMARY points (order r, lambda) with their finite-cutoff limits h(lambda) and the per-point error components;
regulator_fits.json; C2_estimate.json). Nothing here reads the raw records (that is replay-full).

1. Verbatim chain M6-M8: the per-order regulator fits (all windows, term sets, weightings; S_r, eps_model, validation),
   the joint fit with its variants, the outcome table, every error component, E and C2 +- dC2 are recomputed from the
   shipped points with the shipped functions (code/continuum/continuum_analysis.py: regulator_order, joint_analysis,
   outcome, c2_from_h0; continuum_driver.py: order_result, error_budget) and compared leaf by leaf with the shipped
   regulator_fits.json and C2_estimate.json: 1e-9 relative for h0, the influence rows, E, the components and C2; the
   regulator coefficients beyond the intercept, the residuals and the condition numbers of the ill-conditioned 4- and
   5-parameter fits 1e-6 relative or 1e-12 absolute (c2cyl_common.fit_detail_tol); flags and counts equal.
2. Independent recomputation (plain numpy and mpmath written here, no package function): every regulator fit of every
   order and every joint variant refitted from its point ids, terms and weighting (h0, max residual, condition number,
   admissibility: dof >= 2, max residual <= 3 max eps_spec, condition < 1e8); S_r, eps_model = max |h0 - h0(S_r)| over
   the admissible fits, E_r = sum_i |w_i| (eps_spec + eps_mix + eps_coll + eps_grid + eps_round + eps_tailcut)_i +
   eps_model with w the intercept row of pinv; pairwise order consistency |h0_a - h0_b| <= E_a + E_b; the joint fit
   (shared h0) and E_joint; C2 = a1/b0 + h0/b0^2, dC2 = E/b0^2, b0 = 9 pi^4/(4 Gamma(1/4)^4), a1 = -pi^2/4.
3. Quoted numbers (../../results/quoted_numbers.json, package c2_cylinder_d2) and the c_2 row of tab:htpert with its
   footnote (f) (public/tab_htpert_c2.json): \\SRtwoCtwoHT (value and uncertainty, PDG two digits), \\SRtwoCtwoHTDev
   (relative deviation from the closed form, evaluated here with mpmath), \\SRtwoCtwoHTNmax (largest N of the points; note only),
   and the statements of footnote (f).
Usage: python3 public/replay_c2cyl.py [--out FILE]
"""
import argparse, json, sys
from pathlib import Path

import numpy as np

from c2cyl_common import (L, PKG, RESULTS, C2_CLOSED_TEXT, current_generation, load_json, c2_closed, b0_a1,
                          matches_paren, quoted_entries, compare_tree, fit_detail_tol)

sys.path.insert(0, str(PKG / 'code' / 'continuum'))
import continuum_analysis as ca                       # noqa: E402  (verbatim, read-only)
import continuum_driver as drv                        # noqa: E402  (verbatim, read-only)

RTOL, ATOL = 1e-9, 1e-14
COMP = ('eps_spec', 'eps_mix', 'eps_coll', 'eps_grid', 'eps_round', 'eps_tailcut')


def points_from(cp):
    """The per-point dict the driver builds before M6 (continuum_driver.run), rebuilt from continuum_points.json."""
    pts = {}
    for q in cp['primary_points']:
        x, e, s = q['extraction'], q['eps'], q['eps_spec_components']
        pts[q['id']] = dict(id=q['id'], order=q['order'], lam=q['lam'], h=q['h'], eps_spec=q['eps_spec'],
                            eps_mix=e['eps_mix'], eps_coll=e['eps_coll'], eps_grid=e['eps_grid'],
                            eps_round=e['eps_round'], eps_tailcut=e['eps_tailcut'], half_spread=s['half_spread'],
                            prefix_d34=s['prefix_d34'], eps_cross=s['eps_cross'], grid_smooth=x.get('smooth'),
                            grid_rough=x.get('rough'), grid_rev4_l1=x.get('rev4_l1'), grid_signed=x.get('signed_shift'))
    return pts


def chain(points):
    """M6-M8 exactly as continuum_driver.estimate_and_write, without writing anything."""
    by_order = {}
    for pt in points.values():
        by_order.setdefault(pt['order'], []).append(pt)
    regs = {k: ca.regulator_order(v, k) for k, v in sorted(by_order.items())}
    per_order, order_results = {}, {}
    for k, reg in regs.items():
        order_results[k], kept = drv.order_result(k, reg, points)
        if kept is not None:
            per_order[k] = kept
    retained = sorted(per_order)
    joint = ca.joint_analysis(regs, retained, points, by_order) if len(retained) >= 2 else None
    out_table = ca.outcome(per_order, joint)
    final = None
    if out_table['h0'] is not None:
        final = dict(h0=out_table['h0'], E_h0=out_table['E'], **ca.c2_from_h0(out_table['h0'], out_table['E']))
    budget = drv.error_budget(out_table, order_results, joint)
    reg_out = dict(orders={str(k): dict(
        order=k, fits=v['fits'], skipped_underdetermined=v['skipped_underdetermined'],
        selected=order_results[k].get('S'), preferred=order_results[k]['preferred'],
        preferred_terms=list(ca.PREFERRED['terms']), selection_status=v['selection_status'],
        validation_status=v['validation_status'], exclusion_reason=v.get('exclusion_reason'))
        for k, v in regs.items()}, joint=joint)
    est = dict(per_order=order_results, retained_orders=retained, joint=None if joint is None else dict(
        h0=joint['preferred']['h0'], accepted=joint['preferred']['accepted'], blocks=joint['preferred']['blocks'],
        condition=joint['preferred']['condition'], n_variants=joint['n_variants'],
        n_admissible_distinct=joint['n_admissible_distinct'], eps_model_joint=joint['eps_model_joint'],
        components=joint['components'], E=joint['E'], validated=joint['validated'],
        C2=ca.c2_from_h0(joint['preferred']['h0'], joint['E'])), outcome=out_table, final=final, error_budget=budget)
    # the same JSON cleaning as the driver's writer (tuples -> lists, numpy scalars -> float, non-finite refused)
    return json.loads(json.dumps(ca.clean(reg_out), allow_nan=False)), json.loads(json.dumps(ca.clean(est), allow_nan=False))


# ------------------------------------------------------------------ independent recomputation

def basis(x, t):
    p = float(t.replace('log', ''))
    return x ** p * (np.log(x) if t.endswith('log') else 1.0)


def fit(pts, terms, weighted):
    x = np.array([p['lam'] for p in pts]); y = np.array([p['h'] for p in pts]); s = np.array([p['eps_spec'] for p in pts])
    A = np.column_stack([np.ones_like(x)] + [basis(x, t) for t in terms])
    sc = s if weighted else np.ones_like(s)
    B = A / sc[:, None]
    c = np.linalg.lstsq(B, y / sc, rcond=None)[0]
    res = A @ c - y
    w = np.linalg.pinv(B)[0] / sc
    cond = float(np.linalg.cond(B))
    dof = len(x) - len(c)
    mres = float(np.max(np.abs(res)))
    adm = dof >= 2 and mres <= 3.0 * float(np.max(s)) and cond < 1e8
    return dict(h0=float(c[0]), w=w, cond=cond, dof=dof, max_res=mres, admissible=bool(adm))


def propagate(w, ids, points):
    return sum(abs(wi) * sum(points[i][c] or 0.0 for c in COMP) for wi, i in zip(w, ids))


def joint_fit(blocks, points):
    """blocks: [(point ids, terms, weighted)]; shared intercept, own regulator coefficients per block."""
    ncols = 1 + sum(len(t) for _, t, _ in blocks)
    rows, y, s, owner, ids = [], [], [], [], []
    col = 1
    for bi, (pids, terms, weighted) in enumerate(blocks):
        for i in pids:
            p = points[i]
            r = np.zeros(ncols); r[0] = 1.0
            for j, t in enumerate(terms):
                r[col + j] = basis(np.array([p['lam']]), t)[0]
            rows.append(r); y.append(p['h']); s.append(p['eps_spec'] if weighted else 1.0); owner.append(bi); ids.append(i)
        col += len(terms)
    A, y, s, owner = np.array(rows), np.array(y), np.array(s), np.array(owner)
    B = A / s[:, None]
    c = np.linalg.lstsq(B, y / s, rcond=None)[0]
    res = A @ c - y
    w = np.linalg.pinv(B)[0] / s
    cond = float(np.linalg.cond(B))
    ok = cond < 1e8
    for bi, (pids, terms, _) in enumerate(blocks):
        m = owner == bi
        ok = ok and (int(m.sum()) - len(terms) - 1 >= 2) and float(np.max(np.abs(res[m]))) <= 3.0 * max(points[i]['eps_spec'] for i in pids)
    return dict(h0=float(c[0]), w=w, ids=ids, cond=cond, accepted=bool(ok))


def close(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(a))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(PKG / '.work' / 'replay_c2cyl.txt'))
    a = ap.parse_args()
    T = L.Table('c2_cylinder_d2 replay (fast, from the shipped result generation)')
    gen = current_generation()
    cp, rf, est = (load_json(gen / f) for f in ('continuum_points.json', 'regulator_fits.json', 'C2_estimate.json'))
    T.check('CURRENT generation', est['meta'].get('generation') == gen.name and cp['meta'].get('generation') == gen.name,
            gen.name, 'meta.generation of the files', 'results/continuum_2026-10/CURRENT -> generations/<name>')
    points = points_from(cp)
    T.check('PRIMARY points', len(points) == 25 and est['extraction_coverage']['n_measured'] == 25
            and est['extraction_coverage']['complete'], f'{len(points)} points, {est["extraction_coverage"]["n_measured"]} '
            'with a measured extraction comparison', '25, coverage complete', 'continuum_points.json primary_points')

    # 1. the verbatim chain
    reg_new, est_new = chain(points)
    cond_rtol = fit_detail_tol
    r = compare_tree(rf['orders'], reg_new['orders'], RTOL, ATOL, rel_tol_for=cond_rtol)
    T.check('regulator fits (verbatim chain)', not r['bad'], f"{r['leaves']} leaves, max rel {r['max_rel']:.1e} at "
            f"{r['max_rel_at'] or '-'}; {len(r['bad'])} outside", 'regulator_fits.json orders, rtol 1e-9 (fit coefficients, residuals, conditions 1e-6)',
            'continuum_analysis.regulator_order + continuum_driver.order_result on the shipped points')
    r = compare_tree(rf['joint'], reg_new['joint'], RTOL, ATOL, rel_tol_for=cond_rtol)
    T.check('joint fit and variants (verbatim chain)', not r['bad'], f"{r['leaves']} leaves, max rel {r['max_rel']:.1e}; "
            f"{len(r['bad'])} outside", 'regulator_fits.json joint, rtol 1e-9', 'continuum_analysis.joint_analysis')
    for key in ('per_order', 'retained_orders', 'joint', 'outcome', 'error_budget'):
        r = compare_tree(json.loads(json.dumps({str(k): v for k, v in est[key].items()} if isinstance(est[key], dict) else est[key])),
                         json.loads(json.dumps({str(k): v for k, v in est_new[key].items()} if isinstance(est_new[key], dict) else est_new[key])),
                         RTOL, ATOL, rel_tol_for=cond_rtol)
        T.check(f'C2_estimate {key}', not r['bad'], f"{r['leaves']} leaves, max rel {r['max_rel']:.1e}; {len(r['bad'])} outside"
                + (f" ({r['bad'][0]})" if r['bad'] else ''), 'C2_estimate.json, rtol 1e-9', 'verbatim chain M6-M8')
    fin = dict(est['final']); fin.pop('label', None)
    r = compare_tree(fin, est_new['final'], RTOL, ATOL)
    T.check('C2_estimate final', not r['bad'], f"C2 = {est_new['final']['C2']:.10f} +- {est_new['final']['dC2']:.10f}",
            f"{est['final']['C2']:.10f} +- {est['final']['dC2']:.10f}", 'verbatim chain; rtol 1e-9')

    # 2. independent recomputation
    bad_fits, n_fits = [], 0
    reg_ind = {}
    for k, o in rf['orders'].items():
        fits = []
        for f in o['fits']:
            pts = [points[i] for i in f['point_ids']]
            g = fit(pts, f['terms'], f['weighted'])
            n_fits += 1
            if not (close(g['h0'], f['h0']) and close(g['max_res'], f['max_residual'], 1e-6)
                    and abs(g['cond'] / f['condition'] - 1) < 1e-6 and g['admissible'] == f['admissible'] and g['dof'] == f['dof']):
                bad_fits.append((k, f['terms'], f['weighted'], f['windows']))
            fits.append((f, g))
        S = o['selected']
        gS = fit([points[i] for i in S['point_ids']], S['terms'], S['weighted'])
        adm = [g for f, g in fits if g['admissible']]
        eps_model = max(abs(g['h0'] - gS['h0']) for g in adm)
        E = propagate(gS['w'], S['point_ids'], points) + eps_model
        reg_ind[int(k)] = dict(h0=gS['h0'], E=E, eps_model=eps_model, n_adm=len(adm))
    T.check('regulator fits (independent refit)', not bad_fits, f'{n_fits} fits; {len(bad_fits)} differ',
            'h0 1e-9, residual/condition 1e-6, admissibility and dof equal', 'plain numpy lstsq/pinv/cond written here')
    for k, v in sorted(reg_ind.items()):
        po = est['per_order'][str(k)]
        ok = close(v['h0'], po['h0']) and close(v['E'], po['E']) and close(v['eps_model'], po['components']['eps_model'])
        b0, a1 = b0_a1()
        c2 = float(a1 / b0 + v['h0'] / b0 ** 2)
        T.check(f'order {k}: h0, E (independent)', ok, f"h0 = {v['h0']:.8f}, E = {v['E']:.3e} (eps_model {v['eps_model']:.2e}, "
                f"{v['n_adm']} admissible); C2 = {c2:.6f}", f"{po['h0']:.8f}, {po['E']:.3e}", 'E_r = sum|w| eps + eps_model; 1e-9')
    pairs_ok = all(abs(reg_ind[x]['h0'] - reg_ind[y]['h0']) <= reg_ind[x]['E'] + reg_ind[y]['E']
                   for x in reg_ind for y in reg_ind if x < y)
    T.check('orders consistent (independent)', pairs_ok and est['outcome']['consistent'],
            ', '.join(f"|h0_{x}-h0_{y}| = {abs(reg_ind[x]['h0'] - reg_ind[y]['h0']):.2e} <= {reg_ind[x]['E'] + reg_ind[y]['E']:.2e}"
                      for x in reg_ind for y in reg_ind if x < y), 'all pairs consistent', 'pre-declared outcome table (M7)')
    J = rf['joint']
    pre = J['preferred']
    blocks = []
    for b in est['joint']['blocks']:
        S = rf['orders'][str(b['order'])]['selected']
        blocks.append((S['point_ids'], S['terms'], S['weighted']))
    gj = joint_fit(blocks, points)
    bad_var, n_acc = [], 0
    hv = []
    for v in J['variants']:
        # a variant's point ids are listed block after block, in the order of its blocks
        bl, pos = [], 0
        for b in v['blocks']:
            ids = v['point_ids'][pos:pos + b['points']]; pos += b['points']
            bl.append((ids, v['terms'], v['weighted']))
        g = joint_fit(bl, points)
        if not (close(g['h0'], v['h0']) and g['accepted'] == v['accepted']):
            bad_var.append(v['window_indices'])
        if g['accepted']:
            n_acc += 1; hv.append(g['h0'])
    eps_model_j = max(abs(h - gj['h0']) for h in hv)
    E_j = propagate(gj['w'], gj['ids'], points) + eps_model_j
    T.check('joint variants (independent)', not bad_var and n_acc == J['n_admissible_distinct'],
            f"{len(J['variants'])} variants, {n_acc} accepted; {len(bad_var)} differ", f"{J['n_admissible_distinct']} accepted",
            'shared-intercept refit of every variant; acceptance: block dof >= 2, residuals <= 3 max eps_spec, cond < 1e8')
    T.check('joint h0, E (independent)', close(gj['h0'], est['final']['h0']) and close(E_j, est['final']['E_h0'])
            and gj['accepted'] and n_acc >= 3,
            f"h0 = {gj['h0']:.10f}, E = {E_j:.10f} (eps_model {eps_model_j:.3e})",
            f"{est['final']['h0']:.10f}, {est['final']['E_h0']:.10f}", 'branch 4: orders consistent and joint fit validated')
    b0, a1 = b0_a1()
    C2 = float(a1 / b0 + gj['h0'] / b0 ** 2)
    dC2 = float(E_j / b0 ** 2)
    T.check('C2 +- dC2 (independent)', close(C2, est['final']['C2']) and close(dC2, est['final']['dC2']),
            f'{C2:.10f} +- {dC2:.10f}', f"{est['final']['C2']:.10f} +- {est['final']['dC2']:.10f}",
            'C2 = a1/b0 + h0/b0^2, dC2 = E/b0^2, b0 = 9 pi^4/(4 Gamma(1/4)^4)')
    comps = est['joint']['components']
    T.add('error components (C2 units)', 'INFO', '; '.join(f'{c} {comps[c] / float(b0) ** 2:.2e}' for c in
          ('eps_model', 'eps_prop', 'eps_mix', 'eps_round', 'eps_grid', 'eps_coll', 'eps_tailcut')),
          'sum = dC2', 'joint fit; linear sum, not a standard deviation')

    # 3. quoted numbers
    Q, _ = quoted_entries()
    e = Q['\\SRtwoCtwoHT']
    ok, how = matches_paren(C2, dC2, e['text'])
    st = 'PASS' if ok else 'FAIL'
    if e['status'] != 'printed':
        st = 'INFO'
    T.add('\\SRtwoCtwoHT', st, f'{C2:.7f} +- {dC2:.7f} [{how}]', e['text'], 'C2 and dC2 half-up to the 4 printed '
          'decimals, uncertainty in units of the last digit (PDG two digits)')
    cf = c2_closed(30)
    T.check('closed form (mpmath, 30 digits)', abs(cf - __import__('mpmath').mpf(C2_CLOSED_TEXT)) < 1e-17,
            __import__('mpmath').nstr(cf, 20), C2_CLOSED_TEXT, 'paper appendix (crossover in d = 2): Gamma ratio and three 4F3(1)')
    dev = abs(C2 - float(cf)) / abs(float(cf))
    T.quoted(Q['\\SRtwoCtwoHTDev'], [dev], '|C2 - c2_closed|/|c2_closed|, half-up to the printed digit')
    T.add('deviation in units of dC2', 'INFO', f'{abs(C2 - float(cf)) / dC2:.2f}', '0.33 (numbers.tex comment)',
          '|C2 - c2_closed| / dC2')
    nmax = max(q['N'] for q in cp['primary_points'])
    nmax_all = max([q['N'] for q in cp['primary_points']] + [o['record']['N'] for o in cp['other_records']])
    T.quoted(Q['\\SRtwoCtwoHTNmax'], [nmax], 'largest N of the PRIMARY points (all records: %d)' % nmax_all)

    # tab:htpert, the C^SR_2(2) (c_2) row and caption (paper source via ../../results/quoted_numbers.json, key
    # tab_htpert_c2; since 2026-10-15 the paper has no footnote (f): the caption states the error kind and the text
    # of the HT results states the cutoff). The analysis facts the former footnote stated are checked as "(note)".
    tab = load_json(PKG.parent.parent / 'results' / 'quoted_numbers.json').get('tab_htpert_c2') or load_json(Path(__file__).resolve().parent / 'tab_htpert_c2.json')
    row = tab['row_tex'].replace(' ', '')
    ok_row = row.split('&')[0] in (r'$C^{\rmSR}_2(2)$', r'$c_2$') and r'\ptClosed{\SRtwoCtwoHT}&$\SRtwoCtwoHTDev$' in row
    T.check('tab:htpert C^SR_2(2) row', ok_row, tab['row_tex'], 'd = 2 columns: \\ptClosed{\\SRtwoCtwoHT}, $\\SRtwoCtwoHTDev$',
            'the row prints the two macros checked above; delta = |C^HT/C - 1| against the closed form (\\ptClosed)')
    cap = tab.get('caption', '')
    T.check('tab:htpert caption: error kind', 'systematic diagnostics' in cap and 'standard deviation' in cap,
            'caption: error sums systematic diagnostics; not a standard deviation', 'as stated',
            'the caption of tab:htpert (paper source)')
    T.check('N <= \\SRtwoCtwoHTNmax', nmax == 1024, f'max N {nmax}', 'N <= 1024',
            'every primary point has N <= 1024 (the note; the paper no longer prints N_max)')
    share = comps['eps_model'] / est['final']['E_h0']
    ok_sum = close(sum(comps[c] for c in ('eps_prop', 'eps_mix', 'eps_coll', 'eps_grid', 'eps_round', 'eps_tailcut',
                                          'eps_model')), est['final']['E_h0'])
    T.check('(note) linear sum of diagnostics', ok_sum and 'not rigorous bounds or standard deviations' in est['error_budget']['status'],
            'E = sum of the seven components', est['error_budget']['status'], 'error_budget.status and the sum')
    T.check('(note) mostly the regulator model', share > 0.5,
            f'eps_model / E = {share:.1%}', '> 50% (numbers.tex: 64%)', 'joint eps_model over E')
    T.check('(note) closed form not an input', est['meta'].get('proposed_closed_form_used') is False
            and not any('06627' in p.read_text() for p in (PKG / 'code' / 'continuum').glob('*.py') if p.name != 'test_continuum.py'),
            'meta.proposed_closed_form_used = false; no 06627 in code/continuum', 'enters it in no way',
            'output flag and a search of the analysis code for the closed-form digits')
    sup = est['superseded_rev4']
    rev4 = load_json(RESULTS / 'evidence' / 'rev4' / 'C2_estimate.json')['final']
    T.check('(note) error rule revised, centre unchanged', sup['C2'] == est['final']['C2'] == rev4['C2']
            and sup['h0'] == est['final']['h0'] and abs(sup['dC2'] - rev4['dC2']) == 0,
            f"rev 4: {rev4['C2']!r} +- {rev4['dC2']:.3f}; rev 7: {est['final']['C2']!r} +- {est['final']['dC2']:.5f}",
            'same central value, bit for bit', 'evidence/rev4/C2_estimate.json vs the current generation')
    for k in ('1', '2', '3'):
        po = est['per_order'][k]
        T.add(f'order {k} C2 (per-order fit)', 'INFO', f"{po['C2']['C2']:.6f} +- {po['C2']['dC2']:.6f}",
              po['selection_status'] + ', ' + po['validation_status'], 'reported alongside; the joint fit is quoted')
    sys.exit(T.report(a.out))


if __name__ == '__main__':
    main()
