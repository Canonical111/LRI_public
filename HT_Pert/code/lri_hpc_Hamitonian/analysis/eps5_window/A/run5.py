"""eps^5 descendant identities and C_k under raw / g2D / g2D+g3W / Dconn / Dfull(literal), with r_k, g_k
retuned per prescription.  Usage:  run5.py Lam [--nodesc] [--fullop] [--pref=11,8] [--pdesc=10,9]
Lam may be a quarter integer (cutoff phase).  Even-L and phases 1/4, 3/4: corrections vanish on the
references through eps^3, so the correction enters linearly through eps^5 and is assembled exactly by
first-order (Hellmann-Feynman) response on the raw psi_1, psi_2.  --fullop re-runs the complete corrected
Hamiltonian (diag operator + rows, full retuning) for g2D and Dconn as a check.
"""
import sys, json, time
from eng5 import *

args = [a for a in sys.argv[1:] if not a.startswith('--')]
Lam = float(args[0])
opts = {a.split('=')[0]: (a.split('=')[1] if '=' in a else True) for a in sys.argv[1:] if a.startswith('--')}
pref = tuple(int(x) for x in opts.get('--pref', '11,8').split(','))
pdesc = tuple(int(x) for x in opts.get('--pdesc', '10,9').split(','))
dodesc = '--nodesc' not in opts
fullop = '--fullop' in opts
K = 5
Lint = 2 * int(math.ceil(Lam / 2 - 1e-12))
if Lint < Lam: Lint += 2
t0 = time.time()
out = {'Lam': Lam, 'Lint': Lint, 'pref': pref, 'pdesc': pdesc}
PRES = ['g2D', 'g2D3W', 'Dconn', 'Dfull']

# ---------------- low-order couplings (exact on P<=7,q<=4 through eps^3) and the low table -------------
sp7 = Space(Lint, 7, 4, 2)
r3 = np.zeros(4); g3 = np.zeros(4)
rs_multi(sp7, [dict(seeds=[find(sp7, p, 0)[0]], mask=mask_for(sp7, 0, p % 2, Lam)) for p in (0, 1, 3)], 3, r3, g3,
         tune={'items': (0, 1, 2), 'orders': {1, 2, 3}})
del sp7
tab = low_table(Lint, r3.copy(), g3.copy(), 3)
tab = {x: np.r_[v, np.zeros(K + 1 - len(v))] for x, v in tab.items()}
sums = vacuum_table(Lint, K)
g = np.r_[g3, 0., 0.]


def alljets(pres, spx):
    """eps^2, eps^3 jets of the correction operator on every state of space spx (prescription pres)."""
    gd, _ = g2D_window(spx.Efree, Lam, g, K, sums)
    if pres == 'g2D':
        d = gd
    elif pres == 'g2D3W':
        d = gd.copy(); d[:, 3] += G1 ** 3 * Wwin(spx.Efree, Lam)
    else:
        d = dconn23(spx.Efree, Lam, tab, K)
    d = d.copy(); d[:, 4:] = 0.; d[:, :2] = 0.
    return d


def integrals(spx, rr):
    p1, p2 = rr['psi1'], rr['psi2']
    o = dict(n11=float(p1 @ p1), n12=float(p1 @ p2))
    for pres in PRES:
        dj = alljets(pres, spx)
        o[pres] = (float(p1 @ (dj[:, 2] * p1)), float(p1 @ (dj[:, 3] * p1)), float(p1 @ (dj[:, 2] * p2)))
        del dj
    return o

# ---------------- references: raw lockstep tuning through eps^5 ----------------
sp = Space(Lint, pref[0], pref[1], K - 1)
r = np.zeros(K + 1); g = np.zeros(K + 1)
refs = {p: dict(seeds=[find(sp, p, 0)[0]], mask=mask_for(sp, 0, p % 2, Lam)) for p in range(4)}
res = rs_multi(sp, [refs[p] for p in range(4)], K, r, g, tune={'items': (0, 1, 3), 'orders': set(range(1, K + 1))},
               keep=True)
items = {}
def item_record(name, sp, rr, Enames=None):
    s = rr['seeds'][0]
    rec = dict(s=s, E0=float(sp.Efree[s]), E=rr['heff'][:, 0, 0].copy(), I=integrals(sp, rr),
               mv1=rr['mv1'], M0=rr['first'][0, 0, 0], V0=rr['first'][0, 0, 1], spect=rr['spect'], spc=rr['spc'])
    return rec
for p in range(4):
    items[f'phi{p}'] = item_record(f'phi{p}', sp, res[p])
del res
assert np.abs(r[:4] - r3).max() < 1e-10 and np.abs(g[:4] - g3).max() < 1e-10, (r, r3, g, g3)
g = g.copy()
out['r_raw'] = r.tolist(); out['g_raw'] = g.tolist(); out['dim_ref'] = int(sp.dim)
if not fullop: del sp
print(f'Lam={Lam} refs dim={out["dim_ref"]} r={np.round(r,6).tolist()} g={np.round(g,6).tolist()} ({time.time()-t0:.1f}s)', flush=True)


