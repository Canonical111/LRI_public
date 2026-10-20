#!/usr/bin/env python3
"""Machine split of the C8 tiers B and C (2026-10-04).

  split_C8BC.py split SPEC --plan PLAN.json [--min-core-h 50] --out-heavy H.json --out-cheap C.json
      Splits a tier spec into its heavy jobs (planned cost >= min-core-h amdq core-h: symmetry amdq, whole nodes) and
      the cheap rest (the personal desktop, a few cores).  Both halves keep the tier name of SPEC, and every entry is copied
      unchanged, so campaign.py plan gives exactly the cfgs and seeds of the unsplit spec (seeds are hashed from
      tier, group, k and chunk, not from the run directory).
  split_C8BC.py order RUNDIR [--out cfglist_sym.txt]
      Array order for symmetry: the first chunk of every job, most expensive job first (so that the budget guard
      sees every heavy group after the first wave), then all other cfgs longest first (estimated cost).
"""
import argparse, json, os, sys


def split(a):
    spec = json.load(open(a.spec))
    plan = json.load(open(a.plan))
    cost = {(j['group'], j['k']): j['core_h'] for j in plan['jobs']}
    heavy, cheap = [], []
    for m in spec['moments']:
        c = cost.get((m['name'], m['powers'][0]))
        if c is None:
            sys.exit(f"{m['name']} k={m['powers'][0]} not in {a.plan}")
        (heavy if c >= a.min_core_h else cheap).append(m)
    for out, moms, what in ((a.out_heavy, heavy, 'heavy'), (a.out_cheap, cheap, 'cheap')):
        d = dict(spec, moments=moms, note=spec.get('note', '') + f' | {what} part (py/split_C8BC.py, '
                                                                    f'planned cost >= {a.min_core_h} core-h: heavy)')
        json.dump(d, open(out, 'w'), indent=1)
        print(f"{what}: {len(moms)} entries ({sum(cost[(m['name'], m['powers'][0])] for m in moms):.1f} planned core-h)"
              f" -> {out} (tier {spec['tier']})")


def order(a):
    man = json.load(open(os.path.join(a.rundir, 'manifest.json')))
    jobs = sorted(man, key=lambda m: -sum(m['est_cost']))
    first = [m['cfgs'][0] for m in jobs]
    rest = sorted([(e, c) for m in man for e, c in zip(m['est_cost'][1:], m['cfgs'][1:])], key=lambda x: -x[0])
    lst = first + [c for _, c in rest]
    out = os.path.join(a.rundir, a.out)
    open(out, 'w').write(''.join(c + '\n' for c in lst))
    print(f'{len(lst)} cfgs -> {out} (first chunks of {len(first)} jobs first)')


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('split')
    p.add_argument('spec')
    p.add_argument('--plan', required=True)
    p.add_argument('--min-core-h', type=float, default=50.0)
    p.add_argument('--out-heavy', required=True)
    p.add_argument('--out-cheap', required=True)
    p = sp.add_parser('order')
    p.add_argument('rundir')
    p.add_argument('--out', default='cfglist_sym.txt')
    a = ap.parse_args()
    split(a) if a.cmd == 'split' else order(a)


if __name__ == '__main__':
    main()
