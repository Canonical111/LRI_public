#!/usr/bin/env python3
"""Rebuild data/HT_1d/c8/extrapolation/data.json (sha256 ccc77dfa...), the input file of the C8 extrapolation and of the
later refits, from the shipped records.

Relative-path copy of the builder written for the LRI HT note on 2026-10-05 (archive/c8_extrap/build_data_json.py of
that note; Claude Code). The recipe and the output format are unchanged; only the five source paths are now arguments
with defaults relative to this package in the public tree.  The recipe is the one stated in the 'note' field of
data.json:
  raw / vacuum_only : C0..C8 from lri_c8 (Lambda <= 50: inputs/<scheme>/<scheme>_L*_d8.json of this package, the
                      original runs; Lambda = 52..92: data/HT_1d/c8/exports/<scheme>_L52-92.json, campaign
                      654fb90d19a573c1)
  thermal_d7        : C0..C7 of the raw HT solver (code/lri_hpc_Hamitonian/analysis/extended/): prior_c7/
                      C7_completed_runs.json and C7_extension.json (Lambda <= 50), thermal_new.json (Lambda = 52..118)
  note, known       : copied verbatim from the shipped data.json (reference values; no builder of them was saved)

Usage:  python3 public/build_data_json.py OUT.json [--data ../../data/HT_1d]
                                                   [--thermal ../lri_hpc_Hamitonian/analysis/extended]
Writes OUT.json, prints the comparison with the shipped data.json and the two sha256; exit status 0 when OUT.json is
byte-identical to the shipped file, 1 otherwise. Standard library only; well under a second."""
import argparse
import hashlib
import json
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
SHA = 'ccc77dfa1e7d3955f3b8f22b2ea3b99ba649976605c5bac6bae39b5f2ad92faa'


def scheme_rows(scheme, c8_inputs, exports):
    rows = {}
    for p in sorted((c8_inputs / scheme).glob(f'{scheme}_L*_d8.json')):
        r = json.loads(p.read_text())
        rows[int(r['cutoff'])] = r['C']
    for r in json.loads((exports / f'{scheme}_L52-92.json').read_text()):
        rows[int(r['cutoff'])] = r['C']
    return {str(k): rows[k] for k in sorted(rows)}


def thermal_rows(ext):
    rows = {}
    for f in ('prior_c7/C7_completed_runs.json', 'C7_extension.json', 'thermal_new.json'):
        for r in json.loads((ext / f).read_text()):
            rows[int(r['cutoff'])] = r['C']
    return {str(k): rows[k] for k in sorted(rows)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path)
    ap.add_argument('--data', type=Path, default=PKG / '..' / '..' / 'data' / 'HT_1d')
    ap.add_argument('--thermal', type=Path, default=PKG / '..' / 'lri_hpc_Hamitonian' / 'analysis' / 'extended')
    a = ap.parse_args()
    c8_inputs = PKG / 'inputs'
    exports = a.data / 'c8' / 'exports'
    archived = a.data / 'c8' / 'extrapolation' / 'data.json'

    old = json.loads(archived.read_text())
    new = {'note': old['note'], 'raw': scheme_rows('raw', c8_inputs, exports),
           'vacuum_only': scheme_rows('vacuum_only', c8_inputs, exports),
           'thermal_d7': thermal_rows(a.thermal), 'known': old['known']}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(new, indent=1))
    for key in ('raw', 'vacuum_only', 'thermal_d7'):
        x, y = old[key], new[key]
        same_keys = sorted(x, key=int) == sorted(y, key=int)
        maxdiff = max(abs(u - v) / max(1.0, abs(u)) for k in x if k in y for u, v in zip(x[k], y[k]))
        print(f'{key}: {len(y)} cutoffs, same cutoff set: {same_keys}, max relative difference {maxdiff:.1e}')
    h_new = hashlib.sha256(a.out.read_bytes()).hexdigest()
    h_old = hashlib.sha256(archived.read_bytes()).hexdigest()
    same = h_new == h_old == SHA
    print(f'sha256 rebuilt {h_new}\nsha256 shipped {h_old}\nbyte-identical to the shipped data.json (sha256 {SHA[:8]}...): {same}')
    raise SystemExit(0 if same else 1)


if __name__ == '__main__':
    main()
