"""Descendant-spacing identities through eps^4 under three prescriptions
(raw, + g(eps)^2 D(eps) operator, + Dfull = E_vac(L)-E_vac(L-E0) operator),
r4,g4 retuned per prescription.  Usage: run_desc.py L [pmax qmax] [--fullop]
--fullop: also run the complete Dfull diagonal OPERATOR (needs the whole E_vac(L')
table, 2L+1 vacuum RS runs) to verify the diagonal-at-state shortcut.
"""
import sys, time, json
from ht4 import *

L = int(sys.argv[1])
pm = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith('-') else 12
qm = int(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith('-') else 9
fullop = '--fullop' in sys.argv
K = 4
t0 = time.time()
sp = Space(L, pm, qm, 3)
tb = time.time() - t0
_, Ecal, rcal, gcal = calibrate(sp, 4)
r0 = rcal.copy(); g0 = gcal.copy(); r0[4] = 0.; g0[4] = 0.

# ---- states -------------------------------------------------------------
states = {}            # name -> list of seed indices (block)
for n in range(0, 5):
    if n + 8 <= pm: states[f'phi{n}'] = find(sp, n, 0)
for n in range(1, 5):
    if n + 8 <= pm and 1 + 8 <= qm:
        states[f'dphi{n}'] = [i for i in find(sp, n, 1)]
if 9 <= pm and 9 <= qm:
    states['d2phi'] = find(sp, 1, 2)
    states['d3phi'] = find(sp, 1, 3)
if 10 <= pm and 10 <= qm:
    states['P2N2'] = find(sp, 2, 2)        # {a0 a2, a1 a1}
for k, v in states.items():
    if not k.startswith('P2N2'): assert len(v) == 1, (k, v)

# ---- vacuum table for Dfull at the states' own E0 ----------------------
E0s = sorted({float(sp.Efree[v[0]]) for v in states.values()})
grid = sorted({math.floor(2 * (L - e) + 1e-9) / 2 for e in E0s} | {float(L)})
Ev = {Lp: evac(sp, Lp, K, r0, g0) for Lp in grid}
g2 = g2D_jets(sp, g0, K)                    # operator jets (dim, K+1)
def dfull_at(E0):
    Lp = math.floor(2 * (L - E0) + 1e-9) / 2
    return Ev[float(L)] - Ev[Lp]

full_tab = None
if fullop:
    full_tab = {x / 2: evac(sp, x / 2, K, r0, g0) for x in range(0, 2 * L + 1)}
    Lpj = np.floor(2 * (L - sp.Efree) + 1e-9) / 2
    DF = np.zeros((sp.dim, K + 1))
    keys = np.array(sorted(full_tab)); vals = np.array([full_tab[k] for k in keys])
    idx = np.searchsorted(keys, Lpj)
    assert np.all(keys[idx] == Lpj)
    DF = vals[-1][None, :] - vals[idx]

out = {'L': L, 'pmax': pm, 'qmax': qm, 'dim': int(sp.dim), 'r_cal': rcal.tolist(), 'g_cal': gcal.tolist(),
       'Evac': {str(k): v.tolist() for k, v in Ev.items()}, 'states': {}}
res = {}
for name, seeds in states.items():
    mask = sector_mask(sp, seeds[0])
    E0 = float(sp.Efree[seeds[0]])
    rec = {'E0': E0, 'W': window_W(L, E0), 'seeds': seeds}
    h_raw, first, spect, spc = block_rs(sp, seeds, K, r0, g0, mask)
    h_g2, _, _, _ = block_rs(sp, seeds, K, r0, g0, mask, diag=g2)
    dd = dfull_at(E0)
    g2s = g2[seeds[0]]
    h_df = h_g2.copy()
    for k in range(K + 1):
        h_df[k] += (dd[k] - g2s[k]) * np.eye(len(seeds))
    rec.update(h_raw=h_raw.tolist(), h_g2D=h_g2.tolist(), h_Dfull=h_df.tolist(),
               M0=first[:, :, 0].tolist(), V0=first[:, :, 1].tolist(),
               Dfull_s=dd.tolist(), g2D_s=g2s.tolist(),
               spectators=[(int(j), int(sp.P[j]), int(sp.N[j])) for j in spect],
               spect_coupling_max=[float(np.max(np.abs(spc[k]))) if len(spect) else 0. for k in range(K + 1)])
    if fullop:
        h_fo, _, _, _ = block_rs(sp, seeds, K, r0, g0, mask, diag=DF)
        rec['h_Dfull_op'] = h_fo.tolist()
    out['states'][name] = rec
    print(f'  {name} done ({time.time()-t0:.1f}s)', flush=True)

# ---- retuning and observables --------------------------------------------
def retune(pres):
    S = out['states']
    e = {p: np.array(S[f'phi{p}'][pres])[:, 0, 0] for p in (0, 1, 3)}
    r4 = -(e[1][4] - e[0][4]) / 2
    g4 = (-(e[3][4] - e[0][4]) - 6 * r4) / 3
    return r4, g4
summary = {}
for pres in ('h_raw', 'h_g2D', 'h_Dfull') + (('h_Dfull_op',) if fullop else ()):
    r4, g4 = retune(pres)
    E = {}
    for name, rec in out['states'].items():
        H = np.array(rec[pres]).copy()
        H[4] += r4 * np.array(rec['M0']) + g4 * np.array(rec['V0'])
        if H.shape[1] == 1:
            E[name] = [H[:, 0, 0]]
        else:
            E[name] = series_eig2(H)
    s = {'r4': r4, 'g4': g4}
    s['C'] = (E['phi2'][0] - E['phi0'][0]).tolist()
    for n in range(1, 5):
        if f'dphi{n}' in E:
            v = E[f'dphi{n}'][0] - E[f'phi{n}'][0]; v[0] -= 1
            s[f'v_dphi{n}'] = v.tolist()
    if 'd2phi' in E:
        v = E['d2phi'][0] - E['phi1'][0]; v[0] -= 2; s['v_d2phi'] = v.tolist()
        v = E['d3phi'][0] - E['phi1'][0]; v[0] -= 3; s['v_d3phi'] = v.tolist()
    if 'P2N2' in E:
        br = [x - E['phi2'][0] for x in E['P2N2']]
        for x in br: x[0] -= 2
        # descendant branch = the one with zero eps^1 relative coefficient
        br.sort(key=lambda x: abs(x[1]))
        s['v_P2N2_desc'] = br[0].tolist(); s['P2N2_prim_rel'] = br[1].tolist()
    summary[pres] = s
out['summary'] = summary
out['check_raw_r4g4'] = [summary['h_raw']['r4'] - rcal[4], summary['h_raw']['g4'] - gcal[4]]
out['seconds'] = time.time() - t0; out['build_seconds'] = tb
json.dump(out, open(f'desc_L{L}_p{pm}q{qm}.json', 'w'))
print(f'L={L} dim={sp.dim} build {tb:.1f}s total {time.time()-t0:.1f}s  rawr4g4 check {out["check_raw_r4g4"]}')
for pres, s in summary.items():
    print(f' [{pres}] r4={s["r4"]:+.6f} g4={s["g4"]:+.6f} C4={s["C"][4]:+.8f}')
    for k, v in s.items():
        if k.startswith('v_'):
            print(f'    {k:14s} ' + ' '.join(f'e{j}:{v[j]:+.8f}' for j in range(1, 5)))
for name, rec in out['states'].items():
    if rec['spectators']:
        print('  spectators', name, rec['spectators'], 'coupling max by order', ['%.1e' % x for x in rec['spect_coupling_max']])
