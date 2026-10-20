import itertools, math, fractions
pairs=list(itertools.combinations(range(4),2))
D=[3,3,4,4]
sol=[]
for vals in itertools.product(range(5),repeat=6):
 deg=[0]*4
 for (i,j),m in zip(pairs,vals):deg[i]+=m;deg[j]+=m
 if deg!=D:continue
 reach={0}
 while True:
  new=reach|{j for (i,j),m in zip(pairs,vals) if m and i in reach}|{i for (i,j),m in zip(pairs,vals) if m and j in reach}
  if new==reach:break
  reach=new
 if len(reach)!=4:continue
 M={p:m for p,m in zip(pairs,vals)}
 swap=[0,1,3,2]
 swapped=tuple(M[tuple(sorted((swap[i],swap[j])))] for i,j in pairs)
 if vals>swapped:continue
 weight=fractions.Fraction(1 if vals==swapped else 2,2*math.prod(math.factorial(m) for m in vals))
 print(vals,'weight',weight)
