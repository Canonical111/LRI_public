import sys, json, numpy as np
sys.path.insert(0,'pkgref')
from lri_hpc.operators import Space
from lri_hpc.solver import calibrate
out={}
for L in [int(a) for a in sys.argv[1:]]:
    sp=Space(L,11,11,3)
    psi,E,r,g=calibrate(sp,4)
    out[L]={'r':r.tolist(),'g':g.tolist(),'dim':sp.global_dim}
    mine=json.load(open(f'res_L{L}.json'))
    dr=np.max(np.abs(np.array(mine['r_raw'])-r)); dg=np.max(np.abs(np.array(mine['g_raw'])-g))
    print(L,'pkg dim',sp.global_dim,'mine',mine['dim'],'r',r.tolist(),'g',g.tolist(),'max|dr|=%.2e max|dg|=%.2e'%(dr,dg),flush=True)
json.dump(out,open('pkg_cal.json','w'),indent=1)
