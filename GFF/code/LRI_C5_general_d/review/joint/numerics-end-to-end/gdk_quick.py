import json, os, sys
import mpmath as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import e2e
from e2e import *
mp.mp.dps = 60
refs = json.load(open(os.path.join(e2e.ROOT, 'references', 'reference_values.json')))['values']
for dk in ['0.8', '1', '1.25', '1.5', '2', '2.5', '2.75', '3']:
    d = mp.mpf(dk); q = d / 4
    A, R, U, V, X = basis(q)
    sB = gdk_s(q); sT, sm1 = gdk_s_taylor(q)
    lau, js = jet_laurent(dk)
    Kj = gdk_K(q, lau[3]); Kt = gdk_K(q, mp.mpf(GDK_TABLE[dk][1])); Kmb = mp.mpf(GDK_TABLE[dk][0])
    out = [dk, 'Bell/Taylor', mp.nstr(max(rel(sB[i], sT[i]) for i in range(4)), 3), 'r-1', mp.nstr(lau[-1]-1, 3),
           'r0-s0', mp.nstr(lau[0]-sB[0], 3), 'r1-s1', mp.nstr(lau[1]-sB[1], 3), 'r2-s2-1.5U', mp.nstr(lau[2]-sB[2]-1.5*U, 3),
           'r3jet/r3tab', mp.nstr(rel(lau[3], mp.mpf(GDK_TABLE[dk][1])), 3), 'Kjet/KprodB', mp.nstr(rel(Kj, mp.mpf(js['K_d'])), 3),
           'Ktab/Kmb', mp.nstr(rel(Kt, Kmb), 3)]
    if 'd=' + dk in refs:
        Kr = mp.mpf(refs['d=' + dk]['K']['value'])
        out += ['Kjet/ref', mp.nstr(rel(Kj, Kr), 3), 'Ktab/ref', mp.nstr(rel(Kt, Kr), 3), 'Kmb/ref', mp.nstr(rel(Kmb, Kr), 3)]
    print(*out)
