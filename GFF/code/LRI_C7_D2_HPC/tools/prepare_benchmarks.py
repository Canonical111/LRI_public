#!/usr/bin/env python3
"""Create portable, deterministic profiling/benchmark input fixtures.

The earlier timing summaries survive, but their original net/task files were
not separately delivered. These NEW fixtures choose 16 highest-cost graphs per
sector/loop, with a documented seed. They allow matched old/new comparisons;
they are not a reconstruction of the historical timing streams.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from common import ROOT, load, dump, checked, digest
from prepare_inputs import prepare
from production import make_net


def prepare_benchmarks() -> dict:
    prepare()
    folder = ROOT / 'benchmarks' / 'fixtures'
    manifest = folder / 'manifest.json'
    if manifest.exists():
        result = load(manifest)
        checked(ROOT / 'inputs/inventory.json', result['inventory_sha256'])
        for name, sha in result['sha256'].items():
            checked(folder / name, sha)
        return result
    folder.mkdir(parents=True, exist_ok=True)
    inv = load(ROOT / 'inputs/inventory.json')
    records, hashes = {}, {}
    for si, sector in enumerate(('free', 'power')):
        for L in (6, 7):
            name = f'{sector}_L{L}'
            rows = sorted(inv[sector][str(L)], key=lambda r: (-r['cost'], r['id']))[:16]
            ids = sorted(r['id'] for r in rows)
            net = folder / (name + '.net')
            task = folder / (name + '.tasks')
            if net.exists() or task.exists():
                raise FileExistsError('Incomplete fixture creation; remove only benchmarks/fixtures and retry')
            metadata = make_net(net, 2, 4*L-1, 60, 2026093017 + 100*si + L)
            n = 512
            tasks = [(i, rep, g, 0, n, n) for i, (rep, g) in
                     enumerate((rep, g) for rep in range(2) for g in ids)]
            task.write_text(f'C7D2TASKS1 {L} {len(tasks)}\n' +
                            ''.join(' '.join(map(str, r))+'\n' for r in tasks))
            hashes[net.name], hashes[task.name] = digest(net), digest(task)
            records[name] = dict(sector=sector, L=L, ids=ids, profiling_points_per_graph_per_replicate=n, net=metadata)
    result = dict(schema='c7-d2-hpc-benchmark-fixtures-1', dimension=2, order=7,
                  inventory_sha256=digest(ROOT/'inputs/inventory.json'),
                  records=records, sha256=hashes,
                  provenance='New deterministic fixtures generated during final packaging; historical timing reports are not reasserted for these streams.')
    dump(manifest, result)
    return result

if __name__ == '__main__':
    import json
    print(json.dumps(prepare_benchmarks(), indent=2))
