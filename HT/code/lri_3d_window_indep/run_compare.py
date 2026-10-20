"""Independent-solver comparison against package records: fixed-coupling replay + independent tuning."""
import sys, json, time, argparse, numpy as np
sys.path.insert(0, '.')
from indep_ht3d import Model
ap = argparse.ArgumentParser()
ap.add_argument('--L', type=int); ap.add_argument('--x', type=float); ap.add_argument('--mode', default='window')
ap.add_argument('--K', type=int, default=16); ap.add_argument('--K2', type=int, default=24)
ap.add_argument('--extract', default='indep_extract.json'); ap.add_argument('--out')
ap.add_argument('--no-tune', action='store_true')
a = ap.parse_args()
ext = json.load(open(a.extract))
e = next(e for e in ext if e['camp'] in ('grid18', 'grid18sri') and abs(e['delta'] - a.x) < 1e-9 and e['bath_cut'] == a.L
         and ((a.mode == 'window') == (e['window'] == 'vacuum')))
win = a.mode == 'window'
t0 = time.time(); m = Model(a.L, a.x); res = {'L': a.L, 'x': a.x, 'mode': a.mode, 'checks': m.checks,
                                              'pkg': {k: e[k] for k in ('r', 'g', 'Delta_thermal', 'even_gaps', 'odd_gaps', 'Ev')}}
print('setup', m.checks, flush=True)
for K in (a.K, a.K2):
    s = m.solve(e['r'], e['g'], K=K, window=win, nroots=4)
    res[f'fixed_K{K}'] = {'even': list(s['even']), 'odd': list(s['odd']), 'Ev': s['Ev'], 'tail': s['tail'],
                          'dD': s['even'][1] - e['Delta_thermal'], 'dsigma': s['odd'][0] - a.x, 'dchi': s['odd'][1] - (3 - a.x)}
    print(f'fixed K={K}: dD {res[f"fixed_K{K}"]["dD"]:+.2e} dsig {res[f"fixed_K{K}"]["dsigma"]:+.2e} dchi {res[f"fixed_K{K}"]["dchi"]:+.2e} '
          f'even {np.round(s["even"],10)} odd {np.round(s["odd"],10)} {time.time()-t0:.0f}s', flush=True)
if not a.no_tune:
    r0, g0 = e['r'] * 1.02, e['g'] * 0.98                    # deliberately displaced start (2%)
    (r, g), s, resid, ok = m.tune(r0, g0, K=a.K, window=win)
    res['tuned'] = {'r': r, 'g': g, 'resid': resid, 'ok': bool(ok), 'Delta': s['even'][1], 'even': list(s['even']),
                    'odd': list(s['odd']), 'dD': s['even'][1] - e['Delta_thermal'], 'dr': r - e['r'], 'dg': g - e['g']}
    print(f"tuned: ok {ok} resid {resid:.1e} r {r:.12f} (pkg {e['r']:.12f}) g {g:.12f} (pkg {e['g']:.12f}) "
          f"Delta {s['even'][1]:.12f} pkg {e['Delta_thermal']:.12f} diff {s['even'][1]-e['Delta_thermal']:+.2e} {time.time()-t0:.0f}s", flush=True)
res['seconds'] = time.time() - t0
json.dump(res, open(a.out or f'cmp_L{a.L}_{a.mode}_x{a.x}.json', 'w'), default=float, indent=1)
