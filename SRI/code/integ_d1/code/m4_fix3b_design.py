"""Fix round 3, amendment B (user decision 2026-10-17, post hoc after the 0.411 ratio): per-decile roundoff rule and a
fresh held-out double-double sample. Fixed before any new data; uses engine outputs only (no reference value).
Strata (from fix3_design.json, recomputed identically here and checked): rank9_24 = the 16 non-override sectors with the
largest fine-level bound eps*B of f_3_0_1; deciles 1..10 = the remaining nonzero-bound non-override sectors sorted by
that bound (ascending) and split at i*n//10.
Rule (per level L in fine, coarse, radius; sectors mapped to the fine-level strata by sector id):
  factor_d = max(10 x largest sampled |double - dd| / (eps B) in stratum d, using the old (Vdd) + new (Vdd2) samples, 0.01)
  fine:   roundoff = sum_d factor_d x (non-sampled double bound in decile d) + sum over all sampled sectors of the
          weighted |double - dd| (rank9_24 fully measured, so its bound term is zero) + dd-override bound
  coarse, radius: roundoff = sum over strata of factor_s x (that level's double bound in the stratum) + dd-override bound
          (the samples were measured at the fine grid only; rank9_24 uses its own factor)
  stop: any sampled ratio > 0.1 in rank9_24, decile 9 or decile 10 (these carry >= 2% of the rest bound each;
        deciles 1-8 together 0.2%).
Fresh sample: random.Random(20261017); excluding the 40 old samples and the 8 overrides: 8 from the upper half of
decile 10 (by bound), 4 from its lower half, 4 from decile 9. Fine-grid parameters (12,14,14), taurat 0.2, dd build
06c88f4c, output results/m4_runs/prod/Vdd2.
usage: python m4_fix3b_design.py   -> results/m4_inputs/fix3b_design.json"""
import sys, os, json, glob, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from m4_fbound import fbound, read_out, mp
import provenance as pv
RES = pv.RES
OUTFILE = os.path.join(RES, 'm4_inputs', 'fix3b_design.json')
if os.path.exists(OUTFILE):    # fix round 4 (MSC-028): a committed design is never overwritten
    sys.exit(f'refusing to overwrite the existing design {OUTFILE}')
w = json.load(open(os.path.join(RES, 'm4_inputs', 'n4.mirror.json')))['weights']
ddprod = set(json.load(open(os.path.join(RES, 'm4_inputs', 'dd_sectors_prod.json')))['sectors'])
old = json.load(open(os.path.join(RES, 'm4_inputs', 'fix3_design.json')))
eps = mp.mpf(2) ** -53
bnd = {}
for f in sorted(glob.glob(os.path.join(RES, 'm4_runs', 'prod', 'F', '*.out'))):
    h, secs = read_out(f)
    for s, sec in secs.items():
        bnd[s] = float(fbound(sec) * eps * w[s])
cand = sorted((s for s in bnd if s not in ddprod), key=lambda s: -bnd[s])
rank = cand[:16]
assert rank == old['dd_sample']['rank9_24'], 'rank9_24 differs from fix3_design'
rest = sorted((s for s in cand[16:] if bnd[s] > 0), key=lambda s: bnd[s])
n = len(rest); dec = [rest[i * n // 10:(i + 1) * n // 10] for i in range(10)]
oldsamp = set(old['dd_sample']['rank9_24']) | set(old['dd_sample']['decile'])
# the old decile picks must lie in the deciles they were drawn from (2 per decile 1-8, 4 per decile 9-10)
chk = [sum(1 for s in old['dd_sample']['decile'] if s in set(d)) for d in dec]
assert chk == [2] * 8 + [4, 4], chk
rng = random.Random(20261017)
d10 = sorted((s for s in dec[9] if s not in oldsamp), key=lambda s: bnd[s])
half = len(d10) // 2
lower10, upper10 = d10[:half], d10[half:]
d9 = [s for s in dec[8] if s not in oldsamp]
new = sorted(rng.sample(upper10, 8)) + sorted(rng.sample(lower10, 4)) + sorted(rng.sample(d9, 4))
strata = {'rank9_24': rank}
for i, d in enumerate(dec): strata[f'decile{i + 1}'] = sorted(d)
restb = {k: sum(bnd[s] for s in v) for k, v in strata.items()}
tot = sum(restb[f'decile{i + 1}'] for i in range(10))
out = {'note': __doc__.split('usage:')[0].strip(), 'strata': strata, 'new_sample': new,
       'new_sample_parts': {'decile10_upper': sorted(new[:8]), 'decile10_lower': sorted(new[8:12]), 'decile9': sorted(new[12:])},
       'stratum_bound': restb, 'stratum_bound_share_of_deciles': {k: restb[k] / tot for k in restb if k != 'rank9_24'},
       'fine_bound_eps_B_new': {str(s): bnd[s] for s in new}, 'n_rest': n}
open(OUTFILE, 'w').write(json.dumps(out, indent=1) + '\n')
print('decile sizes', [len(d) for d in dec], 'n', n)
print('shares', {k: round(v, 4) for k, v in out['stratum_bound_share_of_deciles'].items()})
print('new sample', new)
