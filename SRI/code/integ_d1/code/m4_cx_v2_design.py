"""Pre-set design of the double-double rerun of the complex-K delta^0 check at K_B (host decision 2026-10-16).
Uses only engine data of the v1 K_B run (results/m4_runs/prod/cxB), never the Bethe-ansatz value:
  per sector the first-order roundoff bound eps*B = 2^-53 |Gamma(7 - 8K)| B_s(0,0) w_s fac_s; sectors sorted by it
  (descending); the dd set is the shortest prefix after which the summed bound of the remaining double sectors is
  <= 1e-13 |J_engine(K_B)|. Everything else as in v1: grid (12,18,14), taurat 0.2, tau 0.5, the same K_B doubles,
  the mirror-reduced set; non-dd sectors keep their v1 double outputs.
usage: python m4_cx_v2_design.py   -> results/m4_inputs/cx_v2_design.json"""
import sys, os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mpmath as mp
import provenance as pv
from cluster_assemble import read_many, assemble_cx, pattern_factors, gamma_derivs
mp.mp.dps = 30
RES = pv.RES
OUTFILE = os.path.join(RES, 'm4_inputs', 'cx_v2_design.json')
if os.path.exists(OUTFILE):    # fix round 4 (MSC-028): a committed design is never overwritten
    sys.exit(f'refusing to overwrite the existing design {OUTFILE}')
manifest = json.load(open(os.path.join(RES, 'm4_inputs', 'n4.manifest.json')))
w = json.load(open(os.path.join(RES, 'm4_inputs', 'n4.mirror.json')))['weights']
expected = [s for s, x in enumerate(w) if x > 0]
files = sorted(glob.glob(os.path.join(RES, 'm4_runs', 'prod', 'cxB', '*.out')))
h, secs, hd = read_many(files, manifest, expected=expected)
kd = [float.fromhex(x) for x in h['Kdd']]
K = mp.mpc(kd[0] + kd[1], kd[2] + kd[3])
J, _ = assemble_cx(4, secs, K, 0, weights=w)
G = abs(gamma_derivs(7 - 8 * K, 0)[0])
fac = pattern_factors(4)
b = {s: float(G * sec['B'][(0, 0)] * w[s] * fac[sec['pat']] * mp.mpf(2) ** -53) for s, sec in secs.items()}
order = sorted(b, key=lambda s: -b[s])
target = float(mp.mpf('1e-13') * abs(J[0]))
rest = sum(b.values()); n = 0
while rest > target:
    rest -= b[order[n]]; n += 1
dd = sorted(order[:n])
out = {'note': __doc__.split('usage:')[0].strip(), 'K': [h['Kdd'][0], h['Kdd'][2]], 'grid': [12, 18, 14], 'taurat': 0.2, 'tau': 0.5,
       'abs_J_engine': float(abs(J[0])), 'target_remaining_bound': target, 'total_bound': sum(b.values()),
       'remaining_bound_after_dd': rest, 'dd_sectors': dd, 'dd_bounds': {str(s): b[s] for s in dd},
       'v1_sources': {os.path.relpath(f, os.path.dirname(RES)): pv.sha256_file(f) for f in files}}
open(OUTFILE, 'w').write(json.dumps(out, indent=1) + '\n')
print(f'|J_engine| {float(abs(J[0])):.6g}; total bound {sum(b.values()):.3g} ({sum(b.values()) / float(abs(J[0])):.3g} rel); '
      f'dd prefix {n} sectors; remaining {rest:.3g} <= target {target:.3g}')
