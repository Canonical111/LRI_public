"""Exact third and fourth integrations of a disjoint weighted P6 source bucket."""
from pathlib import Path
import json,sys,hashlib,time,os
from fractions import Fraction as F
import full_boundary as b
import linear_boundary as lb
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'C8_full_numerical_completion/code'))
import period_algebra as pa
r=b.ROOT

def scalar_terms(c):
 # After partial fractions all remaining variables must be constant periods.
 pp=pa.parse_expr(str(c));return pp

def terminal(src,dest):
 start=time.time();out={};n=0;count=0;scalars={}
 def add_word(w,ll,mon,c):
  key=(w,ll,mon);v=out.get(key,F(0))+c
  if v:out[key]=v
  else:out.pop(key,None)
 for line in src.open():
  ww,ll,cs=json.loads(line);assert not any(ww[:-1]);ll=tuple(sorted(ll))
  if 1 in ll:continue
  w=tuple(F(str(b.rm.parseK(t))) for t in ww[-1]);R=b.rm.parseK(cs)
  pol,po=b.apart(R,4)
  for kind,a,p,c in [('poly',0,p,c) for p,c in pol.items()]+[('pole',F(str(a)),p,c) for (a,p),c in po.items()]:
   text=str(c)
   if text not in scalars:scalars[text]=scalar_terms(c)
   cp=scalars[text]
   for tail,v in lb.functional(kind,a,p,w,5,0,True):
    for mon,co in cp.items():add_word(tail,ll,mon,v*co)
   count+=1
  n+=1
  if n%500==0:print('TERM',n,len(out),count,time.time()-start,flush=True)
 raw=dest.with_suffix('.words.jsonl');tmp=raw.with_suffix('.tmp')
 with tmp.open('w') as f:
  for (w,ll,mon),c in out.items():f.write(json.dumps([[str(t) for t in w],ll,mon,str(c)],separators=(',',':'))+'\n')
 tmp.replace(raw)
 poly={}
 for (w,ll,mon),c in out.items():
  p=pa.R(w)
  for k in ll:p=pa.mul(p,pa.log(k))
  if mon:p=pa.mul(p,{mon:F(1)})
  pa.add(poly,p,c)
 dest.write_text(pa.dump(poly))
 report={'complete':True,'input_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'input_rows':n,'basis':count,'raw_word_terms':len(out),'period_terms':len(poly),'rational_projection':str(poly.get((),F(0))),'seconds':time.time()-start,'full_constant_periods':True}
 dest.with_suffix('.report.json').write_text(json.dumps(report,indent=2));print('DONE_TERMINAL',report,flush=True)

def main():
 i=int(sys.argv[1]);folder=r/'weighted_s2';src=folder/f'bucket{i:03}.jsonl';dst=r/'weighted_final'/f'b{i:03}';dst.mkdir(parents=True,exist_ok=True)
 st3=dst/'stage3.jsonl'
 if not st3.exists():
  rows=b.load(src);ans=b.one_stage(rows,3,4,6);b.dump(st3,ans);del rows,ans;b.clear()
 if not (dst/'finite.report.json').exists():terminal(st3,dst/'finite.expr')
if __name__=='__main__':main()
