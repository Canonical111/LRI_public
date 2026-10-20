import json, sys, time
import numpy as np
from indep_ht2d import solve_spectrum, Bath

def compare(rec_path, Ks=((24,24),), M=400, extraJ=(), verbose=False):
    r = json.load(open(rec_path))
    x, L, th = r['delta'], r['bath_cut'], r['theta']
    bath = Bath(L, x)
    rows = []
    for Ke, Ko in Ks:
        t = time.time()
        o = solve_spectrum(x, th, L, M=M, Ke=Ke, Ko=Ko, nev=5, bath=bath, extraJ=extraJ, verbose=verbose)
        de = np.array(o['even']) - np.array(r['even_gaps'][:5])
        do = np.array(o['odd']) - np.array(r['odd_gaps'][:5])
        evr = {int(k): v for k, v in r['window_correction']['Ev'].items()}
        dEv = max(abs(o['Ev'][k] - evr[k]) for k in evr)
        res = dict(x=x, L=L, K=(Ke, Ko), M=M, DeltaE_indep=o['even'][1], DeltaE_rec=r['Delta_thermal'],
                   dDeltaE=o['even'][1] - r['Delta_thermal'], sigma_res=o['odd'][0] - x, shadow_res=o['odd'][1] - (2 - x),
                   max_even=float(np.abs(de).max()), max_odd=float(np.abs(do).max()), max_Ev=dEv,
                   secs=round(time.time() - t, 1), lam=o['lam'], zm_tail=o['zm_tail'])
        for J in extraJ:
            for par in (0, 1):
                mine = np.array(o[f'J{J}_{par}'])
                rec = np.array(r['diagnostics']['angular_spectra'][str(J)][str(par)])
                n = min(len(mine), len(rec))
                res[f'J{J}_{par}'] = float(np.abs(mine[:n] - rec[:n]).max())
        rows.append(res)
        print(json.dumps(res), flush=True)
    return rows

if __name__ == '__main__':
    import ast
    Ks = ast.literal_eval(sys.argv[2]) if len(sys.argv) > 2 else ((24, 24),)
    M = int(sys.argv[3]) if len(sys.argv) > 3 else 400
    J = ast.literal_eval(sys.argv[4]) if len(sys.argv) > 4 else ()
    compare(sys.argv[1], Ks, M, J)
