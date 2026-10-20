#!/usr/bin/env python3
"""Lane schedule and submission sizing of the planned symmetry pilot (from stage5/pilot/pilot_lanes.py, J-PIL-1).
  pilot_lanes.py MANIFEST CAMPAIGN OUT.json
From the plan's own index estimates (manifest.json jobs: est_core_seconds, est_peak_bytes):
- schedules on N = 1..5 amdq nodes of 8 x 8 lanes (the lane default on symmetry, R5b): the indices heaviest first,
  each onto the lane that frees first, at est_core_seconds / (8 threads x 0.9) (the planner's assumed efficiency);
  allocated core-hours = wall x 64 x N (the merge is extra);
- the lane deadline rule (tools/lanes.py): a lane claims an index only if est x f_class / (8 x 0.9) x 1.5 + 300 s fits
  the job's remaining time, with f_class 1.0 on the cost model's CPU model (EPYC 7543) and 1.5 on an unknown class
  (the EPYC 7532 nodes: the symmetry cost model lists no factor for them). For each N it gives the latest
  claim-time requirement (claim start + requirement) of the greedy schedule under f = 1.0 and under f = 1.5 for every
  lane (the worst case: all lanes on 7532 nodes); C8_LANE_TIME must exceed it, or the lanes leave indices unclaimed
  for a later worker;
- the lane memory guard (tools/lanes.py): lanes x the largest est_peak_bytes <= 0.85 x the job's memory limit, at
  C8_LANE_MEM=245G (245 GiB as Slurm reads it) with 8 lanes."""
import hashlib, heapq, json, sys
m_path, campaign, out = sys.argv[1], sys.argv[2], sys.argv[3]
data = open(m_path, 'rb').read(); m = json.loads(data)
thr = m['threads']; per_node = 64 // thr
jobs = sorted(m['jobs'], key=lambda j: -j['est_core_seconds'])
est = [j['est_core_seconds'] for j in jobs]
wall = lambda e, f=1.0: e * f / (thr * 0.9)
req = lambda e, f: wall(e, f) * 1.5 + 300

def schedule(nodes, f_speed=1.0, f_deadline=1.0):
    lanes = [(0., k) for k in range(per_node * nodes)]; heapq.heapify(lanes); latest = 0.; ends = []
    for e in est:
        t, k = heapq.heappop(lanes); latest = max(latest, t + req(e, f_deadline)); end = t + wall(e, f_speed); ends.append(end)
        heapq.heappush(lanes, (end, k))
    w = max(ends); busy = sum(wall(e, f_speed) for e in est)
    return {'nodes': nodes, 'lanes': per_node * nodes, 'wall_hours': w / 3600, 'allocated_core_hours': w * 64 * nodes / 3600,
            'lane_occupancy': busy / (w * per_node * nodes), 'latest_claim_requirement_hours': latest / 3600}

rows = []
for n in (1, 2, 3, 4, 5):
    a = schedule(n); b = schedule(n, 1.0, 1.5)
    rows.append({**a, 'latest_claim_requirement_hours_f1.5': b['latest_claim_requirement_hours']})
GiB = 1 << 30
peak = max(j['est_peak_bytes'] for j in m['jobs'])
lane_mem = 245 * GiB
by_L = {}
for j in m['jobs']:
    r = by_L.setdefault(f"L{j['L']}", {'indices': 0, 'est_core_hours': 0.}); r['indices'] += 1; r['est_core_hours'] += j['est_core_seconds'] / 3600
rec = {'manifest': m_path, 'manifest_sha256': hashlib.sha256(data).hexdigest(), 'campaign': campaign, 'seed': m['seed'], 'threads': thr,
       'checkpoint_tasks': m.get('checkpoint_tasks'), 'indices': len(est), 'estimated_core_hours': sum(est) / 3600,
       'largest_index_core_seconds': est[0], 'largest_index_group': jobs[0].get('group'), 'largest_index_wall_seconds_8_lane': wall(est[0]),
       'largest_index_claim_requirement_seconds': {'f_1.0': req(est[0], 1.0), 'f_1.5': req(est[0], 1.5)},
       'max_index_wall_seconds_manifest': (m.get('estimates') or {}).get('max_index_wall_seconds'),
       'L8_indices': sum(1 for j in m['jobs'] if j['L'] == 8), 'by_L': by_L,
       'peak_memory': {'largest_est_peak_bytes': peak, 'largest_est_peak_GiB': peak / GiB, 'lane_mem': '245G', 'per_lane_share_GiB': 245 / 8,
                       'guard_GiB_8_lanes': 0.85 * lane_mem / 8 / GiB, 'guard_ok_8_lanes': 8 * peak <= 0.85 * lane_mem,
                       'headroom_x': (0.85 * lane_mem / 8) / peak},
       'estimates': m.get('estimates'), 'rule': __doc__, 'schedule': rows}
json.dump(rec, open(out, 'w'), indent=1)
print(json.dumps({k: rec[k] for k in ('indices', 'estimated_core_hours', 'L8_indices', 'largest_index_core_seconds', 'largest_index_group',
                                      'largest_index_wall_seconds_8_lane', 'largest_index_claim_requirement_seconds', 'peak_memory')}, indent=1))
for r in rows: print(json.dumps(r))
