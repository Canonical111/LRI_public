#!/usr/bin/env python3
"""Replay of the d = 3 independent-solver check (HT note, \\HTnpDthreeIndep: 2e-11 at N <= 12).

Reads the shipped comparison records results/cmp_L{L}_{mode}_x{x}.json written by run_compare.py (clean-room solver,
fixed-coupling replay at the production couplings with K = 16 and 24 local states, then independent tuning of (r, g)
from a start displaced by 2%), and recomputes:
  INDEP-TUNED   max |Delta_E(indep, tuned) - Delta_E(production)| over all comparisons -> 2e-11 (1 significant digit)
  INDEP-FIXED   max |Delta_E(indep, K=16 or 24 at production couplings) - Delta_E(production)| (<= 3e-12)
  INDEP-RESID   every independent tuning converged: residual <= 1e-12
  INDEP-PKG     the production values each comparison used equal the shipped production records byte for value
                (../../data/HT_3d/campaigns), and equal indep_extract.json
Prints a PASS/FAIL table, writes it to --out, exits 1 on FAIL. Python >= 3.10, standard library only.
"""
import argparse, glob, json, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--results', default=str(PKG / 'results'))
    ap.add_argument('--extract', default=str(PKG / 'indep_extract.json'))
    ap.add_argument('--campaigns', default=str(PKG / '../../data/HT_3d/campaigns'))
    ap.add_argument('--out', default=str(PKG / '.work/replay'))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    files = sorted(glob.glob(str(Path(a.results) / 'cmp_*.json')))
    cmp = [json.load(open(f)) for f in files]
    rows = []
    def add(cid, quoted, value, rule, ok, note=''):
        rows.append((cid, quoted, value, 'PASS' if ok else 'FAIL', rule, note))
    tuned = [(abs(c['tuned']['dD']), c) for c in cmp if 'tuned' in c]
    mx, worst = max(tuned, key=lambda t: t[0])
    add('INDEP-TUNED', '2e-11', f'{mx:.2e} ({len(tuned)} comparisons, L = {sorted({c["L"] for c in cmp})})',
        r'\HTnpDthreeIndep: max |dDelta_E| after independent tuning, to 1 significant digit',
        float(f'{mx:.0e}') == 2e-11, f'worst: L={worst["L"]} {worst["mode"]} x={worst["x"]}')
    fx = [abs(c[k]['dD']) for c in cmp for k in c if k.startswith('fixed_K')]
    add('INDEP-FIXED', '<= 3e-12', f'{min(fx):.1e} .. {max(fx):.1e}', 'fixed (production) couplings, K = 16 and 24 local states: max |dDelta_E| <= 3e-12', max(fx) <= 3e-12)
    res = max(c['tuned']['resid'] for c in cmp if 'tuned' in c)
    add('INDEP-RESID', '<= 1e-12', f'{res:.1e}', 'independent tuning residual (sigma, chi gaps) <= 1e-12 in every comparison', res <= 1e-12)
    ext = json.load(open(a.extract))
    bad = []; checked = 0; root = Path(a.campaigns)
    for c in cmp:
        win = c['mode'] == 'window'
        e = next(e for e in ext if e['camp'] in ('grid18', 'grid18sri') and abs(e['delta'] - c['x']) < 1e-9
                 and e['bath_cut'] == c['L'] and ((e['window'] == 'vacuum') == win))
        if any(c['pkg'][k] != e[k] for k in ('r', 'g', 'Delta_thermal')): bad.append(f'extract {c["L"]} {c["mode"]} {c["x"]}')
        rec = root / e['file'].split('campaigns/', 1)[1]
        if rec.exists():
            r = json.loads(rec.read_text()); checked += 1
            if any(c['pkg'][k] != r[k] for k in ('r', 'g', 'Delta_thermal')): bad.append(f'record {rec.name} {c["x"]}')
        else:
            bad.append(f'missing record {rec}')
    add('INDEP-PKG', 'production values', f'{checked}/{len(cmp)} records compared',
        'production (r, g, Delta_E) used by each comparison == shipped record == indep_extract.json', not bad, '; '.join(bad[:3]))
    w = [max(len(str(r[i])) for r in rows) for i in range(4)]
    txt = '\n'.join('  '.join(str(r[i]).ljust(w[i]) for i in range(4)) + '  ' + r[4] + (f'  [{r[5]}]' if r[5] else '') for r in rows)
    print(txt); (out / 'replay_table.txt').write_text(txt + '\n')
    fails = [r for r in rows if r[3] == 'FAIL']
    print(f'{len(rows) - len(fails)}/{len(rows)} passed ({len(files)} comparison records)')
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
