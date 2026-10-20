import sys, json, time, numpy as np
sys.path.insert(0, '.')
from indep_ht3d import *
ext = json.load(open('indep_extract.json'))
def pick(x, L, mode):
    for e in ext:
        if e['camp'] in ('grid18','grid18sri') and abs(e['delta']-x)<1e-9 and e['bath_cut']==L:
            if (mode=='window' and e['window']=='vacuum') or (mode=='raw' and e['window']!='vacuum'):
                return e
L = int(sys.argv[1]); mode = sys.argv[2]; Ks = [int(k) for k in sys.argv[3].split(',')]
for x in (0.7499, 0.7, 0.6, 0.55, 0.518149):
    e = pick(x, L, mode)
    if e is None: print('missing', x); continue
    t = time.time(); m = Model(L, x)
    for K in Ks:
        s = m.solve(e['r'], e['g'], K=K, window=(mode=='window'), nroots=3)
        print(f"x={x:<8} L={L} {mode:6} K={K:3d} r={e['r']:.6f} g={e['g']:.6f} | sigma {s['odd'][0]-x:+.2e} chi {s['odd'][1]-(3-x):+.2e} | "
              f"D_th indep {s['even'][1]:.12f} pkg {e['Delta_thermal']:.12f} diff {s['even'][1]-e['Delta_thermal']:+.2e} | tail {max(s['tail'].values()):.1e} {time.time()-t:.1f}s", flush=True)
