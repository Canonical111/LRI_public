#!/usr/bin/env python3
"""Build a campaign spec (py/campaign.py plan) from the production group list specs/production_D4.json.

  make_spec.py --tier TIER --out SPEC.json [--shifts 8] [--N 16001] [--only G1,G2] [--set G:N=..,chunks=..] ...
       [--from-spec OLD.json]   (take N / chunks per group from an older spec, e.g. specs/pilot5_e2e.json)

Every moment entry carries 'coeffs' (the needed eps^k log^j per k), so collect writes explicit structural
zeros and fails on genuinely missing coefficients; seeds are derived by campaign.py from (tier, group, k, chunk).
"""
import argparse, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tier', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--shifts', type=int, default=8)
    ap.add_argument('--N', type=int, default=16001)
    ap.add_argument('--only')
    ap.add_argument('--from-spec')
    ap.add_argument('--set', action='append', default=[])
    a = ap.parse_args()
    prod = json.load(open(os.path.join(ROOT, 'specs', 'production_D4.json')))
    old = {}
    if a.from_spec:
        for m in json.load(open(a.from_spec))['moments']:
            old[m['name']] = m
    over = {}
    for s in a.set:
        g, kv = s.split(':', 1)
        for item in kv.split(','):
            k, v = item.split('=')
            over.setdefault(g, {})[k] = int(v)
    only = set(a.only.split(',')) if a.only else None
    moms = []
    for g in prod:
        if only and g['name'] not in only:
            continue
        m = {'name': g['name'], 'kind': g['kind'], 'n': g['n'], 'nv': g['nv'], 'nd': g['nd'], 'ne': g['ne'],
             'powers': g['powers'], 'jmin': g['jmin'], 'coeffs': g['coeffs'], 'N': a.N, 'chunks': 1}
        if g['name'] in old:
            m['N'] = old[g['name']].get('N', a.N)
            m['chunks'] = old[g['name']].get('chunks', 1)
        m.update(over.get(g['name'], {}))
        moms.append(m)
    spec = {'tier': a.tier, 'defaults': {'shifts': a.shifts, 'transform': 3, 'prec': 'auto'}, 'moments': moms}
    json.dump(spec, open(a.out, 'w'), indent=1)
    print(f'{len(moms)} groups -> {a.out} (tier {a.tier}, shifts {a.shifts})')


if __name__ == '__main__':
    main()
