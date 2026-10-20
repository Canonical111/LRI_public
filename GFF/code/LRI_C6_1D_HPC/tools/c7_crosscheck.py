"""C7-package six-loop by-product versus the exact C6, with every stage labelled (review finding RR-002).

Usage: python c7_crosscheck.py C7_FINAL.json C6_FINAL.json OUT.json
Stages, all from C7_final.json (the C7 package's own C6 coefficient):
  degree6  : the pre-registered degree-6 estimate (lower_order_checks, n = 6), with its sampling SE;
  step7    : + the measured degree 6->7 check level (check_levels.refine7, entry 6; never part of the C7 estimate);
  tail     : + a post hoc geometric tail beyond degree 7, ratio r = step7 / refine6-level (power_levels.refine6),
             tail = step7 r / (1 - r). Model-dependent.
z uses the C7 package's SE only (the exact C6 uncertainty, 4.9e-7, is negligible).
"""
import sys, json, hashlib
from pathlib import Path
c7p, c6p, outp = sys.argv[1:4]
c7 = json.loads(Path(c7p).read_bytes()); c6 = json.loads(Path(c6p).read_bytes())
lo = [x for x in c7['lower_order_checks'] if int(x['n']) == 6][0]
d6, se = float(lo['value']), float(lo['sampling_se'])
s7 = float(c7['check_levels']['refine7']['mean'][6]); s6 = float(c7['power_levels']['refine6']['mean'][6])
r = s7 / s6; tail = s7 * r / (1 - r)
ref = float(c6['headline']['C6_unrounded'])
stages = {'degree6': d6, 'degree6_plus_step7': d6 + s7, 'degree6_plus_step7_plus_tail': d6 + s7 + tail}
out = {'exact_C6': ref, 'exact_C6_allowance': c6['headline']['allowance_U'], 'C7_package_SE': se,
       'step7': s7, 'refine6_level': s6, 'tail_ratio': r, 'tail': tail,
       'stages': {k: {'value': v, 'minus_exact': v - ref, 'z': (v - ref) / se} for k, v in stages.items()},
       'scope': 'degree6 and step7 are measured; the tail is a post hoc geometric model.',
       'inputs_sha256': {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (c7p, c6p)}}
Path(outp).write_text(json.dumps(out, indent=1))
for k, v in out['stages'].items():
    print(f"{k:30s} {v['value']:.5f}  {v['minus_exact']:+.5f}  z {v['z']:+.2f}")
print(f"tail ratio {r:.5f}, tail {tail:+.5f}")
