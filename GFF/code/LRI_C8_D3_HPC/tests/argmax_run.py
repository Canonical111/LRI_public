#!/usr/bin/env python3
"""A-DES-6 (PLAN.md; J-ARGMAX, Stage 3b; RECON section 6.3.6 "next step"): the argmax run. A recorded measurement, not
a pass/fail gate; it feeds the margin re-derivation (RECON:1357-1392). Expanse, inside a shared job.

  python3 -B tests/argmax_run.py RUN --cost-model MODEL --seed S --output DIR [--graphs 228,1357,318,3754]
                                 [--points 262144] [--replicates 8] [--threads N] [--scratch DIR]

1. A selection (schema c8-d3-selection-1, role "argmax") of the power-L7 graphs at --points (2^18) each.
2. `production.py plan RUN --pilot --graphs SEL --replicates 8 --test-only` on the measured basis: MODEL, J-SWEEP-1's
   model of this binary (role campaign; HD11), --mp-check on, --forbid-seeds-from $C8_SEEDS --reserve-seed $C8_SEEDS: the
   seed is rechecked and reserved in $C8_SEEDS by the plan itself, before anything is built or run (HD6, S2-002; no
   `seeds.py add` afterwards); then `tools/cost_identity.py check RUN`.
3. Every index run in this job (`production.py run --index`), then `production.py merge` (role pilot_subset; its merge
   path is `pilot_report.py subset-check`, run too).
4. For every (campaign, replicate, graph) the tail_argmax of graph_tails.csv is regenerated with
   `bin/c8d3_inspect --point` (the group's net, seed, layout and rate): |t| must equal tail_top[0] bit for bit
   (A-KER-6 (c) on campaign data). Recorded per point: lx (log-coordinates), the edge order (sample()'s picks, lx
   descending), the gaps between consecutive lx (the scales -lt of the remaining sets), the flag the point approaches
   (the nested remaining sets whose gap exceeds 2 and 5 in natural log), the evaluate() level, and for each flag set
   its rate-table entry (gen3/g3common.d3_rates: the lifted rate in quarters and the raw p4) and its relation to the
   graph's double-lift subsets (raw p4 <= -5): equal, inside one, containing one, or none.
Output: DIR/argmax.json (and the selection, the cost identity check and the subset-check summary). The tail fields of
every (campaign, replicate, graph) are kept (graph_tails.csv rows).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'tools'), str(ROOT / 'gen3')]
import native_common as nc  # noqa: E402
import production as prod  # noqa: E402
import g3common as g3  # noqa: E402

GRAPHS = (228, 1357, 318, 3754)
GAPS = (2.0, 5.0)


def tool(script, *args, check=True, env=None):
    cp = subprocess.run([sys.executable, '-B', str(ROOT / 'tools' / script), *map(str, args)], capture_output=True, text=True, env=env)
    if check and cp.returncode:
        raise RuntimeError(f'{script} {" ".join(map(str, args))}: exit {cp.returncode}\n{(cp.stderr or cp.stdout)[-3000:]}')
    return cp


def csv_rows(path: Path) -> list[dict]:
    lines = Path(path).read_text().splitlines()
    head = lines[0].split(',')
    return [dict(zip(head, ln.split(','))) for ln in lines[1:] if ln]


def flags(lx: list[float]) -> dict:
    """sample()'s structure: lx[order[0]] = 0 and lx[order[j+1]] = lx[order[j]] + lt[j] (lt <= 0); the remaining set
    after step j is S_j = {order[j+1..E-1]}, scaled by exp(lt[j]) together. Returns the order, the gaps -lt and the
    remaining sets (bitmasks) at every step."""
    E = len(lx)
    order = sorted(range(E), key=lambda e: (-lx[e], e))
    gaps = [lx[order[j]] - lx[order[j + 1]] for j in range(E - 1)]
    sets = []
    for j in range(E - 1):
        S = 0
        for e in order[j + 1:]:
            S |= 1 << e
        sets.append(S)
    return {'order': order, 'gaps': gaps, 'sets': sets}


def relation(S: int, dl: list[int]) -> str:
    if S in dl:
        return 'double-lift subset'
    if any(S & d == S for d in dl):
        return 'inside a double-lift subset'
    if any(S & d == d for d in dl):
        return 'contains a double-lift subset'
    return 'none'


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run', type=Path)
    ap.add_argument('--cost-model', type=Path, required=True)
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--graphs', default=','.join(map(str, GRAPHS)))
    ap.add_argument('--points', type=int, default=1 << 18)
    ap.add_argument('--replicates', type=int, default=8)
    ap.add_argument('--threads', type=int, default=nc.threads_default())
    ap.add_argument('--scratch', default=os.environ.get('C8_SCRATCH'))
    ap.add_argument('--reinspect', action='store_true',
                    help='step 4 only, on an existing merged RUN of this tool (no plan, no new point): regenerate the argmax points again')
    a = ap.parse_args(argv)
    seeds_log = os.environ.get('C8_SEEDS')
    if not seeds_log:
        raise SystemExit('argmax_run: C8_SEEDS (the forbidden-seed log) is required')
    t0 = time.time()
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    run = a.run.resolve()
    ids = [int(x) for x in a.graphs.split(',')]
    inv = nc.inventory()
    im = nc.digest(ROOT / 'inputs/manifest.json')
    have = {r['id']: r for r in inv['power']['7']}
    missing = [g for g in ids if g not in have]
    if missing:
        raise SystemExit(f'argmax_run: power L7 graphs {missing} are not in the inventory')
    if a.reinspect:
        m = json.loads((run / 'manifest.json').read_text())
        if m.get('seed') != a.seed or m.get('campaign_role') != 'pilot_subset' or json.loads((run / 'selection.json').read_text()).get('role') != 'argmax':
            raise SystemExit(f'argmax_run --reinspect: {run} is not an argmax campaign of seed {a.seed}')
        plan_seconds = run_seconds = None
        sc = subprocess.CompletedProcess([], None, '', '')
        (out / 'reinspect.txt').write_text(f'step 4 only, on the merged campaign {run} (manifest sha256 {nc.digest(run / "manifest.json")})\n')
    else:
        m, plan_seconds, run_seconds, sc = campaign(a, run, ids, im, out, seeds_log)
    points, rate, summary = inspect_points(run, m, ids)
    doc = {'schema': 'c8-d3-argmax-1', 'run': str(run), 'manifest_sha256': nc.digest(run / 'manifest.json'), 'seed': a.seed, 'graphs': ids,
           'points_per_graph': a.points, 'replicates': a.replicates, 'campaigns': sorted({p['campaign'] for p in points}),
           'cost_model': str(a.cost_model), 'cost_model_sha256': nc.digest(a.cost_model), 'executable_sha256': m['executable_sha256'],
           'cost_identity_check': 'see the original run (--reinspect)' if a.reinspect else 'passed', 'subset_check_exit': sc.returncode, 'gap_thresholds': list(GAPS), 'reinspect': a.reinspect,
           'double_lift_subsets': {str(g): rate[g]['double_lift'] for g in ids}, 'summary': summary, 'points': points,
           'timing': {'plan_seconds': None if plan_seconds is None else round(plan_seconds, 1), 'run_seconds': None if run_seconds is None else round(run_seconds, 1),
                      'total_seconds': round(time.time() - t0, 1)},
           'note': 'a recorded measurement (A-DES-6), not a gate; lx are sample()\'s log-coordinates (lx[order[0]] = 0); a gap is -lt of the '
                   'remaining set after that step; rate_quarters/raw_p4 are the d=3 rate table entries of the set (gen3/g3common.d3_rates); '
                   'y = v_0 (the integrand value sample() returns, its sector Jacobian included) and jac the grid Jacobian (1 without a grid), t = y jac',
           'host': nc.host_info(), 'slurm_job': os.environ.get('SLURM_JOB_ID')}
    (out / 'argmax.json').write_text(json.dumps(doc, indent=1) + '\n')
    print(json.dumps({k: v for k, v in doc.items() if k not in ('points', 'double_lift_subsets')}, indent=1))
    return 0


def campaign(a, run, ids, im, out, seeds_log):
    """Steps 1-3: the selection, the plan on the measured basis, the run of every index, the merge, subset-check."""
    sel = {'schema': prod.SELECTION_SCHEMA, 'inputs_manifest_sha256': im, 'role': 'argmax', 'seed': a.seed,
           'groups': {'power:7': [{'id': g, 'points': a.points, 'label': 'argmax'} for g in ids]}, 'empty_reason': None}
    sf = out / 'selection_argmax.json'
    sf.write_text(json.dumps(sel, indent=1) + '\n')
    tp = time.time()
    tool('production.py', 'plan', run, '--seed', a.seed, '--pilot', '--graphs', sf, '--replicates', a.replicates, '--test-only', '--cost-model', a.cost_model,
         '--mp-check', 'on', '--backend', 'gmp', '--threads', a.threads, '--forbid-seeds-from', seeds_log, '--reserve-seed', seeds_log,
         *(['--scratch', a.scratch] if a.scratch else []))   # the plan reserves the seed before it builds anything (HD6, S2-002)
    plan_seconds = time.time() - tp
    ci = tool('cost_identity.py', 'check', run, check=False)
    (out / 'cost_identity_check.txt').write_text(ci.stdout + ci.stderr)
    if ci.returncode:
        raise SystemExit(f'argmax_run: tools/cost_identity.py check failed on {run} ({ci.returncode}): {(ci.stderr or ci.stdout)[-1500:]}')
    m = json.loads((run / 'manifest.json').read_text())
    assert m['test_only'] and m['plan_role'] == 'campaign' and m['cost_basis'] == 'measured' and m['campaign_role'] == 'pilot_subset', \
        (m['plan_role'], m['cost_basis'], m['campaign_role'])
    tr = time.time()
    for j in m['jobs']:
        tool('production.py', 'run', run, '--index', j['id'], '--threads', a.threads, *(['--scratch', a.scratch] if a.scratch else []))
    run_seconds = time.time() - tr
    tool('production.py', 'merge', run, '--jobs', 4, *(['--scratch', a.scratch] if a.scratch else []))
    sc = tool('pilot_report.py', 'subset-check', run, check=False)
    (out / 'subset_check.txt').write_text(sc.stdout + sc.stderr)
    return m, plan_seconds, run_seconds, sc


def inspect_points(run, m, ids):
    """Step 4: every (campaign, replicate, graph)'s tail_argmax regenerated and analysed."""
    # rates and double-lift subsets of each graph (gen3's pure-Python regenerate_rates formula)
    with nc.extracted([('power', 7, g) for g in ids]) as root:
        rate = {}
        for g in ids:
            f = root / 'power' / 'L7' / f'G{g}.txt'
            gf = g3.parse_gfile(f.read_bytes(), str(f))
            pos, raw = g3.d3_rates(gf)
            ALL = (1 << gf.E) - 1
            dl = [s for s in range(1, ALL) if raw[s] <= -5]
            rate[g] = {'positive': pos, 'raw': raw, 'double_lift': dl, 'E': gf.E}
        points = []
        for name in sorted(g['name'] for g in m['groups']):
            cfg = json.loads((run / 'groups' / name / 'config.json').read_text())
            net = run / 'groups' / name / 'sobol.bin'
            tails = csv_rows(run / 'groups' / name / 'graph_tails.csv')
            for t in tails:
                g, rep, arg = int(t['graph']), int(t['replicate']), int(t['tail_argmax'])
                cp = subprocess.run([str(nc.INSPECT), '--point', str(g), str(rep), str(arg), '--', str(root / 'power'), '7', str(net), str(cfg['seed']),
                                     str(cfg['layout']), str(cfg['rate']), '-'], capture_output=True, text=True)
                if cp.returncode:
                    raise RuntimeError(f'c8d3_inspect --point {g} {rep} {arg}: {cp.stderr[-800:]}')
                pt = json.loads(cp.stdout)
                if pt['abs_t'] != t['tail_top_1']:
                    raise AssertionError(f'{name} rep {rep} graph {g}: --point |t| {pt["abs_t"]} != tail_top[0] {t["tail_top_1"]} (A-KER-6 (c))')
                lx = [float(x) for x in pt['lx']]
                fl = flags(lx)
                R = rate[g]
                approached = {}
                for th in GAPS:
                    approached[str(th)] = [{'step': j, 'gap': fl['gaps'][j], 'set': fl['sets'][j], 'edges': [e for e in range(R['E']) if fl['sets'][j] >> e & 1],
                                            'size': bin(fl['sets'][j]).count('1'), 'rate_quarters': R['positive'][fl['sets'][j]], 'raw_p4': R['raw'][fl['sets'][j]],
                                            'double_lift_relation': relation(fl['sets'][j], R['double_lift'])}
                                           for j in range(len(fl['gaps'])) if fl['gaps'][j] > th]
                points.append({'group': name, 'campaign': cfg['campaign'], 'rate': cfg['rate'], 'graph': g, 'replicate': rep, 'index': arg,
                               'abs_t': pt['abs_t'], 't': pt['t'], 'y': pt['y'], 'jac': pt['jac'], 'tail_sum': t['tail_sum'], 'tail_top': [t[f'tail_top_{i}'] for i in range(1, 17)],
                               'level': pt['level'], 'direct': pt['direct'], 'moderate': pt['moderate'], 'lx': pt['lx'], 'order': fl['order'],
                               'gaps': [round(x, 6) for x in fl['gaps']], 'flags': approached})
    summary = {}
    for g in ids:
        P = [p for p in points if p['graph'] == g]
        hit = [p for p in P if any(f['double_lift_relation'] != 'none' for f in p['flags']['2.0'])]
        deep = [p for p in P if p['flags']['5.0']]
        summary[str(g)] = {'points': len(P), 'double_lift_subsets': len(rate[g]['double_lift']),
                           'double_lift_sizes': sorted({bin(s).count('1') for s in rate[g]['double_lift']}),
                           'argmax_points_whose_flag_meets_a_double_lift_subset': len(hit),
                           'argmax_points_with_a_gap_above_5': len(deep),
                           'max_abs_t': max((p['abs_t'] for p in P), key=float) if P else None}
    return points, rate, summary


if __name__ == '__main__':
    sys.exit(main())
