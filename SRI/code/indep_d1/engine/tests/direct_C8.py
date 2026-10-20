#!/usr/bin/env python3
"""C8 phase: the engine's series of the C8-era atoms against the direct finite-cutoff table, with the direct
component's GLS tool (../direct/src/compare_engine.py --offset-fit; method, verdicts and resolution in
../direct/README.md: 3-4 kinks resolve [eps^0 l^0], [eps^0 l^1] to 1e-13..3e-4 relative, 5 kinks with K = 0 to
3e-5..6e-4, 6-8 kinks are a gross-error screen).

Engine series: every group of the C8 runs given (default runs/c8val, runs/c8conv, runs/c8kplus1; all-sector entries
only, strided ones are skipped; for one job at several N the smaller error), completed coefficient by coefficient by conv1, the tier-1 production (results_final.json),
poles1, kplus1 (a coefficient is added only when no earlier source has it).  Errors: stat (+) floor (diagonal).
No archive file is read (compare_engine reads only the direct table).  Runtime ~1 min (local).
usage: python3 tests/direct_C8.py [--run runs/c8val ...] [--out results/direct_C8]
"""
import argparse, json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJ = os.path.dirname(ROOT)
CE = os.path.join(PROJ, 'direct', 'src', 'compare_engine.py')
sys.path.insert(0, os.path.join(PROJ, 'direct', 'src'))
from compare_engine import direct_name          # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='append', default=None)
    ap.add_argument('--out', default=os.path.join(ROOT, 'results', 'direct_C8'))
    a = ap.parse_args()
    runs = a.run or [os.path.join(ROOT, 'runs', x) for x in ('c8val', 'c8conv', 'c8kplus1')]
    merged, groups = {}, set()
    for rd in runs:
        man = json.load(open(os.path.join(rd, 'manifest.json')))
        strided = {m['moment'] for m in man if any('sectorstride' in str(e) for e in (m.get('extra') or []))}
        for g, ser in json.load(open(os.path.join(rd, 'results.json')))['results'].items():
            if g in strided:
                continue
            gg = re.sub(r'_N\d+$', '', g)
            groups.add(gg)
            merged.setdefault(gg, {})
            for kj, ve in ser.items():
                cur = merged[gg].get(kj)
                if cur is None or ve[1] < cur[1]:         # several N of one job (pilot): the smaller error
                    merged[gg][kj] = ve
    added = {}
    # completion order: the assembly-phase convergence re-check conv1 (Z4_E k = -1, 0, A3_vdE, A5_vv at 4-16x the
    # production N; README section 8c) before the production values, then poles1 and kplus1
    for tag, path in (('conv1', 'runs/conv1/results.json'), ('production', 'runs/prod_6digit/results_final.json'),
                      ('poles1', 'runs/poles1/results.json'), ('kplus1', 'runs/kplus1/results.json')):
        for g, ser in json.load(open(os.path.join(ROOT, path)))['results'].items():
            gg = re.sub(r'_N\d+$', '', g)
            if gg not in groups:
                continue
            for kj, ve in ser.items():
                if kj not in merged[gg]:
                    merged[gg][kj] = ve
                    added.setdefault(tag, []).append(f'{gg}:{kj}')
    eng_file = a.out + '_engine.json'
    json.dump({'note': 'C8-era engine series: validation run(s) ' + ', '.join(os.path.relpath(r, ROOT) for r in runs)
                       + ', completed by conv1, production, poles1, kplus1', 'added': added, 'results': merged},
              open(eng_file, 'w'), indent=1)
    only = sorted({direct_name(g) for g in groups if direct_name(g)})
    with open(a.out + '.txt', 'w') as fh:
        subprocess.run([sys.executable, CE, eng_file, '--offset-fit', '--quiet-raw', '--only', ','.join(only),
                        '--out', a.out + '.json'], stdout=fh, stderr=subprocess.STDOUT, check=True,
                       cwd=os.path.join(PROJ, 'direct', 'src'))
    rows = json.load(open(a.out + '_offsets.json'))
    tally = {}
    for r in rows:
        tally[r['verdict']] = tally.get(r['verdict'], 0) + 1
    print('direct comparison of the C8-era atoms:', tally)
    print(open(a.out + '.txt').read()[-6000:])


if __name__ == '__main__':
    main()
