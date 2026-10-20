#!/usr/bin/env python3
"""G-RUN1 (PLAN.md A-RPL-7, component F "G-RUN1 tolerance policy"; J-RUN1): a subset of the C7(3) run1 campaign
(symmetry, GCC 11.4) replayed on Expanse (GCC 13.3) as whole tasks from the pinned archive, with three builds on the
same node in the same job: bin/ref/c7d3_gmp (`make c7ref`), bin/c8d3_gmp in order 7 (the archived C7D3TASKS1 rows fed
as they are, HD3) and bin/c8d3_gmp in order 8 (the same rows under a C8D3TASKS1 8 header with gamma_d3_8.txt).

  python3 -B tests/run1_replay.py --archive $C8_STORE/run1-20260930-m4096_full.tgz --sha256 08969c10... \\
      [--per-group 40] [--max-seconds 30] [--seed 20261004] [--threads N] [--work DIR] [--output FILE]

Inputs, each identified before use: the archive by its sha256; per group (20) its config.json (native seed, layout,
rate, net sha256, tasks sha256), sobol.bin (the net; its sha256 must equal the config's), tasks.sqlite (the
config's tasks_sha256 is not re-derived here; the tasks are taken from the archived checkpoint rows, which carry the
task coordinates), the checkpoints (the archived rows) and the lane logs (each checkpoint's host and CPU model:
lanes/logs/idx<N>.<job>.log names the committed checkpoint, lanes/node-<job>.out the node and its CPU). Graph files
are extracted from the packs (tools/members.py; the run1 inputs manifest 5048b336... pinned a6ce987's packs, which
inputs/manifest.json still pins for L3-L7).
Selection: per group, --per-group tasks drawn with --seed (random.Random, sorted rows) among the archived rows whose
row seconds are <= --max-seconds; plus, for power-L7 graphs 228, 1357, 318 and 3754, the 8 rows per campaign with the
largest max_abs.
Gates (the tolerance policy):
  T1 task coordinates and row counts identical, for every build;
  T2 promotion counters (quad, mp) identical in every row; at most 2 mismatched rows per build are accepted, each only
     if `forced_tiers --scan` finds in that row at least as many points whose ld or binary128 test ratio is within a
     factor 1 +- 1e-6 of its threshold as the counters moved; a third mismatch, or one failing that diagnosis, is red;
  T3 values within 1e-10 normalized per row; a row with an accepted T2 mismatch is bounded by 1e-6 instead;
     (order 8: on the common slots, b and c slots 0..7-L);
  T4 the bitwise fraction, reported separately for AMD- and Intel-produced rows;
  T5 c7ref and C8 order 7 give bitwise identical rows (every C7 row field but "seconds"), and C8 order 8's common slots,
     counters and max_abs are bitwise C8 order 7's (this isolates the code change from the toolchain change).
The registered-seed rule (PLAN F, HD6): the selection seed is recorded in the output and registered in $C8_SEEDS
(`tools/seeds.py add --seed S --label ...`), so that no campaign reuses it; the default 20261004 was registered on
2026-10-05 (Stage 3a repair round 1, Expanse job 54672281). A run with another --seed registers it first.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_common as nc  # noqa: E402

RUN = 'run1-20260930-m4096'
HEAVY = (228, 1357, 318, 3754)
ROW_TOL, MISMATCH_TOL = D('1e-10'), D('1e-6')
FORCED = nc.ROOT / 'tests/forced_tiers.cpp'


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def hosts(run: Path) -> dict:
    """{'<group>/<checkpoint stem>': (node, cpu model)} from the lane logs."""
    node = {}
    for f in glob.glob(str(run / 'lanes/node-*.out')):
        m = re.search(r'node (\S+) job (\d+) .*?model name\s*:\s*(.*)', Path(f).read_text())
        if m:
            node[m.group(2)] = (m.group(1), m.group(3).strip())
    out = {}
    for f in glob.glob(str(run / 'lanes/logs/idx*.log')):
        job = re.search(r'idx\d+\.(\d+)\.log', f).group(1)
        for c in re.findall(r'committed (\S+)', Path(f).read_text()):
            out[c] = node.get(job, ('?', '?'))
    return out


def load_group(run: Path, g: str, where: dict) -> tuple[dict, list]:
    cfg = json.loads((run / 'groups' / g / 'config.json').read_text())
    rows = []
    for f in sorted((run / 'groups' / g / 'checkpoints').glob('*.json')):
        d = json.loads(f.read_text())['native']
        key = f'{g}/{f.stem}'
        for r in d['rows']:
            rows.append(dict(r, _ckpt=key, _cpu=where.get(key, ('?', '?'))[1], _threads=d['threads']))
    return cfg, rows


def select(run: Path, per_group: int, max_seconds: float, seed: int, where: dict) -> dict:
    groups = sorted(p.name for p in (run / 'groups').iterdir())
    if len(groups) != 20:
        raise AssertionError(f'{run}: {len(groups)} groups, expected 20')
    rng = random.Random(seed)
    sel = {}
    for g in groups:
        cfg, rows = load_group(run, g, where)
        small = sorted((r for r in rows if r['seconds'] <= max_seconds), key=lambda r: r['uid'])
        pick = {r['uid']: r for r in rng.sample(small, min(per_group, len(small)))}
        if g.endswith('_power_L7'):
            heavy = sorted((r for r in rows if r['graph'] in HEAVY), key=lambda r: -D(r['max_abs']))[:8]
            for r in heavy:
                pick[r['uid']] = dict(r, _heavy=True)
        sel[g] = (cfg, [pick[u] for u in sorted(pick)])
    return sel


def scan(forced: Path, root: Path, L: int, netf: Path, cfg: dict, r: dict) -> int:
    cp = subprocess.run([str(forced), '--scan', str(r['graph']), str(r['rep']), str(r['begin']), str(r['end']), '--', str(root), str(L),
                         str(netf), str(cfg['seed']), str(cfg['layout']), cfg['rate'], '-'], capture_output=True, text=True)
    if cp.returncode:
        raise RuntimeError(f'forced_tiers --scan failed: {cp.stderr[-800:]}')
    return json.loads(cp.stdout.splitlines()[-1])['near_threshold_points']


def compare(arch: list, new: dict, L: int, order: int) -> list:
    """Per archived row: (row, counters_equal, normalized error on the common slots, bitwise)."""
    out = []
    byuid = {r['uid']: r for r in new['rows']}
    if sorted(byuid) != sorted(r['uid'] for r in arch):
        raise AssertionError('T1: the replayed rows are not the selected tasks')
    for a in arch:
        b = byuid[a['uid']]
        if any(a[k] != b[k] for k in ('rep', 'graph', 'begin', 'end', 'total')):
            raise AssertionError(f'T1: task coordinates differ at uid {a["uid"]}')
        av = a['values']
        bv = b['values'] if order == 7 else [b['values'][j] for j in range(8 - L)] + [b['values'][9 - L + j] for j in range(8 - L)]
        if len(av) != 2 * (8 - L) or len(bv) != len(av):
            raise AssertionError(f'T1: widths at uid {a["uid"]}')
        e = max(nc.normalized(u, v) for u, v in zip(av, bv))
        out.append((a, (a['quad'], a['mp']) == (b['quad'], b['mp']), e, av == bv and a['max_abs'] == b['max_abs']))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--archive', type=Path, required=True)
    ap.add_argument('--sha256', required=True)
    ap.add_argument('--per-group', type=int, default=40)
    ap.add_argument('--max-seconds', type=float, default=30.0)
    ap.add_argument('--seed', type=int, default=20261004)
    ap.add_argument('--threads', type=int, default=nc.threads_default())
    ap.add_argument('--parallel', type=int, default=8, help='concurrent worker invocations (threads/parallel threads each)')
    ap.add_argument('--work', type=Path, help='extraction directory (default: a temporary directory under TMPDIR)')
    ap.add_argument('--select-only', action='store_true', help='print the selection and its archived cost, run nothing')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args(argv)
    t0 = time.time()
    if sha(a.archive) != a.sha256:
        raise SystemExit(f'{a.archive}: sha256 differs from {a.sha256}')
    builds = {'c7ref': nc.C7REF['gmp'], 'c8_order7': nc.C8['gmp'], 'c8_order8': nc.C8['gmp']}
    if not a.select_only:
        nc.require(*builds.values())
        probe = nc.check_ref_probe(nc.C7REF['gmp'])
    with tempfile.TemporaryDirectory(prefix='c8d3_run1_', dir=a.work) as td:
        td = Path(td)
        with tarfile.open(a.archive) as tf:
            tf.extractall(td, filter='data') if 'filter' in tarfile.TarFile.extractall.__code__.co_varnames else tf.extractall(td)
        run = td / RUN
        where = hosts(run)
        sel = select(run, a.per_group, a.max_seconds, a.seed, where)
        archived_cost = sum(r['seconds'] for _, rows in sel.values() for r in rows)
        summary = {'selection_seed': a.seed, 'per_group': a.per_group, 'max_seconds': a.max_seconds,
                   'tasks': sum(len(rows) for _, rows in sel.values()), 'archived_row_seconds': round(archived_cost, 1),
                   'heavy_rows': sum(1 for _, rows in sel.values() for r in rows if r.get('_heavy'))}
        print(json.dumps(summary), flush=True)
        if a.select_only:
            nc.dump(a.output, summary)
            return
        forced = td / 'forced_tiers_gmp'
        from common import cxx_command
        subprocess.run(cxx_command([FORCED], forced, defines=('C7_USE_GMP',), libs=('-lquadmath', '-lgmp')), check=True)
        groups_out = {}
        stats = {b: {'rows': 0, 'bitwise': {'AMD': [0, 0], 'Intel': [0, 0], '?': [0, 0]}, 'max_normalized': D(0), 'counter_mismatches': []} for b in builds}
        t5 = {'c7ref_vs_c8_order7_bitwise_rows': 0, 'order8_common_slots_bitwise_rows': 0}
        # Every graph once (members of the packs), then every (group, build) invocation in a pool: --parallel
        # concurrent workers of threads/parallel threads each (rows are bitwise across thread counts, F28).
        need = sorted({(g.split('_')[1], int(g.split('_')[2][1:]), r['graph']) for g, (_, rows) in sel.items() for r in rows})
        per = max(1, a.threads // a.parallel)
        with nc.extracted(need) as root:
            jobs = []
            for g, (cfg, rows) in sel.items():
                L = int(g.split('_')[2][1:])
                netf = run / 'groups' / g / 'sobol.bin'
                if sha(netf) != cfg['net']['sha256']:
                    raise AssertionError(f'{g}: sobol.bin differs from the config net sha256')
                trows = [(r['uid'], r['rep'], r['graph'], r['begin'], r['end'], r['total']) for r in rows]
                gd = td / 'tasks' / g
                gd.mkdir(parents=True)
                nc.write_tasks(gd / 'tasks7', L, trows)
                nc.write_tasks(gd / 'tasks8', L, trows, order=8)
                jobs += [(g, b) for b in builds]

            def go(job):
                g, b = job
                cfg, rows = sel[g]
                sector, L = g.split('_')[1], int(g.split('_')[2][1:])
                order = 8 if b == 'c8_order8' else 7
                gd = td / 'tasks' / g
                out, _ = nc.run_worker(builds[b], root / sector, nc.GAMMA[order], run / 'groups' / g / 'sobol.bin', gd / f'tasks{order}',
                                       gd / f'{b}.json', cfg['seed'], cfg['layout'], cfg['rate'], per)
                if out['seed'] != cfg['seed'] or out['L'] != L:
                    raise AssertionError(f'{g} {b}: metadata')
                return job, out
            # heaviest groups first (power L7 holds the long max_abs rows)
            jobs.sort(key=lambda j: -sum(r['seconds'] for r in sel[j[0]][1]))
            with ThreadPoolExecutor(a.parallel) as ex:
                results = dict(ex.map(go, jobs))
            for g, (cfg, rows) in sel.items():
                sector, L = g.split('_')[1], int(g.split('_')[2][1:])
                netf = run / 'groups' / g / 'sobol.bin'
                outs = {b: results[(g, b)] for b in builds}
                for b in builds:
                    order = 8 if b == 'c8_order8' else 7
                    res = compare(rows, outs[b], L, order)
                    st = stats[b]
                    for row, counters, e, bitwise in res:
                        st['rows'] += 1
                        cpu = 'AMD' if 'AMD' in row['_cpu'] else 'Intel' if 'Intel' in row['_cpu'] else '?'
                        st['bitwise'][cpu][0] += bitwise
                        st['bitwise'][cpu][1] += 1
                        if not counters:
                            near = scan(forced, root / sector, L, netf, cfg, row)
                            new = next(x for x in outs[b]['rows'] if x['uid'] == row['uid'])
                            moved = abs(new['quad'] - row['quad']) + abs(new['mp'] - row['mp'])
                            st['counter_mismatches'].append(dict(group=g, uid=row['uid'], archived=[row['quad'], row['mp']], replayed=[new['quad'], new['mp']],
                                                                 near_threshold_points=near, moved=moved, normalized=str(e), accepted=near >= moved and e <= MISMATCH_TOL))
                        elif e > ROW_TOL:
                            raise AssertionError(f'T3 {b} {g} uid {row["uid"]}: normalized difference {e} > {ROW_TOL}')
                        st['max_normalized'] = max(st['max_normalized'], e)
                # T5
                e = nc.rows_equal(outs['c7ref'], outs['c8_order7'], nc.C7_ROW_FIELDS)
                if e:
                    raise AssertionError(f'T5 {g}: c7ref and C8 order 7 differ: {e}')
                t5['c7ref_vs_c8_order7_bitwise_rows'] += len(rows)
                for x, y in zip(outs['c8_order7']['rows'], outs['c8_order8']['rows'], strict=True):
                    common = [y['values'][j] for j in range(8 - L)] + [y['values'][9 - L + j] for j in range(8 - L)]
                    if common != x['values'] or (x['quad'], x['mp'], x['max_abs']) != (y['quad'], y['mp'], y['max_abs']):
                        raise AssertionError(f'T5 {g} uid {x["uid"]}: order 8 common slots differ from order 7')
                t5['order8_common_slots_bitwise_rows'] += len(rows)
                groups_out[g] = {'rows': len(rows), 'graphs': len({r['graph'] for r in rows}),
                                 'archived_row_seconds': round(sum(r['seconds'] for r in rows), 1)}
                print(f'{g}: {len(rows)} rows compared ({time.strftime("%H:%M:%S")})', flush=True)
    for b, st in stats.items():
        mm = st['counter_mismatches']
        if len(mm) > 2 or not all(m['accepted'] for m in mm):
            raise AssertionError(f'T2 {b}: counter mismatches {mm}')
    res = dict(status='passed', summary=summary, groups=groups_out, ref_probe=probe, host=nc.host_info(), threads=a.threads, parallel=a.parallel,
               builds={b: {'path': str(e), 'sha256': nc.digest(e)} for b, e in builds.items()},
               T1='coordinates and row counts identical (all builds)',
               T2={b: st['counter_mismatches'] for b, st in stats.items()},
               T3={b: {'max_normalized': str(st['max_normalized']), 'tolerance': str(ROW_TOL)} for b, st in stats.items()},
               T4={b: {cpu: {'bitwise': v[0], 'rows': v[1], 'fraction': (v[0] / v[1]) if v[1] else None} for cpu, v in st['bitwise'].items()} for b, st in stats.items()},
               T5=t5, archive={'path': str(a.archive), 'sha256': a.sha256}, wall_seconds=round(time.time() - t0, 1))
    nc.dump(a.output, res)
    print(json.dumps({k: v for k, v in res.items() if k != 'groups'}, indent=2, default=str))


if __name__ == '__main__':
    main()
