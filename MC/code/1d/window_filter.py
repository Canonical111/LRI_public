#!/usr/bin/env python3
"""Keep only the entries whose temperature GROUP has beta_index in --keep (default: central three of five).

Usage: window_filter.py summary.json campaigns.json --keep 1 2 3 --out summary_c3.json
For every entry the replica tasks of the ACTIVE campaign for that (s, N) with the same simulated beta are collected;
they must agree on beta_index and beta_center. Every (s, N) present must retain exactly len(keep) temperatures.
Block paths are re-expressed relative to the output file's directory.
"""
from __future__ import annotations
import argparse, json, os
from pathlib import Path
from registry import load, validate, key

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('summary', type=Path); p.add_argument('registry', type=Path)
    p.add_argument('--keep', type=int, nargs='+', default=[1, 2, 3]); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); r = load(a.registry); pairs = validate(r, Path(r['root']), 'active')
    src_dir = a.summary.resolve().parent; out_dir = a.out.resolve().parent
    S = json.loads(a.summary.read_text()); kept = []; per = {}
    for e in S['entries']:
        k = key(e['s'], e['N'])
        if k not in pairs: raise SystemExit(f'entry {k} has no active campaign')
        lst = pairs[k]
        if 'campaign' in e:
            hit = [ct for ct in lst if ct[0]['name'] == e['campaign']]
            if not hit: raise SystemExit(f'entry {k} from {e["campaign"]} but active are {[ct[0]["name"] for ct in lst]}')
            c, tasks = hit[0]
        elif len(lst) == 1: c, tasks = lst[0]
        else: raise SystemExit(f'entry {k} carries no campaign stamp but the pair has several active campaigns')
        b = e.get('beta_simulated', e['beta']); grp = [t for t in tasks if abs(t['beta'] - b) < 1e-12]
        if not grp: raise SystemExit(f'no task of {c["name"]} at {k} beta={b!r}')
        idx = {t['beta_index'] for t in grp}; cen = {t['beta_center'] for t in grp}
        if len(idx) != 1 or len(cen) != 1: raise SystemExit(f'inconsistent group metadata at {k} beta={b}')
        if idx.pop() in a.keep:
            e = dict(e); src = (src_dir / e['blocks_file']).resolve()
            if not src.exists(): raise SystemExit(f'missing block file {src}')
            e['blocks_file'] = os.path.relpath(src, out_dir); kept.append(e); per[(c['name'], k)] = per.get((c['name'], k), 0) + 1
    bad = {k: v for k, v in per.items() if v != len(a.keep)}
    if bad: raise SystemExit(f'(campaign, pair) not retaining exactly {len(a.keep)} temperatures: {bad}')
    out = dict(S); out['entries'] = kept; out['window'] = dict(keep=a.keep, source=str(a.summary.resolve()))
    out_dir.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + '\n'); print(f'{a.out}: {len(kept)} entries over {len(per)} pairs')
if __name__ == '__main__': main()
