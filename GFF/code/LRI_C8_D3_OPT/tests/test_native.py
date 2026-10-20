#!/usr/bin/env python3
"""Same-sample C7 regression and C8 array-boundary/split checks.

The synthetic L2/L8 inputs exercise storage and Taylor limits only. They are
explicitly excluded from scientific production and do not estimate any C_L.
The reference binary must be compiled from the untouched uploaded C7 source.
"""
from __future__ import annotations
import argparse
from decimal import Decimal
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import tempfile

import numpy as np
from scipy.stats import qmc

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_net(path, dimension, seed=617730124, bits=52, replicates=2):
    matrices = []
    for rep in range(replicates):
        engine = qmc.Sobol(d=dimension, scramble=True, bits=bits, seed=seed + rep)
        matrices.append(engine._sv.astype('<u8', copy=True))
    with Path(path).open('wb') as f:
        f.write(struct.pack('<III', replicates, dimension, bits))
        for matrix in matrices:
            f.write(matrix.tobytes())


def execute(exe, graphs, gamma, net, tasks, output, *, loop, legacy=False,
            layout=0, threads=1, rows=None):
    if rows is None:
        raise ValueError('explicit tasks required')
    Path(tasks).write_text(('C7D3TASKS1' if legacy else 'C8D3TASKS1')
                          + f' {loop} {len(rows)}\n'
                          + ''.join(' '.join(map(str, row)) + '\n' for row in rows))
    cmd = [str(exe), str(graphs), str(gamma), str(net), str(tasks), str(output),
           '598349273', str(layout), '.8', str(threads), 'compensated', '-']
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    result = json.loads(Path(output).read_text())
    if len(result['rows']) != len(rows):
        raise AssertionError('native output dropped tasks')
    return result


def synthetic_graph(path, loop):
    """U = product_i (x_2i + x_(2i+1)); an algebra test, not a phi4 input."""
    edges = 2 * loop
    masks = sorted(sum(1 << (2*i + bit) for i, bit in enumerate(choice))
                   for choice in itertools.product((0, 1), repeat=loop))
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f'C8D3GRAPH1 {loop} 0 3 1 {len(masks)} 1',
             ' '.join(map(str, masks)),
             ' '.join(map(str, [len(masks), *range(len(masks)), *([1] * edges)])),
             str(1 << edges),
             ' '.join('0' if i in (0, (1 << edges)-1) else '.25'
                      for i in range(1 << edges))]
    path.write_text('\n'.join(lines) + '\n')