# ---------------- descendants ----------------
spd = None
if dodesc:
    spd = Space(Lint, pdesc[0], pdesc[1], K - 1)
    dlist = {'dphi1': (1, 1, find(spd, 1, 1)), 'dphi2': (1, 0, find(spd, 2, 1)),
             'd2phi': (0, 1, find(spd, 1, 2)), 'd3phi': (1, 1, find(spd, 1, 3))}
    # P, N of seeds: a1 (P1,N1), a0a1 (P2,N1), a2 (P1,N2), a3 (P1,N3)
    for name, (Npar, Ppar, seeds) in dlist.items():
        assert len(seeds) == 1, (name, seeds)
        rr = rs_multi(spd, [dict(seeds=seeds, mask=mask_for(spd, Npar, Ppar, Lam))], K, r, g, keep=True)[0]
        rec = item_record(name, spd, rr)
        # degenerate partners (exactly degenerate states in the sector): eps^5 eigenvalue shift h_js[3]^2/(h_ss1-h_jj1)
        part = []
        for jj, j in enumerate(rec['spect']):
            x = np.zeros((spd.dim, 1)); x[j, 0] = 1.
            m, v = vertices_nomask(spd, x, 0, int(spd.P[j] % 2))
            hjj1 = spd.F1[j] + r[1] * m[j, 0] + g[1] * v[j, 0]
            c = rec['spc'][:, jj, 0]
            part.append(dict(j=int(j), P=int(spd.P[j]), N=int(spd.N[j]), coupling=c.tolist(), hjj1=float(hjj1),
                             shift5=float(c[3] ** 2 / (rec['E'][1] - hjj1)) if abs(c[1]) + abs(c[2]) < 1e-14 else None))
        rec['partners'] = part
        items[name] = rec
        del rr
        print(f'  {name} dim={spd.dim} partners={[(q["P"],q["N"],["%.1e"%y for y in q["coupling"]]) for q in part]} ({time.time()-t0:.1f}s)', flush=True)
    out['dim_desc'] = int(spd.dim)
    if not fullop: del spd

# ---------------- vacuum jets at the needed cutoffs ----------------
xs = sorted({fh(Lam)} | {fh(Lam - it['E0']) for it in items.values()})
spv = Space(Lint, 8, 8, K - 1)
Ec = {}; Er = {}
for x in xs:
    Ec[x] = vac_jets(spv, x, K, r, g, tab)
    Er[x] = vac_jets(spv, x, K, r, g, None)
out['dim_vac'] = int(spv.dim)
out['vac'] = {str(x): dict(Ec=Ec[x].tolist(), Eraw=Er[x].tolist()) for x in xs}
del spv
print(f'  vacuum tables at {xs} ({time.time()-t0:.1f}s)', flush=True)
xt = fh(Lam)


def D0win(E0):
    return float(g2D_window(np.array([E0]), Lam, np.r_[0, 1, np.zeros(K - 1)], K, sums)[1][0, 0])


def row(pres, E0, g4):
    """row jets (k=0..5) of the correction on a model state with free energy E0, with coupling g4."""
    gg = g.copy(); gg[4] = g4
    gd, _ = g2D_window(np.array([E0]), Lam, gg, K, sums)
    if pres == 'g2D':
        return gd[0]
    if pres == 'g2D3W':
        x = gd[0].copy(); x[3] += G1 ** 3 * Wwin(np.array([E0]), Lam)[0]; return x
    tabv = Ec if pres == 'Dconn' else Er
    x = tabv[xt] - tabv[fh(Lam - E0)]
    x = x.copy(); x[5] += 2 * G1 * (g4 - g[4]) * D0win(E0)
    return x


# ---------------- linear-response assembly ----------------
summary = {}
Eraw = {n: it['E'].copy() for n, it in items.items()}
for n, it in items.items():
    for q in it.get('partners', []):
        if q['shift5'] is not None: Eraw[n][5] += q['shift5']
def observables(E):
    o = {'C': (E['phi2'] - E['phi0']).tolist()}
    if dodesc:
        for nm, prim, lev in [('dphi1', 'phi1', 1), ('dphi2', 'phi2', 1), ('d2phi', 'phi1', 2), ('d3phi', 'phi1', 3)]:
            v = E[nm] - E[prim]; v[0] -= lev; o['v_' + nm] = v.tolist()
    return o
