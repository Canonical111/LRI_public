#!/usr/bin/env python3
"""Compare re-run production job indices with run1's checkpoints (make -f public.mk smoke).

    python3 public/compare_smoke.py NEW_RUN OLD_RUN INDEX [INDEX ...]

NEW_RUN is a fresh plan of the production commit with run1's seed and flags (public.mk smoke), in which the listed job
indices were run; OLD_RUN is run1's directory from the hosted run1-20260930-m4096_full.tgz. The same procedure (re-plan
with the same seed and flags, run indices, compare checkpoint rows) was the AMD-vs-Intel check of 2026-09-30 (job
566410).

PASS requires, for every index: the same group and shard; identical group plans (seed, layout, rate, replicates, counts,
shards, tasks, samples) and an identical Sobol net (sha256; it depends on the SciPy version, run1 used 1.17.1); every
checkpoint of the shard present with the same task coordinates (uid, rep, graph, begin, end, total) and the same
binary128 and GMP promotion counts; values bit for bit or within 1e-10 normalized, |new-old|/max(1,|old|) (run1 mixed
AMD EPYC 7532/7543/8534P and Intel Gold 6148 nodes; across CPU types rows differ by up to 2.0e-11). The share of bitwise
rows is reported. Exits 1 on FAIL.
"""
import json, sys
from decimal import Decimal as D
from pathlib import Path

new, old = Path(sys.argv[1]), Path(sys.argv[2])
idxs = [int(x) for x in sys.argv[3:]]
load = lambda p: json.loads(Path(p).read_text())
mn, mo = load(new / 'manifest.json'), load(old / 'manifest.json')
fails, rows_total, bitwise, worst = [], 0, 0, D(0)
for i in idxs:
    jn, jo = mn['jobs'][i], mo['jobs'][i]
    if (jn['group'], jn['shard']) != (jo['group'], jo['shard']):
        fails.append(f'index {i}: job {jn} differs from run1 {jo}')
        continue
    g, s = jn['group'], jn['shard']
    cn, co = load(new / 'groups' / g / 'config.json'), load(old / 'groups' / g / 'config.json')
    for k in ('seed', 'layout', 'rate', 'replicates', 'counts', 'shards', 'tasks', 'samples', 'sum_mode', 'primitive_mode'):
        if cn[k] != co[k]:
            fails.append(f'{g}: config {k} differs')
    if cn['net']['sha256'] != co['net']['sha256']:
        fails.append(f"{g}: Sobol net differs (SciPy {cn['net']['scipy']} vs run1 {co['net']['scipy']}); install scipy=={co['net']['scipy']}")
        continue
    olds = sorted((old / 'groups' / g / 'checkpoints').glob(f's{s:06d}_p*.json'))
    if not olds:
        fails.append(f'{g}: run1 has no checkpoints for shard {s}')
    for fo in olds:
        fn = new / 'groups' / g / 'checkpoints' / fo.name
        if not fn.exists():
            fails.append(f'{g}/{fo.name}: not produced')
            continue
        a, b = load(fo)['native']['rows'], load(fn)['native']['rows']
        if len(a) != len(b):
            fails.append(f'{g}/{fo.name}: {len(b)} rows, run1 {len(a)}')
            continue
        for x, y in zip(a, b):
            rows_total += 1
            if any(x[k] != y[k] for k in ('uid', 'rep', 'graph', 'begin', 'end', 'total')):
                fails.append(f'{g}/{fo.name} uid {x["uid"]}: task coordinates differ')
                continue
            if (x['quad'], x['mp']) != (y['quad'], y['mp']):
                fails.append(f'{g}/{fo.name} uid {x["uid"]}: promotion counts differ')
            if x['values'] == y['values']:
                bitwise += 1
            else:
                e = max(abs(D(u) - D(v)) / max(D(1), abs(D(u))) for u, v in zip(x['values'], y['values']))
                worst = max(worst, e)
    print(f'index {i}: {g} shard {s}: {len(olds)} checkpoint file(s) compared')
if worst > D('1e-10'):
    fails.append(f'largest normalized difference {float(worst):.2e} > 1e-10')
for f in fails[:40]:
    print('FAIL', f)
print(f'rows {rows_total}, bitwise {bitwise}, largest normalized difference {float(worst):.2e}')
print('smoke:', 'FAIL' if fails or not rows_total else 'PASS')
sys.exit(1 if fails or not rows_total else 0)
