"""Markdown summary table of C_2..C_8 from results/*.json (values shortened to `nd` significant digits)."""
import json, glob, os, sys
import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
nd = int(sys.argv[1]) if len(sys.argv) > 1 else 30
mp.mp.dps = 80
rows = []
for f in sorted(glob.glob(os.path.join(HERE, 'results', '*.json'))):
    d = json.load(open(f))
    rows.append(d)
order = {'raw': 0, 'consistent': 1, 'literal': 2}
rows.sort(key=lambda d: (order[d['scheme']], d['L']))
print(f"| scheme | L | n | C_n ({nd} significant digits) | error estimate | rational candidate |")
print("|---|---|---|---|---|---|")
for d in rows:
    for e in d['C'][2:]:
        v = mp.nstr(mp.mpf(e['value']), nd)
        print(f"| {d['scheme']} | {d['L']} | {e['n']} | {v} | {e['err']} | {e.get('rational_candidate', '')} |")
print()
print("| scheme | L | abs(C_0 - 1) | abs(C_1 + 1/6) | max |dC_n| cap21/cap23 | C_8(cap17) - C_8 | C_8(cap18) - C_8 | min ref. weight |")
print("|---|---|---|---|---|---|---|---|")
for d in rows:
    c0 = mp.mpf(d['check_C0_minus_1'])
    c1 = mp.mpf(d['check_C1_plus_1/6'])
    capdev = max(mp.mpf(x) for v in ('cap21', 'cap23') if v in d['variant_deviations_C']
                 for x in d['variant_deviations_C'][v].values()) if 'cap21' in d['variant_deviations_C'] else None
    cc = d['cap_controls_C_minus_base']
    print(f"| {d['scheme']} | {d['L']} | {mp.nstr(c0, 2)} | {mp.nstr(c1, 2)} | {mp.nstr(capdev, 2) if capdev is not None else '-'} | "
          f"{cc.get('cap17', {}).get('8', '-')} | {cc.get('cap18', {}).get('8', '-')} | "
          f"{d['newton_and_tracking']['min_reference_weight']:.5f} |")
