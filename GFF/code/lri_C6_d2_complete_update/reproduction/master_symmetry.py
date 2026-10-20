import json,itertools
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
root=Path(__file__).parent;rows=json.load(open(root/'position_reduction.json'))
P5=list(itertools.combinations(range(5),2));idx={e:i for i,e in enumerate(P5)}
perms=[tuple(idx[tuple(sorted((p[i],p[j])))]for i,j in P5)for p in itertools.permutations(range(5))]
def add(*p):return (sum(x[0]for x in p),sum(x[1]for x in p))
def neg(p):return tuple(-x for x in p)
def complete(ps):
 a,b,c,d,e=ps
 return [add((3,0),*map(neg,ps)),a,c,add(b,d,e,(-1,0)),b,d,add(a,c,e,(-1,0)),e,add((2,0),neg(a),neg(b),neg(e)),add((2,0),neg(c),neg(d),neg(e))]
def selberg(ps):
 lam=complete(ps)
 for pm in perms:
  a,b,c,d,e=[lam[pm[i]]for i in[1,4,2,5,7]]
  if a==c and b==d:return a,b,e
 return None
counts=Counter();nsy=[];allmast={};examples={}
for r in rows:
 if r['size']!=2:continue
 n=0
 for t,qs in r['factors']:
  if t=='J':
   ps=[tuple(F(x)for x in p)for p in qs]
   sb=selberg(ps);sig=tuple(ps);allmast[sig]=sb
   if not sb and all(p!=(0,0)for p in ps): n+=1;nsy.append((r['id'],ps));examples[r['id']]=ps
 r['nonsymmetric_master_count']=n
 if r['remaining']:counts[(r['id'][1],bool(n),r['power'])]+=1
print(counts)
print('unique masters',len(allmast),'nonsym',sum(v is None for v in allmast.values()))
print('nonsym examples',nsy[:8])
(root/'position_reduction_selberg.json').write_text(json.dumps(rows,indent=2))
(root/'master_list.json').write_text(json.dumps([{'p':[[str(x)for x in p]for p in k], 'selberg':[[str(x)for x in p]for p in v]if v else None}for k,v in allmast.items()],indent=2))
