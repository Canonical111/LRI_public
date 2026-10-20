#!/usr/bin/env python3
"""Size-class launch plans for run_pack.py --plan (FIT_MODEL_3D D2/§5.2; 3D defaults: --lbig 128 --slot-big 32). Array A = the L = LBIG chains in slots of SLOT_BIG chains; array B =
the remaining chains LPT-balanced (N × sweeps) into NSLOT_SMALL slots. Plan files are named by their parameters and never overwritten
(FIT2D-009). --only-s restricts to one point (per-point extension, §5.4)."""
import argparse, heapq, json
from pathlib import Path
p = argparse.ArgumentParser(description=__doc__); p.add_argument('campaign', type=Path); p.add_argument('--lbig', type=int, default=128)
p.add_argument('--slot-big', type=int, default=32); p.add_argument('--nslot-small', type=int, default=4); p.add_argument('--only-s', type=float)
p.add_argument('--tag', default=''); a = p.parse_args()
mf = json.loads((a.campaign / 'manifest.json').read_text()); tasks = [t for t in mf['tasks'] if a.only_s is None or abs(t['s'] - a.only_s) < 1e-10]
if not tasks: raise SystemExit('no tasks selected')
big = [t['id'] for t in tasks if t['L'] == a.lbig]; small = [t for t in tasks if t['L'] != a.lbig]
slots_big = [big[i:i + a.slot_big] for i in range(0, len(big), a.slot_big)]
heap = [(0, i) for i in range(a.nslot_small)]; slots_small = [[] for _ in range(a.nslot_small)]
for t in sorted(small, key=lambda t: t['N'] * (t['measurements'] + t['warmup']), reverse=True):
    w, i = heapq.heappop(heap); slots_small[i].append(t['id']); heapq.heappush(heap, (w + t['N'] * (t['measurements'] + t['warmup']), i))
slots_small = [s for s in slots_small if s]
suffix = (f'_s{a.only_s:g}' if a.only_s is not None else '') + (f'_{a.tag}' if a.tag else '')
(a.campaign / 'logs').mkdir(exist_ok=True); written = []
for name, slots in ((f'plan_big_{a.slot_big}x{len(slots_big)}{suffix}.json', slots_big), (f'plan_small_{len(slots_small)}{suffix}.json', slots_small)):
    if not slots: continue
    f = a.campaign / 'logs' / name
    try:   # FIT3D-006: exclusive creation — two concurrent invocations cannot both write the same plan
        with open(f, 'x') as fh: fh.write(json.dumps(dict(campaign_id=mf['campaign_id'], shards=1, shard=0, slots=slots), indent=1) + '\n')
    except FileExistsError: raise SystemExit(f'{f} exists: launch plans are immutable (a queued job may read it); choose another --tag')
    written.append(str(f)); print(name, 'slots', [len(s) for s in slots])
ids = sorted(i for s in slots_big + slots_small for i in s); assert ids == sorted(t['id'] for t in tasks), 'plans do not partition the selected tasks'
print('partition check ok:', len(ids), 'chains'); print(json.dumps(written))
