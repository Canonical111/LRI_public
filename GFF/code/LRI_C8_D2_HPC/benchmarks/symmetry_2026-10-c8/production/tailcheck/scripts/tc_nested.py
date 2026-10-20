#!/usr/bin/env python3
"""Tail check, part B: fresh nested-N runs of selected L8 graphs with the production executable (read-only on the
export; writes only RUNDIR).

  tc_nested.py --pkg EXPORT --rundir RUNDIR --graphs LIST --seed S [--reps 32] [--chunk 4096] [--threads 64] [--only c_s]

LIST lines: "<sector> <L> <graph> <nmax>" (nmax a power of two, the largest prefix). Both campaigns run every graph:
a (rate .8, 52-bit net) and b (rate .9, 60-bit net), as the production groups (tools/production.py: derive_seeds(S, c,
s, L) gives the native digital-shift seed and the net seed; make_net writes R independently scrambled Sobol matrices;
layout 0, sum_mode compensated, the gamma file of the export, the export's gated dd+mp256 executable, checked by
sha256). Each graph-replicate's points [0, nmax) are cut into rows of --chunk points, so every prefix [0, N) with N a
multiple of the chunk is an exact sub-estimate of the same scramble: prefix mean = (nmax / N) sum of its rows' values,
prefix tails = the union of its rows' tail fields (exact for the top 16). One native call per (campaign, graph); its
output is published by rename, so a rerun skips finished calls (requeue-safe)."""
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--pkg', type=Path, required=True)
ap.add_argument('--rundir', type=Path, required=True)
ap.add_argument('--graphs', type=Path, required=True)
ap.add_argument('--seed', type=int, required=True)
ap.add_argument('--reps', type=int, default=32)
ap.add_argument('--chunk', type=int, default=4096)
ap.add_argument('--threads', type=int, default=64)
ap.add_argument('--only', default=None, help='comma list of <campaign>_<sector> to run (default all)')
ap.add_argument('--setup-only', action='store_true')
a = ap.parse_args()
sys.path.insert(0, str(a.pkg / 'tools'))
import production as prod  # noqa: E402

EXE_SHA = 'a46f3060a27f4d5e3af19023fc5bb67a7ca2dc6c4242e671ef4bdb9427254c8c'
RATES = {'a': '.8', 'b': '.9'}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


R = a.rundir; R.mkdir(parents=True, exist_ok=True); (R / 'out').mkdir(exist_ok=True); (R / 'tasks').mkdir(exist_ok=True)
items = []
for line in a.graphs.read_text().splitlines():
    if line.strip() and not line.startswith('#'):
        s, L, g, n = line.split()[:4]; items.append((s, int(L), int(g), int(n)))
exe = a.pkg / 'bin' / 'c8d2_gmp_dd+mp256'
gamma = a.pkg / 'inputs' / 'gamma_d2_8.txt'
setup_f = R / 'setup.json'
if not setup_f.exists():
    if sha(exe) != EXE_SHA:
        raise SystemExit(f'{exe}: sha256 is not the gated build {EXE_SHA}')
    inv = json.loads((a.pkg / 'inputs' / 'inventory.json').read_bytes())
    members = {}
    for s, L, g, n in items:
        if n % a.chunk or n & (n - 1):
            raise SystemExit(f'nmax {n} of {s} G{g} is not a power-of-two multiple of the chunk')
        r = next(x for x in inv[s][str(L)] if x['id'] == g)
        with open(a.pkg / 'inputs' / 'packs' / f'{s}_L{L}.pack', 'rb') as f:
            f.seek(r['offset']); data = f.read(r['length'])
        if hashlib.sha256(data).hexdigest() != r['sha256']:
            raise SystemExit(f'{s} L{L} G{g}: member sha256 mismatch')
        d = R / f'graphs_{s}' / f'L{L}'; d.mkdir(parents=True, exist_ok=True)
        (d / f'G{g}.txt').write_bytes(data); members[f'{s}/L{L}/G{g}'] = r['sha256']
    nets = {}
    for c in ('a', 'b'):
        for s in sorted({x[0] for x in items}):
            seeds = prod.derive_seeds(a.seed, c, s, 8)
            top = max(n for ss, L, g, n in items if ss == s)
            info = prod.make_net(R / f'net_{c}_{s}.bin', a.reps, 4 * 8 - 1, prod.NET_BITS[c], seeds['net'], top)
            nets[f'{c}_{s}'] = dict(seeds=seeds, net=info)
    doc = dict(schema='c8-d2-tailcheck-nested-1', seed=a.seed, reps=a.reps, chunk=a.chunk, executable=str(exe), executable_sha256=EXE_SHA,
               gamma_sha256=sha(gamma), inventory_sha256=sha(a.pkg / 'inputs' / 'inventory.json'), members=members, nets=nets,
               rates=RATES, layout=0, sum_mode='compensated', items=items, created=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    setup_f.write_text(json.dumps(doc, indent=1))
    print(f'setup written: {len(items)} graphs, nets {list(nets)}', flush=True)
setup = json.loads(setup_f.read_text())
if setup['seed'] != a.seed or setup['reps'] != a.reps or setup['chunk'] != a.chunk:
    raise SystemExit('setup.json was written with other arguments')
if a.setup_only:
    sys.exit(0)
if sha(exe) != EXE_SHA:
    raise SystemExit('executable changed')
only = set(a.only.split(',')) if a.only else None
env = dict(os.environ, OMP_NUM_THREADS=str(a.threads), OMP_PROC_BIND='spread', OMP_PLACES='cores')
log = (R / 'calls.jsonl').open('a')
for c in ('a', 'b'):
    # heaviest graphs first is irrelevant here: the calls run one after another with all threads
    for s, L, g, n in items:
        if only and f'{c}_{s}' not in only:
            continue
        out = R / 'out' / f'{c}_{s}_L{L}_G{g}.json'
        if out.exists():
            continue
        tasks = R / 'tasks' / f'{c}_{s}_L{L}_G{g}.txt'
        rows = [(rep, b) for rep in range(a.reps) for b in range(0, n, a.chunk)]
        with tasks.open('w') as f:
            f.write(f'C8D2TASKS1 8 {L} {len(rows)}\n')
            for uid, (rep, b) in enumerate(rows):
                f.write(f'{uid} {rep} {g} {b} {b + a.chunk} {n}\n')
        tmp = out.with_suffix('.tmp')
        seed_native = setup['nets'][f'{c}_{s}']['seeds']['native']
        cmd = [str(exe), str(R / f'graphs_{s}'), str(gamma), str(R / f'net_{c}_{s}.bin'), str(tasks), str(tmp), str(seed_native), '0', RATES[c],
               str(a.threads), 'compensated', '-']
        t0 = time.time()
        p = subprocess.run(cmd, env=env, capture_output=True, text=True)
        dt = time.time() - t0
        rec = dict(campaign=c, sector=s, L=L, graph=g, nmax=n, reps=a.reps, rows=len(rows), exit=p.returncode, wall_s=dt, stderr=p.stderr[-500:],
                   host=os.uname().nodename, utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        log.write(json.dumps(rec) + '\n'); log.flush()
        print(json.dumps(rec), flush=True)
        if p.returncode != 0:
            raise SystemExit(f'native call failed: {rec}')
        os.replace(tmp, out)
print('all calls done', flush=True)
