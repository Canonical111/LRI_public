#!/usr/bin/env python3
"""Estimate and wall-time schedule of the planned C8(2) production campaign on symmetry amdq (8 x 8 lanes per node), from
the plan's own index estimates (manifest.json `jobs`: est_core_seconds, est_peak_bytes; `scale`, `estimates`).
Standard library only; runs on the Mac on the evidence copy of the manifest, or on the login node.

  prod_lanes.py plan MANIFEST OUT.json [--nodes 8] [--wall-hours 24]
  prod_lanes.py remaining RUN [--nodes 8] [--wall-hours 24]      (read-only; on symmetry with the export's tools: the
                                                                  indices still incomplete, from the checkpoint blocks,
                                                                  and the schedule of the next submit round)

The lane rule is tools/lanes.py's (cmd_lane): when a lane is free it takes the HEAVIEST unclaimed index whose claim
requirement fits the job's remaining time, need = est x f / (8 x 0.9) x C8_LANE_SAFETY 1.5 + C8_LANE_MARGIN 300 s, with
f = 1.0 on the cost model's CPU model (EPYC 7543, the only nodes of the production pool); a lane that finds nothing it
can fit stops, and a worker job ends when its 8 lanes have stopped (or at the wall limit). Every worker of a round
starts at t = 0 (the probe and the idle 7543 nodes say so; a late start only shifts that worker). Speed models for the
time an index actually runs on its 8-core lane:
  planner : est / (8 x 0.9)                       the planner's assumed lane efficiency (what the deadline rule uses)
  pilot   : est / (8 x 0.990)                     the pilot's measured in-index efficiency (analysis/README.md, sec. 2)
  stress  : est x 1.08 / (8 x 0.990) at free L8   the exact cost model under-estimated free L8 by 7-8% in the pilot; the
            (other indices as pilot)              profile model was measured by the same kind of sweep (570538)
Allocated core-hours = sum over workers of (end x 64). The merge job is extra (one amdq node)."""
from __future__ import annotations
import argparse, hashlib, heapq, json, sys
from pathlib import Path

T = 8; LANES_PER_NODE = 8; CORES = 64; EFF = 0.9; SAFETY = 1.5; MARGIN = 300.; F_CLASS = 1.0; GiB = 1 << 30
MODELS = {'planner': lambda j: j['est_core_seconds'] / (T * EFF),
          'pilot': lambda j: j['est_core_seconds'] / (T * 0.990),
          'stress': lambda j: j['est_core_seconds'] * (1.08 if (j['sector'], j['L']) == ('free', 8) else 1.0) / (T * 0.990)}

def need(j): return j['est_core_seconds'] * F_CLASS / (T * EFF) * SAFETY + MARGIN

def round_sim(jobs, nodes, wall_s, model):
    """One submit round: `nodes` workers of 8 lanes, all starting at 0 with `wall_s` seconds each. Returns the record and
    the indices left unclaimed."""
    todo = sorted(jobs, key=lambda j: (-j['est_core_seconds'], j['id']))
    run = MODELS[model]; lanes = [(0., k) for k in range(nodes * LANES_PER_NODE)]; heapq.heapify(lanes)
    stop = {}; claimed = set(); busy = 0.; nclaims = 0
    while lanes:
        t, k = heapq.heappop(lanes)
        pick = None
        for j in todo:
            if j['id'] not in claimed and need(j) <= wall_s - t: pick = j; break
        if pick is None: stop[k] = t; continue
        claimed.add(pick['id']); d = run(pick); busy += d; nclaims += 1
        if t + d > wall_s: raise SystemExit(f'index {pick["id"]} would run past the wall under model {model}: the 1.5 x margin is too small')
        heapq.heappush(lanes, (t + d, k))
    ends = [max(stop[n * LANES_PER_NODE + i] for i in range(LANES_PER_NODE)) for n in range(nodes)]
    left = [j for j in todo if j['id'] not in claimed]
    rec = {'nodes': nodes, 'model': model, 'claimed_indices': nclaims, 'worker_end_hours': [round(e / 3600, 3) for e in ends],
           'wall_hours': max(ends) / 3600 if ends else 0., 'allocated_core_hours': sum(ends) * CORES / 3600,
           'busy_lane_hours': busy / 3600, 'lane_occupancy': busy / (sum(ends) * LANES_PER_NODE) if sum(ends) else None,
           'left_indices': len(left), 'left_est_core_hours': sum(j['est_core_seconds'] for j in left) / 3600,
           'left_lane_hours_planner': sum(MODELS['planner'](j) for j in left) / 3600,
           'left_by_group': {}}
    for j in left:
        g = rec['left_by_group'].setdefault(j['group'], {'indices': 0, 'est_core_hours': 0.}); g['indices'] += 1; g['est_core_hours'] += j['est_core_seconds'] / 3600
    return rec, left

