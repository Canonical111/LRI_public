from itertools import combinations, permutations
from fractions import Fraction
from math import factorial, prod
import json

def enumerate_graphs(n):
    pairs=list(combinations(range(n),2)); deg=[3,3]+[4]*(n-2)
    vals=[0]*len(pairs); allsol=[]
    def step(k):
        if k==len(pairs):
            if any(deg):return
            reach={0}
            while True:
                new=reach|{j for (i,j),m in zip(pairs,vals) if m and i in reach}|{i for (i,j),m in zip(pairs,vals) if m and j in reach}
                if new==reach:break
                reach=new
            if len(reach)==n:allsol.append(tuple(vals))
            return
        i,j=pairs[k]
        for m in range(min(3,deg[i],deg[j])+1):
            deg[i]-=m;deg[j]-=m;vals[k]=m
            if all(not deg[v] or any(v in p for p in pairs[k+1:]) for v in range(n)):step(k+1)
            deg[i]+=m;deg[j]+=m
    step(0)
    perms=[(a,b)+r for a,b in ((0,1),(1,0)) for r in permutations(range(2,n))]
    def trans(x,p):
        M=dict(zip(pairs,x));return tuple(M[tuple(sorted((p[i],p[j])))] for i,j in pairs)
    groups={}
    for v in allsol:
        canon=min(trans(v,p) for p in perms)
        groups.setdefault(canon,[]).append(v)
    result=[]
    for i,(v,orbit) in enumerate(sorted(groups.items())):
        w=Fraction(len(orbit),factorial(n-2)*prod(factorial(m) for m in v))
        result.append(dict(index=i+1,edges=v,weight=str(w),orbit=len(orbit),distinct_degrees=[sum(bool(m) for p,m in zip(pairs,v) if j in p) for j in range(n)]))
    return result
if __name__=='__main__':
    for n in (2,3,4,5):
        print('n',n)
        result=enumerate_graphs(n)
        for r in result:print(r)
        with open(f'graphs_n{n}.json','w') as f:json.dump(result,f,indent=2)
