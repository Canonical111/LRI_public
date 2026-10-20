#!/usr/bin/env python3
"""A-RPL-6 (PLAN.md; J-VAL-3, Stage 3b): the scientific fields do not depend on threads, lane processes, chunking or
layout. Expanse (an exclusive compute node: 128 cores, 8 NUMA domains of 16); needs `make gmp decimal`.

  python3 -B tests/thread_identity.py [--threads-list 1,16,64,128] [--splits numa,numa:2,numa:4] [--backends gmp,decimal]
                                      [--parts blocks,chunks] [--output FILE]

blocks  An L8 free and an L8 power block, 64 tasks x 256 points each (32 kernels drawn with random.Random(SEED) x 2
        replicates; whole tasks), order 8, rate .8 and a 52-bit net (campaign a's), layout 0, --mp-check on, both
        backends:
        (i) threads: the block run at 1, 16, 64 and 128 threads gives identical scientific fields (every row field
            but "seconds"; the header fields that do not describe the run's threads, timing, memory or loaded-graph
            count) to the 1-thread run;
        (ii) lane processes: the block cut into P contiguous parts of 64/P tasks, run as P concurrent worker
            processes, each pinned to its lane's cores (tools/lanes.cpu_lanes: numa = 8 x 16, numa:2 = 4 x 32,
            numa:4 = 2 x 64 on the J-E0 layout; 32 x 4 only on 4-core NUMA domains, so not on Expanse) with as many
            threads as cores and its own fresh output; the concatenated rows equal the 1-thread rows.
chunks  Chunk splits and layouts at L7 and L8: per (sector, L) the heaviest kernel and one drawn kernel, 2 replicates
        x 256 points, order 8, rate .7 and 60-bit nets (campaign b's), layouts 0, 1 and 2, both backends: the
        23-point chunks (one worker run) summed per (replicate, graph) agree with the whole tasks to <= 1e-12
        normalized (|x - y| / max(1, |x|), Decimal), and their quad and mp counters add up to the whole task's.
Every executable writes a distinct, pre-deleted output in a temporary directory; nothing is written into the package
unless --output. Seeds (HD6, registered before use): native SEED, net seeds 880600 + L (blocks) and
880700 + L + 10 * layout (chunks), the draw seed SEED.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_common as nc  # noqa: E402
import lanes  # noqa: E402  (tools/lanes.py)

SEED = 8806401
RESULTS: list[dict] = []
# Header fields that describe the run rather than the science (threads, timing, memory, how many graphs were loaded).
RUN_FIELDS = {'threads', 'load_seconds', 'integration_seconds', 'graphs_loaded', 'max_rss_kb', 'max_rss_source', 'rusage_maxrss_kb', 'rows', '_wall'}


def record(**kw):
    RESULTS.append(kw)
    print(json.dumps(kw, default=str), flush=True)


def header(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in RUN_FIELDS}


def rows_of(d: dict) -> list:
    return sorted((nc.scientific(r) for r in d['rows']), key=lambda r: r['uid'])


def worker_cmd(exe, root, netf, tasks, out, layout, rate, threads, mp_check='on'):
    return [str(exe), str(root), str(nc.GAMMA[8]), str(netf), str(tasks), str(out), str(SEED), str(layout), str(rate), str(threads),
            'compensated', '-', '--mp-check', mp_check]


def part_blocks(td: Path, a):
    inv = nc.inventory()
    if '8' not in inv['free']:
        raise AssertionError('thread_identity blocks: no L8 kernels in the inventory (Stage 2b inputs needed)')
    rng = random.Random(SEED)
    L = 8
    netf = nc.net(td, nc.dim_of(L, 0), 52, 880600 + L)
    try:
        cpus = sorted(os.sched_getaffinity(0))
    except AttributeError:
        cpus = list(range(os.cpu_count() or 1))
    shapes = {}
    for spec in a.splits:
        try:
            shapes[spec] = lanes.cpu_lanes(cpus, spec)
        except Exception as e:  # noqa: BLE001  (recorded: a shape this node cannot form)
            shapes[spec] = e
    nodes = lanes.numa_nodes()
    four_core = bool(nodes) and all(len(v) == 4 for v in nodes.values())
    out = {}
    for s in nc.SECTORS:
        ids = sorted(rng.sample([r['id'] for r in inv[s][str(L)]], 32))
        rows = nc.task_rows(ids, reps=2, points=256)
        assert len(rows) == 64
        t = nc.write_tasks(td / f'block_{s}.tasks', L, rows, order=8)
        with nc.extracted([(s, L, g) for g in ids]) as root:
            for b in a.backends:
                exe = nc.C8[b]
                runs = {}
                for th in a.threads_list:
                    o = td / f'blk_{s}_{b}_t{th}.json'
                    t0 = time.time()
                    runs[th], _ = nc.run_worker(exe, root / s, nc.GAMMA[8], netf, t, o, SEED, 0, '.8', th, mp_check='on')
                    runs[th]['_wall'] = time.time() - t0
                ref = runs[a.threads_list[0]]
                for th, d in runs.items():
                    if header(d) != header(ref) or rows_of(d) != rows_of(ref):
                        diff = [k for k in set(header(d)) | set(header(ref)) if header(d).get(k) != header(ref).get(k)]
                        raise AssertionError(f'A-RPL-6 {s} L8 {b}: {th} threads differ from {a.threads_list[0]} (header {diff}; '
                                             f'rows {nc.rows_equal(ref, d, [k for k in ref["rows"][0] if k != "seconds"])})')
                split = {}
                for spec, lane_cpus in shapes.items():
                    if isinstance(lane_cpus, Exception):
                        split[spec] = f'not formed: {lane_cpus}'
                        continue
                    P = len(lane_cpus)
                    if 64 % P:
                        split[spec] = f'{P} lanes do not divide 64 tasks; skipped'
                        continue
                    procs = []
                    for k, lc in enumerate(lane_cpus):
                        part = rows[k * 64 // P:(k + 1) * 64 // P]
                        tp = nc.write_tasks(td / f'split_{s}_{b}_{k}.tasks', L, part, order=8)
                        op = td / f'split_{s}_{b}_{spec.replace(":", "_")}_{k}.json'
                        op.unlink(missing_ok=True)
                        env = {**os.environ, 'OMP_NUM_THREADS': str(len(lc)), 'OMP_PROC_BIND': 'close', 'OMP_PLACES': 'cores'}

                        def pin(c=lc):
                            os.sched_setaffinity(0, c)
                        procs.append((op, subprocess.Popen(worker_cmd(exe, root / s, netf, tp, op, 0, '.8', len(lc)), stdout=subprocess.PIPE,
                                                           stderr=subprocess.PIPE, text=True, env=env, preexec_fn=pin)))
                    got = []
                    for op, pr in procs:
                        so, se = pr.communicate()
                        if pr.returncode:
                            raise RuntimeError(f'lane split {spec} {s} {b}: worker failed ({pr.returncode}): {se[-1500:]}')
                        d = json.loads(op.read_text())
                        op.unlink()
                        if header(d) != header(ref):
                            raise AssertionError(f'A-RPL-6 {s} L8 {b} split {spec}: header fields differ')
                        got += d['rows']
                    if sorted((nc.scientific(r) for r in got), key=lambda r: r['uid']) != rows_of(ref):
                        raise AssertionError(f'A-RPL-6 {s} L8 {b}: the {spec} lane split ({P} x {len(lane_cpus[0])}) differs from the 1-thread rows')
                    split[spec] = {'lanes': P, 'cores_per_lane': sorted({len(c) for c in lane_cpus})}
                out[f'{s}_{b}'] = {'kernels': ids, 'tasks': 64, 'points': 256, 'rows': len(ref['rows']), 'mp_points': sum(r['mp'] for r in ref['rows']),
                                   'quad_points': sum(r['quad'] for r in ref['rows']),
                                   'threads': {str(th): round(d['_wall'], 2) for th, d in runs.items()}, 'splits': split}
    record(test='A-RPL-6 threads and lane processes (L8 blocks)', gate='identical scientific fields at every thread count and lane split',
           threads=a.threads_list, numa_nodes=len(nodes), numa_sizes=sorted({len(v) for v in nodes.values()}),
           four_core_domains=four_core, split_32x4='run' if four_core else 'not applicable (no 4-core NUMA domains)', blocks=out)


def part_chunks(td: Path, a):
    inv = nc.inventory()
    rng = random.Random(SEED + 1)
    worst, n = D(0), 0
    res = {}
    for L in [L for L in (7, 8) if str(L) in inv['free']]:
        for s in nc.SECTORS:
            rows = inv[s][str(L)]
            heavy = max(rows, key=lambda r: (r['cost'], r['id']))['id']
            other = rng.choice([r['id'] for r in rows if r['id'] != heavy])
            ids = sorted({heavy, other})
            with nc.extracted([(s, L, g) for g in ids]) as root:
                for layout in (0, 1, 2):
                    netf = nc.net(td, nc.dim_of(L, layout), 60, 880700 + L + 10 * layout)
                    whole_t = nc.write_tasks(td / 'c_whole', L, nc.task_rows(ids, points=256), order=8)
                    chunk_t = nc.write_tasks(td / 'c_chunk', L, nc.task_rows(ids, points=256, chunk=23), order=8)
                    for b in a.backends:
                        whole, _ = nc.run_worker(nc.C8[b], root / s, nc.GAMMA[8], netf, whole_t, td / 'cw.json', SEED, layout, '.7', a.threads)
                        many, _ = nc.run_worker(nc.C8[b], root / s, nc.GAMMA[8], netf, chunk_t, td / 'cc.json', SEED, layout, '.7', a.threads)
                        sums, cnt = {}, {}
                        for r in many['rows']:
                            k = (r['rep'], r['graph'])
                            sums[k] = [x + D(v) for x, v in zip(sums.get(k, [D(0)] * len(r['values'])), r['values'])]
                            c = cnt.setdefault(k, [0, 0])
                            c[0] += r['quad']
                            c[1] += r['mp']
                        e = D(0)
                        for r in whole['rows']:
                            k = (r['rep'], r['graph'])
                            e = max(e, max(nc.normalized(v, str(z)) for v, z in zip(r['values'], sums[k])))
                            if cnt[k] != [r['quad'], r['mp']]:
                                raise AssertionError(f'A-RPL-6 chunks {b} {s} L{L} layout {layout} graph {r["graph"]}: counters {cnt[k]} vs whole {r["quad"]},{r["mp"]}')
                        if e > D('1e-12'):
                            raise AssertionError(f'A-RPL-6 chunks {b} {s} L{L} layout {layout}: {e} normalized > 1e-12')
                        worst = max(worst, e)
                        n += 1
                        res[f'{s}_L{L}_layout{layout}_{b}'] = f'{e:.3e}'
    record(test='A-RPL-6 chunk splits (23 points) and layouts 0/1/2 at L7 and L8', gate='<= 1e-12 normalized; quad and mp counters add up',
           comparisons=n, max_normalized=f'{worst:.3e}', per_case=res, backends=a.backends)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--threads-list', default='1,16,64,128')
    ap.add_argument('--splits', default='numa,numa:2,numa:4', help='tools/lanes.py shapes of the lane-process splits')
    ap.add_argument('--backends', default='gmp,decimal')
    ap.add_argument('--parts', default='blocks,chunks')
    ap.add_argument('--threads', type=int, default=nc.threads_default(), help='threads of the chunk part')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args(argv)
    a.threads_list = [int(x) for x in a.threads_list.split(',')]
    a.splits = [x for x in a.splits.split(',') if x]
    a.backends = [x for x in a.backends.split(',') if x]
    if a.threads_list[0] != 1 or set(a.backends) - set(nc.C8):
        ap.error('--threads-list starts at 1 (the reference); --backends takes gmp and decimal')
    nc.require(*(nc.C8[b] for b in a.backends))
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix='c8d3_threads_') as td:
        td = Path(td)
        for p in a.parts.split(','):
            {'blocks': part_blocks, 'chunks': part_chunks}[p](td, a)
    res = dict(status='passed', parts=a.parts.split(','), tests=RESULTS, host=nc.host_info(), seed=SEED,
               sha256={str(nc.C8[b]): nc.digest(nc.C8[b]) for b in a.backends}, wall_seconds=round(time.time() - t0, 1))
    nc.dump(a.output, res)
    print(json.dumps({k: v for k, v in res.items() if k != 'tests'}, indent=2))


if __name__ == '__main__':
    main()
