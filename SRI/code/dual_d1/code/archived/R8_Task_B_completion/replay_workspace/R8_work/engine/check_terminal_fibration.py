"""Actual eight-kink rows: moving final functional versus full fixed-word fibration."""
import json,time,hashlib,math
from fractions import Fraction as Q
from pathlib import Path
import scaled_b as sb
from hyperlog_core import *
ROOT=sb.ROOT;tp=sb.tp

def ordinary(items,n):
 N=n-2
 out=sb.tb.one_stage(items,N-1,N)
 total=Q(0);neg=[Q(0)]*6
 demands=[(p,r) for p in [-3,-2,-1] for r in (0,1)]
 for (words,logs),co in out.items():
  assert not logs and not any(words[:-1])
  w=tuple(Q(str(a)) for a in words[-1]);num,den=sb.rparts(co,N)
  for kappa,scale,nn in [(0,Q(1),num),(1,Q(-(n-1)),num),(1,Q(-1),(Q(0),)+num)]:
   total+=scale*tp.normalized_functional(nn,den,w,kappa,n-1,0,0)
   pol,rem=tp.quotient(nn,den)
   for j,(p,r) in enumerate(demands):
    for m in range(r,len(w)+2):
     b=sum(c*tp.poly_functional(k,w,kappa,n-1,p,m) for k,c in enumerate(pol) if c)
     neg[j]+=scale*b*Q(math.factorial(m),(-p)**(m-r+1))
 return total,neg,len(out)

def main():
 st=time.time();checks=[]
 for block in ['n8_f1_b00','n8_f1_b04','n8_f2_b03','n8_f3_b02','n8_f4_b02']:
  path=sb.OUT/block/'stage4.jsonl'
  if not path.exists():raise RuntimeError(path)
  raw=path.read_text().splitlines()
  # Select an actual longest-word row and a row without that restriction.
  lens=[sum(map(len,json.loads(line)[0])) for line in raw]
  inds=list(dict.fromkeys([0,lens.index(max(lens))]))
  for i in inds:
   ww,ll,cs=json.loads(raw[i]);assert ll==0
   row=((tuple(tuple(sb.tb.br.rr.rm.parseK(s) for s in w) for w in ww),()),sb.tb.br.rr.rm.parseK(cs))
   a,ct,an=sb.last_two_scaled([row],8)
   b,bn,nrows=ordinary([row],8)
   assert a==b and an==bn,(block,i,a,b,an,bn)
   d={'block':block,'row_index':i,'input_word_weight':lens[i],'source_line_sha256':hashlib.sha256(raw[i].encode()).hexdigest(),'moving_value':str(a),'ordinary_value':str(b),'negative_coefficients_equal':True,'ordinary_rows':nrows}
   checks.append(d);print('EXACT_TERMINAL',d,'elapsed',time.time()-st,flush=True)
   sb.tb.br.rr.clear();sb.mt.clear();tp.clear_caches()
 result={'status':'actual_eight_kink_ordinary_fibration_checks_pass','checks':checks,'seconds':time.time()-st}
 (ROOT/'terminal_fibration_checks.json').write_text(json.dumps(result,indent=2));print('ALL_PASS',flush=True)
if __name__=='__main__':main()
