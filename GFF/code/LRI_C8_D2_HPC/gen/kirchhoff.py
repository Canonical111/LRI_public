"""A-INV-3(h): exact Fraction check of generated G-files against an independent Kirchhoff evaluation.

Port of reference/power_mass/code/validate_kirchhoff.py (same det/independent/stored arithmetic). The complete
forest kernel of a class is evaluated from its edge list by rational Laplacian minors on contracted forest
blocks (root numerator excluding logarithmic blocks only), independently of the stored masks, and compared with
the kernel stored in the G-file (spanning-tree masks and forest terms) at random rational points: exact
equality is required. Changes from the original: G-file directories and loops are arguments (range(3,9)), the
sample follows PLAN A-INV-3(h) (per sector at L8 the 16 largest M*T plus 48 random kernels, seed 8812; 8 random
kernels per sector at every other loop), each kernel is checked at two random rational points (the second with
three edges scaled by 1e-12, as in the original), and the kernels are spread over a process pool.

Usage: python3 -B gen/kirchhoff.py --stage DIR [--loops 7,8] [--jobs N] [--output FILE]
  DIR holds L{L}_free/ and L{L}_power/ builder outputs (G*.txt and inventory.json)."""
import argparse,sys
from multiprocessing import Pool
from pathlib import Path
from fractions import Fraction as F
import itertools,json,time,random
sys.path.insert(0,str(Path(__file__).resolve().parent))  # gen/regress.py's strict G-file reader (stored)
# Independent determinant evaluation using the graph Laplacian, not polynomial masks.
def det(M):
 n=len(M);A=[list(map(F,r))for r in M];out=F(1)
 for i in range(n):
  k=next((k for k in range(i,n)if A[k][i]),None)
  if k is None:return F(0)
  if k!=i:A[k],A[i]=A[i],A[k];out=-out
  x=A[i][i];out*=x
  for k in range(i+1,n):
   y=A[k][i]/x
   for j in range(i+1,n):A[k][j]-=y*A[i][j]
 return out

def independent(ed,x):
 n=max(max(e)for e in ed)+1;full=(1<<n)-1;E=len(ed);subs=[];logs=set()
 for s in range(1,full):
  vs=[i for i in range(n)if s>>i&1];es=[k for k,(a,b)in enumerate(ed)if s>>a&1 and s>>b&1]
  if len(vs)<2 or len(es)<2*(len(vs)-1):continue
  if any(sum(((s0>>ed[k][0])^(s0>>ed[k][1]))&1 for k in es)<2 for s0 in range(1,full)if s0&s==s0 and s0!=s):continue
  subs.append(s)
  if len(es)==2*(len(vs)-1):logs.add(s)
 cache={}
 def block(P,children):
  pp=list(range(n))
  def root(a):
   while pp[a]!=a:a=pp[a]
   return a
  for c in children:
   r=(c&-c).bit_length()-1
   for i in range(n):
    if c>>i&1:pp[root(i)]=root(r)
  vs=sorted(set(root(i)for i in range(n)if P>>i&1));ids={v:j for j,v in enumerate(vs)};ee=[]
  for k,(a,b)in enumerate(ed):
   if not(P>>a&1 and P>>b&1)or any(c>>a&1 and c>>b&1 for c in children):continue
   ee.append((k,ids[root(a)],ids[root(b)]))
  if not ee:return F(1),[]
  key=tuple(ee)
  if key not in cache:
   M=[[F(0)for _ in vs]for _ in vs]
   for k,a,b in ee:
    v=1/x[k];M[a][a]+=v;M[b][b]+=v;M[a][b]-=v;M[b][a]-=v
   cache[key]=det([row[:-1]for row in M[:-1]])*__import__('math').prod(x[k]for k,a,b in ee)
  return cache[key],[k for k,a,b in ee]
 total=F(0);forests=0
 def emit(ch):
  nonlocal total,forests
  sets=ch+[full];den=F(1);root=[]
  for P in sets:
   children=[c for c in ch if c!=P and c&P==c and not any(c!=z and z!=P and c&z==c and z&P==z for z in ch)]
   d,ids=block(P,children);den*=d
   if P==full:root=[k for k,(aa,bb)in enumerate(ed)if not any(c in logs and c>>aa&1 and c>>bb&1 for c in ch)]
  total+=(-1)**len(ch)*sum(x[k]for k in root)/den;forests+=1
 def rec(ch,possible):
  emit(ch)
  for i,c in enumerate(possible):rec(ch+[c],[z for z in possible[i+1:]if (c&z)==c or (c&z)==z or (c&z).bit_count()<=1])
 rec([],subs)
 return total/sum(x),forests

