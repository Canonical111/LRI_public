import mpmath as mp, sys, time
from emsum import emsum
mp.mp.dps=40
tau=mp.mpf(sys.argv[1]) if len(sys.argv)>1 else mp.mpf(1)
e8=mp.mpf(1)/8
def Phi1(w): return mp.exp(3*mp.loggamma(w+e8)-2*mp.loggamma(w+7*e8)-mp.loggamma(w+e8+tau))
A=lambda k: Phi1(k+5*e8); B=lambda j: Phi1(j+e8)
t=time.time()
T0=emsum(A,0,40); T1=emsum(lambda k:k*A(k),0,40)
print('tails done %.0fs'%(time.time()-t),flush=True)
Jmax=6400
S=[];s=mp.mpf(0);t0,t1=T0,T1
checkpoints={}
for j in range(Jmax):
    Cj=2*t1+(1-2*j)*t0
    s+=B(j)*Cj
    a=A(j); t0-=a; t1-=j*a
    if (j+1) in (400,800,1600,3200,6400): checkpoints[j+1]=+s
Js=sorted(checkpoints)
# Richardson in h=1/J with S(J)=V - sum e_i J^{-2-i}: eliminate J^-2, J^-3, J^-4, J^-5
import itertools
M=mp.matrix([[1]+[-mp.mpf(J)**(-2-i) for i in range(len(Js)-1)] for J in Js])
sol=mp.lu_solve(M,mp.matrix([checkpoints[J] for J in Js]))
print('tau',tau,'partial',mp.nstr(checkpoints[Js[-1]],25),' V(extrap) =',mp.nstr(sol[0],25),' %.0fs'%(time.time()-t))
M2=mp.matrix([[1]+[-mp.mpf(J)**(-2-i) for i in range(len(Js)-2)] for J in Js[1:]])
sol2=mp.lu_solve(M2,mp.matrix([checkpoints[J] for J in Js[1:]]))
print('   alt extrap',mp.nstr(sol2[0],25),' diff',mp.nstr(sol[0]-sol2[0],3))
