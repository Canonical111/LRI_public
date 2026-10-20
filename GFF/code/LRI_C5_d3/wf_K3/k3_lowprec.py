import mpmath as mp, time, sys
from kres import consts, spin
from ktail import Ktail
mp.mp.dps=int(sys.argv[1]); L=int(sys.argv[2]); K=int(sys.argv[3])
c=consts(mp.mpf(3)/4)
t0=time.time()
head=mp.fsum((2*l+1)*spin(c,l) for l in range(L))
t1=time.time()
tl,F=Ktail(L,K)
K3=-c['A']*c['U']/4+head+tl
ref=mp.mpf('1.1485946495271793365566463108106731876338481')
print('L',L,'K',K,'K3 =',mp.nstr(mp.re(K3),mp.mp.dps-3),' diff ref',mp.nstr(mp.re(K3)-ref,3),' F0,F1 (should vanish):',mp.nstr(abs(F[0]),3),mp.nstr(abs(F[1]),3),' head %.0fs tail %.0fs'%(t1-t0,time.time()-t1))
