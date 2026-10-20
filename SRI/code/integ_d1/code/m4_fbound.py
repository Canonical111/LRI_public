"""Per-sector f_3_0_1 contribution and first-order roundoff estimate eps * |R . Gamma * B| from engine outputs
written with -bound 1 (pilot analysis helper).
usage: python m4_fbound.py OUTPUT...  (paths relative to the repository root or absolute)"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
src=open(os.path.join(HERE, 'm4_pilot_analyze.py')).read().split("grids = sorted")[0].replace("pdir, stride = sys.argv[1], int(sys.argv[2])", "pdir, stride = 'x', 100")
exec(src)
from cluster_assemble import read_out
import mpmath as mp
def fbound(sec):
    """sum_e |R_e| sum_j sum_ea |Lg_j[e-ea]| B(1,j,ea) * fac"""
    B=sec['B']; wt=fac[sec['pat']]; tot=mp.mpf(0)
    for e,r in R.items():
        for (k,j,ea),v in B.items():
            if k==1 and (e-ea) in Lg[j]: tot+=abs(r)*abs(Lg[j][e-ea])*v*wt
    return tot
if __name__=='__main__':
    fs=sys.argv[1:]
    vals=[]
    for fn in fs:
        h,secs=read_out(fn)
        for s,sec in secs.items():
            vals.append((s, contrib(sec)[0], fbound(sec) if 'B' in sec else None))
    for v in vals: print(v[0], mp.nstr(v[1],15), 'eps*bound', mp.nstr(v[2]*mp.mpf(2)**-53,3) if v[2] is not None else '-')
    if len(vals)==2: print('diff', mp.nstr(vals[0][1]-vals[1][1],3))
