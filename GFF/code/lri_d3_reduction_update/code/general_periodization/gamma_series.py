"""Numerical evaluators for the ordinary hypergeometric values used in d=2.
A Hurwitz-zeta asymptotic tail, and a finite Euler transform, are numerical
acceleration methods only; their residuals are not interval bounds.
"""
import mpmath as mp

def ratio_power_sum(A,B,r,N=96,K=44):
    A=mp.mpc(A);B=mp.mpc(B)
    h=(mp.gamma(A)/mp.gamma(B))**r
    ans=h
    for n in range(1,N):
        h*=((n-1+A)/(n-1+B))**r
        ans+=h
    logs=[mp.mpc(0)]+[r*(-1)**(k+1)*(mp.bernpoly(k+1,A)-mp.bernpoly(k+1,B))/(k*(k+1)) for k in range(1,K+1)]
    ex=[mp.mpc(1)]
    for k in range(1,K+1):
        ex.append(sum(j*logs[j]*ex[k-j] for j in range(1,k+1))/k)
    power=r*(B-A)
    if mp.re(power)<=1:raise ValueError('This summation requires Re[r(B-A)]>1')
    ans+=sum(ex[k]*mp.zeta(power+k,N) for k in range(K+1))
    return ans

def alternating_linear_sum(A,B,r,v,start=20,depth=260):
    A=mp.mpc(A);B=mp.mpc(B);v=mp.mpc(v)
    h=(mp.gamma(A)/mp.gamma(B))**r
    values=[]
    for n in range(start+depth):
        values.append((v+2*n)*h)
        h*=((n+A)/(n+B))**r
    ans=sum((-1)**n*values[n] for n in range(start))
    row=values[start:];fac=mp.mpf('.5');tail=mp.mpc(0)
    while row:
        tail+=row[0]*fac;row=[row[i]-row[i+1] for i in range(len(row)-1)];fac/=2
    return ans+(-1)**start*tail
