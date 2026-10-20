"""Exact noncommuting finite-matrix Wigner check (not a physical tail claim)."""
from pathlib import Path
from fractions import Fraction as F
import json
ROOT=Path(__file__).resolve().parents[1]

def dot(x,y):return sum((a*b for a,b in zip(x,y)),F())
def mv(A,x):return [dot(row,x) for row in A]
def main():
    dim=5;D=8
    H=[[[F(0) for _ in range(dim)] for _ in range(dim)] for k in range(D+1)]
    for i in range(dim):H[0][i][i]=F(i+1,3)
    for k in range(1,D+1):
        for i in range(dim):
            for j in range(i,dim):H[k][i][j]=H[k][j][i]=F((i+2)*(j+3)+(-1)**k, (k+2)*(i+j+3))
    cases=[]
    for ref in [0,1,3]:
        psi=[[F(0)]*dim for _ in range(D+1)];psi[0][ref]=F(1);E=[H[0][ref][ref]]+[F(0)]*D
        for k in range(1,D+1):
            r=[F(0)]*dim
            for j in range(1,k+1):r=[a+b for a,b in zip(r,mv(H[j],psi[k-j]))]
            E[k]=r[ref]
            for j in range(1,k+1):r=[a-E[j]*b for a,b in zip(r,psi[k-j])]
            for i in range(dim):
                if i!=ref:psi[k][i]=r[i]/(E[0]-H[0][i][i])
        for m in [2,3,4]:
            norm=[F(0)]*(D+1);num=norm.copy()
            for a in range(m+1):
                for b in range(m+1):
                    norm[a+b]+=dot(psi[a],psi[b])
                    for c in range(D+1-a-b):num[a+b+c]+=dot(psi[a],mv(H[c],psi[b]))
            val=[]
            for k in range(D+1):val.append((num[k]-sum((norm[j]*val[k-j] for j in range(1,k+1)),F()))/norm[0])
            upto=min(D,2*m+1);assert val[:upto+1]==E[:upto+1]
            # The next coefficient generally requires the next wavefunction.
            wrong= D>upto and val[upto+1]!=E[upto+1]
            cases.append(dict(reference=ref,wave_degree=m,exact_energy_degree=upto,first_omitted_differs=wrong))
    (ROOT/'results/exact_stationarity.json').write_text(json.dumps(cases,indent=2)+'\n');print('9 exact stationarity cases passed')
if __name__=='__main__':main()