def schedule(jobs, nodes, wall_s, model):
    """Round 1 on `nodes`; round 2 on every N2 = 1..nodes for what is left (each round's workers start at 0)."""
    r1, left = round_sim(jobs, nodes, wall_s, model)
    r2 = []
    if left:
        for n2 in range(1, nodes + 1):
            r, l2 = round_sim(left, n2, wall_s, model); r['complete'] = not l2; r2.append(r)
    return {'round1': r1, 'round2_by_nodes': r2}

def no_deadline(jobs, nodes, model):
    """The single-pass schedule without a wall limit (heaviest first onto the lane that frees first)."""
    run = MODELS[model]; lanes = [0.] * (nodes * LANES_PER_NODE); heapq.heapify(lanes)
    for j in sorted(jobs, key=lambda j: (-j['est_core_seconds'], j['id'])): heapq.heappush(lanes, heapq.heappop(lanes) + run(j))
    return max(lanes) / 3600

def summary(m, jobs):
    est = sorted(j['est_core_seconds'] for j in jobs); peak = max(j['est_peak_bytes'] for j in jobs)
    by_L = {}
    for j in jobs:
        r = by_L.setdefault(f"{j['sector']}_L{j['L']}", {'indices': 0, 'est_core_hours': 0., 'tasks': 0}); r['indices'] += 1
        r['est_core_hours'] += j['est_core_seconds'] / 3600; r['tasks'] += j.get('tasks', 0)
    big = max(jobs, key=lambda j: j['est_core_seconds'])
    sc = m.get('scale') or {}; mg = sc.get('merge') or {}
    return {'indices': len(jobs), 'tasks': sc.get('tasks'), 'checkpoints': sc.get('checkpoints'), 'projected_files': sc.get('projected_files'),
            'estimated_core_hours': sum(est) / 3600, 'estimated_core_hours_manifest': (m.get('estimates') or {}).get('total_core_hours'),
            'lane_hours_planner': sum(est) / 3600 / (T * EFF), 'lane_hours_pilot': sum(est) / 3600 / (T * 0.990),
            'largest_index': {'id': big['id'], 'group': big['group'], 'est_core_seconds': big['est_core_seconds'],
                              'wall_seconds_8_lane_planner': big['est_core_seconds'] / (T * EFF), 'wall_seconds_8_lane_pilot': big['est_core_seconds'] / (T * 0.990),
                              'claim_requirement_seconds': need(big)},
            'smallest_index_est_core_seconds': est[0], 'median_index_est_core_seconds': est[len(est) // 2],
            'max_index_wall_seconds_manifest': (m.get('estimates') or {}).get('max_index_wall_seconds'),
            'latest_claim_of_largest_index_hours_into_a_24h_job': (24 * 3600 - need(big)) / 3600,
            'peak_memory': {'largest_est_peak_bytes': peak, 'largest_est_peak_GiB': peak / GiB, 'lane_mem': '245G', 'per_lane_share_GiB': 245 / 8,
                            'guard_GiB_per_lane_8_lanes': 0.85 * 245 / 8, 'guard_ok_8_lanes': 8 * peak <= 0.85 * 245 * GiB,
                            'headroom_x': 0.85 * 245 * GiB / 8 / peak},
            'merge': {'fan_in': sc.get('merge_fan_in'), 'projected_max_seconds': sc.get('merge_projected_max_seconds'),
                      'suggested_merge_time': sc.get('suggested_merge_time'), 'groups': len(mg),
                      'largest_group': max(mg.items(), key=lambda kv: kv[1]['projected_seconds'])[0] if mg else None,
                      'passes': sorted({v['passes'] for v in mg.values()}), 'rows_total': sum(v['rows'] for v in mg.values()),
                      'projected_seconds_sum_over_groups': sum(v['projected_seconds'] for v in mg.values())},
            'by_sector_L': by_L}

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest='cmd', required=True)
    q = s.add_parser('plan'); q.add_argument('manifest', type=Path); q.add_argument('out', type=Path)
    q.add_argument('--nodes', type=int, default=8); q.add_argument('--wall-hours', type=float, default=24.)
    q = s.add_parser('remaining'); q.add_argument('run', type=Path); q.add_argument('--nodes', type=int, default=8); q.add_argument('--wall-hours', type=float, default=24.)
    a = p.parse_args(argv); wall = a.wall_hours * 3600
    if a.cmd == 'plan':
        data = a.manifest.read_bytes(); m = json.loads(data); jobs = m['jobs']
        rec = {'manifest': str(a.manifest), 'manifest_sha256': hashlib.sha256(data).hexdigest(), 'seed': m['seed'], 'threads': m['threads'],
               'checkpoint_tasks': m['checkpoint_tasks'], 'rule': __doc__, 'summary': summary(m, jobs),
               'no_deadline_wall_hours': {mo: {n: no_deadline(jobs, n, mo) for n in (4, 8, 16)} for mo in MODELS},
               'schedule': {mo: schedule(jobs, a.nodes, wall, mo) for mo in MODELS}}
        a.out.write_text(json.dumps(rec, indent=1) + '\n')
        print(json.dumps(rec['summary'], indent=1))
        print('no-deadline wall (h):', json.dumps(rec['no_deadline_wall_hours']))
        for mo, sch in rec['schedule'].items():
            r1 = sch['round1']
            print(f"[{mo}] round 1 on {a.nodes} nodes: workers end {r1['worker_end_hours']} h; allocated {r1['allocated_core_hours']:.0f} core-h; "
                  f"lane occupancy {r1['lane_occupancy']:.3f}; left {r1['left_indices']} indices, {r1['left_est_core_hours']:.1f} est core-h "
                  f"({r1['left_lane_hours_planner']:.1f} lane-h planner)")
            for r in sch['round2_by_nodes']:
                print(f"   round 2 on {r['nodes']} node(s): wall {r['wall_hours']:.2f} h, allocated {r['allocated_core_hours']:.0f} core-h, complete {r['complete']}")
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import os
        pkg = os.environ.get('C8_PACKAGE'); sys.path.insert(0, f'{pkg}/tools') if pkg else None
        import production as prod
        run = a.run.resolve(); m = json.loads((run / 'manifest.json').read_bytes()); prog = prod.job_progress(run, m)
        left = [j for j in m['jobs'] if prog[j['id']][0] < prog[j['id']][1]]
        part = sum(1 for j in left if prog[j['id']][0] > 0)
        print(f'{len(left)} incomplete indices ({part} partly done), {sum(j["est_core_seconds"] for j in left) / 3600:.1f} est core-h as the queue counts them '
              f'(whole indices), {sum(j["est_core_seconds"] * (1 - prog[j["id"]][0] / prog[j["id"]][1]) for j in left) / 3600:.1f} pro rata by blocks')
        for n in range(1, a.nodes + 1):
            r, l2 = round_sim(left, n, wall, 'planner'); rp, lp = round_sim(left, n, wall, 'pilot')
            print(f'  --lanes {n}: wall {r["wall_hours"]:.2f} h (pilot speed {rp["wall_hours"]:.2f} h), allocated <= {r["allocated_core_hours"]:.0f} core-h, '
                  f'complete in this round: {not l2}')

if __name__ == '__main__':
    main()
