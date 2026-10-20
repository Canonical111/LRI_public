#!/usr/bin/env python3
"""Member list for tc_cert: every inventory graph of the given (sector, L) packs, each member's bytes checked against
its inventory sha256 (read-only; the packs and inventory.json of an inputs directory).

  tc_cert_list.py INPUTS_DIR OUT_LIST [--loops 3-8] [--sectors free,power] [--ids FILE]

INPUTS_DIR is the package's inputs/ (L3..L7 on the Mac) or the export's inputs/ on symmetry (L3..L8). With --ids, only
the graphs listed in FILE ('<sector> <L> <id>' lines)."""
import argparse, hashlib, json, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('inputs', type=Path)
ap.add_argument('out', type=Path)
ap.add_argument('--loops', default='3-8')
ap.add_argument('--sectors', default='free,power')
ap.add_argument('--ids', type=Path)
a = ap.parse_args()
lo, hi = map(int, a.loops.split('-'))
want = None
if a.ids:
    want = {tuple(l.split()[:3]) for l in a.ids.read_text().splitlines() if l.strip()}
inv = json.loads((a.inputs / 'inventory.json').read_bytes())
n = bad = 0
with a.out.open('w') as out:
    for s in a.sectors.split(','):
        for L in range(lo, hi + 1):
            rows = inv[s].get(str(L), [])
            pack = (a.inputs / f'packs/{s}_L{L}.pack').resolve()
            if not rows or not pack.exists():
                print(f'skip {s} L{L}: {len(rows)} rows, pack {"present" if pack.exists() else "absent"}', file=sys.stderr)
                continue
            with pack.open('rb') as f:
                for r in sorted(rows, key=lambda r: r['offset']):
                    if want is not None and (s, str(L), str(r['id'])) not in want:
                        continue
                    f.seek(r['offset']); data = f.read(r['length'])
                    if hashlib.sha256(data).hexdigest() != r['sha256']:
                        bad += 1; print(f'sha256 mismatch {s} L{L} G{r["id"]}', file=sys.stderr); continue
                    out.write(f"{s} {L} {r['id']} {pack} {r['offset']} {r['length']}\n"); n += 1
print(f'{n} members listed, {bad} sha256 mismatches', file=sys.stderr)
sys.exit(1 if bad else 0)
