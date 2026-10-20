#!/usr/bin/env python3
"""Exact bookkeeping of all eight-loop target classes and lower-loop kernels (A-INV-3(f)).

Port of reference/power_mass/code/coverage.py from order 7 to order 8. The zero-channel exclusion (s_G = 4, so
3w_B - w_A = 6(s_G - 4)/D_G = 0) applies only at the top loop of the order, now L = 8; at every lower loop all
finite kernels are retained, since their coupling and mass jets enter separately (at order 8 the L7 kernels with
s_G = 4 are integrated). Every class of every loop is assigned exactly one category. The free and power builder
inventories must agree on id, key, D_G and s_G for every class.

Top loop categories (the original names): zero_channel_weight, zero_mixed_forest_kernel_at_nonzero_weight,
retained_primitive, retained_powerfree_nonprimitive, new_power_containing. Lower loops: exact_zero_kernel,
retained_primitive, retained_powerfree_nonprimitive, new_power_containing.

Usage: python3 -B gen/coverage.py --stage DIR [--loops 7,8] [--top 8] [--output FILE]
  DIR holds L{L}_free/inventory.json and L{L}_power/inventory.json."""
import argparse
import json
import sys
from pathlib import Path

TOP_CATEGORIES = ('zero_channel_weight', 'zero_mixed_forest_kernel_at_nonzero_weight', 'retained_primitive',
                  'retained_powerfree_nonprimitive', 'new_power_containing')
LOWER_CATEGORIES = ('exact_zero_kernel', 'retained_primitive', 'retained_powerfree_nonprimitive', 'new_power_containing')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--stage', type=Path, required=True)
    ap.add_argument('--loops', default='7,8')
    ap.add_argument('--top', type=int, default=8)
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    rows, partitions, selection, detail = [], {}, {}, []
    for L in [int(v) for v in a.loops.split(',')]:
        p = json.load(open(a.stage / f'L{L}_power/inventory.json'))
        f = json.load(open(a.stage / f'L{L}_free/inventory.json'))
        assert len(p) == len(f), (L, len(p), len(f))
        top = L == a.top
        partition = dict.fromkeys(TOP_CATEGORIES if top else LOWER_CATEGORIES, 0)
        cc = dict(loop=L, classes=len(p), power_classes=0, new_nonzero_kernels=0, new_sampled_classes=0,
                  new_zero_kernels=0)
        sel = dict(free=[], power=[])
        seen = set()
        for i, (pa, fb) in enumerate(zip(p, f)):
            assert pa['id'] == fb['id'] == i and pa['key'] == fb['key'] and pa['denominator'] == fb['denominator'] \
                and pa['mass_numerator'] == fb['mass_numerator'], (L, i)
            if pa['power_subgraphs']:
                cc['power_classes'] += 1
                if pa['status'] == 'finite-kernel':
                    cc['new_nonzero_kernels'] += 1
                if pa['status'] == 'exact-zero-kernel':
                    cc['new_zero_kernels'] += 1
                if pa['status'] == 'finite-kernel' and (not top or pa['mass_numerator'] != 4):
                    cc['new_sampled_classes'] += 1
            if top and pa['mass_numerator'] == 4:
                c = 'zero_channel_weight'
            elif pa['power_subgraphs']:
                c = 'new_power_containing' if pa['status'] == 'finite-kernel' else (
                    'zero_mixed_forest_kernel_at_nonzero_weight' if top else 'exact_zero_kernel')
            elif fb['status'] != 'finite-kernel':
                c = 'zero_mixed_forest_kernel_at_nonzero_weight' if top else 'exact_zero_kernel'
            elif fb['primitive']:
                c = 'retained_primitive'
            else:
                c = 'retained_powerfree_nonprimitive'
            assert i not in seen
            seen.add(i)
            partition[c] += 1
            if c == 'new_power_containing':
                sel['power'].append(i)
            elif c in ('retained_primitive', 'retained_powerfree_nonprimitive'):
                sel['free'].append(i)
            if top:
                detail.append(dict(id=i, category=c, denominator=pa['denominator'], mass_numerator=pa['mass_numerator'],
                                   power_subgraphs=pa['power_subgraphs']))
        assert sum(partition.values()) == len(p) == len(seen), (L, partition)
        rows.append(cc)
        partitions[str(L)] = partition
        selection[str(L)] = dict(free=sel['free'], power=sel['power'],
                                 primitive=[i for i in sel['free'] if f[i]['primitive']])
    out = dict(schema='c8-d2-gate-1', gate='A-INV-3(f) coverage', status='passed', loops=rows, partitions=partitions,
               top_loop=a.top, total_classes={str(r['loop']): r['classes'] for r in rows},
               definitions='zero-channel exclusions apply only to the eighth-order simple-pole target (top loop L=8). '
                           'All lower-loop coupling/mass jets are retained separately.',
               selection=selection, top_loop_classes=detail)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(out, indent=1) + '\n')
    print(rows)
    print(partitions)
    return 0


if __name__ == '__main__':
    sys.exit(main())
