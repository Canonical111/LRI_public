#!/usr/bin/env python3
"""PUBLIC COPY of review/joint/numerics-end-to-end/e2e_k3.py with relative paths (added for the release; the original
ships unchanged). Changes, and only these: (1) the folder of e2e.py, consts.py and samples_dps60.json is taken from the
environment variable C5GD_E2E_DIR (default: review/joint/numerics-end-to-end of this package) instead of this file's
folder; (2) the 430-digit K3 is read from ROOT/../LRI_C5_d3/wf_K3/K3_value.json (the sibling package GFF/code/LRI_C5_d3)
instead of an absolute path; (3) samples_dps60.json is opened in that folder instead of the working directory.
Original docstring follows.

K_d from the three-node rule (gdk:threeNodeRule) jets of kjet3.py via gdk:Kr3; K_d via gdk:Ktau from C63d's stored
five-node F points; C5(3) end to end with the three-node K.  usage: e2e_k3_public.py k3_jets.json"""
import json, os, sys
import mpmath as mp
E2E_DIR = os.path.abspath(os.environ.get('C5GD_E2E_DIR') or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'review', 'joint', 'numerics-end-to-end'))
sys.path.insert(0, E2E_DIR)
from e2e import basis, gdk_s, gdk_K, rel, ROOT, gdr_DL, gdr_C5reduced, jet_laurent
from consts import note_values
mp.mp.dps = 72
pi = mp.pi


def laurent(pts, N, r, kmin=-1, kmax=4):
    f = {}
    for j in range(N // 2 + 1):
        p = pts[str(j)]
        f[j] = mp.mpc(p['Re_tR'], p['Im_tR'])
    for j in range(N // 2 + 1, N):
        f[j] = mp.conj(f[N - j])
    return {k: mp.re(mp.fsum(f[j] * mp.expjpi(-2 * mp.mpf(j) * k / N) for j in range(N)) / (N * r ** k))
            for k in range(kmin, kmax + 1)}


refs = json.load(open(os.path.join(ROOT, 'references', 'reference_values.json')))['values']
mb = json.load(open(os.path.join(ROOT, 'K_general', 'position_space', 'K_d_values_mb_D100.json')))['values']
K3 = mp.mpf(json.load(open(os.path.join(ROOT, '..', 'LRI_C5_d3', 'wf_K3', 'K3_value.json')))['K3'])
if len(sys.argv) > 1:
    js = json.load(open(sys.argv[1]))
    N, r = int(js['N']), mp.mpf(js['r'])
    for dk, pts in js['points'].items():
        q = mp.mpf(dk) / 4
        A, R, U, V, X = basis(q)
        s = gdk_s(q)
        L = laurent(pts, N, r)
        K3n = gdk_K(q, L[3])
        lau5, _ = jet_laurent(dk)
        line = ['d=%s three-node:' % dk, 'r-1-1', mp.nstr(L[-1] - 1, 3), 'r0-s0', mp.nstr(L[0] - s[0], 3), 'r1-s1', mp.nstr(L[1] - s[1], 3),
                'r2-s2-1.5U', mp.nstr(L[2] - s[2] - 1.5 * U, 3), '| K3node vs MB', mp.nstr((K3n - mp.mpf(mb[dk]['K'])) / mp.mpf(mb[dk]['K']), 3),
                '| r3(3node) vs r3(5node)', mp.nstr(rel(L[3], lau5[3]), 3)]
        if 'd=' + dk in refs:
            line += ['| vs spectral ref', mp.nstr(rel(K3n, mp.mpf(refs['d=' + dk]['K']['value'])), 3)]
        if dk == '3':
            line += ['| vs K3 (430 dig)', mp.nstr(rel(K3n, K3), 3)]
            S = json.load(open(os.path.join(E2E_DIR, 'samples_dps60.json')))['values']['3']
            nv, _ = note_values(60)
            mp.mp.dps = 72
            d = mp.mpf(3); C = mp.cos(3 * pi / 4)
            f = lambda k: mp.mpf(S[k])
            DL = gdr_DL(C, f('dX0'), f('dXh'), f('dXT'))
            T3 = [mp.mpf(x) for x in S['T3']]; c0 = [mp.mpf(x) for x in S['c0']]
            C5 = gdr_C5reduced(d, nv['3']['P5hp'], K3n, f('X0'), f('Xh'), f('XT'), DL, T3[0], T3[2], c0[0], c0[1], c0[2])
            line += ['| C5(3) three-node K', mp.nstr(C5, 45), 'vs LRI_C5_d3', mp.nstr(rel(C5, nv['3']['C5_d3json']), 3)]
        print(*line)
# gdk:Ktau from C63d's stored F = C<t^2R> - C^2 X^2 points (five-node production)
for dk in ['0.8', '1', '1.25', '1.5', '2', '2.5', '2.75', '3']:
    fn = os.path.join(ROOT, 'K_general', 'R_part', 'prod', 'prod_B_d%s.json' % dk)
    jj = json.load(open(fn))
    N, r = int(jj['N']), mp.mpf(jj['r'])
    pts = {j: dict(Re_tR=p['Re_F'], Im_tR=p['Im_F']) for j, p in jj['points'].items()}
    Lf = laurent(pts, N, r, 0, 3)
    q = mp.mpf(dk) / 4
    A, R, U, V, X = basis(q)
    Ktau = -A * U / 4 + Lf[2] / 4
    print('gdk:Ktau d=%s  [tau^0]F=%s [tau^1]F-1.5U=%s  K vs MB %s' % (dk, mp.nstr(Lf[0], 3), mp.nstr(Lf[1] - 1.5 * U, 3),
          mp.nstr((Ktau - mp.mpf(mb[dk]['K'])) / mp.mpf(mb[dk]['K']), 3)))
