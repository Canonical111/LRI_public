"""Complete Delta C4, Delta C5 (prescription minus raw) at every even L = 8..118 from the building blocks
(res5_L.json for L<=72, c5tab_L.json for 58<=L<=118).  Reference-window contents W8_k(L) = Ec(L)-Ec(L-1/2),
W6_k(L) = Ec(L-1/2)-Ec(L-1) are computed up to L=Lv (local memory limit) and continued beyond by a fitted
smooth form (eps^4: exact top-level sums of challenge-num/top_a.jsonl are used to L=288).
Writes dC_table.json."""
import json, glob, math, sys
sys.dont_write_bytecode = True
import numpy as np

PRES = ['g2D', 'g2D3W', 'Dconn', 'Dfull']
top = {}
for line in open('<PROJECT>/lri_hpc_Hamitonian/analysis/identity_checks/challenge-num/top_a.jsonl'):
    d = json.loads(line); top[d['L']] = d

blocks = {}   # L -> dict(refs={p: rec}, vac={x: dict(Ec, Eraw)})
for f in glob.glob('res5_*.json'):
    o = json.load(open(f))
    if o['Lam'] != int(o['Lam']): continue
    L = int(o['Lam'])
    refs = {p: dict(M0=o['items'][f'phi{p}']['M0'], V0=o['items'][f'phi{p}']['V0'], mv1=o['items'][f'phi{p}']['mv1'],
                    **{k: o['items'][f'phi{p}']['I'][k] for k in ['n11', 'n12'] + PRES}) for p in range(4)}
    blocks[L] = dict(refs=refs, vac=o['vac'], src='res5', raw_r=o['r_raw'], raw_g=o['g_raw'],
                     summary=o['summary'])
for f in glob.glob('c5tab_*.json'):
    tag = f[len('c5tab_'):-5]
    if not tag.isdigit(): continue
    o = json.load(open(f)); L = o['L']
    refs = {int(p): v for p, v in o['refs'].items()}
    if L in blocks:   # cross-check overlap
        b = blocks[L]
        dmax = max(abs(np.array(refs[p][k]) - np.array(b['refs'][p][k])).max() for p in range(4) for k in PRES)
        dvac = max(abs(np.array(o['vac'][x]['Ec']) - np.array(b['vac'][x]['Ec']))[4:].max() for x in o.get('vac', {})) if 'vac' in o else 0.
        blocks[L]['check_c5tab'] = (float(dmax), float(dvac))
        if 'vac' in o:
            blocks[L]['vac_q'] = o['vac']
        continue
    blocks[L] = dict(refs=refs, vac=o.get('vac'), src='c5tab')

Ls = sorted(blocks)
# window contents
W = {}
for L in Ls:
    v = blocks[L]['vac']
    if v is None: continue
    g = lambda x, key: np.array(v[str(float(x))][key])
    W[L] = dict(W8=g(L, 'Ec') - g(L - .5, 'Ec'), W6=g(L - .5, 'Ec') - g(L - 1, 'Ec'),
                W8r=g(L, 'Eraw') - g(L - .5, 'Eraw'), W6r=g(L - .5, 'Eraw') - g(L - 1, 'Eraw'))
Lv = max(W)
LW = np.array(sorted(W), float)
# eps^4 checks against exact top sums
chk4 = max(max(abs(W[L]['W8'][4] - top[L]['Yc'] / 81), abs(W[L]['W6'][4] - top[L]['Z'] / 81),
               abs(W[L]['W8r'][4] - top[L]['P8top'] / 81)) for L in W)
print(f'window data L={int(LW.min())}..{Lv}; eps^4 vs exact top sums max diff {chk4:.1e}')

# smooth continuation of the eps^5 window contents beyond Lv
BAS = {
    'A': lambda L: [L ** 0, np.log(L), L ** -.5, L ** -1, np.log(L) / L, L ** -1.5, L ** -2],
    'B': lambda L: [L ** 0, np.log(L), L ** -1, np.log(L) / L, L ** -2, np.log(L) / L ** 2, L ** -3],
    'C': lambda L: [L ** 0, np.log(L), L ** -.5, np.log(L) * L ** -.5, L ** -1, np.log(L) / L, L ** -1.5],
    'D': lambda L: [L ** 0, L ** -.5, L ** -1, np.log(L) / L, L ** -1.5, L ** -2, np.log(L) / L ** 2],
}


def fitw(key, k, bas, lo=30, hi=None):
    m = (LW >= lo) & (LW <= (hi or Lv))
    y = np.array([W[int(L)][key][k] for L in LW[m]])
    X = np.column_stack(BAS[bas](LW[m]))
    s = np.linalg.norm(X, axis=0)
    p = np.linalg.lstsq(X / s, y, rcond=None)[0] / s
    return p, float(np.max(np.abs(X @ p - y)))


def evalw(p, bas, L):
    return float(np.array(BAS[bas](np.array([float(L)]))).ravel() @ p)


fitinfo = {}
cont = {}
for key in ('W8', 'W6', 'W8r', 'W6r'):
    fitinfo[key] = {}
    for bas in BAS:
        p, res = fitw(key, 5, bas)
        # hold-out: fit to Lv-16, predict Lv
        ph, _ = fitw(key, 5, bas, hi=Lv - 16)
        ho = evalw(ph, bas, Lv) - W[Lv][key][5]
        fitinfo[key][bas] = dict(par=p.tolist(), res=res, holdout16=ho, c0=float(p[0]),
                                 log=float(p[1]) if bas in 'ABC' else 0.)
    cont[key] = fitinfo[key]['A']['par']
