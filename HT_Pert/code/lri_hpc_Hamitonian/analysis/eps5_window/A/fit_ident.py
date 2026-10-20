"""Extrapolate eps^4 / eps^5 descendant-identity violations v_k(L) (k=4,5) per prescription and cutoff phase.
Tail families (x = L^-1/2, z = log L); each fitted on L >= Lmin for several Lmin; non-decaying log allowed
only in the explicitly labelled 'nl' families.  Output: fits_ident.json + printed table (central = median over
the decaying families with residual <= 10 x best; range = min..max over those)."""
import json, glob, sys, math
import numpy as np

phase = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
LMINS = [int(a) for a in sys.argv[2].split(',')] if len(sys.argv) > 2 else [16, 24, 32]
FAM = {
    'a': lambda x, z: [x ** 0, x, x ** 2, x ** 3, x ** 4],
    'b': lambda x, z: [x ** 0, x, x * z, x ** 2, x ** 3],
    'c': lambda x, z: [x ** 0, x, x ** 2, x ** 2 * z, x ** 3],
    'd': lambda x, z: [x ** 0, x, x * z, x * z * z, x ** 2, x ** 3],
    'e': lambda x, z: [x ** 0, x, x * z, x ** 2, x ** 2 * z, x ** 3],
    'f': lambda x, z: [x ** 0, x, x * z, x * z * z, x ** 2, x ** 2 * z],
    'g': lambda x, z: [x ** 0, x, x * z, x * z ** 2, x * z ** 3, x ** 2],
    'h': lambda x, z: [x ** 0, x, x * z, x * z ** 2, x * z ** 3, x ** 2, x ** 2 * z],
    'j': lambda x, z: [x ** 0, x, x * z, x * z ** 2, x ** 2, x ** 2 * z, x ** 2 * z ** 2],
    'nl1': lambda x, z: [x ** 0, z, x, x * z, x ** 2, x ** 3],
    'nl2': lambda x, z: [x ** 0, z, x, x * z, x * z * z, x ** 2],
}
DECAY = ['a', 'b', 'c', 'd', 'e', 'f']
RICH = ['g', 'h', 'j']


def fitone(L, y, fam, lmin):
    m = L >= lmin
    if m.sum() < len(FAM[fam](1., 1.)) + 2: return None
    x = L[m] ** -0.5; z = np.log(L[m])
    X = np.column_stack(FAM[fam](x, z))
    s = np.linalg.norm(X, axis=0)
    p = np.linalg.lstsq(X / s, y[m], rcond=None)[0] / s
    res = float(np.max(np.abs(X @ p - y[m])))
    return dict(c0=float(p[0]), log=float(p[1]) if fam.startswith('nl') else 0., res=res)


def load(phase):
    data = {}
    for f in glob.glob('res5_*.json'):
        o = json.load(open(f))
        Lam = o['Lam']
        if abs((Lam - 2 * math.floor(Lam / 2)) - phase) > 1e-9: continue
        data[Lam] = o['summary']
    return data


if __name__ == '__main__':
    data = load(phase)
    Ls = np.array(sorted(data))
    print(f'phase {phase}: {len(Ls)} cutoffs {Ls.min()}..{Ls.max()}')
    out = {}
    pres = ['raw', 'g2D', 'g2D3W', 'Dconn', 'Dfull']
    keys = [k for k in data[Ls[0]]['raw'] if k.startswith('v_')]
    for key in keys:
        for k in (3, 4, 5):
            for p in pres:
                y = np.array([data[l][p][key][k] for l in Ls])
                fits = {}
                for fam in FAM:
                    for lm in LMINS:
                        r = fitone(Ls, y, fam, lm)
                        if r: fits[f'{fam}@{lm}'] = r
                dec = {n: r for n, r in fits.items() if n.split('@')[0] in DECAY}
                best = min(r['res'] for r in dec.values())
                good = [r['c0'] for r in dec.values() if r['res'] <= 10 * best]
                nl = {n: r for n, r in fits.items() if n.startswith('nl')}
                rich = [r['c0'] for n, r in fits.items() if n.split('@')[0] in RICH and int(n.split('@')[1]) >= max(LMINS)]
                out[f'{key}|e{k}|{p}'] = dict(central=float(np.median(good)), lo=float(min(good)), hi=float(max(good)),
                                              all_decaying=[float(min(r['c0'] for r in dec.values())), float(max(r['c0'] for r in dec.values()))],
                                              best_res=best, finite={str(l): float(v) for l, v in zip(Ls[-3:], y[-3:])},
                                              rich_log3_at_maxLmin=[float(min(rich)), float(max(rich))] if rich else None,
                                              nonlocal_log={n: (r['c0'], r['log'], r['res']) for n, r in nl.items()})
                o = out[f'{key}|e{k}|{p}']
                nlogs = [v[1] for v in o['nonlocal_log'].values()]
                print(f'{key:9s} e{k} {p:6s} lim {o["central"]:+.5f} [{o["lo"]:+.5f},{o["hi"]:+.5f}] all[{o["all_decaying"][0]:+.4f},{o["all_decaying"][1]:+.4f}] res {best:.1e} | rich(x log^3, Lmin {max(LMINS)}) [{o["rich_log3_at_maxLmin"][0]:+.3f},{o["rich_log3_at_maxLmin"][1]:+.3f}] | L={Ls[-1]:g}: {y[-1]:+.5f} | free-log coef {min(nlogs):+.4f}..{max(nlogs):+.4f}')
    json.dump(out, open(f'fits_ident_ph{phase:g}.json', 'w'), indent=1)
