#!/usr/bin/env python3
"""Measure native cost across graph-complexity strata without a physical estimate."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import time

import numpy as np
from scipy.stats import qmc

ROOT = Path(__file__).resolve().parents[1]


def make_net(path, dimension, bits, replicates, seed):
    with Path(path).open('wb') as f:
        f.write(struct.pack('<III', replicates, dimension, bits))
        for rep in range(replicates):
            engine = qmc.Sobol(dimension, scramble=True, bits=bits, seed=seed+rep)
            f.write(engine._sv.astype('<u8', copy=False).tobytes())


def scan(directory):
    rows = []
    for path in directory.glob('G*.txt'):
        with path.open() as f:
            h = f.readline().split()
        if len(h) != 7:
            continue
        graph, monomials, terms = int(h[2]), int(h[5]), int(h[6])
        rows.append({'id': graph, 'monomials': monomials, 'terms': terms,
                     'cost': monomials*terms, 'file': str(path)})
    return sorted(rows, key=lambda r: (r['cost'], r['id']))


def stratified(rows, n):
    bins = np.array_split(np.arange(len(rows)), min(n, len(rows)))
    selected = []
    for indices in bins:
        sample = dict(rows[int(indices[len(indices)//2])])
        sample['bin_graphs'] = len(indices)
        selected.append(sample)
    return selected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--generated-root', type=Path)
    p.add_argument('--points', type=int, default=64)
    p.add_argument('--replicates', type=int, default=4)
    p.add_argument('--strata', type=int, default=8)
    p.add_argument('--loops', nargs='+', type=int, default=list(range(3, 9)))
    p.add_argument('--threads', type=int, default=1)
    p.add_argument('--output', type=Path, default=ROOT/'verification/benchmark_c8.json')
    a = p.parse_args()
    if a.points < 1 or a.points & (a.points-1) or a.replicates < 2 or a.strata < 1 or a.threads < 1:
        raise ValueError('invalid benchmark size')
    a.output.parent.mkdir(parents=True, exist_ok=True)
    exe = ROOT/'bin/c8d3_gmp'
    gamma = ROOT/'inputs/gamma_d3_8.txt'
    report = {'purpose': 'performance_only', 'points': a.points, 'replicates': a.replicates,
              'threads': a.threads, 'dimension': 3, 'order': 8, 'groups': [],
              'scope': 'One median-complexity graph per equal-count complexity bin; approximate total CPU cost. No physical coefficient is estimated.',
              'binary_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
              'rate': 0.8, 'net_bits': 52}
    with tempfile.TemporaryDirectory(prefix='c8_benchmark_', dir=ROOT/'bin') as tmp:
        td = Path(tmp)
        for loop in a.loops:
            base = a.generated_root/f'generated_L{loop}' if a.generated_root else ROOT/'inputs'
            for sector in ('free', 'power'):
                rows = scan(base/sector/f'L{loop}')
                if not rows:
                    raise ValueError(f'no graphs in {sector} L{loop}')
                selected = stratified(rows, a.strata)
                make_net(td/'net', 4*loop-1, 52, a.replicates, 715683741 + 107*loop + (41 if sector=='power' else 0))
                tasks = [(uid, rep, row['id'], 0, a.points, a.points)
                         for uid, (rep, row) in enumerate((rep, row)
                             for rep in range(a.replicates) for row in selected)]
                (td/'tasks').write_text(f'C8D3TASKS1 {loop} {len(tasks)}\n'
                                       + ''.join(' '.join(map(str, t))+'\n' for t in tasks))
                started = time.monotonic()
                cp = subprocess.run([str(exe), str(base/sector), str(gamma), str(td/'net'),
                    str(td/'tasks'), str(td/'out'), '716397108621', '0', '.8', str(a.threads),
                    'compensated', '-'], check=True, capture_output=True, text=True)
                wall = time.monotonic()-started
                result = json.loads((td/'out').read_text())
                measured = []
                for row in selected:
                    samples = [r for r in result['rows'] if r['graph']==row['id']]
                    seconds = sum(r['seconds'] for r in samples)
                    measured.append({**row, 'samples': a.points*a.replicates,
                        'seconds': seconds, 'seconds_per_point': seconds/(a.points*a.replicates),
                        'quad': sum(r['quad'] for r in samples), 'MP': sum(r['mp'] for r in samples)})
                estimate = sum(row['seconds']*row['bin_graphs'] for row in measured)
                group = {'L': loop, 'sector': sector, 'available_graphs': len(rows),
                    'sampled_graphs': measured, 'wall_seconds': wall,
                    'native_load_seconds': result['load_seconds'],
                    'native_integration_seconds': result['integration_seconds'],
                    'estimated_all_graph_integration_core_seconds_one_campaign': estimate}
                report['groups'].append(group)
                report['estimated_all_graph_integration_core_seconds_two_campaigns'] = 2*sum(
                    g['estimated_all_graph_integration_core_seconds_one_campaign'] for g in report['groups'])
                a.output.write_text(json.dumps(report, indent=2)+'\n')
                print(json.dumps({'L': loop, 'sector': sector, 'graphs': len(rows), 'measured_wall': wall,
                    'estimated_all_graph_core_seconds': estimate}), flush=True)
    print(json.dumps({'status': 'complete', 'output': str(a.output), 'two_campaign_core_seconds':
        report['estimated_all_graph_integration_core_seconds_two_campaigns']}))


if __name__ == '__main__':
    main()
