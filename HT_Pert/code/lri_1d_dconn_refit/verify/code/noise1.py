import numpy as np, math
from myload import *
D=load()
th,c8,s10C,dC=D['th'],D['c8'],D['s10C'],D['dC678']
# input checks
mx={6:0,7:0,8:0}
for L in range(46,73,2):
    for k in (6,7,8):
        mx[k]=max(mx[k],abs(s10C[L][k]-c8[L][k]-dC[L][k]))
print('CSV dC == S10 C - lri_c8 raw: maxabs',mx)
m4=max(abs(s10C[L][4]-c8[L][4]-D['rc'][L]['dC4_Dconn']) for L in range(46,73,2))
m5=max(abs(s10C[L][5]-c8[L][5]-D['rc'][L]['dC5_Dconn']) for L in range(46,73,2))
m4t=max(abs(s10C[L][4]-th[L][4]-D['rc'][L]['dC4_Dconn']) for L in range(46,73,2))
m5t=max(abs(s10C[L][5]-th[L][5]-D['rc'][L]['dC5_Dconn']) for L in range(46,73,2))
print('dC4,dC5 (S10-lri_c8 raw) vs reconciled at 46..72:',m4,m5,' using thermal_d7 raw:',m4t,m5t)
m03=max(abs(s10C[L][k]-c8[L][k]) for L in range(46,73,2) for k in range(4))
print('C0..C3 S10 vs lri_c8:',m03)
# same at L<=44
m4a=max(abs(s10C[L][4]-c8[L][4]-D['rc'][L]['dC4_Dconn']) for L in range(10,45,2))
m5a=max(abs(s10C[L][5]-c8[L][5]-D['rc'][L]['dC5_Dconn']) for L in range(10,45,2))
print('L<=44: dC4,dC5 S10-lri_c8 vs reconciled:',m4a,m5a)
print('thermal_d7 - lri_c8 at 46..72 (C4..C7) maxabs:',[max(abs(th[L][k]-c8[L][k]) for L in range(46,73,2)) for k in (4,5,6,7)])
print()
print('fd noise estimates (min over diff order k of rms(D^k)/sqrt(C(2k,k)))')
def rep(name,f,Ls):
    y=[f(L) for L in Ls]
    e=fd_noise(y)
    kbest=min(e,key=e.get)
    return '%-26s L=%d..%d best %.2e (k=%d)  [%s]'%(name,Ls[0],Ls[-1],e[kbest],kbest,' '.join('%d:%.1e'%(k,v) for k,v in e.items()))
for k in (4,5,6,7,8):
    for Ls in (list(range(16,45,2)),list(range(30,45,2)),list(range(46,73,2)),list(range(30,73,2))):
        print(rep('dC%d (S10-c8raw / recon)'%k,(lambda L,k=k: dC[L][k] if k>=6 or L<=44 else (s10C[L][k]-c8[L][k])),Ls))
        print(rep('S10 C%d'%k,(lambda L,k=k: s10C[L][k]),Ls))
        print(rep('lri_c8 raw C%d'%k,(lambda L,k=k: c8[L][k]),Ls))
        if k<8: print(rep('thermal_d7 C%d'%k,(lambda L,k=k: th[L][k]),Ls))
    print()
