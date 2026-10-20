from jan import *
T=ld('o7')
STAT={4:1e-3,5:0.03,6:1.0,7:100.}  # placeholder, replaced below if found
import re
src=open('<TMP>/scratchpad/dconn_refit72/joint/code/analyze_r72.py').read()
m=re.search(r'STAT\s*=\s*(\{[^}]*\})',src); STAT=eval(m.group(1)); print('STAT',STAT)
for ds in ('dconn','dconn_w','dconn_s46','dconn_old'):
    for crit in ('w','p'):
        if crit=='p' and ds not in ('dconn',): continue
        base=(T['ds']==ds)&(T['hi']==118)&(T['lo']>=40)&(T['lo']<=70)
        fl={n:(T['flw%d'%n] if crit=='w' else T['flp%d'%n]) for n in range(4,8)}
        ok={n:(fl[n]<=1.5)&(T['dof%d'%n]>=4) for n in range(4,8)}
        out=[]
        for kk in (6,7):
            okk=np.all([ok[n] for n in range(4,kk+1)],axis=0); st=np.all([T['stat%d'%n]<=STAT[n] for n in range(4,kk+1)],axis=0)
            mm=base&okk&st
            out.append('C%d floor+stat %s'%(kk,s(T['miss%d'%kk][mm])))
        hit=base&(np.abs(T['miss4'])<=0.005)&(np.abs(T['miss5'])<=0.2)&(np.abs(T['miss6'])<=1.5)&(np.abs(T['miss7'])<=82)
        nf=hit&np.all([fl[n]<=3 for n in range(4,8)],axis=0)
        print('%-9s crit=%s | %s | hit4567 n=%d nearfloor %d'%(ds,crit,' | '.join(out),hit.sum(),nf.sum()))
