"""Local tests of merge / assemble / rounding / analyze (no engine needed). Run: python tests/test_tools.py"""
import sys, json, tempfile, subprocess, math
from pathlib import Path
import mpmath as mp
mp.mp.dps = 40

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import merge as M  # noqa: E402

REF = ROOT / 'reference'
failures = []


def check(name, cond, info=''):
    print(('PASS ' if cond else 'FAIL ') + name + (f'  [{info}]' if info else ''))
    if not cond:
        failures.append(name)


def header(**kw):
    h = {'type': 'header', 'engine': 'c6sum', 'kind': 'double8', 'git': 'x', 'source_sha256': 's', 'exe_sha256': 'e', 'graphs_sha256': 'g',
         'weights_file': 'w_6_8.bin', 'weights_sha256': 'w', 'L': 6, 'N': 8, 'mode': 'H', 'stratum': 'all', 'comp': 1, 'perturb': 0,
         'first': 0, 'stop': 360, 'mod': 1, 'sectors_total': 360, 'normalization': '1/(L*864)'}
    h.update(kw)
    return h


def write(path, hdr, sectors, vals=None, torn=False):
    lines = [json.dumps(hdr), json.dumps({'type': 'attempt', 'host': 'test', 'threads': 1})]
    for s in sectors:
        v = vals(s) if vals else [f'{s}.5'] * 12
        lines.append('{"type":"sector","sector":%d,"values":[%s],"active_groups":1,"seconds":0.1}' % (s, ','.join(v)))
    text = '\n'.join(lines) + '\n'
    if torn:
        text = text[:-5]
    Path(path).write_text(text)


def expect_refusal(name, files, subset='all', needle=''):
    try:
        M.merge(files, subset)
        check(name, False, 'merge accepted')
    except M.MergeError as e:
        check(name, needle in str(e), str(e)[:100])


