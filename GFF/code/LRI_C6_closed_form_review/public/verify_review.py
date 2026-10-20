#!/usr/bin/env python3
"""Replay of the independent review of the C6(1) analytic representation (REVIEW.md, 8 October 2026).

  test    every shipped check script compiles and every recorded output the replay reads is present.
  replay  re-derives the review's quoted agreements from the recorded outputs in checks/ (or, with
          --records, from a fresh rerun made by public/rerun_checks.py) and compares them with the
          package records of ../C6_research_note (outputs/reassembly.json) and with the numbers the
          condensed note quotes (../../results/C6_1/analytic/quoted_numbers.json, block "review").
          It also reruns checks/c6_repair.py (30 digits, instantaneous).
Writes a PASS/FAIL table to the work directory; exit status 1 on any FAIL.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True   # never write __pycache__ into the shipped tree

RECORDED = ['reduced_input/assembly.json', 'reduced_input/ordinary.json', 'reduced_input/wheel.log',
            'reduced_input/polylog.log', 'reduced_input/m7.json', 'reduced_input/primitive_dps95.json',
            'final_values/assemble.out', 'final_values/polylog_out.json', 'final_values/gvals_mb_50.json',
            'final_values/reduced1d_40.json', 'final_values/primitive1d_40.json', 'final_values/h2d_nested.json',
            'final_values/h2d_trap_HW.json', 'final_values/h2d_trap_H7.json', 'final_values/h2d_trap_HP.json']


class Table:
    def __init__(self, title):
        self.title, self.rows = title, []

    def ok(self, cid, cond, what, detail='', tol=''):
        st = 'PASS' if cond else 'FAIL'
        self.rows.append(dict(id=cid, status=st, check=what, detail=str(detail), tolerance=tol))
        print(f'{st:4s}  {cid:26s} {what}' + (f'  [{detail}]' if detail else ''), flush=True)

    def write(self, work, name):
        work.mkdir(parents=True, exist_ok=True)
        n = {s: sum(r['status'] == s for r in self.rows) for s in ('PASS', 'FAIL')}
        lines = [f'# {self.title}', f'# {time.strftime("%Y-%m-%d %H:%M:%S")}  python {sys.version.split()[0]}',
                 f'# PASS {n["PASS"]}  FAIL {n["FAIL"]}', '']
        lines += [f'{r["status"]:6s} {r["id"]:26s} {r["check"]:66s} {r["detail"]} | {r["tolerance"]}' for r in self.rows]
        (work / f'{name}.txt').write_text('\n'.join(lines) + '\n')
        (work / f'{name}.json').write_text(json.dumps(dict(title=self.title, counts=n, rows=self.rows), indent=1) + '\n')
        print(f'\n{self.title}: PASS {n["PASS"]}  FAIL {n["FAIL"]}   (table: {work / (name + ".txt")})')
        return 1 if n['FAIL'] else 0


def load(p):
    return json.loads(Path(p).read_text())


def test(t, recs):
    bad = []
    scripts = sorted((PKG / 'checks').rglob('*.py')) + sorted((PKG / 'public').glob('*.py'))
    for p in scripts:
        try:
            compile(p.read_text(), str(p), 'exec')
        except SyntaxError as e:
            bad.append(f'{p.relative_to(PKG)}: {e}')
    t.ok('scripts.compile', not bad, f'{len(scripts)} Python scripts compile', f'{bad[:3]}', 'syntax')
    miss = [r for r in RECORDED if not (recs / r).is_file()]
    t.ok('records.present', not miss, f'{len(RECORDED)} recorded outputs used by the replay are present', f'missing {miss}', 'exact')


def replay(t, recs, reassembly, quoted, work):
    import mpmath as mp
    mp.mp.dps = 100
    R = load(reassembly)
    Q = load(quoted)['review']
    fv = {k: mp.mpf(v) for k, v in R['fixed_values'].items()}
    pi = mp.pi

    def digits(a, b):
        d = abs(mp.mpf(a) - b)
        return 99.0 if d == 0 else float(-mp.log10(d / abs(b)))

    # 1. reduced input (eq. 2.7) recomputed from the definitions, no package code
    a = load(recs / 'reduced_input/assembly.json')
    d = abs(mp.mpf(a['C6']) - mp.mpf(R['C6_reassembled_from_series']))
    t.ok('reduced_input.C6', d < mp.mpf(Q['reduced_input_abs_diff_below']),
         'C6(1) from the independently evaluated reduced input agrees with the package (about 65 digits)',
         f'|diff| = {mp.nstr(d, 3)}', f'< {Q["reduced_input_abs_diff_below"]} abs')
    E, Ereal = mp.mpf(a['E']), mp.mpf(a['Ereal'])
    pairs = dict(known_real=Ereal, log_sine_and_Clausen=mp.mpf(a['Bpol']) - (Ereal - E), lower=mp.mpf(a['Blow']),
                 sixth=mp.mpf(a['B6']), eighth=mp.mpf(a['B8']), wheel=mp.mpf(a['wheel']), seventh=mp.mpf(a['seventh']),
                 primitive=mp.mpf(a['primitive']))
    dg = {k: digits(v, mp.mpf(R['blocks_r6'][k])) for k, v in pairs.items()}
    t.ok('reduced_input.blocks_json', min(dg.values()) >= Q['blocks_min_digits'],
         'all eight blocks of outputs/reassembly.json reproduced by reduced_input/assembly.json',
         ', '.join(f'{k} {v:.1f}' for k, v in dg.items()),
         f'>= {Q["blocks_min_digits"]} significant digits (assembly.json stores 70 digits, so this caps near 70)')
    logd = []
    for line in (recs / 'reduced_input/assemble.log').read_text().splitlines():
        m = re.match(r'^.*\((known_real|log_sine_and_Clausen|lower|sixth|eighth|wheel|seventh|primitive)\)\s+\S+\s+([\d.]+|exact)\s+diff', line)
        if m:
            logd.append(99.0 if m.group(2) == 'exact' else float(m.group(2)))
    lo, hi = (int(x) for x in Q['blocks_digits_range'].split('-'))
    t.ok('reduced_input.blocks', len(logd) == 8 and min(logd) >= lo and max(logd) < hi + 1,
         f'block agreement printed by assemble.py (full working precision) is {Q["blocks_digits_range"]} digits',
         ', '.join(f'{v:.1f}' for v in logd), f'all 8 in [{lo}, {hi + 1}) significant digits')
    # 2. inherited identities
    o = {k: mp.mpf(v['EM']) for k, v in load(recs / 'reduced_input/ordinary.json').items()}
    Qg = mp.gamma(mp.mpf(1) / 4) ** 4 / pi; s2 = mp.sqrt(2)
    Pb = 6 * Qg ** 3 / pi * (2 * o['Hm'] - 1) - 104 * pi ** 5 * o['H0'] + 2 ** 18 * pi ** 5 / Qg ** 3 * o['Hp']
    B8 = pi ** 6 * (4932 - 5004 * s2) * o['U8'] + 556 * pi ** 2 * ((17 + 12 * s2) * o['Y1'] - (17 - 12 * s2) * o['Y7'])
    res = {'eq:Pbseries': abs(Pb - 24 * pi ** 3 * o['PbS']) / abs(Pb), 'eq:B8series': abs(B8 - 8 * pi ** 4 * o['B8S']) / abs(B8)}
    pat = re.compile(r'^\s*(?P<name>[^=]+?)\s*=\s*(?P<val>[-+]?\d[\d.]*(?:e[-+]?\d+)?)\s*(?:\(scale\s*(?P<sc>[\d.]+)\s*\))?\s*$')
    want = {'W0 - (8D4+5pi D6)': 'eq:wheel (8D4+5piD6)', 'core:': 'eq:wheel-core', 'line2:': 'eq:wheelperiodinputs line 2',
            'line1:': 'eq:wheelperiodinputs line 1', 'vanish:': 'eq:wheelvanish', 'S7 - (pi^2 Vw + 2 D6)': 'eq:wheel-core S7 form'}
    for line in (recs / 'reduced_input/wheel.log').read_text().splitlines():
        m = pat.match(line)
        if m:
            for pre, lab in want.items():
                if m.group('name').startswith(pre):
                    res[lab] = abs(mp.mpf(m.group('val'))) / mp.mpf(m.group('sc') or 1)
    pr = load(recs / 'reduced_input/primitive_dps95.json')
    res['primitive contour I22-4I12+4I02-4I00'] = abs(mp.mpf(pr['relation'])) / abs(mp.mpf(pr['I22']))
    for line in (recs / 'reduced_input/polylog.log').read_text().splitlines():
        if line.startswith('D3 - (-Ls3/2 - 7pi^3/192)'):
            res['D3 = -Ls3/2 - 7pi^3/192'] = abs(mp.mpf(line.split('=')[-1]))
    lim = mp.mpf(Q['identities_below'])
    t.ok('identities', len(res) == 10 and all(v < lim for v in res.values()),
         f'{len(res)} inherited identities hold numerically (better than {Q["identities_below"]})',
         ', '.join(f'{k} {mp.nstr(v, 2)}' for k, v in res.items()), f'< {Q["identities_below"]} relative (10 expected)')
    m7 = load(recs / 'reduced_input/m7.json')
    spread = max(abs(mp.mpf(v) - mp.mpf(m7['avg_4000_150'])) for k, v in m7.items() if k != 'cvz_80')
    t.ok('M7.two_methods', spread < mp.mpf('1e-80'), 'M7 by Euler averaging and by CVZ agree', f'spread {mp.nstr(spread, 2)}', '< 1e-80 abs')
    # 3. the nine final values
    pl = load(recs / 'final_values/polylog_out.json'); gm = load(recs / 'final_values/gvals_mb_50.json')
    r1 = load(recs / 'final_values/reduced1d_40.json'); p1 = load(recs / 'final_values/primitive1d_40.json')
    mine = dict(Ls3_pi_over_2=pl['L3_quad'], Cl212_pi_over_2=pl['C212_cvz'], G4=gm['G4'][0], G6=gm['G6'][0], G8=gm['G8'][0],
                G7=gm['G7'][0], H_W=r1['H_W_1d'], H7_unit=r1['H7_1d'], H_star=p1['H_star_1d'])
    dg = {k: digits(v, fv[k]) for k, v in mine.items()}
    t.ok('nine_values.1d', min(dg.values()) >= Q['one_d_values_min_digits'],
         'the nine values by separate one-dimensional codes agree with the package (40 to 64 digits)',
         ', '.join(f'{k} {"all" if v == 99 else f"{v:.1f}"}' for k, v in dg.items()),
         f'>= {Q["one_d_values_min_digits"]} digits (G7, H7 are stated to 40 digits)')
    rel = None
    for line in (recs / 'final_values/assemble.out').read_text().splitlines():
        if line.startswith('note reference Crefval') and 'rel diff' in line:
            rel = mp.mpf(line.split('rel diff')[-1])
    t.ok('nine_values.reassembly', rel is not None and rel <= mp.mpf('1e-49'),
         'eq:preferred rebuilt from these nine values gives the reference value', f'rel diff {mp.nstr(rel, 2) if rel is not None else "?"}',
         f'<= 1e-49 (quoted {Q["nine_value_reassembly_rel_diff"]})')
    two = {}
    n2 = load(recs / 'final_values/h2d_nested.json')
    two['H_W nested quad'] = digits(n2['HW'], fv['H_W']); two['H7 nested quad'] = digits(n2['H7'], fv['H7_unit'])
    hw = load(recs / 'final_values/h2d_trap_HW.json')['HW'][-1]; two['H_W trapezoid finest'] = digits(hw[4], fv['H_W'])
    h7 = load(recs / 'final_values/h2d_trap_H7.json')['H7'][-1]; two['H7 trapezoid finest'] = digits(h7[4], fv['H7_unit'])
    hp = load(recs / 'final_values/h2d_trap_HP.json')['HP']
    hmin = min(r[1] for r in hp)
    for r in hp:
        if r[1] == hmin:
            two[f'H* trapezoid tau={r[0]} h={r[1]}'] = digits(r[3][max(r[3], key=int)][0], fv['H_star'])
    lo, hi = (int(x) for x in Q['two_fold_digits_range'].split('-'))
    t.ok('two_fold.direct', min(two.values()) >= lo and max(two.values()) < hi + 1,
         f'H_W, H7, H* as genuine two-fold Mellin-Barnes integrals ({Q["two_fold_digits_range"]} digits)',
         ', '.join(f'{k} {v:.1f}' for k, v in two.items()), f'all in [{lo}, {hi + 1}) digits (double precision)')
    # 4. repair size and graph-sum comparison (checks/c6_repair.py, rerun)
    cp = PKG / 'checks/c6_repair.py'
    out = subprocess.run([sys.executable, str(cp)], capture_output=True, text=True, cwd=work).stdout
    (work / 'c6_repair.log').write_text(out)
    num = re.compile(r'[-+]?\d[\d.]*(?:e[-+]?\d+)?')
    vals = {}
    for line in out.splitlines():
        if line.startswith('Delta r6 repair'):
            vals['dC6'] = mp.mpf(line.split('Delta C6 =')[1])
        elif line.startswith('closed form - graph sum'):
            x = num.findall(line.split('=', 1)[1]); vals['diff'] = mp.mpf(x[0]); vals['units'] = mp.mpf(x[-1])
        elif line.startswith('closed form without repair'):
            vals['without'] = mp.mpf(line.split('=')[1])
    good = len(vals) == 4 and mp.nstr(vals['dC6'], 15) == Q['repair_delta_C6_12'] and f'{float(vals["diff"]):.2e}' == Q['graph_sum_diff_3sig'] \
        and f'{float(vals["units"]):.3f}' == Q['graph_sum_diff_allowance_units'] and f'{float(vals["without"]):.3f}' == Q['C6_without_repair_3']
    t.ok('repair_and_graph_sum', good, 'checks/c6_repair.py: repair +659.278983198744, difference -1.03e-8 = -0.021 U, 13672.408 without repair',
         ', '.join(f'{k} {mp.nstr(v, 15)}' for k, v in vals.items()), 'exact digits as quoted in REVIEW.md')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['test', 'replay'])
    ap.add_argument('--records', default=str(PKG / 'checks'), help='folder with reduced_input/ and final_values/ outputs')
    ap.add_argument('--reassembly', default=str(PKG / '../C6_research_note/outputs/reassembly.json'))
    ap.add_argument('--quoted', default=str(PKG / '../../results/C6_1/analytic/quoted_numbers.json'))
    ap.add_argument('--work', default=str(PKG / '.work'))
    ap.add_argument('--name', default='')
    a = ap.parse_args()
    work = Path(a.work).resolve(); work.mkdir(parents=True, exist_ok=True)
    recs = Path(a.records).resolve()
    t = Table(f'LRI_C6_closed_form_review {a.mode} ({recs})')
    if a.mode == 'test':
        test(t, recs)
    else:
        replay(t, recs, Path(a.reassembly).resolve(), Path(a.quoted).resolve(), work)
    return t.write(work, a.name or f'{a.mode}_report')


if __name__ == '__main__':
    raise SystemExit(main())
