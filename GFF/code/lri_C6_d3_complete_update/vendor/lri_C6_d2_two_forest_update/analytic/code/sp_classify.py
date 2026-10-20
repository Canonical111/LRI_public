"""Massless two-terminal series-parallel reductions, d=2, rational edge indices.
Degree-four vertices carry no external momentum. Every degree-two vertex is
chosen as a momentum terminal; reductions with an internal infrared-borderline
line are rejected. Counterterms are checked separately.
"""
from fractions import Fraction as F
from collections import Counter
from functools import lru_cache
import itertools, json, math
from pathlib import Path
import networkx as nx
ROOT=Path(__file__).resolve().parents[2]
inv=json.load(open(ROOT/'classified_inventory.json'))

def canon(edges):
 es=tuple(sorted(tuple(sorted(e)) for e in edges));return canonical(es)
@lru_cache(None)
def canonical(es):
 vs=sorted({v for e in es for v in e}); degrees=Counter(v for e in es for v in e); M=Counter(es)
 parts={}
 for v in vs:parts.setdefault(degrees[v],[]).append(v)
 best=None
 for pp in itertools.product(*(itertools.permutations(parts[d])for d in sorted(parts))):
  p=sum((tuple(x)for x in pp),());key=tuple(M[tuple(sorted((p[i],p[j])))]for i in range(len(vs))for j in range(i+1,len(vs)))
  if best is None or key<best:best=key
 return len(vs),best

def reduction(edges):
 degrees=Counter(v for e in edges for v in e); verts=sorted(degrees)
 ext=[v for v in verts if degrees[v]<4]; required={v for v in verts if degrees[v]==2}
 for terminals in itertools.combinations(ext,2):
  if not required<=set(terminals):continue
  E=[(min(a,b),max(a,b),F(1,2),F(1,4))for a,b in edges]; gam=Counter();trace=[];safe=True
  while len(E)>1:
   groups={}
   for a,b,x,y in E:groups.setdefault((a,b),[]).append((x,y))
   parallel=next((k for k,vals in groups.items()if len(vals)>1),None)
   if parallel is not None:
    vals=groups[parallel]; n=len(vals); beta=(sum(x for x,y in vals)-(n-1),sum(y for x,y in vals))
    for x,y in vals:gam[(1-x,-y)]+=1;gam[(x,y)]-=1
    gam[beta]+=1;gam[(1-beta[0],-beta[1])]-=1
    E=[e for e in E if e[:2]!=parallel]+[(*parallel,*beta)]
    trace.append(('parallel',parallel,vals,beta));continue
   adj={}
   for i,(a,b,x,y)in enumerate(E):adj.setdefault(a,[]).append(i);adj.setdefault(b,[]).append(i)
   v=next((v for v,idx in adj.items()if len(idx)==2 and v not in terminals),None)
   if v is None:break
   i,j=adj[v];e1,e2=E[i],E[j];a=e1[1]if e1[0]==v else e1[0];b=e2[1]if e2[0]==v else e2[0]
   beta=(e1[2]+e2[2],e1[3]+e2[3]);E=[e for k,e in enumerate(E)if k not in (i,j)]
   if a==b:safe=False;break
   if beta[0]>=1 and E:safe=False;break
   E.append((min(a,b),max(a,b),*beta));trace.append(('series',v,beta))
  if len(E)==1 and safe:
   if E[0][2:]!=(F(0),F(len(edges),4)):raise RuntimeError(('wrong final index',E))
   gam={k:v for k,v in gam.items()if v}
   if any(x.denominator not in (1,2)or (x.denominator==1 and x<=0 and y==0)for x,y in gam):continue
   return {'terminals':terminals,'gamma':tuple(sorted((x,y,int(v))for (x,y),v in gam.items())),'trace':trace}
 return None

def serialize(r):
 return {'terminals':r['terminals'],'gamma':[[str(x),str(y),v]for x,y,v in r['gamma']],'trace':str(r['trace'])}

if __name__=='__main__':
 out=[]
 for row in inv['loops']:
  L=row['loop'];d=[];cnt=Counter()
  for g in row['graphs']:
   r=reduction(g['edges']);cnt['total']+=1
   if r is not None:
    cnt['SP']+=1;cnt['SP_power' if g['power_subgraphs']else 'SP_no_power']+=1
    d.append({'id':g['id'],'edges':g['edges'],'weight4':g['weight4'],'weight2':g['weight2'],'power_subgraphs':g['power_subgraphs'],**serialize(r)})
  print(L,dict(cnt),flush=True);out.append({'loop':L,'counts':dict(cnt),'graphs':d})
 p=Path(__file__).resolve().parents[1]/'verification/sp_inventory.json';p.write_text(json.dumps(out,indent=2))
