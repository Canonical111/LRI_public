"""Exact QQ-polynomial serialization without per-symbol SymPy printing.
The byte format is tested against the original Frac.__str__; no arithmetic or
integration identity is changed. Denominator factors retain their old ordering.
"""
import factored_field as ff
OLD=ff.Frac.__str__

def polynomial(P):
 if not P:return '0'
 names=tuple(str(a) for a in P.ring.symbols);out=[]
 for k,(powers,c) in enumerate(P.terms()):
  num=int(c.numerator);den=int(c.denominator);negative=num<0;num=abs(num)
  if k:out.append(' - ' if negative else ' + ')
  elif negative:out.append('-')
  pieces=[]
  if not any(powers) or num!=den:pieces.append(str(num) if den==1 else f'{num}/{den}')
  pieces += [name if p==1 else f'{name}**{p}' for name,p in zip(names,powers) if p]
  out.append('*'.join(pieces))
 return ''.join(out)

def text(a):
 if not a.denf:return polynomial(a.numer)
 den='*'.join('('+polynomial(f)+')'+(f'**{m}' if m!=1 else '')
              for f,m in sorted(a.denf.items(),key=lambda x:str(x[0])))
 return '('+polynomial(a.numer)+')/('+den+')'

def install():
 ff.Frac.__str__=text;ff.Frac.__repr__=text

if __name__=='__main__':
 import install_fastq;install_fastq.install_domain()
 import scaled_b as sb
 from hyperlog_core import K,GEN
 import random,time,json,hashlib
 from pathlib import Path
 random.seed(92928);st=time.time();checks=0
 for _ in range(300):
  P=K.ring.zero
  for __ in range(random.randrange(1,50)):
   mon=tuple([0]+[random.randrange(4) for i in range(K.ngens-1)])
   P+=K.ring.from_dict({mon:K.ring.domain(random.randrange(-100,101),random.randrange(1,20))})
  f=K(P)/(1+GEN[3])**random.randrange(4)/(2+GEN[4])**random.randrange(3)
  before=OLD(f);after=text(f);assert before==after,(before,after)
  assert K.from_expr(after)==f
  checks+=1
 # Actual large source coefficients from current production, not just toys.
 actual=[]
 for path in [sb.ROOT/'tail_blocks/A_base/n9_f2_b04/stage3.jsonl',sb.ROOT/'endpoint_odd/EA7_b01/stage5.jsonl']:
  lines=path.read_text().splitlines();selected=list(dict.fromkeys([0,len(lines)//2,len(lines)-1]))
  for i in selected:
   cs=json.loads(lines[i])[2];f=K.from_expr(cs);assert OLD(f)==text(f);assert K.from_expr(text(f))==f
   actual.append({'source':str(path.relative_to(sb.ROOT)),'row':i,'coefficient_characters':len(cs),'exact_bytes_equal':True})
 result={'status':'serializer_matches_original_exactly','random_cases':checks,'actual_coefficients':actual,'seconds':time.time()-st}
 (sb.ROOT/'exact_text_check.json').write_text(json.dumps(result,indent=2));print(result)
