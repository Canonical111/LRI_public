"""Split sectors into contiguous chunks of about equal measured cost.
usage: python m3_chunks.py NCHUNKS timing.err [timing.err ...]   (engine stderr lines 'sector N done T s')
prints 's0 s1' per chunk."""
import sys, re
nch = int(sys.argv[1])
t = {}
for f in sys.argv[2:]:
    for line in open(f):
        m = re.match(r'sector (\d+) done ([\d.]+)s', line)
        if m: t[int(m.group(1))] = float(m.group(2))
ns = max(t) + 1
cost = [t.get(s, max(t.values())) for s in range(ns)]
tot = sum(cost); target = tot / nch
bounds, acc, s0 = [], 0.0, 0
for s in range(ns):
    acc += cost[s]
    if acc >= target * (len(bounds) + 1) and len(bounds) < nch - 1:
        bounds.append((s0, s + 1)); s0 = s + 1
bounds.append((s0, ns))
for a, b in bounds: print(a, b, round(sum(cost[a:b]), 1))
