#!/usr/bin/env python3
"""COMPARISON ONLY (after our values exist): the pilot-level preview (results/preview_C8.json, written by
tests/preview_C8.py from the engine's own data) against the claims quoted in the C8 task brief (archive numbers, typed
in from the brief; no archive file is read).  The SHA-256 of our preview file is recorded BEFORE the comparison.
  B_done = B_old + 4W + 2S + 3/32 L3 - 1/4 M21 + 1/2 M12 - 1/16 N2 (the six 'inherited-record' terms of the archive)
  U ~ -1296.7 (brief: 'U = -1296.7 from A7_d_1 ~ 3.2e5'), quoted to 5 digits only
Output: results/compare_brief_C8.json
"""
import hashlib, json, os
import mpmath as mp
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pv = os.path.join(ROOT, 'results', 'preview_C8.json')
sha = hashlib.sha256(open(pv, 'rb').read()).hexdigest()
ours = json.load(open(pv))['outputs']
mp.mp.dps = 40
BRIEF = {'B_done8': ('563.404066124777663118309147204616', 'archive B_done (task brief)'),
         'U': ('-1296.7', 'archive U, 5 digits (task brief)')}
rows = {}
for k, (v, src) in BRIEF.items():
    o = ours.get(k, {})
    if 'value' not in o:
        rows[k] = {'missing': True}
        continue
    sig = max(mp.mpf(o['sigma_linear']), mp.mpf(o['rep_se']))
    d = mp.mpf(o['value']) - mp.mpf(v)
    rows[k] = {'ours': o['value'], 'sigma': mp.nstr(sig, 3), 'claim': v, 'claim_source': src, 'diff': mp.nstr(d, 4),
               'pull': mp.nstr(d / sig, 3)}
    print(f"{k:8s} ours {o['value'][:22]:>24s} +- {mp.nstr(sig, 3):>9s}  claim {v[:22]:>24s}  diff {mp.nstr(d, 3):>10s}"
          f"  pull {mp.nstr(d / sig, 3)}")
out = {'note': 'comparison only; our preview was written and hashed first; claims typed in from the C8 task brief',
       'preview_sha256_before_comparison': sha, 'rows': rows}
json.dump(out, open(os.path.join(ROOT, 'results', 'compare_brief_C8.json'), 'w'), indent=1)
print('preview sha256', sha)