print('eps^5 window fits (L>=30): coefficient of 1, log L; max residual; hold-out error at Lv from L<=Lv-16')
for key in fitinfo:
    print('  ', key, ' '.join(f"{b}: c0={v['c0']:+.6f} log={v['log']:+.6f} res={v['res']:.1e} ho={v['holdout16']:+.1e}" for b, v in fitinfo[key].items()))


def window(L, key, k, bas='A'):
    if L in W:
        return float(W[L][key][k])
    if k == 4:
        return {'W8': top[L]['Yc'], 'W6': top[L]['Z'], 'W8r': top[L]['P8top'], 'W6r': top[L]['Z']}[key] / 81
    return evalw(np.array(fitinfo[key][bas]['par']), bas, L)


def assemble(L, bas='A'):
    R = blocks[L]['refs']
    out = {}
    for pres in PRES:
        X = {4: [0.] * 4, 5: [0.] * 4}
        if pres in ('Dconn', 'Dfull'):
            k8, k6 = ('W8', 'W6') if pres == 'Dconn' else ('W8r', 'W6r')
            for k in (4, 5):
                w8 = window(L, k8, k, bas); w6 = window(L, k6, k, bas)
                X[k] = [0., w8, w8, w8 + w6]
        dE = {}
        for p in range(4):
            I22, I33, I23 = R[p][pres]
            dE[p] = np.array([0, 0, 0, 0, X[4][p] + I22, X[5][p] + I33 + 2 * I23])
        M0 = [R[p]['M0'] for p in range(4)]; V0 = [R[p]['V0'] for p in range(4)]
        A_ = np.array([[M0[1] - M0[0], V0[1] - V0[0]], [M0[3] - M0[0], V0[3] - V0[0]]])
        solve = lambda k: np.linalg.solve(A_, -np.array([dE[1][k] - dE[0][k], dE[3][k] - dE[0][k]]))
        dr4, dg4 = solve(4)
        for p in range(4):
            dE[p][4] += dr4 * M0[p] + dg4 * V0[p]
            dE[p][5] += dr4 * R[p]['mv1'][0] + dg4 * R[p]['mv1'][1]
        dr5, dg5 = solve(5)
        for p in range(4):
            dE[p][5] += dr5 * M0[p] + dg5 * V0[p]
        out[pres] = dict(dC4=float(dE[2][4] - dE[0][4]), dC5=float(dE[2][5] - dE[0][5]), dr4=float(dr4), dg4=float(dg4),
                         dr5=float(dr5), dg5=float(dg5), window_measured=L in W)
    return out


if __name__ == '__main__':
    sys.path.insert(0, '<PROJECT>/lri_eh_hpc/lri_eh')
    from exact import fast
    pk = json.load(open('<PROJECT>/lri_hpc_Hamitonian/analysis/eh_addon_review/physics-impact/d5_all.json'))
    pkd = {}
    if isinstance(pk, dict):
        for k, v in pk.items():
            try: pkd[int(k)] = v
            except ValueError: pass
    else:
        for r in pk: pkd[r['cutoff']] = r
    table = {}
    worst = dict(c4=0., c5pkg=0., res5=0., alt=0.)
    for L in Ls:
        a = assemble(L)
        alt = assemble(L, 'C')
        a['alt_window_basis_dC5_Dconn'] = alt['Dconn']['dC5']
        worst['alt'] = max(worst['alt'], abs(alt['Dconn']['dC5'] - a['Dconn']['dC5']))
        worst['c4'] = max(worst['c4'], abs(a['g2D']['dC4'] - fast(L)))
        if L in pkd:
            v = pkd[L]
            dc = v['delta_C'] if isinstance(v, dict) and 'delta_C' in v else v
            worst['c5pkg'] = max(worst['c5pkg'], abs(a['g2D']['dC5'] - dc[5]))
        b = blocks[L]
        if 'summary' in b:
            S = b['summary']
            for pres in PRES:
                worst['res5'] = max(worst['res5'], abs(a[pres]['dC5'] - (S[pres]['C'][5] - S['raw']['C'][5])),
                                    abs(a[pres]['dC4'] - (S[pres]['C'][4] - S['raw']['C'][4])))
        a['check_c5tab_vs_res5'] = b.get('check_c5tab')
        table[L] = a
    print('checks: max|g2D dC4 - exact formula| = %.1e ; max|g2D dC5 - package d5_all| = %.1e ; max|assembly - res5 full| = %.1e ; window-basis A vs C (L>Lv) = %.1e'
          % (worst['c4'], worst['c5pkg'], worst['res5'], worst['alt']))
    json.dump(dict(Lv=Lv, fitinfo=fitinfo, table={str(L): v for L, v in table.items()}), open('dC_table.json', 'w'), indent=1)
    print('  L   dC4(g2D)       dC5(g2D)       dC5(g2D3W)     dC4(Dconn)     dC5(Dconn)      dC5(Dfull)   meas')
    for L in Ls:
        a = table[L]
        print(f"{L:4d} {a['g2D']['dC4']:.10f} {a['g2D']['dC5']:.10f} {a['g2D3W']['dC5']:.10f} {a['Dconn']['dC4']:.10f} {a['Dconn']['dC5']:.10f} {a['Dfull']['dC5']:.10f} {int(a['Dconn']['window_measured'])}")
