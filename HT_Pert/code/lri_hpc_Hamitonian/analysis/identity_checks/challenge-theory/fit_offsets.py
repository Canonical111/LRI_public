"""Extrapolate the dphi identity v_k = E(dphi)-E(phi)-1 (and C_k) at fixed cutoff phase
Lam = L + delta (L even) with the same tail families the reconciler used (x = L^-1/2)."""
import json, glob, sys
import numpy as np
HERE = '<TMP>/scratchpad/identity/challenge-theory/'
A = json.load(open(HERE + '../A/analysis_table.json'))
FAM = {
 'x,x2,x3': [(1, 0), (2, 0), (3, 0)],
 'x,x2,x3,x4': [(1, 0), (2, 0), (3, 0), (4, 0)],
 'x,xl,x2,x3': [(1, 0), (1, 1), (2, 0), (3, 0)],
 'x,xl,x2,x3,x4': [(1, 0), (1, 1), (2, 0), (3, 0), (4, 0)],
 'x,x2,x2l,x3': [(1, 0), (2, 0), (2, 1), (3, 0)],
 'x,xl,xl2,x2,x3': [(1, 0), (1, 1), (1, 2), (2, 0), (3, 0)],
 'x,xl,xl2,x2,x2l,x3': [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (3, 0)],
 'x,xl,x2,x2l,x3,x3l,x4': [(1, 0), (1, 1), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0)],
 'x2,x3,x4 (no x)': [(2, 0), (3, 0), (4, 0)],
 'x2,x2l,x3,x4 (no x)': [(2, 0), (2, 1), (3, 0), (4, 0)],
}
def cols(L, t):
    x = L ** -0.5; z = np.log(L)
    return np.column_stack([np.ones_like(L)] + [x ** p * z ** q for p, q in t])

def fits(L, y, lmins=(16, 24, 32), tol=None):
    rows = []
    for fn, t in FAM.items():
        for lo in lmins:
            m = L >= lo; X = cols(L[m], t)
            if m.sum() < X.shape[1] + 3: continue
            c = np.linalg.lstsq(X, y[m], rcond=None)[0]
            rows.append((fn, lo, int(m.sum()), c[0], float(np.max(np.abs(X @ c - y[m])))))
    return rows

def load_phase(ph):
    d = {}
    for f in glob.glob(HERE + f'offset_ph{ph}*.json'):
        for o in json.load(open(f)):
            d[o['Lam']] = o
    Lams = sorted(d)
    return np.array(Lams), d

if __name__ == '__main__':
    phases = sys.argv[1:] or ['0.25', '0.5', '0.75', '1.25']
    summary = {}
    for ph in phases:
        Lams, d = load_phase(ph)
        if len(Lams) == 0: continue
        L = Lams - float(ph)
        for q, k in [('v_dphi', 2), ('v_dphi', 3), ('v_dphi', 4), ('C', 4)]:
            for sch in ('raw', 'corr'):
                y = np.array([d[l][sch][q][k] for l in Lams])
                rows = fits(L, y)
                c = np.array([r[3] for r in rows])
                tight = [r for r in rows if r[4] < 1e-6]
                ct = np.array([r[3] for r in tight]) if tight else np.array([np.nan])
                key = f'ph{ph}|{q}|e{k}|{sch}'
                summary[key] = dict(Lmax=float(Lams[-1]), last=float(y[-1]), all_lo=float(c.min()), all_hi=float(c.max()),
                                    median=float(np.median(c)), tight_n=len(tight), tight_lo=float(np.nanmin(ct)), tight_hi=float(np.nanmax(ct)),
                                    rows=[dict(b=r[0], lo=r[1], n=r[2], c0=r[3], res=r[4]) for r in rows])
                print(f'{key:24s} Lam<= {Lams[-1]:6.2f} last={y[-1]:+.6f} median={np.median(c):+.5f} all[{c.min():+.5f},{c.max():+.5f}] '
                      f'res<1e-6: n={len(tight)} [{np.nanmin(ct):+.5f},{np.nanmax(ct):+.5f}]')
    json.dump(summary, open(HERE + 'fit_offsets.json', 'w'), indent=1)
