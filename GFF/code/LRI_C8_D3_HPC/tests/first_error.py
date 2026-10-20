#!/usr/bin/env python3
"""R5a's error check (Stage 4b, PLAN C.6: "errors collected as in the integration loop"; port of C62d's
r5a_first_error.py, LRI_C8_D2_HPC@3453e5b benchmarks/expanse_2026-10-c8/stage4b/dev_r5/scripts/): the parallel graph
loading of src/c8d3_integrate.cpp reports the same error as the serial loading of the Stage-3 baseline, whatever the
thread count and timing, and loads a valid block identically. Expanse; needs `make gmp decimal baseline`.

  python3 -B tests/first_error.py --baseline bin/baseline [--repeats 5] [--threads 1,2,4,8,16] [--output FILE]

The eight costliest free L4 kernels (staged from the pinned pack and checked against the inventory sha256) form one block
of 2 replicates x 64 points (order 8, rate .8, layout 0, the 60-bit net of seed 4242, native seed validate.SEED, both
registered test seeds, HD6). In each case some G-files are made bad: truncated inside the rate table (the reader's
"truncated or malformed rate ..."), missing ("cannot open the graph file") or with another id in the header ("graph
identity mismatch"), always at more than one id except in `last_only`, so that the lowest bad id's error is the one the
serial loop throws first. Each case runs the baseline once at 1 thread and the candidate bin/c8d3_<backend> at every
--threads value --repeats times: every candidate run must exit 2 with stderr byte-identical to the baseline's and write
no output. The all-valid case must give rows identical to the baseline's in every field but "seconds" and the same
graphs_loaded. Both backends."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_common as nc  # noqa: E402
from validate import SEED  # noqa: E402

NET_SEED = 4242
CASES = (('valid', {}), ('truncated_then_identity', {2: 'truncated', 5: 'identity'}),
         ('missing_then_truncated', {1: 'missing', 3: 'truncated', 6: 'identity'}),
         ('identity_then_missing', {0: 'identity', 7: 'missing'}), ('last_only', {7: 'identity'}))


def bad_file(p: Path, kind: str) -> None:
    if kind == 'truncated':
        t = p.read_text().split()
        p.write_text(' '.join(t[:len(t) - 7]) + '\n')           # cut inside the rate table
    elif kind == 'missing':
        p.unlink()
    elif kind == 'identity':
        t = p.read_text().split(' ', 3)                          # header: magic L id ...
        t[2] = str(int(t[2]) + 1000000)
        p.write_text(' '.join(t))
    else:
        raise ValueError(kind)


def cmd(exe, root, netf, tasks, out, threads):
    return [str(exe), str(root), str(nc.GAMMA[8]), str(netf), str(tasks), str(out), str(SEED), '0', '.8', str(threads), 'compensated', '-',
            '--mp-check', 'on']


def run(c, out: Path):
    out.unlink(missing_ok=True)
    p = subprocess.run(c, capture_output=True, text=True, errors='replace')
    d = json.loads(out.read_text()) if out.exists() else None
    out.unlink(missing_ok=True)
    return p.returncode, p.stderr, d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--baseline', type=Path, required=True)
    ap.add_argument('--repeats', type=int, default=5)
    ap.add_argument('--threads', default='1,2,4,8,16')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args(argv)
    threads = [int(x) for x in a.threads.split(',')]
    old = {b: a.baseline.resolve() / f'c8d3_{b}' for b in nc.C8}
    nc.require(*nc.C8.values(), *old.values())
    inv = nc.inventory()
    L = 4
    ids = sorted(r['id'] for r in sorted(inv['free'][str(L)], key=lambda r: -r['cost'])[:8])
    t0 = time.time()
    rec = {'schema': 'c8-d3-first-error-1', 'graphs': ids, 'L': L, 'sector': 'free', 'points': 64, 'replicates': 2, 'threads': threads,
           'repeats': a.repeats, 'seed': SEED, 'net_seed': NET_SEED, 'baseline': {b: nc.digest(e) for b, e in old.items()},
           'candidate': {b: nc.digest(e) for b, e in nc.C8.items()}, 'cases': []}
    ok = True
    with tempfile.TemporaryDirectory(prefix='c8d3_first_error_') as td, nc.extracted([('free', L, g) for g in ids]) as clean:
        td = Path(td)
        netf = nc.net(td, nc.dim_of(L, 0), 60, NET_SEED)
        tasks = nc.write_tasks(td / 'tasks', L, nc.task_rows(ids, reps=2, points=64), order=8)
        out = td / 'out.json'
        for name, bad in CASES:
            root = td / name
            shutil.copytree(clean / 'free', root)
            for pos, kind in bad.items():
                bad_file(root / f'L{L}' / f'G{ids[pos]}.txt', kind)
            for b in nc.C8:
                code0, err0, d0 = run(cmd(old[b], root, netf, tasks, out, 1), out)
                rows0 = [nc.scientific(r) for r in d0['rows']] if d0 else None
                c = {'case': name, 'backend': b, 'bad': {str(ids[p]): k for p, k in bad.items()}, 'baseline_exit': code0,
                     'baseline_stderr': err0.strip()[-400:], 'runs': 0, 'mismatches': []}
                if bad and (code0 != 2 or d0 is not None):
                    c['mismatches'].append(f'baseline: exit {code0}, wrote output {d0 is not None}')
                if not bad and code0 != 0:
                    c['mismatches'].append(f'baseline failed on the valid block: {err0[-300:]}')
                for th in threads:
                    for k in range(a.repeats):
                        code, err, d = run(cmd(nc.C8[b], root, netf, tasks, out, th), out)
                        c['runs'] += 1
                        if bad:
                            if code != 2 or d is not None or err != err0:
                                c['mismatches'].append({'threads': th, 'repeat': k, 'exit': code, 'wrote': d is not None, 'stderr': err.strip()[-400:]})
                        elif code != 0 or d is None or [nc.scientific(r) for r in d['rows']] != rows0 or d['graphs_loaded'] != d0['graphs_loaded']:
                            c['mismatches'].append({'threads': th, 'repeat': k, 'exit': code, 'stderr': err.strip()[-400:]})
                if not bad and d0:
                    c['rows'] = len(rows0)
                    c['graphs_loaded'] = d0['graphs_loaded']
                c['passed'] = not c['mismatches']
                ok &= c['passed']
                rec['cases'].append(c)
                print(f"{name} {b}: {'passed' if c['passed'] else 'FAILED'} ({c['runs']} candidate runs); baseline: {c['baseline_stderr'][-160:]!r}", flush=True)
    rec['status'] = 'passed' if ok else 'failed'
    rec['wall_seconds'] = round(time.time() - t0, 1)
    nc.dump(a.output, rec)
    print(json.dumps({'status': rec['status'], 'cases': len(rec['cases']), 'wall_seconds': rec['wall_seconds']}))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
