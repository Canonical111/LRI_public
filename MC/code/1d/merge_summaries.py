#!/usr/bin/env python3
"""Merge per-campaign analysis summaries of ALL ACTIVE campaigns of every pair into one summary (FIT_MODEL_V3.md §4.7 union).

Usage: merge_summaries.py campaigns.json --coverage stageA|all --suffix _an_b4096_final --out DIR
Required coverage is the registry's EXPECTED pair set (all, or those with N <= stageA_max_N), independent of the active mapping.
For every active campaign of every pair in that coverage the analysis directory is <root>/<campaign dir><suffix>; its entries are
concatenated: exactly beta_points entries per (pair, campaign), so beta_points x (number of active campaigns) per pair; coincident
temperatures of different campaigns are kept as separate entries; every entry is stamped with campaign, campaign_index (position in
the registry) and the chain task ids; no duplicate (campaign, beta) and no reweighted entry.
"""
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
from registry import load, validate, expected, key, campaign_index, grid_of

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('registry', type=Path); p.add_argument('--coverage', choices=['stageA', 'all'], required=True)
    p.add_argument('--suffix', required=True); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); r = load(a.registry); root = Path(r['root']); pairs = validate(r, root, 'all' if a.coverage == 'all' else 'stageA')
    want = expected(r, a.coverage); out_dir = a.out.resolve()
    entries = []; seen = set(); sources = []; S = None
    names = sorted({c['name'] for k in want for c, _ in pairs[k]}, key=lambda n: campaign_index(r, n))
    for name in names:
        c = next(c for c in r['campaigns'] if c['name'] == name)
        adir = (root / (c['dir'] + a.suffix)).resolve(); sfile = adir / 'summary.json'
        if not sfile.exists(): raise SystemExit(f'missing analysis {sfile}')
        S = json.loads(sfile.read_text()); mine = {k for k in want if any(cc['name'] == name for cc, _ in pairs[k])}
        sources.append(dict(campaign=name, campaign_index=campaign_index(r, name), dir=str(adir), sha256=hashlib.sha256(sfile.read_bytes()).hexdigest()))
        for e in S['entries']:
            k = key(e['s'], e['N'])
            if k not in mine: continue
            if abs(e['beta'] - e.get('beta_simulated', e['beta'])) > 1e-14: raise SystemExit('reweighted entry in input')
            coord = (name, k, round(e['beta'], 12))
            if coord in seen: raise SystemExit(f'duplicate (campaign, s, N, beta) {coord}')
            seen.add(coord); e = dict(e)
            src = (adir / e['blocks_file']).resolve()        # block path is relative to its source summary
            if not src.exists(): raise SystemExit(f'missing block file {src}')
            tids = sorted(int(d['task_id']) for d in e.get('replica_diagnostics', []) if 'task_id' in d)
            g = grid_of(r, c, json.loads((root / c['dir'] / 'manifest.json').read_text()))
            if len(tids) != g['replicas']: raise SystemExit(f'{name} {k} beta={e["beta"]}: {len(tids)} chain task ids in the analysis, expected {g["replicas"]}')
            e['blocks_file'] = os.path.relpath(src, out_dir); e['campaign'] = name; e['campaign_index'] = campaign_index(r, name); e['task_ids'] = tids; entries.append(e)
    count = {}
    for e in entries: count[(e['campaign'], key(e['s'], e['N']))] = count.get((e['campaign'], key(e['s'], e['N'])), 0) + 1
    bad = {}; per_pair_total = {}
    for k in want:
        for c, _ in pairs[k]:
            g = grid_of(r, c, json.loads((root / c['dir'] / 'manifest.json').read_text()))   # REV-003: each campaign contributes exactly its own grid
            if count.get((c['name'], k), 0) != g['beta_points']: bad[(c['name'], k)] = (count.get((c['name'], k), 0), g['beta_points'])
            per_pair_total[k] = per_pair_total.get(k, 0) + count.get((c['name'], k), 0)
    if bad: raise SystemExit(f'coverage {a.coverage}: (campaign, pair) without exactly its own grid of entries (found, expected): {bad}')
    few = {k: v for k, v in per_pair_total.items() if v < 3}
    if few: raise SystemExit(f'pairs with fewer than 3 entries (§4.7): {few}')
    if {k for _, k in count} - want: raise SystemExit(f'entries outside the required coverage: {sorted({k for _, k in count} - want)}')
    per_pair = {k: sorted(c['name'] for c, _ in pairs[k]) for k in want}
    out_dir.mkdir(parents=True, exist_ok=True)
    out = dict(observable_order=S['observable_order'], entries=sorted(entries, key=lambda e: (e['s'], e['N'], e['beta'], e['campaign_index'])),
               coverage=a.coverage, pairs=sorted(want), sources=sources, active_campaigns_per_pair=per_pair,
               union=any(len(v) > 1 for v in per_pair.values()),
               covariance_note='merged from independent campaigns (union of all active campaigns per pair, §4.7); each entry keeps its own K_reference')
    (out_dir / 'summary.json').write_text(json.dumps(out, indent=1) + '\n')
    print(f'{out_dir / "summary.json"}: {len(entries)} entries, {len(want)} pairs, {len(sources)} campaigns, union={out["union"]}')
if __name__ == '__main__': main()