summary['raw'] = dict(r=r.tolist(), g=g.tolist(), **observables(Eraw))
for pres in PRES:
    dE = {}
    # responses with Delta r4=g4=r5=g5=0
    for n, it in items.items():
        rw = row(pres, it['E0'], g[4])
        I22, I33, I23 = it['I'][pres]; n11 = it['I']['n11']; n12 = it['I']['n12']
        e = np.zeros(K + 1)
        e[2] = rw[2]; e[3] = rw[3]
        e[4] = rw[4] + I22 - rw[2] * n11
        e[5] = rw[5] + I33 - rw[3] * n11 + 2 * (I23 - rw[2] * n12)
        dE[n] = e
    # retune: refs must stay tuned
    def solve(k):
        A_ = np.array([[items['phi1']['M0'] - items['phi0']['M0'], items['phi1']['V0'] - items['phi0']['V0']],
                       [items['phi3']['M0'] - items['phi0']['M0'], items['phi3']['V0'] - items['phi0']['V0']]])
        b_ = -np.array([dE['phi1'][k] - dE['phi0'][k], dE['phi3'][k] - dE['phi0'][k]])
        return np.linalg.solve(A_, b_)
    lowres = max(abs(dE['phi1'][k] - dE['phi0'][k]) + abs(dE['phi3'][k] - dE['phi0'][k]) for k in (2, 3))
    dr4, dg4 = solve(4)
    for n, it in items.items():
        dE[n][4] += dr4 * it['M0'] + dg4 * it['V0']
        dE[n][5] += dr4 * it['mv1'][0] + dg4 * it['mv1'][1] + 2 * G1 * dg4 * D0win(it['E0'])
    dr5, dg5 = solve(5)
    for n, it in items.items():
        dE[n][5] += dr5 * it['M0'] + dg5 * it['V0']
    E = {n: Eraw[n] + dE[n] for n in items}
    s = dict(dr4=dr4, dg4=dg4, dr5=dr5, dg5=dg5, low_order_ref_residual=lowres, **observables(E))
    s['dC'] = (dE['phi2'] - dE['phi0']).tolist()
    s['rows'] = {n: row(pres, it['E0'], g[4] + dg4).tolist() for n, it in items.items()}
    s['dE'] = {n: dE[n].tolist() for n in items}
    summary[pres] = s
out['summary'] = summary
out['items'] = {n: dict(E0=it['E0'], E=it['E'].tolist(), M0=it['M0'], V0=it['V0'], mv1=list(it['mv1']),
                        I=it['I'], partners=it.get('partners', [])) for n, it in items.items()}
print(f'  assembled ({time.time()-t0:.1f}s)', flush=True)

# ---------------- optional: complete corrected Hamiltonian (check of the linear assembly) ----------------
if fullop:
    out['fullop'] = {}
    for pres in ('g2D', 'Dconn'):
        g4f = g[4] + summary[pres]['dg4']
        rr = np.zeros(K + 1); gg = np.zeros(K + 1)
        dj = alljets(pres, sp)
        its = []
        for p in range(4):
            s0 = refs[p]['seeds'][0]
            its.append(dict(seeds=refs[p]['seeds'], mask=refs[p]['mask'], row=row(pres, p / 4, g4f) - dj[s0]))
        res = rs_multi(sp, its, K, rr, gg, diag=dj, tune={'items': (0, 1, 3), 'orders': set(range(1, K + 1))})
        Ef = {f'phi{p}': res[p]['heff'][:, 0, 0].copy() for p in range(4)}
        if dodesc:
            djd = alljets(pres, spd)
            for name, (Npar, Ppar, seeds) in dlist.items():
                rw = row(pres, float(spd.Efree[seeds[0]]), g4f) - djd[seeds[0]]
                x = rs_multi(spd, [dict(seeds=seeds, mask=mask_for(spd, Npar, Ppar, Lam), row=rw)], K, rr, gg, diag=djd)[0]
                Ef[name] = x['heff'][:, 0, 0].copy()
                for q in items[name]['partners']:
                    if q['shift5'] is not None: Ef[name][5] += q['shift5']
        o = dict(r=rr.tolist(), g=gg.tolist(), **observables(Ef))
        out['fullop'][pres] = o
        dev = max(abs(o['C'][k] - summary[pres]['C'][k]) for k in range(K + 1))
        devv = max([abs(o[k_][j] - summary[pres][k_][j]) for k_ in o if k_.startswith('v_') for j in range(K + 1)] + [0])
        print(f'  fullop {pres}: max|C diff|={dev:.2e} max|v diff|={devv:.2e} dg4 {gg[4]-g[4]:+.3e} vs {summary[pres]["dg4"]:+.3e} ({time.time()-t0:.1f}s)', flush=True)

out['seconds'] = time.time() - t0
tag = opts.get('--tag', '')
json.dump(out, open(f'res5_{Lam:g}{tag}.json', 'w'))
for pres in ['raw'] + PRES:
    s = summary[pres]
    line = f' [{pres:6s}] C4={s["C"][4]:+.10f} C5={s["C"][5]:+.10f}'
    if dodesc:
        line += ' | v5 ' + ' '.join(f'{k[2:]}={s[k][5]:+.6f}' for k in s if k.startswith('v_'))
        line += ' | v4 ' + ' '.join(f'{k[2:]}={s[k][4]:+.6f}' for k in s if k.startswith('v_'))
    print(line)
print(f'total {time.time()-t0:.1f}s')
