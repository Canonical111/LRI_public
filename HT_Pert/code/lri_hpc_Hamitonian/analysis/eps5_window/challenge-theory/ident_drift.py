"""Skeptic check of the eps^5 identity extrapolations: drift of the extrapolated v5(dphi) with the upper end Lmax of the
data (same tail families as the reconciler), and the same at eps^4 for comparison.  A limit that drifts steadily with
Lmax is not converged; its spread across families at fixed Lmax understates the uncertainty."""
import json, numpy as np, sys
R = '<TMP>/scratchpad/eps5/reconcile'
D = {float(k): v for k, v in json.load(open(R + '/ident_union.json')).items()}
F = {'a': ['1', 'x', 'x2', 'x3', 'x4'], 'b': ['1', 'x', 'xl', 'x2', 'x3'], 'c': ['1', 'x', 'xl', 'x2', 'x2l', 'x3'],
     'd': ['1', 'x', 'xl', 'xl2', 'x2', 'x3'], 'e': ['1', 'x', 'xl', 'xl2', 'x2', 'x2l'], 'g': ['1', 'x', 'x2', 'x2l', 'x3', 'x4'],
     'f_rich': ['1', 'x', 'xl', 'xl2', 'xl3', 'x2', 'x2l']}
def col(n, L):
    x = L ** -.5; l = np.log(L)
    return {'1': np.ones_like(L), 'x': x, 'xl': x * l, 'xl2': x * l * l, 'xl3': x * l ** 3, 'x2': x * x, 'x2l': x * x * l, 'x3': x ** 3, 'x4': x ** 4}[n]
def fit(L, y, fam):
    X = np.column_stack([col(n, L) for n in F[fam]]); s = np.linalg.norm(X, axis=0)
    p = np.linalg.lstsq(X / s, y, rcond=None)[0] / s
    return p[0]
out = {}
for ph in (0.0, 0.25, 0.75):
    Ls = np.array(sorted(l for l in D if abs(l % 2 - ph) < 1e-9 and l >= 8))
    for var in ('g2D3W', 'Dconn'):
        for k in (4, 5):
            LL = np.array([l for l in Ls if 'v_dphi1' in D[l][var]])
            y = np.array([D[l][var]['v_dphi1'][k] for l in LL])
            print(f'phase {ph} {var} eps^{k}: last value at L={LL[-1]:g}: {y[-1]:+.4f}')
            for lmax in (40, 48, 56, LL.max()):
                vals = {}
                for fam in F:
                    m = (LL >= 16) & (LL <= lmax + 1e-9)
                    if m.sum() < len(F[fam]) + 3: continue
                    vals[fam] = fit(LL[m], y[m], fam)
                out[f'{ph}|{var}|{k}|{lmax:g}'] = vals
                print(f'   Lmax={lmax:6.2f}: ' + ' '.join(f'{f}:{v:+.3f}' for f, v in vals.items()))
json.dump(out, open('ident_drift.json', 'w'), indent=1)
