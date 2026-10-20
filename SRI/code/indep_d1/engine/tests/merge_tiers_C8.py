#!/usr/bin/env python3
"""Scalar-level merge of the C8 tier deliverables into one framework input (2026-10-04, tiers B/C production).

  merge_tiers_C8.py --in TAG=FILE [--in TAG=FILE ...] --out OUT.json

Each FILE is a canonical framework input (`lri-framework-raw/1`, e.g. runs/c8tierA/framework_input_final.json).
The tiers are independent runs (different tier names, hence disjoint seeds), so every replicate block id is renamed
to '<TAG>:<block>' exactly as `run_framework.py --independent-files` does for separate --raw files; a scalar name
supplied by two inputs is an error (exit 2), as are different conventions or replicate counts.  Groups that appear in
several tiers with different eps powers (Z4_d: A and B; Z6_base: B and C) are kept, because the merge works per scalar,
never per group (py/merge_runs.py replaces whole groups and is only for top-ups inside one tier).
The output carries 'producer.merged_tiers' = {TAG: {file, sha256, n_scalars}}.
"""
import argparse, hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'py'))
from lri_moments import atomic_write_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', action='append', required=True, help='TAG=FILE')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    scal, conv, nrep, tiers = {}, None, None, {}
    for x in a.inp:
        tag, _, f = x.partition('=')
        d = json.load(open(f))
        if d.get('format') != 'lri-framework-raw/1':
            print(f'{f}: not a canonical framework input', file=sys.stderr)
            sys.exit(2)
        if conv is not None and d.get('convention') != conv:
            print(f'{f}: convention {d.get("convention")} != {conv}', file=sys.stderr)
            sys.exit(2)
        conv = d.get('convention')
        if nrep is not None and d.get('n_replicates') != nrep:
            print(f'{f}: n_replicates {d.get("n_replicates")} != {nrep}', file=sys.stderr)
            sys.exit(2)
        nrep = d.get('n_replicates')
        for name, v in d['scalars'].items():
            if name in scal:
                print(f'{name} is supplied by two inputs ({scal[name][0]} and {tag})', file=sys.stderr)
                sys.exit(2)
            if isinstance(v, dict) and 'reps' in v:
                v = dict(v, block=f"{tag}:{v.get('block', 'default')}")
            scal[name] = (tag, v)
        tiers[tag] = {'file': os.path.abspath(f), 'sha256': hashlib.sha256(open(f, 'rb').read()).hexdigest(),
                      'n_scalars': len(d['scalars']), 'producer': d.get('producer')}
    out = {'format': 'lri-framework-raw/1', 'convention': conv,
           'producer': {'component': 'engine', 'note': 'C8 tiers merged per scalar (tests/merge_tiers_C8.py); blocks '
                                                       'renamed <tier>:<block> (independent runs)',
                        'merged_tiers': tiers},
           'scalars': {k: v for k, (_, v) in sorted(scal.items())}, 'n_replicates': nrep}
    atomic_write_json(a.out, out, indent=1)
    print(f'wrote {a.out}: {len(scal)} scalars from {len(tiers)} inputs ('
          + ', '.join(f"{t} {v['n_scalars']}" for t, v in tiers.items()) + f'), R = {nrep}')


if __name__ == '__main__':
    main()
