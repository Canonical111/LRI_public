"""Fix round 3, MSC-018: fixed-in-advance design of (a) the independent radius run and (b) the double-double
validation sample at the fine production grid. Uses only engine outputs and the bound surveys (no reference value).
(b) strata: 'rank9_24' = the 16 non-overridden sectors with the largest fine-level first-order bound eps*B of
    f_3_0_1 (ranks 9-24 overall; ranks 1-8 are the production dd overrides); 'decile' = 24 sectors drawn with
    random.Random(20261016) from the remaining non-overridden sectors with nonzero bound, split into bound deciles
    (2 per decile for deciles 1-8, 4 per decile for deciles 9-10).
(a) radius run: taurat 0.3 (production 0.2), grid (10,14,12), tau cap 0.5, -radii rouche -bound 1, double build
    b0da6f7b; dd overrides (build 06c88f4c) for the sectors whose G0 taurat-0.3 survey bound eps*B > 0.1
    (results/m4_runs/b3.tar.xz). Aliasing at taurat 0.3, m 14: pilot maximum 2.4e-4 per sector (sector 2337).
usage: python m4_fix3_design.py   -> results/m4_inputs/fix3_design.json"""
import sys, os, json, glob, random, tarfile, io
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from m4_fbound import fbound, read_out, mp
import provenance as pv
RES = pv.RES
OUTFILE = os.path.join(RES, 'm4_inputs', 'fix3_design.json')
if os.path.exists(OUTFILE):    # fix round 4 (MSC-028): a committed design is never overwritten
    sys.exit(f'refusing to overwrite the existing design {OUTFILE}')
w = json.load(open(os.path.join(RES, 'm4_inputs', 'n4.mirror.json')))['weights']
ddprod = set(json.load(open(os.path.join(RES, 'm4_inputs', 'dd_sectors_prod.json')))['sectors'])
eps = mp.mpf(2) ** -53
bnd = {}
for f in sorted(glob.glob(os.path.join(RES, 'm4_runs', 'prod', 'F', '*.out'))):
    h, secs = read_out(f)
    for s, sec in secs.items():
        bnd[s] = float(fbound(sec) * eps * w[s])
cand = sorted((s for s in bnd if s not in ddprod), key=lambda s: -bnd[s])
rank = cand[:16]
rest = [s for s in cand[16:] if bnd[s] > 0]
rest_sorted = sorted(rest, key=lambda s: bnd[s])
n = len(rest_sorted); dec = [rest_sorted[i * n // 10:(i + 1) * n // 10] for i in range(10)]
rng = random.Random(20261016)
pick = []
for i, d in enumerate(dec):
    pick += sorted(rng.sample(d, 2 if i < 8 else 4))
# (a) radius-run dd overrides from the taurat-0.3 G0 survey
b3 = {}
with tarfile.open(os.path.join(RES, 'm4_runs', 'b3.tar.xz')) as tf:
    for m in tf.getmembers():
        if not m.name.endswith('.out'): continue
        tmp = os.path.join('/tmp', 'b3_' + os.path.basename(m.name) + str(os.getpid()))
        open(tmp, 'wb').write(tf.extractfile(m).read())
        h, secs = read_out(tmp); os.remove(tmp)
        for s, sec in secs.items():
            b3[s] = float(fbound(sec) * eps * w[s])
radius_dd = sorted(s for s, v in b3.items() if v > 0.1 and w[s] > 0)
out = {'note': __doc__.split('usage:')[0].strip(),
       'dd_sample': {'rank9_24': rank, 'decile': pick},
       'fine_bound_eps_B': {str(s): bnd[s] for s in rank + pick},
       'fine_bound_total_double': sum(v for s, v in bnd.items() if s not in ddprod),
       'radius_run': {'taurat': 0.3, 'tau': 0.5, 'grid': [10, 14, 12], 'dd_sectors': radius_dd,
                      'survey_bound_eps_B': {str(s): b3[s] for s in radius_dd}}}
open(OUTFILE, 'w').write(json.dumps(out, indent=1) + '\n')
print('rank9_24', rank); print('decile', pick); print('radius dd', radius_dd)
print('fine double bound total %.3f; rank9_24 bounds %.3g..%.3g' % (out['fine_bound_total_double'], bnd[rank[0]], bnd[rank[-1]]))
