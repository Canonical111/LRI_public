#!/usr/bin/env python3
"""A-KER-5 (PLAN.md; L <= 7 in Stage 3a, L8 in J-IN-1): the inventory's inspect fields against independent counts.

  python3 -B tests/inspect_check.py [--no-worker] [--graphs 100] [--output FILE]

  * every inventory row has its inspect fields (inspect_complete true), and its products and addends equal
    gen3/opcount.py's re-derivation from the member's payload text (the union of the masks' lowest-bit peeling chains;
    the nodes of the prefix trie over the terms' monomial lists); the header's M and T equal the row's monomials and
    terms; fmax is a non-negative integer and kernel_bytes > 0 (pure Python: runs on the Mac);
  * unless --no-worker (Expanse; `make inspect test-builds`): on `--graphs` kernels spread over every (sector, L) (equal
    shares, the slots of groups smaller than their share handed to the larger groups, so the count reaches --graphs),
    bin/c8d3_inspect files reports masks = M and terms = T and the inventory's products, segments, addends, numerators
    and kernel_bytes, and the order-trace build of the worker (bin/diag/c8d3_gmp_ordertrace, -DC8_ORDER_TRACE) reports
    the inventory's addends as each graph's addends.size(), and executes the tasks in the order of the stable sort by
    points x addends, descending: the worker's in-block ordering key (a6ce987 src/c7d3_integrate.cpp:44);
  * unless --no-worker, the index reader of `c8d3_inspect sizes` (S1-07) on the free L3 pack: the full index gives one
    line per member; a last record cut after one, two or three fields, a malformed or trailing field, and an empty or
    blank index each exit 2 with the reason and print nothing.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_common as nc  # noqa: E402
sys.path.insert(0, str(nc.ROOT / 'gen3'))
import opcount  # noqa: E402

FIELDS = ('products', 'segments', 'addends', 'numerators', 'kernel_bytes', 'fmax')
ORDERTRACE = nc.BIN / 'diag/c8d3_gmp_ordertrace'


def static_part(inv) -> dict:
    bad, n = [], 0
    for s in nc.SECTORS:
        for L, rows in inv[s].items():
            with (nc.ROOT / 'inputs' / f'packs/{s}_L{L}.pack').open('rb') as f:
                for r in rows:
                    f.seek(r['offset'])
                    st = opcount.stats(f.read(r['length']).decode())
                    where = f'{s} L{L} G{r["id"]}'
                    if any(r[k] is None for k in FIELDS):
                        bad.append(f'{where}: inspect fields missing')
                        continue
                    if (st['products'], st['addends']) != (r['products'], r['addends']):
                        bad.append(f'{where}: opcount products/addends {st["products"]}/{st["addends"]} != {r["products"]}/{r["addends"]}')
                    if (st['M'], st['T']) != (r['monomials'], r['terms']):
                        bad.append(f'{where}: header M/T {st["M"]}/{st["T"]} != {r["monomials"]}/{r["terms"]}')
                    if not (r['kernel_bytes'] > 0 and r['fmax'] >= 0 and r['segments'] >= 1 and r['numerators'] >= 1):
                        bad.append(f'{where}: implausible inspect fields')
                    n += 1
    if not inv.get('inspect_complete'):
        bad.append('inventory: inspect_complete is not true')
    if bad:
        raise AssertionError(f'A-KER-5: {len(bad)} problems: {bad[:10]}')
    return {'kernels': n, 'gate': 'products and addends = gen3/opcount.py re-derivation; M, T = headers; every row inspected'}


def allocate(sizes: dict, total: int) -> dict:
    """Kernels per (sector, L): equal shares, and the slots a small group cannot fill handed on to the larger groups
    (round by round, in group order) until `total` kernels are taken or every group is exhausted (Stage 3a repair round
    1: an equal split of 100 over the 10 L <= 7 groups took only 79, free L3 holding 5 kernels, power L3 1, power L4 3)."""
    alloc = {k: 0 for k in sizes}
    left = min(total, sum(sizes.values()))
    open_ = [k for k in sizes if sizes[k] > 0]
    while left > 0 and open_:
        share = max(1, left // len(open_))
        for k in list(open_):
            take = min(share, sizes[k] - alloc[k], left)
            alloc[k] += take
            left -= take
            if alloc[k] >= sizes[k]:
                open_.remove(k)
            if left == 0:
                break
    return alloc


def selection(inv, graphs: int) -> dict:
    """{(sector, L): rows}: allocate()'s count per group, spread evenly over the group's rows (inventory order)."""
    groups = [(s, int(L)) for s in nc.SECTORS for L in inv[s]]
    n = allocate({k: len(inv[k[0]][str(k[1])]) for k in groups}, graphs)
    picks = {}
    for s, L in groups:
        rows = inv[s][str(L)]
        picks[(s, L)] = [rows[(i * len(rows)) // n[(s, L)]] for i in range(n[(s, L)])]
    want = min(graphs, sum(len(inv[s][str(L)]) for s, L in groups))
    got = sum(len(v) for v in picks.values())
    if got != want or any(len({r['id'] for r in v}) != len(v) for v in picks.values()):
        raise AssertionError(f'A-KER-5 selection: {got} distinct kernels, {want} required')
    return picks


def worker_part(inv, graphs: int, td: Path) -> dict:
    nc.require(nc.INSPECT, ORDERTRACE)
    picks = selection(inv, graphs)
    sel = [(s, L, r['id']) for (s, L), rs in picks.items() for r in rs]
    checked = 0
    with nc.extracted(sel) as root:
        for (s, L), rs in picks.items():
            paths = [str(root / s / f'L{L}' / f'G{r["id"]}.txt') for r in rs]
            cp = subprocess.run([str(nc.INSPECT), 'files', *paths], capture_output=True, text=True)
            if cp.returncode:
                raise AssertionError(f'c8d3_inspect files failed: {cp.stderr[-800:]}')
            for r, line in zip(rs, cp.stdout.splitlines(), strict=True):
                o = json.loads(line)
                if (o['masks'], o['terms']) != (r['monomials'], r['terms']) or any(o[k] != r[k] for k in FIELDS if k != 'fmax'):
                    raise AssertionError(f'{s} L{L} G{r["id"]}: c8d3_inspect files {o} differs from the inventory row')
            # the worker's ordering key: tasks with varying point counts
            rows = [(i, 0, r['id'], 0, pts, 64) for i, (r, pts) in enumerate((r, p) for r in rs for p in (8, 64))]
            t = nc.write_tasks(td / 'trace_tasks', L, rows, order=8)
            netf = nc.net(td, nc.dim_of(L, 0), 52, 5555 + L)
            d, _ = nc.run_worker(ORDERTRACE, root / s, nc.GAMMA[8], netf, t, td / 'trace.json', 1, 0, '.8', 1)
            add = {int(k): v for k, v in d['addends'].items()}
            for r in rs:
                if add[r['id']] != r['addends']:
                    raise AssertionError(f'{s} L{L} G{r["id"]}: worker addends.size() {add[r["id"]]} != inventory {r["addends"]}')
            key = {r['id']: r['addends'] for r in rs}
            want = [u for u, *_ in sorted(rows, key=lambda x: -((x[4] - x[3]) * key[x[2]]))]
            if d['execution_order'] != want:
                raise AssertionError(f'{s} L{L}: execution order {d["execution_order"][:10]} != the points x addends order {want[:10]}')
            checked += len(rs)
    if checked < min(graphs, sum(len(v) for s in nc.SECTORS for v in inv[s].values())):
        raise AssertionError(f'A-KER-5: {checked} graphs checked, {graphs} required')
    return {'graphs': checked, 'graphs_requested': graphs, 'per_group': {f'{s}_L{L}': len(rs) for (s, L), rs in picks.items()},
            'gate': 'c8d3_inspect files = inventory; worker addends.size() = inventory; execution order = stable sort by points x addends'}


def index_part(inv, td: Path) -> dict:
    """S1-07: `c8d3_inspect sizes` reads complete four-field index records only and refuses an empty index."""
    nc.require(nc.INSPECT)
    rows = inv['free']['3']
    pack = nc.ROOT / 'inputs/packs/free_L3.pack'
    lines = [f'{r["id"]} 3 {r["offset"]} {r["length"]}' for r in rows]
    last = lines[-1].split()

    def run(name, text, rc, reason=None):
        idx = td / f'index_{name}'
        idx.write_text(text)
        cp = subprocess.run([str(nc.INSPECT), 'sizes', str(pack), str(idx), '2'], capture_output=True, text=True)
        if cp.returncode != rc or (reason and (reason not in cp.stderr or cp.stdout)):
            raise AssertionError(f'S1-07 index case {name}: exit {cp.returncode} (want {rc}{", " + repr(reason) if reason else ""}): {cp.stderr[-500:]}')
        return cp
    cp = run('full', '\n'.join(lines) + '\n', 0)
    if [json.loads(x)['id'] for x in cp.stdout.splitlines()] != [r['id'] for r in rows]:
        raise AssertionError('S1-07: the full index did not report every member in order')
    cases = [(f'last_record_{k}_fields', '\n'.join(lines[:-1] + [' '.join(last[:k])]) + '\n', 'incomplete or malformed') for k in (1, 2, 3)]
    cases += [('last_record_no_newline', '\n'.join(lines[:-1] + [' '.join(last[:2])]), 'incomplete or malformed'),
              ('id_L_only', f'{last[0]} 3\n', 'incomplete or malformed'),
              ('malformed_field', '\n'.join(lines[:-1] + [' '.join(last[:3] + ['x'])]) + '\n', 'incomplete or malformed'),
              ('trailing_field', '\n'.join(lines[:-1] + [lines[-1] + ' 7']) + '\n', 'trailing field'),
              ('empty', '', 'empty index'), ('blank', '\n  \n', 'empty index')]
    for name, text, reason in cases:
        run(name, text, 2, reason)
    return {'members': len(rows), 'refused': [c[0] for c in cases], 'gate': 'complete four-field records only; an empty index refused'}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--no-worker', action='store_true')
    ap.add_argument('--graphs', type=int, default=100)
    ap.add_argument('--output', type=Path)
    a = ap.parse_args(argv)
    inv = nc.inventory()
    res = {'status': 'passed', 'static': static_part(inv), 'host': nc.host_info()}
    picks = selection(inv, a.graphs)   # checked here too (pure Python): the worker part's kernel count reaches --graphs
    res['static']['worker_selection'] = {f'{s}_L{L}': len(rs) for (s, L), rs in picks.items()}
    print(json.dumps(res['static']), flush=True)
    if not a.no_worker:
        with tempfile.TemporaryDirectory(prefix='c8d3_inspect_check_') as td:
            res['worker'] = worker_part(inv, a.graphs, Path(td))
            print(json.dumps(res['worker']), flush=True)
            res['index'] = index_part(inv, Path(td))
            print(json.dumps(res['index']), flush=True)
    nc.dump(a.output, res)
    print(json.dumps(res, indent=2))


if __name__ == '__main__':
    main()
