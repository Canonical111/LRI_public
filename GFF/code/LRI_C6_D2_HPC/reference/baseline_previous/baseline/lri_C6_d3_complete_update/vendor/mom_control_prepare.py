import json,math,numpy as np
from pathlib import Path
W=Path(__file__).parent;B=W/'lri_C6_d2_two_forest_update'

def parse(p):
 it=iter(p.read_text().split());L=int(next(it));N=int(next(it));gs=[]
 for k in range(N):
  gid=int(next(it));wa=float(next(it));wb=float(next(it));M=int(next(it));T=int(next(it));edges=[int(next(it))for _ in range(4*L)];masks=[int(next(it))for _ in range(M)];terms=[]
  for _ in range(T):
   n=int(next(it));terms.append(([int(next(it))for _ in range(n)],[int(next(it))for _ in range(2*L)]))
  gs.append(dict(id=gid,wa=wa,wb=wb,edges=edges,masks=masks,terms=terms))
 return L,gs

def write(p,L,gs):
 with open(p,'w')as f:
  print(L,len(gs),file=f)
  for g in gs:
   print(g['id'],g['wa'],g['wb'],len(g['masks']),len(g['terms']),file=f);print(*g['edges'],file=f);print(*g['masks'],file=f)
   for ids,co in g['terms']:print(len(ids),*ids,*co,file=f)