def close_decimal(x, y, tolerance='1e-12'):
    x, y = Decimal(x), Decimal(y)
    return abs(x-y) <= Decimal(tolerance) * max(Decimal(1), abs(x), abs(y))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--c7-package', type=Path, default=ROOT/'reference_c7',
                        help='Default: bundled minimal untouched C7 fixtures; a full extracted upload is also accepted.')
    parser.add_argument('--c7-binary', type=Path, default=ROOT/'bin/c7d3_reference')
    parser.add_argument('--binary', type=Path, default=ROOT/'bin/c8d3_gmp')
    parser.add_argument('--output', type=Path, default=ROOT/'verification/native_checks.json')
    args = parser.parse_args()
    c7 = args.c7_package.resolve()
    gamma8 = ROOT/'inputs/gamma_d3_8.txt'
    inv = json.loads((c7/'inputs/inventory.json').read_text())
    checks = []
    points, promotion_quad, promotion_mp = 0, 0, 0
    selected_paths = []
    with tempfile.TemporaryDirectory(prefix='c8_native_', dir=ROOT/'bin') as temp:
        td = Path(temp)
        for sector in ('free', 'power'):
            for loop in range(3, 8):
                ordered = sorted(inv[sector][str(loop)], key=lambda row: row['cost'])
                ids = sorted({ordered[0]['id'], ordered[-1]['id']})
                selected_paths += [c7/f'reference/inputs/{sector}/L{loop}/G{gid}.txt' for gid in ids]
                rows = [(uid, rep, gid, 0, 64, 64)
                        for uid, (rep, gid) in enumerate(itertools.product(range(2), ids))]
                make_net(td/'net.bin', 4*loop - 1)
                kwargs = dict(loop=loop, rows=rows)
                old = execute(args.c7_binary, c7/f'reference/inputs/{sector}',
                              c7/'inputs/gamma_d3_7.txt', td/'net.bin', td/'old.tasks',
                              td/'old.json', legacy=True, **kwargs)
                new = execute(args.binary, c7/f'reference/inputs/{sector}', gamma8,
                              td/'net.bin', td/'new.tasks', td/'new.json', **kwargs)
                old_width, new_width = 8-loop, 9-loop
                for a, b in zip(old['rows'], new['rows'], strict=True):
                    for identity in ('uid', 'rep', 'graph', 'begin', 'end', 'total', 'quad', 'mp'):
                        if a[identity] != b[identity]:
                            raise AssertionError(f'{sector}, L{loop}: changed {identity}')
                    overlap = b['values'][:old_width] + b['values'][new_width:new_width+old_width]
                    if a['values'] != overlap:
                        raise AssertionError(f'{sector}, L{loop}: shared C7 jets changed')
                    if len(b['values']) != 2*new_width:
                        raise AssertionError('wrong expanded jet width')
                points += 64*len(rows)
                promotion_quad += sum(row['quad'] for row in new['rows'])
                promotion_mp += sum(row['mp'] for row in new['rows'])
                checks.append({'test': 'common_C7_jets', 'sector': sector, 'L': loop,
                               'graphs': ids, 'points_per_replicate': 64, 'replicates': 2,
                               'all_common_values_and_counters_exact': True})

        # L2 reaches all seven scalar Taylor slots; L8 reaches sixteen edges and
        # 31 Sobol coordinates. Each native row is additionally checked at a split
        # and with two threads. These inputs are synthetic and never production data.
        for loop in (2, 8):
            graph = td/f'synthetic/L{loop}/G0.txt'
            synthetic_graph(graph, loop)
            for layout in (0, 1, 2):
                make_net(td/'net.bin', 2*loop if layout == 2 else 4*loop-1)
                rows = [(0, 0, 0, 0, 32, 32), (1, 1, 0, 0, 32, 32)]
                kwargs = dict(loop=loop, layout=layout)
                whole = execute(args.binary, td/'synthetic', gamma8, td/'net.bin',
                                td/'whole.tasks', td/'whole.json', rows=rows, **kwargs)
                threaded = execute(args.binary, td/'synthetic', gamma8, td/'net.bin',
                                   td/'thread.tasks', td/'thread.json', rows=rows, threads=2, **kwargs)
                split_rows = [(2*rep+i, rep, 0, 16*i, 16*(i+1), 32)
                              for rep, i in itertools.product(range(2), range(2))]
                split = execute(args.binary, td/'synthetic', gamma8, td/'net.bin',
                                td/'split.tasks', td/'split.json', rows=split_rows, **kwargs)
                for rep in range(2):
                    full, par = whole['rows'][rep], threaded['rows'][rep]
                    if full['values'] != par['values'] or any(full[k] != par[k] for k in ('quad', 'mp')):
                        raise AssertionError('thread-count dependence')
                    ss = split['rows'][2*rep:2*rep+2]
                    for col, value in enumerate(full['values']):
                        rebuilt = sum(Decimal(row['values'][col]) for row in ss)
                        if not close_decimal(value, str(rebuilt)):
                            raise AssertionError('Sobol random-access split differs')
                    if any(full[k] != sum(row[k] for row in ss) for k in ('quad', 'mp')):
                        raise AssertionError('Sobol split promotion counts differ')
                checks.append({'test': 'synthetic_storage_split_threads', 'L': loop,
                               'layout': layout, 'scalar_slots': 9-loop, 'passed': True,
                               'scientific_input': False})

        point_report = None
        point_binary = ROOT/'bin/point_checks_gmp'
        if point_binary.exists():
            (td/'points.list').write_text('\n'.join(map(str, selected_paths)) + '\n'
                                        + str(td/'synthetic/L8/G0.txt') + '\n')
            cp = subprocess.run([str(point_binary), str(td/'points.list')], check=True,
                                capture_output=True, text=True)
            point_report = json.loads(cp.stdout)

    report = {'status': 'passed', 'dimension': 3, 'order': 8, 'checks': checks,
              'C7_regression_samples': points, 'quad_promotions': promotion_quad,
              'MP_promotions': promotion_mp, 'precision_points': point_report,
              'c8_binary_sha256': sha(args.binary), 'c7_binary_sha256': sha(args.c7_binary),
              'gamma8_sha256': sha(gamma8), 'C7_sources_sha256': {
                  str(name): sha(c7/name) for name in ('src/kernel.hpp', 'src/c7d3_integrate.cpp')},
              'scope': 'Native arithmetic regression, precision tiers and storage limits; not graph coverage or a C8 estimate.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'C7_regression_samples': points,
                      'quad': promotion_quad, 'MP': promotion_mp, 'output': str(args.output)}))


if __name__ == '__main__':
    main()
