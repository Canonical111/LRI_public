"""Exact full-period polynomial source aggregation; no integral is evaluated here.
Unlike the general rational combiner, this accepts only polynomials.  All
input/output hashes and complete source coverage are retained.
"""
from pathlib import Path
from fractions import Fraction as F
from functools import lru_cache
import ast,json,hashlib,time,sys
ROOT=Path(__file__).resolve().parent.parent

def add(a,b,sgn=1):
 c=a.copy()
 for m,v in b.items():
  cv=c.get(m,F(0))+sgn*v
  if cv:c[m]=cv
  else:c.pop(m,None)
 return c

def mul(a,b):
 out={}
 for ma,ca in a.items():
  for mb,cb in b.items():
   d=dict(ma)
   for k,n in mb:d[k]=d.get(k,0)+n
   m=tuple(sorted(d.items()));v=out.get(m,F(0))+ca*cb
   if v:out[m]=v
   else:out.pop(m,None)
 return out
@lru_cache(maxsize=30000)
def parse(text):
 def ev(n):
  if isinstance(n,ast.Constant) and isinstance(n.value,int):return {():F(n.value)} if n.value else {}
  if isinstance(n,ast.Name):
   assert n.id=='r' or n.id in ('Z2','Z3','Z4','Z5','Z6'),n.id
   return {((n.id,1),):F(1)}
  if isinstance(n,ast.UnaryOp):return {m:(-c if isinstance(n.op,ast.USub) else c) for m,c in ev(n.operand).items()}
  if isinstance(n,ast.BinOp):
   a=ev(n.left);b=ev(n.right)
   if isinstance(n.op,ast.Add):return add(a,b)
   if isinstance(n.op,ast.Sub):return add(a,b,-1)
   if isinstance(n.op,ast.Mult):return mul(a,b)
   if isinstance(n.op,ast.Div):
    assert set(b)=={()},('not polynomial',text)
    return {m:v/b[()] for m,v in a.items()}
   if isinstance(n.op,ast.Pow):
    assert set(b)<={()} and b.get((),0).denominator==1
    k=int(b.get((),0));assert k>=0;out={():F(1)}
    for _ in range(k):out=mul(out,a)
    return out
  raise ValueError(ast.dump(n))
 return tuple(ev(ast.parse(text.replace('^','**'),mode='eval').body).items())

def text_poly(p):
 out=''
 for m,c in sorted(p.items()):
  if not c:continue
  term=str(abs(c))+''.join('*'+v+('**'+str(n) if n>1 else '') for v,n in m)
  out+=(' - ' if c<0 else (' + ' if out else ''))+term
 return out.strip() or '0'

def main():
 manifest=json.loads((ROOT/'data/XE_final_plan.json').read_text());out={};records=[];st=time.time()
 for rec in manifest['evaluation_folders']:
  folder=ROOT/rec
  fp=folder/'growth_stage5.jsonl';rp=folder/'growth_stage5_report.json'
  assert fp.is_file() and rp.is_file(),fp
  r=json.loads(rp.read_text());assert r['complete']
  assert hashlib.sha256(fp.read_bytes()).hexdigest()==r['output_sha256']
  count=0
  for line in fp.open():
   ww,ll,c=json.loads(line);assert not any(ww[:-1]);key=(tuple(map(int,ww[-1])),tuple(sorted(ll)));count+=1
   pol=out.setdefault(key,{})
   for m,v in parse(c):
    cv=pol.get(m,F(0))+v
    if cv:pol[m]=cv
    else:pol.pop(m,None)
   if not pol:out.pop(key,None)
  records.append({'file':str(fp),'sha256':r['output_sha256'],'rows':count})
  print('ADDED',folder.name,count,len(out),'seconds',time.time()-st,flush=True)
 dest=ROOT/'XE_growth_total';dest.mkdir(exist_ok=True);path=dest/'stage5.jsonl';tmp=path.with_suffix('.tmp')
 with tmp.open('w') as f:
  for (w,ll),p in sorted(out.items()):f.write(json.dumps([[[],[],[],[],[],list(map(str,w))],list(ll),text_poly(p)],separators=(',',':'))+'\n')
 tmp.replace(path)
 report={'complete':True,'source_chunks':len(records),'inputs':records,'input_rows':sum(r['rows'] for r in records),'output_rows':len(out),'output_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'all_constant_periods_retained':True,'seconds':time.time()-st}
 (dest/'assembly.json').write_text(json.dumps(report,indent=2));print('GROWTH_SUM_DONE',len(out),flush=True)
if __name__=='__main__':main()
