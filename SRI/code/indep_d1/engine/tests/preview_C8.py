#!/usr/bin/env python3
"""Preview of the C8 inputs from the PILOT data (not a production result; archive-free).

Input: the tier-1 production deliverable (runs/prod_6digit/framework_input_final.json, the 116 order-D4 scalars)
plus the 85 beyond-D4 scalars taken from the C8 pilot runs (runs/c8val, runs/c8conv) and the assembly-phase check
runs (runs/poles1, runs/kplus1): all-sector entries only, the one with the smallest replicate error per scalar, merged as independent runs (framework merge_inputs,
independent=True).  The framework assembles at order C8 once per replicate (strict=False: inputs whose raw scalars
the pilot has not computed with all sectors are reported MISSING, never zeroed).
Output: results/preview_C8.json (value, sigma_linear, rep_se of the ten new inputs, B_old8, C8_partial) and the
independent comparison of W with the spec's three-kink value (spec/out/C8/validation_targets_C8.json, archive-free).
usage: python3 tests/preview_C8.py [--run runs/c8val --run runs/c8conv --run runs/poles1 --run runs/kplus1]
"""
import argparse, json, os, re, sys
import mpmath as mp
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJ = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(PROJ, 'framework'))
import lri_framework as L     # noqa: E402


def pilot_scalars(runs, names):
    best = {}
    for rd in runs:
        man = json.load(open(os.path.join(rd, 'manifest.json')))
        strided = {m['moment'] for m in man if any('sectorstride' in str(e) for e in (m.get('extra') or []))}
        R = json.load(open(os.path.join(rd, 'results.json')))
        tag = os.path.basename(os.path.normpath(rd))
        for g, co in R['results'].items():
            if g in strided:
                continue
            for key, (v, e) in co.items():
                k, j = key.split(',')
                nm = L.canonical_raw_name(f"{re.sub(r'_N[0-9]+$', '', g).replace('_base', '')}[eps^{k} l^{j}]")
                if nm not in names:
                    continue
                ex = R['errors'][g][key]
                if ex.get('zero'):
                    ent = {'value': '0', 'sigma': '0', 'exact': True}
                    err = 0.0
                else:
                    ent = {'reps': [repr(x) for x in R['replicates'][g][key]], 'sys': repr(ex['floor']),
                           'block': f"{tag}:{ex['block']}"}
                    err = e
                if nm not in best or err < best[nm][0]:
                    best[nm] = (err, ent, f'{tag}:{g}')
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='append', default=None)
    ap.add_argument('--out', default=os.path.join(ROOT, 'results', 'preview_C8.json'))
    a = ap.parse_args()
    runs = [os.path.abspath(r) for r in (a.run or [os.path.join(ROOT, 'runs', x) for x in
                                                  ('c8val', 'c8conv', 'poles1', 'kplus1')])]
    new = json.load(open(os.path.join(ROOT, 'specs', 'framework_C8_new_scalars.json')))['all_beyond_D4']
    names = {L.canonical_raw_name(n) for n in new}
    best = pilot_scalars(runs, names)
    pil = {'format': 'lri-framework-raw/1', 'convention': 'derivative', 'sources': ['c8pilot'],
           'scalars': {nm: ent for nm, (_, ent, _) in best.items()}}
    prod = L.load_inputs(os.path.join(ROOT, 'runs', 'prod_6digit', 'framework_input_final.json'))
    pil = L.load_inputs(pil)
    merged = L.merge_inputs([prod, pil], independent=True)
    fw = L.Framework('C8', dps=40)
    res = fw.from_replicates(merged, strict=False)
    st = res.stats
    outs = ['W', 'S', 'L3', 'M21', 'M12', 'N2', 'Ndelta', 'U', 'Kv', 'J9', 'B_old8', 'B_done8', 'C8_partial', 'C8']
    rows = {}
    for o in outs:
        s = st.get(o)
        if s is None:
            continue
        if 'missing' in s:
            rows[o] = {'missing': s['missing'][:6]}
            print(f'{o:10s} MISSING ({len(s["missing"])} names, e.g. {s["missing"][:2]})')
            continue
        rows[o] = {k: mp.nstr(v, 20) for k, v in s.items() if k in ('value', 'sigma_linear', 'rep_se', 'sigma_rep_total')}
        print(f"{o:10s} {mp.nstr(s['value'], 18):>26s}  sigma_lin {mp.nstr(s['sigma_linear'], 3):>9s}  "
              f"rep_se {mp.nstr(s['rep_se'], 3):>9s}")
    vt = json.load(open(os.path.join(PROJ, 'spec', 'out', 'C8', 'validation_targets_C8.json')))
    Wind = next(t for t in vt['independent_values'] if t['id'] == 'input.W')
    if 'W' in rows and 'value' in rows['W']:
        d = mp.mpf(rows['W']['value']) - mp.mpf(Wind['value'])
        sig = max(mp.mpf(rows['W']['sigma_linear']), mp.mpf(rows['W']['rep_se']))
        rows['W']['independent_three_kink'] = Wind['value']
        rows['W']['diff'] = mp.nstr(d, 4)
        rows['W']['pull'] = mp.nstr(d / sig, 3) if sig > 0 else None
        print(f"W engine - spec three-kink value: {mp.nstr(d, 4)} (sigma {mp.nstr(sig, 3)})")
    out = {'note': 'PREVIEW from pilot data (tests/preview_C8.py); not a production result; archive-free',
           'runs': runs, 'pilot_sources': {nm: src for nm, (_, _, src) in best.items()},
           'n_pilot_scalars': len(best), 'n_beyond_D4': len(names), 'outputs': rows}
    json.dump(out, open(a.out, 'w'), indent=1)
    print(f'{len(best)} of {len(names)} beyond-D4 scalars from the pilot; wrote {a.out}')


if __name__ == '__main__':
    main()
