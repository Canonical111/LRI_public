#!/usr/bin/env python3
"""Consistency of a C8 production tier with the earlier, independent (other seeds) runs of the same jobs
(phase 3, 2026-10-04; the C8 analogue of README section 9, criterion 6).

usage: tier_vs_pilot_C8.py TIERDIR [--ref runs/c8val --ref runs/c8conv ...] [--json OUT.json]

For every job (moment, eps power) of TIERDIR and every reference run that holds the same job (group name with an
optional _N<size> suffix, same eps power, ALL sectors, i.e. no sector stride), every needed coefficient of the tier
(manifest 'need') that both runs computed is compared:
  pull_stat = (x_tier - x_ref) / sqrt(stat_tier^2 + stat_ref^2)          (replicate errors only)
  pull_tot  = (x_tier - x_ref) / sqrt(err_tier^2 + err_ref^2)            (quoted errors, stat (+) floor)
Both results.json files must exist (campaign.py collect).  The seeds of the runs are disjoint (seedcheck), so
the statistical errors are independent.  No archive data is read.
"""
import argparse, json, math, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def base(name):
    return re.sub(r'(_N\d+)?(_S\d+)?$', '', name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tier')
    ap.add_argument('--ref', action='append', default=None)
    ap.add_argument('--json', default=None)
    a = ap.parse_args()
    refs = a.ref or [os.path.join(ROOT, 'runs', r) for r in ('c8val', 'c8conv', 'c8kplus1', 'poles1', 'kplus1')]
    tm = json.load(open(os.path.join(a.tier, 'manifest.json')))
    tr = json.load(open(os.path.join(a.tier, 'results.json')))
    rows = []
    for m in tm:
        name, k, need = m['moment'], m['job']['k'], m.get('need') or []
        for rd in refs:
            if not os.path.exists(os.path.join(rd, 'results.json')):
                continue
            rm = json.load(open(os.path.join(rd, 'manifest.json')))
            rr = json.load(open(os.path.join(rd, 'results.json')))
            for m2 in rm:
                if base(m2['moment']) != base(name) or m2['job']['k'] != k:
                    continue
                if any(str(e).startswith('sectorstride') for e in (m2.get('extra') or [])):
                    continue
                for j in need:
                    key = f'{k},{j}'
                    if key not in tr['results'].get(name, {}) or key not in rr['results'].get(m2['moment'], {}):
                        continue
                    x1, e1 = tr['results'][name][key]
                    x2, e2 = rr['results'][m2['moment']][key]
                    s1 = tr['errors'][name][key]['stat']
                    s2 = rr['errors'][m2['moment']][key]['stat']
                    z1 = tr['errors'][name][key].get('zero')
                    d = x1 - x2
                    ps = d / math.hypot(s1, s2) if math.hypot(s1, s2) > 0 else (0.0 if d == 0 else float('inf'))
                    pt = d / math.hypot(e1, e2) if math.hypot(e1, e2) > 0 else (0.0 if d == 0 else float('inf'))
                    rows.append({'job': name, 'k': k, 'j': j, 'ref': os.path.relpath(rd, ROOT), 'ref_entry': m2['moment'],
                                 'N_tier': m['N'], 'N_ref': m2['N'], 'x_tier': x1, 'x_ref': x2, 'diff': d,
                                 'stat_tier': s1, 'stat_ref': s2, 'err_tier': e1, 'err_ref': e2,
                                 'pull_stat': ps, 'pull_tot': pt, 'zero': bool(z1)})
    print('%-10s %3s %2s %-16s %8s %8s %24s %10s %10s %10s %8s %8s' % (
        'job', 'k', 'j', 'ref', 'N_tier', 'N_ref', 'x_tier', 'diff', 'stat_tier', 'stat_ref', 'p_stat', 'p_tot'))
    for r in rows:
        print('%-10s %3d %2d %-16s %8d %8d %24.16g %10.2e %10.2e %10.2e %8.2f %8.2f%s' % (
            r['job'], r['k'], r['j'], r['ref'] + ':' + r['ref_entry'][len(base(r['ref_entry'])):], r['N_tier'],
            r['N_ref'], r['x_tier'], r['diff'], r['stat_tier'], r['stat_ref'], r['pull_stat'], r['pull_tot'],
            '  (structural zero)' if r['zero'] else ''))
    fin = [r for r in rows if not r['zero'] and math.isfinite(r['pull_tot'])]
    if fin:
        rms_s = math.sqrt(sum(r['pull_stat'] ** 2 for r in fin if math.isfinite(r['pull_stat'])) / len(fin))
        rms_t = math.sqrt(sum(r['pull_tot'] ** 2 for r in fin) / len(fin))
        print(f'\n{len(fin)} comparisons (structural zeros excluded): rms pull_stat {rms_s:.2f}, rms pull_tot {rms_t:.2f}; '
              f'max |pull_stat| {max(abs(r["pull_stat"]) for r in fin):.2f}, max |pull_tot| '
              f'{max(abs(r["pull_tot"]) for r in fin):.2f}; |pull_stat| > 3: {sum(abs(r["pull_stat"]) > 3 for r in fin)}')
    if a.json:
        json.dump({'tier': a.tier, 'refs': refs, 'rows': rows}, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
