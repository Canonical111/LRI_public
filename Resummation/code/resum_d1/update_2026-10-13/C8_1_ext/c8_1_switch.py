#!/usr/bin/env python3
"""C8(1) input switch for the 1d resummation (2026-10-13).

Every program that uses the eighth-order GFF coefficient C8(1) or its allowance reads it from here:
  update_2026-10-12/sr_endpoint.py, update_2026-10-12/pipeline_K8/cbk.py (and through them all pipeline stages,
  prepare_fig05_K8.py, gff_only_v.py, make_fig.py), update_2026-10-13/*.py and C8_1_ext/instanton_mismatch/analyze.py.

Environment:
  LRI_C8_1 = final     (default) C8(1) FINAL of 2026-10-13 from c8_1_final.json: 8059766.723129955, allowance 17000.
  LRI_C8_1 = previous  the value used until 2026-10-13, from the frozen baseline/inputs/evidence.json EV['C8']:
                       8066723.342964563, allowance 33000 (reproduces the 2026-10-12/13 outputs).
  LRI_C8_1_OUT         optional output root. Default: update_2026-10-13/C8_1_ext/ (final) or
                       update_2026-10-13/C8_1_ext/repro_previous/ (previous). The archived 2026-10-12/13 outputs in
                       update_2026-10-12/ and update_2026-10-13/ are never written by the switched programs.
The frozen inputs (baseline/inputs/evidence.json, inputs/*) are only read. C0..C7 are unchanged in both modes.
References (2026-10-13 evening, NRG rev 2): references_csv() gives the 1d reference table of the mode. final reads
update_2026-10-13/references_nrg_rev2.csv (NRG rows from the revised NRG results, update_2026-10-13/refresh_nrg_rev2.py);
previous reads update_2026-10-12/references_refreshed.csv, so the previous mode still reproduces the previous outputs.
"""
import json
import os
from pathlib import Path

EXT = Path(__file__).resolve().parent                 # update_2026-10-13/C8_1_ext
PKG = EXT.parent.parent                               # resummation root
OVERRIDE = EXT/'c8_1_final.json'
EVIDENCE = PKG/'baseline'/'inputs'/'evidence.json'
MODES = ('final', 'previous')
MODE = (os.environ.get('LRI_C8_1') or 'final').strip().lower()
if MODE not in MODES:
    raise SystemExit("LRI_C8_1 must be 'final' or 'previous', not %r" % MODE)

# archived scenario value of the hypothetical C9 (K=4 endpoint-v PB[5/3], b_L=3, computed with the PREVIOUS C8(1));
# exact double recorded in update_2026-10-12/pipeline_K8/results/c9_validation.json 'reference_C9'
C9_REF_ARCHIVED = '-219050663.30085608'


def c8_inputs(mode=None):
    """C8(1) value (decimal string, exact as recorded), sampling SE, allowance and provenance for a mode."""
    mode = mode or MODE
    if mode == 'final':
        o = json.loads(OVERRIDE.read_text())
        return {'mode': 'final', 'C8': o['C8_full'], 'sampling_se': float(o['sampling_se']), 'allowance': int(o['allowance']),
                'reported': o['reported'], 'label': 'C8(1) final 2026-10-13, (8.060 +- 0.017) x 10^6',
                'source': 'update_2026-10-13/C8_1_ext/c8_1_final.json (condensed note fa71533, lines 104, 129, 147, 11390)'}
    ev = json.loads(EVIDENCE.read_text())['C8']
    return {'mode': 'previous', 'C8': str(ev['C8_full']), 'sampling_se': float(ev['sampling_se']),
            'allowance': int(ev['allowance']['headline_2sf']), 'reported': '(8.067 +- 0.033) x 10^6',
            'label': 'C8(1) previous (b1-b4, 2026-10-03), (8.067 +- 0.033) x 10^6',
            'source': "baseline/inputs/evidence.json EV['C8']"}


def out_root(mode=None):
    mode = mode or MODE
    if os.environ.get('LRI_C8_1_OUT'):
        root = Path(os.environ['LRI_C8_1_OUT']).resolve()
    else:
        root = EXT if mode == 'final' else EXT/'repro_previous'
    root.mkdir(parents=True, exist_ok=True)
    return root


def references_csv(mode=None):
    mode = mode or MODE
    return PKG/'update_2026-10-13'/'references_nrg_rev2.csv' if mode == 'final' else PKG/'update_2026-10-12'/'references_refreshed.csv'


def describe():
    c = c8_inputs()
    refs = {'references': str(references_csv().relative_to(PKG))} if MODE == 'final' else {}   # previous: output unchanged
    return {'LRI_C8_1': MODE, 'C8': c['C8'], 'allowance': c['allowance'], 'sampling_se': c['sampling_se'],
            'source': c['source'], **refs, 'output_root': str(out_root().relative_to(PKG)) if str(out_root()).startswith(str(PKG)) else str(out_root())}


if __name__ == '__main__':
    print(json.dumps(describe(), indent=1))