def stored(g,x,gdir):
 # W4's class (Stage-6 fix round 4, integration): the G-file is read by gen/regress.py's strict reader (gfile_text,
 # parse_gfile), the format the native loader reads (LF, spaces and printable ASCII, plain decimals, the loader's header
 # bounds); before, read_text().split() and int() also took U+00A0 or U+001C separators, '+7', '0_7' and M = T = 0
 # (ValueError now; check() records it as the kernel's failure). The arithmetic is unchanged.
 from regress import gfile_text,parse_gfile
 P=parse_gfile(gfile_text((Path(gdir)/Path(g['file']).name).read_bytes()))
 if P['E']!=len(x):raise ValueError(f"the G-file has E = {P['E']} edges, the point {len(x)} coordinates")
 masks=[int(m)for m in P['lines'][1].split()];mons=[__import__('math').prod(x[j]for j in range(len(x))if mask>>j&1)for mask in masks];v=F(0)
 for line in P['terms']:
  t=[int(z)for z in line.split()];k=t[0];den=sum(mons[i]for i in t[1:1+k]);co=t[1+k:];v+=sum(a*b for a,b in zip(co,x))/den
 return v/sum(x)
SEED=8812
def plan(stage,loops):
 rr=random.Random(SEED);out=[]
 for L in loops:
  for sector in ('free','power'):
   gdir=Path(stage)/f'L{L}_{sector}';gs=[g for g in json.load(open(gdir/'inventory.json')) if g['status']=='finite-kernel']
   if L==8:
    top=sorted(gs,key=lambda g:(-g['masks']*g['terms'],g['id']))[:16];ids={g['id'] for g in top}
    chosen=top+rr.sample(sorted((g for g in gs if g['id'] not in ids),key=lambda g:g['id']),48)
   else:chosen=rr.sample(sorted(gs,key=lambda g:g['id']),min(len(gs),8))
   for g in chosen:
    pts=[[F(rr.randrange(1,12),rr.randrange(1,12))*(F(1,10**12) if scale and j<3 else F(1)) for j in range(2*L)] for scale in (0,1)]
    out.append(dict(L=L,sector=sector,gdir=str(gdir),g=g,points=pts))
 return out
def check(job):
 g=job['g'];t0=time.time();res=[]
 for scale,x in enumerate(job['points']):
  a,n=independent(g['edges'],x)
  try:b=stored(g,x,job['gdir'])
  except ValueError as e:res.append(dict(endpoint_scaled=bool(scale),forests=n,exact_match=False,error=f'malformed G-file: {e}',point=[str(v) for v in x]));continue
  res.append(dict(endpoint_scaled=bool(scale),forests=n,exact_match=a==b,point=[str(v) for v in x]))
 return dict(loop=job['L'],sector=job['sector'],id=g['id'],masks=g['masks'],terms=g['terms'],checks=res,
             exact_match=all(r['exact_match'] for r in res),seconds=round(time.time()-t0,3))
if __name__=='__main__':
 ap=argparse.ArgumentParser(description='A-INV-3(h) exact Kirchhoff check');ap.add_argument('--stage',required=True)
 ap.add_argument('--loops',default='7,8');ap.add_argument('--jobs',type=int,default=1);ap.add_argument('--output')
 a=ap.parse_args();start=time.time();jobs=plan(a.stage,[int(v) for v in a.loops.split(',')])
 jobs.sort(key=lambda j:-j['g']['masks']*j['g']['terms'])
 if a.jobs>1:
  with Pool(a.jobs) as pool:out=pool.map(check,jobs,chunksize=1)
 else:out=list(map(check,jobs))
 bad=[(r['loop'],r['sector'],r['id']) for r in out if not r['exact_match']]
 for r in out:print(r['loop'],r['sector'],r['id'],r['masks'],r['terms'],r['exact_match'],r['seconds'],flush=True)
 rec=dict(schema='c8-d2-gate-1',gate='A-INV-3(h) kirchhoff',passed=not bad and len(out)>0,failures=bad,count=len(out),seed=SEED,
          per_group={f'L{L}_{s}':sum(1 for r in out if r['loop']==L and r['sector']==s) for L in sorted({r['loop'] for r in out}) for s in ('free','power')},
          seconds=time.time()-start,checks=sorted(out,key=lambda r:(r['loop'],r['sector'],r['id'])),
          method='Independent rational Laplacian minors on contracted forest blocks, with root numerator excluding logarithmic blocks only')
 if a.output:Path(a.output).write_text(json.dumps(rec,indent=1))
 print('A-INV-3(h)','PASSED' if rec['passed'] else 'FAILED',len(out),'kernels',bad[:10])
 sys.exit(0 if rec['passed'] else 1)