with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    a, b = td / 'a.jsonl', td / 'b.jsonl'
    write(a, header(first=0, stop=180), range(0, 180)); write(b, header(first=180, stop=360), range(180, 360))
    res = M.merge([a, b])
    check('merge_good_two_ranges', len(res['sectors']) == 360 and mp.mpf(res['totals'][0]) == sum(s + mp.mpf('0.5') for s in range(360)))
    write(b, header(first=180, stop=360), list(range(180, 360)) + [5])
    expect_refusal('merge_rejects_out_of_range_sector', [a, b], needle='outside')
    write(b, header(first=100, stop=360), range(100, 360))
    expect_refusal('merge_rejects_cross_file_duplicate', [a, b], needle='more than one file')
    write(b, header(first=180, stop=360), range(181, 360))
    expect_refusal('merge_rejects_missing_sector', [a, b], needle='missing [180]')
    write(b, header(first=180, stop=360, weights_sha256='other'), range(180, 360))
    expect_refusal('merge_rejects_weights_mismatch', [a, b], needle='weights_sha256')
    write(b, header(first=180, stop=360, exe_sha256='other'), range(180, 360))
    expect_refusal('merge_rejects_engine_mismatch', [a, b], needle='exe_sha256')
    write(b, header(first=180, stop=360, N=10), range(180, 360))
    expect_refusal('merge_rejects_mixed_N', [a, b], needle='N')
    write(b, header(first=180, stop=360, stratum='hard'), range(180, 360))
    expect_refusal('merge_rejects_mixed_stratum', [a, b], needle='stratum')
    write(b, header(first=180, stop=360), range(180, 360), vals=lambda s: ['NaN'] + ['1'] * 11)
    expect_refusal('merge_rejects_nonfinite', [a, b], needle='non-finite')
    write(b, header(first=180, stop=360), range(180, 360), torn=True)
    expect_refusal('merge_rejects_torn_file', [a, b], needle='truncated')
    c = td / 'c.jsonl'
    Path(c).write_text(json.dumps(header()) + '\n{"type":"attempt"}\n' + '{"type":"sector","sector":3,"values":["1"]}\n' + '{"type":"sector","sector":3,"values":["1"]}\n')
    expect_refusal('merge_rejects_in_file_duplicate', [c], needle='duplicate')
    s = td / 's.jsonl'
    write(s, header(mod=10), [x for x in range(360) if x % 10 == 0])
    check('merge_subset_mod10', len(M.merge([s], 'mod10')['sectors']) == 36)
    w = td / 'w.jsonl'; write(w, header(L=6, sectors_total=60, stop=60), range(60))
    expect_refusal('merge_rejects_wrong_sectors_total', [w], needle='L!/2')
    write(w, header(), range(360), vals=lambda s: ['1'] * 10)
    expect_refusal('merge_rejects_wrong_width', [w], needle='vector length')
    Path(w).write_text(json.dumps(header()) + '\n' + ''.join('{"type":"sector","sector":%d,"values":[%s]}\n' % (x, ','.join(['1'] * 12)) for x in range(360)))
    expect_refusal('merge_rejects_missing_attempt', [w], needle='attempt')
    expect_refusal('merge_subset_mod_mismatch', [s], 'all', needle='mod')
    write(s, header(mod=1), [x for x in range(360) if x % 10 == 0])
    expect_refusal('merge_subset_header_mod1_as_mod10', [s], 'mod10', needle='mod')

    # ---- assemble: reference configuration reproduces the reference N6 baseline and the five-loop control
    lv = td / 'levels'; lv.mkdir()
    rd = lambda f: json.loads((REF / f).read_text(), parse_float=str)['values']
    def fake_level(name, L, mode, stratum, kind, N, vec, **kw):
        h = header(L=L, N=N, mode=mode, stratum=stratum, kind={'dbl': 'double8', 'ld': 'reference-longdouble'}[kind],
                   exe_sha256='e_' + kind, graphs_sha256=f'g{L}', sectors_total=360 if L == 6 else 60, stop=360 if L == 6 else 60, **kw)
        nsec = 360 if L == 6 else 60; subset = 'mod10' if kw.get('mod') == 10 else 'all'
        secs = [s for s in range(nsec) if subset == 'all' or s % 10 == 0]
        per = {str(s): (list(vec) if s == secs[0] else ['0'] * len(vec)) for s in secs}
        rec = {'header': h, 'subset': subset, 'sectors': secs, 'per_sector': per, 'totals': vec, 'inputs_sha256': {}}
        (lv / name).write_text(json.dumps(rec))
    allN6 = rd('full_H_L6_N6_0_10000.json'); hardN6 = rd('full_H_hard_L6_N6_0_10000.json')
    with mp.workdps(50):
        lightN6 = [mp.nstr(mp.mpf(a) - mp.mpf(b), 35) for a, b in zip(allN6, hardN6)]
    fake_level('L6_H_light_N6.dbl.json', 6, 'H', 'light', 'dbl', 6, lightN6)
    fake_level('L6_H_hard_N6.ld.json', 6, 'H', 'hard', 'ld', 6, hardN6)
    fake_level('L5_H_all_N16.ld.json', 5, 'H', 'all', 'ld', 16, rd('full_H_L5_N16_0_10000.json'))
    fake_level('L5_J_all_N16.ld.json', 5, 'J', 'all', 'ld', 16, rd('full_J_L5_N16_0_10000.json'))
    # auxiliary files in the same directory must be ignored by the production loader (R01)
    fake_level('L6_H_light_N6.dbl.pert1.mod10.json', 6, 'H', 'light', 'dbl', 6, ['0'] * 12, perturb=1, mod=10)
    fake_level('L6_H_all_N6.dbl.json', 6, 'H', 'all', 'dbl', 6, ['0'] * 12)
    manf = td / 'weights_manifest.json'
    manf.write_text(json.dumps({k: {'bin_sha256': 'w', 'dd_sha256': 'w'} for k in ('L6_N6', 'L6_N8', 'L6_N10', 'L5_N16')}))
    out = td / 'assembled.json'
    r = subprocess.run([sys.executable, str(ROOT / 'tools/assemble.py'), str(lv), str(manf), str(out)], capture_output=True, text=True)
    check('assemble_runs', r.returncode == 0, r.stderr[-300:])
    if r.returncode == 0:
        A = json.loads(out.read_text())
        base = [mp.mpf('14334.549123637884'), mp.mpf('14332.554493138334')]
        got = [mp.mpf(A['levels']['6']['C6']['retained_poles_J16ref'][c]) for c in ('maxgap', 'span')]
        check('assemble_light_plus_hard_reproduces_reference_C6_baseline_N6', all(abs(x - y) < mp.mpf('1e-9') for x, y in zip(got, base)), f'{got}')
        ctl = json.loads((REF / 'five_loop_input_control.json').read_text())
        for c in ('maxgap', 'span'):
            dR6 = mp.mpf(A['configs']['L5_M16'][c]['R6']) - mp.mpf(A['configs']['retained_poles_J16ref'][c]['R6'])
            check(f'assemble_five_loop_override_{c}', abs(dR6 - mp.mpf(ctl[c]['change_in_C6_lower'])) < mp.mpf('1e-25'), mp.nstr(dR6, 12))
        pe = A['levels']['6']['pole_errors']['retained_poles_J16ref']['maxgap']
        old = json.loads((REF / 'H6_predicted_higher_poles.json').read_text())
        check('assemble_pole_prediction_matches_reference', abs(mp.mpf(pe['-2']) - (mp.mpf(allN6[4]) - mp.mpf(old['maxgap']['-2']))) < mp.mpf('1e-6'), pe['-2'])
    def run_asm(d):
        return subprocess.run([sys.executable, str(ROOT / 'tools/assemble.py'), str(d), str(manf), str(td / 'x.json')], capture_output=True, text=True)
    lv3 = td / 'levels3'; lv3.mkdir()
    def copy_levels():
        for f in lv3.iterdir():
            f.unlink()
        for f in lv.iterdir():
            (lv3 / f.name).write_text(f.read_text())
    copy_levels()
    rec = json.loads((lv / 'L6_H_hard_N6.ld.json').read_text()); rec['header']['N'] = 8
    (lv3 / 'L6_H_hard_N10.ld.json').write_text(json.dumps(rec))
    r = run_asm(lv3)
    check('assemble_refuses_mislabelled_degree', r.returncode != 0 and ('does not match the file name' in r.stderr or 'file name does not match' in r.stderr), r.stderr[-160:])
    copy_levels()
    rec = json.loads((lv / 'L6_H_hard_N6.ld.json').read_text()); rec['header']['N'] = 10; rec['header']['exe_sha256'] = 'other'
    (lv3 / 'L6_H_hard_N10.ld.json').write_text(json.dumps(rec))
    r = run_asm(lv3)
    check('assemble_refuses_mixed_executables', r.returncode != 0 and 'different executables' in r.stderr, r.stderr[-160:])
    copy_levels()
    rec = json.loads((lv / 'L6_H_hard_N6.ld.json').read_text()); rec['header']['source_sha256'] = 'other'
    (lv3 / 'L6_H_hard_N6.ld.json').write_text(json.dumps(rec))
    r = run_asm(lv3)
    check('assemble_refuses_mixed_sources', r.returncode != 0 and 'different source' in r.stderr, r.stderr[-160:])
    copy_levels()
    rec = json.loads((lv / 'L6_H_hard_N6.ld.json').read_text()); rec['header']['weights_sha256'] = 'not-in-manifest'
    (lv3 / 'L6_H_hard_N6.ld.json').write_text(json.dumps(rec))
    r = run_asm(lv3)
    check('assemble_refuses_weights_not_in_manifest', r.returncode != 0 and 'manifest' in r.stderr, r.stderr[-160:])
    copy_levels(); (lv3 / 'L5_J_all_N16.ld.json').unlink()
    r = run_asm(lv3)
    check('assemble_refuses_unpaired_L5', r.returncode != 0 and 'H and J degrees differ' in r.stderr, r.stderr[-160:])
    copy_levels(); (lv3 / 'L6_H_hard_N6.ld.json').unlink()
    r = run_asm(lv3)
    check('assemble_reports_incomplete_degree', r.returncode == 0 and json.loads((td / 'x.json').read_text())['incomplete_degrees'] == [6], r.stderr[-160:])

    # ---- analyze arithmetic on a synthetic geometric sequence (complete mandatory inputs)
    Cinf = mp.mpf('14331.6600')
    def err(c, N):
        return (mp.mpf('0.01') if c == 'maxgap' else -mp.mpf('0.02')) * mp.mpf('0.1') ** ((N - 12) // 2)
    names = [f'L5_M{M}' for M in range(12, 41, 4)] + ['L5pert_M40', 'retained_poles_J16ref']
    off = {n: mp.mpf(0) for n in names}; off['L5_M36'] = mp.mpf('1e-8'); off['L5pert_M40'] = mp.mpf('3e-9')
    levels = {str(N): {'H6_vector': ['0'] * 12, 'C6': {n: {c: mp.nstr(Cinf + err(c, N) + off[n], 30) for c in ('maxgap', 'span')} for n in names},
                       'pole_errors': {n: {} for n in names}} for N in range(6, 19, 2)}
    ident = {f'L6_H_{s}_N{N}.{k}.json': f'sha{N}{s}' for N in range(6, 19, 2) for s, k in (('light', 'dbl'), ('hard', 'ld'))}
    As = {'configs': {n: {} for n in names}, 'levels': levels, 'level_identities': ident, 'weights_manifest_sha256': 'm'}
    rho = {'cal': '2', 'calibration_complete': True, 'level_identities': dict(ident), 'weights_manifest_sha256': 'm', 'levels': {str(N): {'rho_light': '1e-10', 'rho_hard': '1e-8', 'rho': mp.nstr(2 * (mp.mpf('1e-10') + mp.mpf('1e-8')) + mp.mpf('1e-12'), 20)} for N in range(6, 19, 2)}}
    (td / 'A2.json').write_text(json.dumps(As)); (td / 'R2.json').write_text(json.dumps(rho))
    r = subprocess.run([sys.executable, str(ROOT / 'tools/analyze.py'), str(td / 'A2.json'), str(td / 'R2.json'), str(td / 'O2.json')], capture_output=True, text=True)
    check('analyze_runs', r.returncode == 0, r.stderr[-300:])
    if r.returncode == 0:
        O = json.loads((td / 'O2.json').read_text())['headline']
        # N*=18: deltas maxgap -9e-5, span +1.8e-4 (ratio 0.1 -> f=1): Uconv=3.6e-4; Ucut=3e-5;
        # rho(18) = 1e-8 x calibration 2 (N=14) = 2e-8 -> Uround=8e-8; U5=2e-8; U5_round=1.2e-8; Ulow=2*1.538e-9.
        import analyze as AN0
        rho18 = 2 * (mp.mpf('1e-10') + mp.mpf('1e-8')) + mp.mpf('1e-12')
        tot = mp.mpf('3.6e-4') + mp.mpf('3e-5') + 4 * rho18 + mp.mpf('2e-8') + mp.mpf('2.4e-8') + 2 * mp.mpf('1.538453936462320942279946547110461050056e-9')
        check('analyze_f_is_1', O['f'] == 1)
        check('analyze_allowance', O['allowance_U'] == str(AN0.ceil_2sf(tot)) == '0.00040', f"{O['allowance_U']} vs {AN0.ceil_2sf(tot)}")
        check('analyze_components', abs(mp.mpf(O['components']['U5_round']) - mp.mpf('2.4e-8')) < mp.mpf('1e-14') and abs(mp.mpf(O['components']['U_round']) - 4 * rho18) < mp.mpf('1e-14'), str(O['components']))
        check('analyze_headline_mean', abs(mp.mpf(O['C6_unrounded']) - (Cinf - mp.mpf('5e-6'))) < mp.mpf('1e-15'), O['C6_unrounded'])
        check('analyze_headline_rounded_to_U', O['C6'] == '14331.66000', O['C6'])
    del rho['levels']['12']['rho']; (td / 'R3.json').write_text(json.dumps(rho))
    r = subprocess.run([sys.executable, str(ROOT / 'tools/analyze.py'), str(td / 'A2.json'), str(td / 'R3.json'), str(td / 'O3.json')], capture_output=True, text=True)
    check('analyze_refuses_missing_rounding', r.returncode != 0 and 'rounding replicates missing at N=12' in r.stderr, r.stderr[-200:])
    r = subprocess.run([sys.executable, str(ROOT / 'tools/analyze.py'), str(td / 'A2.json'), str(td / 'R3.json'), str(td / 'O3.json'), '--provisional'], capture_output=True, text=True)
    check('analyze_provisional_without_allowance', r.returncode == 0 and json.loads((td / 'O3.json').read_text())['headline'] is None, r.stderr[-200:])
    r = subprocess.run([sys.executable, str(ROOT / 'tools/analyze.py'), str(td / 'A2.json'), str(td / 'R2.json'), str(td / 'O6.json'), '--provisional'], capture_output=True, text=True)
    O6 = json.loads((td / 'O6.json').read_text()) if r.returncode == 0 else {}
    check('analyze_provisional_never_headline_even_if_complete', r.returncode == 0 and O6['headline'] is None and not any('stop_a_converged_to_floor' in x for x in O6['levels']), r.stderr[-200:])
    few = {'configs': As['configs'], 'levels': {k: v for k, v in levels.items() if k in ('6', '8')}, 'level_identities': ident, 'weights_manifest_sha256': 'm'}
    (td / 'A7.json').write_text(json.dumps(few))
    r = subprocess.run([sys.executable, str(ROOT / 'tools/analyze.py'), str(td / 'A7.json'), str(td / 'R2.json'), str(td / 'O7.json'), '--provisional'], capture_output=True, text=True)
    check('analyze_provisional_with_two_levels', r.returncode == 0 and len(json.loads((td / 'O7.json').read_text())['levels']) == 2, r.stderr[-200:])
    rho4 = json.loads(json.dumps(rho)); rho4['level_identities']['L6_H_hard_N12.ld.json'] = 'other'; (td / 'R5.json').write_text(json.dumps(rho4))
    r = subprocess.run([sys.executable, str(ROOT / 'tools/analyze.py'), str(td / 'A2.json'), str(td / 'R5.json'), str(td / 'O5.json')], capture_output=True, text=True)
    check('analyze_refuses_rounding_from_other_records', r.returncode != 0 and 'did not use the same record' in r.stderr, r.stderr[-200:])
    # stopping decision (REV-005): unresolved without resources; continue within budgets; stop beyond them
    def decide(res):
        args = [sys.executable, str(ROOT / 'tools/analyze.py'), str(td / 'A2.json'), str(td / 'R2.json'), str(td / 'Od.json'), '--decision-dir', str(td / 'dec')]
        if res is not None:
            (td / 'res.json').write_text(json.dumps(res)); args += ['--resources', str(td / 'res.json')]
        rr = subprocess.run(args, capture_output=True, text=True)
        return json.loads((td / 'dec' / 'decision_N18.json').read_text()) if rr.returncode == 0 else {'error': rr.stderr[-200:]}
    cov = {'coverage_complete': True, 'coverage': {'light': 'COMPLETED x3', 'hard': 'COMPLETED x3'}}
    d0 = decide(None); d1 = decide({'production_node_hours': 120, 'N_star': 18, 'N_star_node_hours': 20, 'projected_next_hours_on_12_nodes': 3, **cov})
    d2 = decide({'production_node_hours': 450, 'N_star': 18, 'N_star_node_hours': 20, 'projected_next_hours_on_12_nodes': 3, **cov})
    d3 = decide({'production_node_hours': 'nan', 'N_star': 18, 'N_star_node_hours': 20, 'projected_next_hours_on_12_nodes': 3, **cov})
    d4 = decide({'production_node_hours': 0, 'N_star': 18, 'N_star_node_hours': 0, 'projected_next_hours_on_12_nodes': 0, 'coverage_complete': False})
    check('analyze_decision_nan_resources_unresolved', d3.get('decision') == 'unresolved', str(d3)[:160])
    check('analyze_decision_missing_coverage_unresolved', d4.get('decision') == 'unresolved', str(d4)[:160])
    check('analyze_decision_unresolved_without_resources', d0.get('decision') == 'unresolved', str(d0)[:160])
    check('analyze_decision_continue_within_budget', d1.get('decision') == 'continue' and d1.get('next_degree') == 20 and 'L6_H_light_N18.dbl.json' in d1.get('levels_at_N_star', {}), str(d1)[:160])
    check('analyze_decision_stop_beyond_budget', d2.get('decision') == 'stop' and any('(c)' in r for r in d2['reasons']), str(d2)[:160])
    O = json.loads((td / 'Od.json').read_text())
    check('analyze_final_keeps_full_provenance', O['provenance']['assembly_level_identities'] == ident and len(O['provenance']['assembled_sha256']) == 64, str(O.get('provenance'))[:120])
    levels2 = {k: v for k, v in levels.items() if k != '10'}
    (td / 'A4.json').write_text(json.dumps({'configs': As['configs'], 'levels': levels2}))
    r = subprocess.run([sys.executable, str(ROOT / 'tools/analyze.py'), str(td / 'A4.json'), str(td / 'R2.json'), str(td / 'O4.json')], capture_output=True, text=True)
    check('analyze_refuses_gap_in_degrees', r.returncode != 0 and 'L6 degrees' in r.stderr, r.stderr[-200:])
    # ---- rounding: subset statistic and calibration on synthetic per-sector data
    lr = td / 'lr'; lr.mkdir()
    def lvl_rec(name, stratum, kind, N, per, pert=0, mod=1, subset='all'):
        h = header(L=6, N=N, stratum=stratum, kind={'dbl': 'double8', 'ld': 'reference-longdouble'}[kind], perturb=pert, mod=mod, exe_sha256='e_' + kind)
        tot = [mp.nstr(mp.fsum(mp.mpf(v[j]) for v in per.values()), 30) for j in range(12)]
        (lr / name).write_text(json.dumps({'header': h, 'subset': subset, 'sectors': sorted(per), 'per_sector': {str(s): v for s, v in per.items()}, 'totals': tot}))
    base = {s: ['1'] * 12 for s in range(360)}
    def shifted(sel, dH):
        return {s: (['1'] * 5 + [mp.nstr(1 + dH, 30)] + ['1'] * 5 + [mp.nstr(1 + dH, 30)]) for s in sel}
    S = [s for s in range(360) if s % 10 == 0]
    for N in (6, 8):
        lvl_rec(f'L6_H_light_N{N}.dbl.json', 'light', 'dbl', N, base)
        lvl_rec(f'L6_H_light_N{N}.dbl.pert1.mod10.json', 'light', 'dbl', N, shifted(S, mp.mpf('729e-12') / 2), 1, 10, 'mod10')   # e_s = -1e-12 each
        lvl_rec(f'L6_H_hard_N{N}.ld.json', 'hard', 'ld', N, base)
        lvl_rec(f'L6_H_hard_N{N}.ld.pert1.mod10.json', 'hard', 'ld', N, shifted(S, mp.mpf('729e-10') / 2), 1, 10, 'mod10')    # e_s = -1e-10 each
    for N, (true, proxy) in {6: ('1e-9', '2e-9'), 8: ('3e-9', '2e-9'), 10: ('1e-9', '1e-9')}.items():
        lvl_rec(f'L6_H_hard_N{N}.ld.json', 'hard', 'ld', N, base) if N == 10 else None
        lvl_rec(f'L6_H_hard_N{N}.dbl.json', 'hard', 'dbl', N, shifted(range(360), -mp.mpf(true) * 729 / 2 / 360))
        lvl_rec(f'L6_H_hard_N{N}.dbl.pert1.json', 'hard', 'dbl', N, shifted(range(360), (-mp.mpf(true) - mp.mpf(proxy)) * 729 / 2 / 360), 1)
    r = subprocess.run([sys.executable, str(ROOT / 'tools/rounding.py'), str(lr), str(manf), str(td / 'rho.json')], capture_output=True, text=True)
    check('rounding_runs', r.returncode == 0, r.stderr[-300:])
    if r.returncode == 0:
        R = json.loads((td / 'rho.json').read_text())
        # sigma_S: all 36 e_s equal -> max(10*36*e, sqrt(10*36)*e) = 360 e ; light 3.6e-10, hard 3.6e-8 ; cal = max(1, 0.5, 1.5, 1) = 1.5
        exp = mp.mpf('1.5') * (mp.mpf('3.6e-10') + mp.mpf('3.6e-8')) + mp.mpf('1e-12')
        check('rounding_calibration', abs(mp.mpf(R['cal']) - mp.mpf('1.5')) < mp.mpf('1e-4') and R['calibration_complete'], str(R['calibration']))
        check('rounding_rho', abs(mp.mpf(R['levels']['8']['rho']) - exp) < mp.mpf('1e-14'), f"{R['levels']['8']} vs {mp.nstr(exp, 8)}")
        check('rounding_records_identities', 'L6_H_light_N8.dbl.json' in R['level_identities'] and 'L6_H_hard_N8.ld.pert1.mod10.json' in R['level_identities'])
    # wrong seed and zero-proxy policies
    import shutil
    lr2 = td / 'lr2'; shutil.copytree(lr, lr2)
    rec = json.loads((lr2 / 'L6_H_hard_N8.ld.pert1.mod10.json').read_text()); rec['header']['perturb'] = 2
    (lr2 / 'L6_H_hard_N8.ld.pert1.mod10.json').write_text(json.dumps(rec))
    r = subprocess.run([sys.executable, str(ROOT / 'tools/rounding.py'), str(lr2), str(manf), str(td / 'rho2.json')], capture_output=True, text=True)
    check('rounding_refuses_wrong_seed', r.returncode != 0 and ('expected perturb=1' in r.stderr or 'pert2' in r.stderr), r.stderr[-160:])
    shutil.rmtree(lr2); shutil.copytree(lr, lr2)
    (lr2 / 'L6_H_hard_N10.dbl.pert1.json').write_text((lr2 / 'L6_H_hard_N10.dbl.json').read_text().replace('"perturb": 0', '"perturb": 1'))
    r = subprocess.run([sys.executable, str(ROOT / 'tools/rounding.py'), str(lr2), str(manf), str(td / 'rho3.json')], capture_output=True, text=True)
    R3 = json.loads((td / 'rho3.json').read_text()) if r.returncode == 0 else {}
    check('rounding_zero_proxy_positive_error_invalidates_calibration', r.returncode == 0 and R3['calibration_complete'] is False and 'rho' not in R3['levels']['8'], str(R3.get('calibration'))[:200])

    # ---- levelio: canonical name, coverage and totals consistency (R6-01)
    import levelio as LIO
    good = lr / 'L6_H_light_N6.dbl.json'
    try:
        LIO.validate_level(good); ok = True
    except LIO.LevelError:
        ok = False
    check('levelio_accepts_valid', ok)
    bad_dir = td / 'badlv'; bad_dir.mkdir()
    def expect_bad(name, rec, needle):
        (bad_dir / name).write_text(json.dumps(rec))
        try:
            LIO.validate_level(bad_dir / name); check(f'levelio_rejects_{needle[:20]}', False)
        except LIO.LevelError as e:
            check(f'levelio_rejects_{needle.replace(" ", "_")[:24]}', needle in str(e), str(e)[:100])
    rec = json.loads(good.read_text())
    expect_bad('L6_H_light_N18.dbl.json', rec, 'file name does not match')
    r2 = json.loads(json.dumps(rec)); r2['sectors'] = r2['sectors'][:-1]; del r2['per_sector']['359']
    expect_bad('L6_H_light_N6.dbl.json', r2, 'sector coverage')
    r3 = json.loads(json.dumps(rec)); r3['totals'][5] = '999'
    expect_bad('L6_H_light_N6.dbl.json', r3, 'inconsistent')
    for j in (5, 11):
        for bad in ('nan', 'inf', 'NaN'):
            rn = json.loads(json.dumps(rec)); rn['totals'][j] = bad
            expect_bad('L6_H_light_N6.dbl.json', rn, 'non-finite totals')
    # the same NaN total is refused by the retry check, the assembly and the rounding analysis
    import shutil
    lrn = td / 'lr_nan'; shutil.copytree(lr, lrn)
    rn = json.loads((lrn / 'L6_H_light_N8.dbl.json').read_text()); rn['totals'][11] = 'nan'
    (lrn / 'L6_H_light_N8.dbl.json').write_text(json.dumps(rn))
    rc = subprocess.run([sys.executable, str(ROOT / 'tools/levelcheck.py'), str(lrn / 'L6_H_light_N8.dbl.json'), json.dumps({'source': 's', 'c6sum': 'e_dbl', 'c6sum_ld': 'e_ld', 'graphs6': 'g', 'graphs7': 'g'}), str(manf)], capture_output=True, text=True)
    check('levelcheck_refuses_nan_total', rc.returncode == 1 and 'non-finite' in rc.stderr, rc.stderr[-120:])
    rr = subprocess.run([sys.executable, str(ROOT / 'tools/rounding.py'), str(lrn), str(manf), str(td / 'rho_nan.json')], capture_output=True, text=True)
    check('rounding_refuses_nan_total', rr.returncode != 0 and 'non-finite' in rr.stderr, rr.stderr[-120:])
    lvn = td / 'lv_nan'; shutil.copytree(lv, lvn)
    an = json.loads((lvn / 'L6_H_hard_N6.ld.json').read_text()); an['totals'][5] = 'nan'
    (lvn / 'L6_H_hard_N6.ld.json').write_text(json.dumps(an))
    ra = subprocess.run([sys.executable, str(ROOT / 'tools/assemble.py'), str(lvn), str(manf), str(td / 'a_nan.json')], capture_output=True, text=True)
    check('assemble_refuses_nan_total', ra.returncode != 0 and 'non-finite' in ra.stderr, ra.stderr[-120:])
    rp = json.loads((lr / 'L6_H_hard_N8.ld.pert1.mod10.json').read_text()); rp['sectors'] = rp['sectors'][:30]
    rp['per_sector'] = {k: v for k, v in rp['per_sector'].items() if int(k) in rp['sectors']}
    expect_bad('L6_H_hard_N8.ld.pert1.mod10.json', rp, 'sector coverage')

    # ---- merge publishes atomically and write-once into a level directory (REV-003)
    md = td / 'mlv'; md.mkdir(); src = td / 'msrc.jsonl'
    write(src, header(stratum='light'), range(360))
    r1 = subprocess.run([sys.executable, str(ROOT / 'tools/merge.py'), '--leveldir', str(md), str(src)], capture_output=True, text=True)
    r2 = subprocess.run([sys.executable, str(ROOT / 'tools/merge.py'), '--leveldir', str(md), str(src)], capture_output=True, text=True)
    names = sorted(p.name for p in md.iterdir())
    check('merge_atomic_write_once', r1.returncode == 0 and r2.returncode == 1 and names == ['L6_H_light_N8.dbl.json'], f'{names} {r1.stderr[-80:]} {r2.stderr[-80:]}')

    # ---- validate.py: failing gates exit nonzero; collector requires every gate
    va, vb = td / 'va.json', td / 'vb.json'
    A1 = td / 'a1.json'; A1.write_text(json.dumps({'totals': ['1', '2', '3']})); B1 = td / 'b1.json'; B1.write_text(json.dumps({'values': ['1', '2', '3.0000001']}))
    V = [sys.executable, str(ROOT / 'tools/validate.py')]
    r1 = subprocess.run(V + [str(va), 'vector', 'G_ok', str(A1), str(A1), '--rel', '0'], capture_output=True, text=True)
    r2 = subprocess.run(V + [str(vb), 'vector', 'G_bad', str(A1), str(B1), '--rel', '1e-12'], capture_output=True, text=True)
    check('validate_failed_gate_exits_nonzero', r1.returncode == 0 and r2.returncode == 1, r2.stdout[-120:])
    r3 = subprocess.run(V + [str(td / 'sum.json'), 'collect', '-', str(va), '--require', 'G_ok'], capture_output=True, text=True)
    r4 = subprocess.run(V + [str(td / 'sum.json'), 'collect', '-', str(va), '--require', 'G_ok,G_missing'], capture_output=True, text=True)
    r5 = subprocess.run(V + [str(td / 'sum.json'), 'collect', '-', str(va), str(vb), '--require', 'G_ok'], capture_output=True, text=True)
    check('validate_collect', r3.returncode == 0 and r4.returncode == 1 and r5.returncode == 1, r4.stdout[-120:] + r5.stdout[-120:])
    sa, sb = td / 'sa.jsonl', td / 'sb.jsonl'
    write(sa, header(), [0, 1], vals=lambda s: ['1.0000000000000001'] * 12); write(sb, header(), [0, 1], vals=lambda s: ['1'] * 12)
    r6 = subprocess.run(V + [str(td / 'vc.json'), 'close-sectors', 'G_close', '--rel', '1e-14', '--a', str(sa), '--b', str(sb)], capture_output=True, text=True)
    r7 = subprocess.run(V + [str(td / 'vc.json'), 'close-sectors', 'G_far', '--rel', '1e-18', '--a', str(sa), '--b', str(sb)], capture_output=True, text=True)
    check('validate_close_sectors', r6.returncode == 0 and r7.returncode == 1, r7.stdout[-120:])

    sys.path.insert(0, str(ROOT / 'tools'))
    import analyze as AN  # noqa: E402
    check('ceil_2sf_basic', str(AN.ceil_2sf(mp.mpf('3.141e-5'))) == '0.000032' or AN.ceil_2sf(mp.mpf('3.141e-5')) == __import__('decimal').Decimal('3.2e-5'))
    check('ceil_2sf_exact', AN.ceil_2sf(mp.mpf('41')) == 41)

print(f'{len(failures)} failures' if failures else 'all tests passed')
sys.exit(1 if failures else 0)
