"""Independent first-quantized evaluation of the eps^4 top-level vacuum pieces.
P8top(L) = -(16/L) sum_{sorted 8-tuples, sum=L-2} w(k) [sum_{|S|=4, N_S even} 1/(N_S+1)]^2
Z(L)     = -(16/(L-1/2)) sum_{sorted 6-tuples, sum=L-2} w(k) [sum_{|T|=3} G_L(N_T)]^2
w(k) = prod u^2 / prod mult!, u_n^2=(1/2)_n/n!,  G_L(s)=sum_{m=s mod 2, s+m<=L-2} u_m^2/(s+m+1)
Y_c = P8top + H_odd(L-1)/36 ; shift = -(Y_c+Z)/243   (g1=1/3)
"""
import numpy as np, itertools, math, sys, json, time
from numba import njit, prange

def u2tab(n):
    u=np.empty(n+1); u[0]=1.
    for k in range(1,n+1): u[k]=u[k-1]*(k-.5)/k
    return u

S8=np.array([sum(1<<i for i in c) for c in itertools.combinations(range(8),4)],dtype=np.int64)
S6=np.array([sum(1<<i for i in c) for c in itertools.combinations(range(6),3)],dtype=np.int64)
FACT=np.array([math.factorial(i) for i in range(9)],dtype=np.float64)

@njit(cache=True)
def wmult(t,k,u2,FACT):
    w=1.
    for i in range(k): w*=u2[t[i]]
    run=1
    for i in range(1,k):
        if t[i]==t[i-1]: run+=1
        else:
            w/=FACT[run]; run=1
    w/=FACT[run]
    return w

@njit(cache=True)
def sub8(t,S8):
    T=0.
    for s in S8:
        N=0
        for i in range(8):
            if (s>>i)&1: N+=t[i]
        if N%2==0: T+=1./(N+1)
    return T

@njit(cache=True)
def sub6(t,S6,G):
    T=0.
    for s in S6:
        N=0
        for i in range(6):
            if (s>>i)&1: N+=t[i]
        T+=G[N]
    return T

@njit(parallel=True,cache=True)
def p8sum(M,u2,S8,FACT):
    # sorted n1<=...<=n8, sum=M ; parallel over n1
    acc=np.zeros(M//8+1)
    for n1 in prange(M//8+1):
        t=np.zeros(8,dtype=np.int64); s=0.
        t[0]=n1
        r1=M-n1
        for n2 in range(n1,r1//7+1):
            t[1]=n2; r2=r1-n2
            for n3 in range(n2,r2//6+1):
                t[2]=n3; r3=r2-n3
                for n4 in range(n3,r3//5+1):
                    t[3]=n4; r4=r3-n4
                    for n5 in range(n4,r4//4+1):
                        t[4]=n5; r5=r4-n5
                        for n6 in range(n5,r5//3+1):
                            t[5]=n6; r6=r5-n6
                            for n7 in range(n6,r6//2+1):
                                t[6]=n7; t[7]=r6-n7
                                w=wmult(t,8,u2,FACT)
                                T=sub8(t,S8)
                                s+=w*T*T
        acc[n1]=s
    return acc

@njit(parallel=True,cache=True)
def p6sum(M,u2,S6,G,FACT):
    acc=np.zeros(M//6+1)
    for n1 in prange(M//6+1):
        t=np.zeros(6,dtype=np.int64); s=0.
        t[0]=n1; r1=M-n1
        for n2 in range(n1,r1//5+1):
            t[1]=n2; r2=r1-n2
            for n3 in range(n2,r2//4+1):
                t[2]=n3; r3=r2-n3
                for n4 in range(n3,r3//3+1):
                    t[3]=n4; r4=r3-n4
                    for n5 in range(n4,r4//2+1):
                        t[4]=n5; t[5]=r4-n5
                        w=wmult(t,6,u2,FACT)
                        T=sub6(t,S6,G)
                        s+=w*T*T
        acc[n1]=s
    return acc

def compute(L):
    M=L-2; u2=u2tab(L+2)
    G=np.zeros(M+1)
    for s in range(M+1):
        G[s]=math.fsum(u2[m]/(s+m+1) for m in range(s%2,M-s+1,2))
    P8=-16./L*math.fsum(p8sum(M,u2,S8,FACT))
    Z=-16./(L-.5)*math.fsum(p6sum(M,u2,S6,G,FACT))
    H=math.fsum(1./e for e in range(1,L,2))
    Yc=P8+H/36
    return dict(L=L,P8top=P8,Z=Z,Hodd=H,Yc=Yc,shift=-(Yc+Z)/243,shift_raw=-(P8+Z)/243)

if __name__=='__main__':
    Ls=[int(x) for x in sys.argv[1:]]
    out={}
    for L in Ls:
        t=time.time(); r=compute(L); r['sec']=time.time()-t
        print(json.dumps(r),flush=True); out[L]=r
