#!/usr/bin/env python3
"""Merge collected campaigns group by group (2026-10-03, tier-1 top-up).

  merge_runs.py BASE_RUNDIR TOPUP_RUNDIR [TOPUP_RUNDIR ...] --tag final [--need specs/production_D4.json]

Reads <rundir>/results.json (campaign.py collect, v2 replicate layout) of every run directory.  Every moment group
present in a later directory REPLACES the whole group (all its eps powers, replicates, errors, covariance blocks,
costs) of the earlier ones; nothing is averaged across runs (the top-up runs a group at a larger lattice with fresh
seeds, so its error is several times smaller and the runs are independent).  Groups must keep their replicate
count so that the per-replicate framework assembly (tests/e2e_framework.py sigma_rep) still sees one R.
Writes BASE_RUNDIR/results_<tag>.json and BASE_RUNDIR/framework_input_<tag>.json (atomic), with a 'merged' record
{group: source run directory}.  Exit status 2 if a source is incomplete or a replicate count differs.
"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lri_moments import atomic_write_json
from campaign import framework_input, _need_lookup, ROOT

KEYS = ('results', 'replicates', 'errors', 'costs')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base')
    ap.add_argument('topups', nargs='+')
    ap.add_argument('--tag', default='final')
    ap.add_argument('--need', default=os.path.join(ROOT, 'specs', 'production_D4.json'))
    a = ap.parse_args()
    out = json.load(open(os.path.join(a.base, 'results.json')))
    if out.get('engine_pipeline') != 'v2' or not out.get('complete'):
        sys.exit(f'{a.base}/results.json is not a complete v2 collect output')
    src = {g: os.path.abspath(a.base) for g in out['results']}
    Rs = {b['R'] for b in out['blocks'].values()}
    for td in a.topups:
        t = json.load(open(os.path.join(td, 'results.json')))
        if t.get('engine_pipeline') != 'v2' or not t.get('complete'):
            print(f'{td}/results.json is not a complete v2 collect output', file=sys.stderr)
            sys.exit(2)
        for g in t['results']:
            if g not in out['results']:
                print(f'WARNING: group {g} of {td} is new (not in the base run); added')
            for b in [b for b in out['blocks'] if b.split('|')[0] == g]:
                del out['blocks'][b]
            for key in KEYS:
                if g in t.get(key, {}):
                    out.setdefault(key, {})[g] = t[key][g]
                elif g in out.get(key, {}):
                    del out[key][g]
            for b, v in t['blocks'].items():
                if b.split('|')[0] == g:
                    out['blocks'][b] = v
                    Rs.add(v['R'])
            out['zeros'] = [z for z in out['zeros'] if not z.startswith(g.replace('_base', '') + '[')] + \
                           [z for z in t.get('zeros', []) if z.startswith(g.replace('_base', '') + '[')]
            src[g] = os.path.abspath(td)
            print(f'{g}: taken from {td}')
    if len(Rs) != 1:
        print(f'replicate counts differ after the merge: {sorted(Rs)}', file=sys.stderr)
        sys.exit(2)
    out['merged'] = src
    out['problems'] = []
    atomic_write_json(os.path.join(a.base, f'results_{a.tag}.json'), out, indent=1)
    fi = framework_input(out, _need_lookup(a.need), a.base)
    fi['producer']['merged'] = {g: s for g, s in src.items() if s != os.path.abspath(a.base)}
    atomic_write_json(os.path.join(a.base, f'framework_input_{a.tag}.json'), fi, indent=1)
    print(f'wrote {a.base}/results_{a.tag}.json and framework_input_{a.tag}.json '
          f'({sum(len(v) for v in out["results"].values())} coefficients, R = {Rs.pop()})')


if __name__ == '__main__':
    main()
