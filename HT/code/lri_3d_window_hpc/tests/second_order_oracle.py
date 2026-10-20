"""Independent second-order oscillator-shell sums for the mode regulator.

No many-body matrix, rotational projector, or quartic graph enumeration is used.
Normal-ordered zero-mode transitions and the scalar part of the sphere covariance
supply all coefficients. Raw thermal coefficients are assembled before summing.
"""
import math,json
from fractions import Fraction as F
import numpy as np

def rational_shells(L,x=F(3,4)):
    top=L//2;h=[]
    for j in range(5):
        a=[F(1)];alpha=j*x
        for m in range(top):a.append(a[-1]*(alpha+m)*(alpha-F(1,2)+m)/((F(3,2)+m)*(m+1)))
        h.append(a)
    terms=[]
    for m in range(top+1):
        total=F(0)
        for p,weight in [(2,F(1)),(1,-F(1)),(3,-F(1,3)),(0,F(1,3))]:
            for k in range(5):
                shell=sum((-1)**(k-j)*math.comb(k,j)*h[j][m] for j in range(k+1))*math.factorial(k)
                if not shell:continue
                r=4-k
                for a in range(min(r,p)+1):
                    p2=p+r-2*a
                    den=-2*m-x*(k+p2-p)
                    if den==0:continue
                    amp2=F(math.comb(4,k)**2*math.comb(r,a)**2*math.factorial(p)*math.factorial(p2),math.factorial(p-a)**2*144)
                    total+=weight*amp2*shell/den/9
        terms.append(total)
    return terms

def C2(L):return float(sum(rational_shells(L)))

if __name__=='__main__':
    for L in (2,4,6,8,10,12,20,40,80):print(L,C2(L))
