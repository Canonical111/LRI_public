import mpmath as mp, time, sys
from kres import consts, spin
for dps in map(int,sys.argv[1:]):
    mp.mp.dps=dps
    c=consts(mp.mpf(3)/4)
    t=time.time();v=spin(c,7,verbose=True);print(dps,mp.nstr(v,20),'%.1fs'%(time.time()-t),flush=True)
