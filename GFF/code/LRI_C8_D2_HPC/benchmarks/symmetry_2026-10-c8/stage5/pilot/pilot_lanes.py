#!/usr/bin/env python3
"""Lane schedule of the planned symmetry pilot (J-PIL-1; A-PIL-2 runbook): the plan's indices, heaviest first, each
onto the lane that frees first, at est_core_seconds / (8 threads x 0.9) (the planner's assumed efficiency), on N amdq
nodes of 8 x 8 lanes; allocated core-hours = wall x 64 x N. The same rule as the Expanse pilot's table
(benchmarks/expanse_2026-10-c8/stage5/exp/scripts/s5e_summary.py). The merge (a few minutes on one node) is extra.
  pilot_lanes.py MANIFEST OUT.json"""
import hashlib, json, sys
m_path, out = sys.argv[1], sys.argv[2]
data = open(m_path, 'rb').read(); m = json.loads(data)
est = sorted((j['est_core_seconds'] for j in m['jobs']), reverse=True); thr = m['threads']; per_node = 64 // thr
rows = []
for nodes in (1, 2, 3, 4):
    lanes = [0.] * (per_node * nodes)
    for e in est:
        i = min(range(len(lanes)), key=lambda k: lanes[k]); lanes[i] += e / (thr * 0.9)
    wall = max(lanes); alloc = wall * 64 * nodes / 3600
    rows.append({'nodes': nodes, 'lanes': len(lanes), 'wall_hours': wall / 3600, 'allocated_core_hours': alloc,
                 'lane_occupancy': sum(lanes) / (wall * len(lanes))})
rec = {'manifest_sha256': hashlib.sha256(data).hexdigest(), 'campaign': '<SCRATCH>/c8-d2/pilot1-20261005', 'seed': m['seed'],
       'indices': len(est), 'estimated_core_hours': sum(est) / 3600, 'largest_index_core_seconds': est[0],
       'max_index_wall_seconds': m['estimates']['max_index_wall_seconds'], 'L8_indices': sum(1 for j in m['jobs'] if j['L'] == 8),
       'rule': __doc__, 'schedule': rows}
json.dump(rec, open(out, 'w'), indent=1); print(json.dumps(rec['schedule'], indent=1)); print(rec['L8_indices'], 'L8 indices')
